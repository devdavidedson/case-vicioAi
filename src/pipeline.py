"""Pipeline de classificacao de topicos.

Passos: carregar -> sugerir candidatos (busca por palavras) -> perguntar ao modelo
(varias vezes, em varios provedores) -> votar -> decidir publicar/revisar/fora.
Nao ha nenhum "while True": todo laco tem limite. Veja a secao "protecoes" no config.json.
"""
import argparse, csv, html, json, math, os, re, sys, time, unicodedata, urllib.request, urllib.error
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
STOP = set("para como pela pelo uma uns umas dos das nos nas com por que sao foi ser tem seu sua ele ela mais mas nao sim sobre entre quando onde apos ate".split())


class LimiteAtingido(Exception):
    """Orcamento de chamadas, custo ou tempo estourou: para tudo."""


# ---------- utilidades ----------
def carregar_env():
    f = RAIZ / ".env"
    if f.exists():
        for linha in f.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokens(s):
    return [t for t in re.findall(r"[a-z0-9]+", norm(s)) if len(t) > 2 and t not in STOP]


def limpar_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))).strip()


def log(pasta, nome, msg):
    with open(pasta / nome, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


# ---------- dados ----------
def texto_alternativas(alt):
    if isinstance(alt, dict):
        return "; ".join(f"{k}) {limpar_html(v)}" for k, v in alt.items())
    if isinstance(alt, list):
        return "; ".join(limpar_html(x if not isinstance(x, dict) else " ".join(map(str, x.values()))) for x in alt)
    return limpar_html(alt)


def carregar_questoes(cfg):
    c = cfg["campos_questao"]
    saida = []
    with open(RAIZ / cfg["arquivos"]["questoes"], encoding="utf-8") as f:
        for n, linha in enumerate(f, 1):
            if not linha.strip():
                continue
            try:
                d = json.loads(linha)
                saida.append({
                    "id": str(d[c["id"]]),
                    "enunciado": limpar_html(d.get(c["enunciado"])),
                    "comando": limpar_html(d.get(c["comando"])),
                    "alternativas": texto_alternativas(d.get(c["alternativas"])),
                    "disciplina": limpar_html(d.get(c["disciplina"])),
                    "assunto": limpar_html(d.get(c["assunto"])),
                })
            except Exception as e:
                print(f"[aviso] linha {n} do jsonl ignorada: {e}")
    return saida


def carregar_temas(cfg):
    caminho = RAIZ / cfg["arquivos"]["temas"]
    amostra = caminho.read_text(encoding="utf-8-sig")[:2000]
    delim = ";" if amostra.count(";") > amostra.count(",") else ","
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=delim))
    tc, temas = cfg["temas"], {}
    if tc.get("hierarquia"):
        for l in linhas:
            partes = [(l.get(c) or "").strip() for c in tc["hierarquia"]]
            partes = [p for p in partes if p]
            if partes:
                tid = " > ".join(partes)
                temas[tid] = {"id": tid, "nome": partes[-1], "caminho": tid}
    else:
        base = {str(l[tc["id"]]).strip(): l for l in linhas}
        for tid, l in base.items():
            nos, atual, vistos = [], tid, set()
            for _ in range(12):  # limite de profundidade: protege contra ciclos
                if atual in vistos or atual not in base:
                    break
                vistos.add(atual)
                nos.append(base[atual][tc["nome"]].strip())
                atual = (base[atual].get(tc.get("pai", ""), "") or "").strip()
            temas[tid] = {"id": tid, "nome": l[tc["nome"]].strip(), "caminho": " > ".join(reversed(nos))}
    return temas


class Indice:
    """Busca simples por palavras (TF-IDF). Pode ser trocada por embeddings."""
    def __init__(self, temas):
        self.toks = {t: set(tokens(v["caminho"])) for t, v in temas.items()}
        df = Counter(w for s in self.toks.values() for w in s)
        n = len(temas)
        self.idf = {w: 1 + math.log(n / c) for w, c in df.items()}

    def candidatos(self, q, k):
        qt = set(tokens(" ".join([q["enunciado"], q["comando"], q["alternativas"]])))
        at = set(tokens(q["assunto"]))
        disc = set(tokens(q["disciplina"]))
        pontos = []
        for tid, s in self.toks.items():
            p = sum(self.idf[w] for w in s & qt) + 2 * sum(self.idf[w] for w in s & at) + len(s & disc)
            pontos.append((p, tid))
        pontos.sort(reverse=True)
        return [t for _, t in pontos[:k]]


# ---------- chamada ao modelo ----------
SISTEMA = ("Voce e um especialista em Direito (Penal, Processo Penal, Legislacao Penal Especial, Criminologia) "
           "classificando questoes de concurso em temas de uma arvore. Escolha o tema MAIS ESPECIFICO que o "
           "enunciado realmente cobre. Se nenhum tema da lista serve, responda fora=true. Nao escolha temas "
           "genericos so porque sao amplos. Responda APENAS com JSON.")


def montar_prompt(q, cands, temas):
    lista = "\n".join(f"{t} | {temas[t]['caminho']}" for t in cands)
    return (f"QUESTAO {q['id']}\nDisciplina de origem: {q['disciplina']}\nAssunto de origem (pode estar errado): {q['assunto']}\n"
            f"Enunciado: {q['enunciado'][:3000]}\nComando: {q['comando']}\nAlternativas: {q['alternativas'][:2000]}\n\n"
            f"TEMAS CANDIDATOS (id | caminho):\n{lista}\n\n"
            'Responda: {"tema_id": "<id da lista ou null>", "fora": <true|false>, "confianca": <0 a 1>, '
            '"extras": ["<ate 2 outros ids da lista relacionados>"], "motivo": "<1 frase>"}')


def extrair_json(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("resposta sem JSON")
    return json.loads(m.group(0))


def chamar(prov, prompt, temperatura, pr, estado, pasta, cands):
    if estado["chamadas"] >= pr["max_chamadas_total"]:
        raise LimiteAtingido("max_chamadas_total")
    if estado["custo"] >= pr["max_custo_usd"]:
        raise LimiteAtingido("max_custo_usd")
    if (time.time() - estado["inicio"]) / 60 >= pr["max_minutos_total"]:
        raise LimiteAtingido("max_minutos_total")
    if prov.get("tipo") == "mock":  # para testar sem gastar nada
        estado["chamadas"] += 1
        return {"tema_id": cands[0], "fora": False, "confianca": 0.85, "extras": cands[1:2], "motivo": "mock"}, 0, 0
    chave = os.environ.get(prov["chave_env"], "")
    if not chave:
        raise LimiteAtingido(f"chave {prov['chave_env']} nao encontrada no .env")
    if "CONFIRMAR" in prov["base_url"] or "CONFIRMAR" in prov["modelo"]:
        raise LimiteAtingido("preencha base_url e modelo do provedor no config.json")
    corpo = json.dumps({"model": prov["modelo"], "temperature": temperatura,
                        "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(prov["base_url"].rstrip("/") + "/chat/completions", data=corpo,
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {chave}"})
    ultimo = None
    for tent in range(1, pr["max_tentativas_por_chamada"] + 1):
        estado["chamadas"] += 1
        try:
            with urllib.request.urlopen(req, timeout=pr["timeout_segundos"]) as r:
                d = json.loads(r.read())
            resp = extrair_json(d["choices"][0]["message"]["content"])
            u = d.get("usage", {})
            return resp, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
        except urllib.error.HTTPError as e:
            ultimo = f"HTTP {e.code}: {e.read()[:200]!r}"
            if e.code in (400, 401, 403, 404):  # repetir nao adianta
                log(pasta, "erros.log", f"[{prov['nome']}] {ultimo}")
                break
        except Exception as e:
            ultimo = repr(e)
        log(pasta, "erros.log", f"[{prov['nome']}] tentativa {tent}: {ultimo}")
        time.sleep(pr["espera_base_segundos"] * 2 ** (tent - 1))
    raise RuntimeError(ultimo)


# ---------- decisao ----------
def decidir(votos, esperados, cl, temas):
    """votos: respostas validas. esperados: quantas deveriam existir (falhas baixam o acordo)."""
    if not votos:
        return {"decisao": "revisar", "tema_id": "", "extras": [], "confianca": 0, "acordo": 0}
    chave = lambda v: "FORA" if v.get("fora") else v["tema_id"]
    cont = Counter(chave(v) for v in votos)
    modal, n = cont.most_common(1)[0]
    acordo = n / max(esperados, 1)
    conf = sum(float(v.get("confianca", 0)) for v in votos if chave(v) == modal) / n
    ok = acordo >= cl["limiar_acordo"] and conf >= cl["limiar_confianca"]
    if modal == "FORA":
        return {"decisao": "fora" if ok else "revisar", "tema_id": "", "extras": [], "confianca": round(conf, 3), "acordo": round(acordo, 3)}
    ex = Counter(e for v in votos for e in (v.get("extras") or []) if e in temas and e != modal)
    extras = [e for e, c in ex.most_common(2) if c >= max(1, n // 2)]
    return {"decisao": "publicar" if ok else "revisar", "tema_id": modal, "extras": extras,
            "confianca": round(conf, 3), "acordo": round(acordo, 3)}


def salvar_csv(caminho, questoes, decisoes, temas, provs):
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "decisao", "tema_id", "tema_nome", "extras", "confianca", "acordo", "provedores"])
        for q in questoes:
            d = decisoes[q["id"]]
            w.writerow([q["id"], d["decisao"], d["tema_id"], temas.get(d["tema_id"], {}).get("caminho", ""),
                        "|".join(d["extras"]), d["confianca"], d["acordo"], "+".join(provs)])


def historico(linha):
    pasta = RAIZ / "comparativos"
    pasta.mkdir(exist_ok=True)
    arq = pasta / "historico.csv"
    novo = not arq.exists()
    with open(arq, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if novo:
            w.writerow(list(linha.keys()))
        w.writerow(list(linha.values()))


# ---------- execucao ----------
def rodar(args):
    carregar_env()
    cfg = json.loads((RAIZ / args.config).read_text(encoding="utf-8"))
    if args.demo:
        cfg["arquivos"] = {"questoes": "exemplo/questoes.jsonl", "temas": "exemplo/temas.csv"}
        cfg["temas"] = {"hierarquia": [], "id": "id", "nome": "nome", "pai": "pai_id"}
        cfg["provedores"] = [{"nome": "mock", "tipo": "mock", "ativo": True}]
    cl, pr = cfg["classificacao"], cfg["protecoes"]
    provs = [p for p in cfg["provedores"] if p.get("ativo")]
    if args.provedores:
        provs = [p for p in cfg["provedores"] if p["nome"] in args.provedores.split(",")]
    if not provs:
        sys.exit("Nenhum provedor ativo. Veja config.json.")
    for k in ("questoes", "temas"):
        if not (RAIZ / cfg["arquivos"][k]).exists():
            sys.exit(f"Arquivo nao encontrado: {cfg['arquivos'][k]}. Copie os arquivos do case para a pasta dados/ (ou rode com --demo).")
    questoes, temas = carregar_questoes(cfg), carregar_temas(cfg)
    if args.limite:
        questoes = questoes[: args.limite]
    idx = Indice(temas)
    exec_nome = args.execucao or datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta = RAIZ / "runs" / exec_nome
    pasta.mkdir(parents=True, exist_ok=True)
    print(f"{len(questoes)} questoes, {len(temas)} temas, provedores: {[p['nome'] for p in provs]} -> {pasta}")

    todos = {q["id"]: [] for q in questoes}
    for prov in provs:
        pp = pasta / prov["nome"]
        pp.mkdir(exist_ok=True)
        cache_f, cache = pp / "respostas.jsonl", {}
        if cache_f.exists():  # retomar de onde parou
            for l in cache_f.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(l)
                    cache[(r["qid"], r["amostra"])] = r
                except Exception:
                    pass
        est = {"chamadas": 0, "custo": 0.0, "inicio": time.time(), "erros_seguidos": 0, "erros": 0, "tin": 0, "tout": 0}
        votos = {q["id"]: [] for q in questoes}
        parar = False
        for q in questoes:
            if parar:
                break
            cands = idx.candidatos(q, cl["candidatos_por_questao"])
            prompt = montar_prompt(q, cands, temas)
            for a in range(cl["amostras_por_provedor"]):
                if (q["id"], a) in cache:
                    r = cache[(q["id"], a)]
                else:
                    try:
                        temp = cl["temperatura_primeira"] if a == 0 else cl["temperatura_demais"]
                        resp, tin, tout = chamar(prov, prompt, temp, pr, est, pp, cands)
                        if not resp.get("fora") and resp.get("tema_id") not in temas:
                            raise ValueError(f"tema_id invalido: {resp.get('tema_id')}")
                        est["tin"] += tin
                        est["tout"] += tout
                        est["custo"] += tin / 1e6 * prov.get("custo_entrada_por_milhao", 0) + tout / 1e6 * prov.get("custo_saida_por_milhao", 0)
                        est["erros_seguidos"] = 0
                        r = {"qid": q["id"], "amostra": a, **resp}
                        with open(cache_f, "a", encoding="utf-8") as f:
                            f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    except LimiteAtingido as e:
                        log(pp, "erros.log", f"[{prov['nome']}] LIMITE: {e}. Parando.")
                        print(f"[{prov['nome']}] parou: {e}")
                        parar = True
                        break
                    except Exception as e:
                        est["erros"] += 1
                        est["erros_seguidos"] += 1
                        log(pp, "erros.log", f"[{prov['nome']}] questao {q['id']} amostra {a}: {e!r}")
                        if est["erros_seguidos"] >= pr["max_erros_seguidos"]:
                            log(pp, "erros.log", f"[{prov['nome']}] erros seguidos demais. Abortando provedor.")
                            print(f"[{prov['nome']}] abortado por erros seguidos. Veja {pp/'erros.log'}")
                            parar = True
                            break
                        continue
                votos[q["id"]].append(r)
                todos[q["id"]].append(r)
        dec = {q["id"]: decidir(votos[q["id"]], cl["amostras_por_provedor"], cl, temas) for q in questoes}
        salvar_csv(pp / "publicacao.csv", questoes, dec, temas, [prov["nome"]])
        c = Counter(d["decisao"] for d in dec.values())
        historico({"quando": datetime.now().isoformat(timespec="seconds"), "execucao": exec_nome, "provedor": prov["nome"],
                   "modelo": prov.get("modelo", "mock"), "questoes": len(questoes), "publicar": c["publicar"],
                   "revisar": c["revisar"], "fora": c["fora"], "chamadas": est["chamadas"], "erros": est["erros"],
                   "tokens_entrada": est["tin"], "tokens_saida": est["tout"], "custo_usd": round(est["custo"], 4),
                   "segundos": round(time.time() - est["inicio"])})
        print(f"[{prov['nome']}] publicar={c['publicar']} revisar={c['revisar']} fora={c['fora']} erros={est['erros']}")

    esperado = cl["amostras_por_provedor"] * len(provs)
    final = {q["id"]: decidir(todos[q["id"]], esperado, cl, temas) for q in questoes}
    salvar_csv(pasta / "publicacao.csv", questoes, final, temas, [p["nome"] for p in provs])
    print(f"FINAL (todos os provedores juntos): {dict(Counter(d['decisao'] for d in final.values()))} -> {pasta/'publicacao.csv'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Classificador de topicos")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--provedores", help="nomes separados por virgula (padrao: todos os ativos)")
    ap.add_argument("--limite", type=int, help="so as N primeiras questoes (teste barato)")
    ap.add_argument("--execucao", help="nome da pasta em runs/. Repita o nome para RETOMAR")
    ap.add_argument("--demo", action="store_true", help="dados de exemplo + provedor falso (nao gasta nada)")
    rodar(ap.parse_args())
