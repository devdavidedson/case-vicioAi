"""Estima a precisao SEM gabarito: voce (ou o professor) confere uma amostra das publicadas.

  python src/auditoria.py sortear NOME_DA_EXECUCAO 100   -> cria auditoria.csv
  (preencha a coluna 'correto' com S ou N)
  python src/auditoria.py calcular NOME_DA_EXECUCAO      -> gera previsao.txt

Também é chamado automaticamente ao final do pipeline (copia publicacao.csv e previsao.txt
para a raiz do projeto, prontos para a entrega do case).
"""
import csv, json, math, random, shutil, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - m), min(1, c + m)


def _ler_publicacao(pasta):
    with open(pasta / "publicacao.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _auditoria_preenchida(pasta):
    arq = pasta / "auditoria.csv"
    if not arq.exists():
        return []
    with open(arq, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("correto", "").strip().upper() in ("S", "N")]


def sortear(exec_nome, n, demo=False):
    pasta = RAIZ / "runs" / exec_nome
    cfg = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    arq = "exemplo/questoes.jsonl" if (demo or exec_nome.endswith("demo")) else cfg["arquivos"]["questoes"]
    enun = {}
    with open(RAIZ / arq, encoding="utf-8") as f:
        for l in f:
            if l.strip():
                d = json.loads(l)
                enun[str(d[cfg["campos_questao"]["id"]])] = str(d.get(cfg["campos_questao"]["enunciado"], ""))[:600]
    pub = [r for r in _ler_publicacao(pasta) if r["decisao"] == "publicar"]
    if not pub:
        print(f"Nenhuma questao 'publicar' em {pasta / 'publicacao.csv'}; auditoria nao criada.")
        return 0
    random.seed(42)
    amostra = random.sample(pub, min(n, len(pub)))
    with open(pasta / "auditoria.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "enunciado_inicio", "tema_sugerido", "correto"])
        for r in amostra:
            w.writerow([r["id"], enun.get(r["id"], ""), r["tema_nome"], ""])
    print(f"{len(amostra)} questoes em {pasta / 'auditoria.csv'}. Preencha 'correto' com S ou N.")
    print("Dica: audite 100+ para provar >=95% com folga. Com 60 acertando tudo, o limite inferior fica ~94%.")
    return len(amostra)


def montar_previsao(exec_nome):
    """Monta o texto de previsao.txt (cobertura sempre; precisao se a auditoria estiver preenchida)."""
    pasta = RAIZ / "runs" / exec_nome
    todas = _ler_publicacao(pasta)
    pub = sum(1 for r in todas if r["decisao"] == "publicar")
    cob = pub / max(len(todas), 1)
    cob_lo, cob_hi = max(0, cob - 0.05), min(1, cob + 0.05)
    aud = _auditoria_preenchida(pasta)

    linhas = [f"PREVISAO (execucao {exec_nome})"]
    if aud:
        n, k = len(aud), sum(1 for r in aud if r["correto"].strip().upper() == "S")
        lo, hi = wilson(k, n)
        linhas.append(
            f"Precisao nas publicadas: {k / max(n, 1):.1%} "
            f"(intervalo 95%: {lo:.1%} a {hi:.1%}), em amostra de {n} questoes conferidas."
        )
        linhas.append(
            f"Cobertura: {cob:.1%} ({pub} de {len(todas)} publicadas). "
            f"Faixa esperada: {cob_lo:.1%} a {cob_hi:.1%}."
        )
        linhas.append(
            f"Como cheguei: sorteei {n} publicadas (semente 42), conferi uma a uma, intervalo de Wilson. "
            f"Cobertura veio direto do publicacao.csv."
        )
        linhas.append(
            "Ressalva: amostra pequena => intervalo largo. Acerto aqui deve seguir a regra do case "
            "(mesmo tema, pai ou filho)."
        )
        completa = True
    else:
        linhas.append(
            "Precisao nas publicadas: PENDENTE — preencha a coluna 'correto' (S/N) em "
            f"{pasta / 'auditoria.csv'} e rode o mesmo comando de novo "
            f"(ou: python src/auditoria.py calcular {exec_nome})."
        )
        linhas.append(
            f"Cobertura: {cob:.1%} ({pub} de {len(todas)} publicadas). "
            f"Faixa esperada: {cob_lo:.1%} a {cob_hi:.1%}."
        )
        linhas.append(
            "Como cheguei (ate agora): a cobertura e a fracao de decisoes 'publicar' no publicacao.csv. "
            "A precisao so fecha depois da auditoria humana da amostra sorteada."
        )
        completa = False
    return "\n".join(linhas) + "\n", completa


def calcular(exec_nome, copiar_raiz=True):
    txt, completa = montar_previsao(exec_nome)
    pasta = RAIZ / "runs" / exec_nome
    (pasta / "previsao.txt").write_text(txt, encoding="utf-8")
    if copiar_raiz:
        (RAIZ / "previsao.txt").write_text(txt, encoding="utf-8")
    print(txt)
    if not completa:
        print("AVISO: previsao.txt gerado sem precisao (auditoria ainda vazia).", file=sys.stderr)
    return completa


def finalizar_entrega(exec_nome, n_auditoria=100, demo=False):
    """Copia artefatos de entrega para a raiz e atualiza previsao/auditoria."""
    pasta = RAIZ / "runs" / exec_nome
    pub = pasta / "publicacao.csv"
    if not pub.exists():
        print(f"Entrega: {pub} nao encontrado.", file=sys.stderr)
        return

    shutil.copy2(pub, RAIZ / "publicacao.csv")
    print(f"Entrega: {RAIZ / 'publicacao.csv'}")

    rel_src = RAIZ / "docs" / "RELATORIO.md"
    if rel_src.exists():
        shutil.copy2(rel_src, RAIZ / "relatorio.md")
        print(f"Entrega: {RAIZ / 'relatorio.md'} (espelho de docs/RELATORIO.md)")

    if not (pasta / "auditoria.csv").exists():
        sortear(exec_nome, n_auditoria, demo=demo)
    elif not _auditoria_preenchida(pasta):
        print(f"Entrega: auditoria em {pasta / 'auditoria.csv'} ainda sem S/N.")

    completa = calcular(exec_nome, copiar_raiz=True)
    print(f"Entrega: {RAIZ / 'previsao.txt'}" + (" (completa)" if completa else " (cobertura ok; precisao pendente)"))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "sortear":
        sortear(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100)
    elif sys.argv[1] == "entrega":
        finalizar_entrega(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100)
    else:
        calcular(sys.argv[2])
