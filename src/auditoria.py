"""Estima a precisao SEM gabarito: voce (ou o professor) confere uma amostra das publicadas.

  python src/auditoria.py sortear NOME_DA_EXECUCAO 100   -> cria auditoria.csv
  (preencha a coluna 'correto' com S ou N)
  python src/auditoria.py calcular NOME_DA_EXECUCAO      -> gera previsao.txt
"""
import csv, json, math, random, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - m), min(1, c + m)


def sortear(exec_nome, n, demo=False):
    pasta = RAIZ / "runs" / exec_nome
    cfg = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    arq = "exemplo/questoes.jsonl" if exec_nome.endswith("demo") else cfg["arquivos"]["questoes"]
    enun = {}
    with open(RAIZ / arq, encoding="utf-8") as f:
        for l in f:
            if l.strip():
                d = json.loads(l)
                enun[str(d[cfg["campos_questao"]["id"]])] = str(d.get(cfg["campos_questao"]["enunciado"], ""))[:600]
    with open(pasta / "publicacao.csv", encoding="utf-8") as f:
        pub = [r for r in csv.DictReader(f) if r["decisao"] == "publicar"]
    random.seed(42)
    amostra = random.sample(pub, min(n, len(pub)))
    with open(pasta / "auditoria.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "enunciado_inicio", "tema_sugerido", "correto"])
        for r in amostra:
            w.writerow([r["id"], enun.get(r["id"], ""), r["tema_nome"], ""])
    print(f"{len(amostra)} questoes em {pasta/'auditoria.csv'}. Preencha 'correto' com S ou N.")
    print("Dica: audite 100+ para provar >=95% com folga. Com 60 acertando tudo, o limite inferior fica ~94%.")


def calcular(exec_nome):
    pasta = RAIZ / "runs" / exec_nome
    with open(pasta / "auditoria.csv", encoding="utf-8") as f:
        aud = [r for r in csv.DictReader(f) if r["correto"].strip().upper() in ("S", "N")]
    with open(pasta / "publicacao.csv", encoding="utf-8") as f:
        todas = list(csv.DictReader(f))
    n, k = len(aud), sum(1 for r in aud if r["correto"].strip().upper() == "S")
    lo, hi = wilson(k, n)
    pub = sum(1 for r in todas if r["decisao"] == "publicar")
    cob = pub / len(todas)
    txt = (f"PREVISAO (execucao {exec_nome})\n"
           f"Precisao nas publicadas: {k/max(n,1):.1%} (intervalo 95%: {lo:.1%} a {hi:.1%}), em amostra de {n} questoes conferidas.\n"
           f"Cobertura: {cob:.1%} ({pub} de {len(todas)} publicadas). Faixa esperada: {max(0,cob-0.05):.1%} a {min(1,cob+0.05):.1%}.\n"
           f"Como cheguei: sorteei {n} publicadas (semente 42), conferi uma a uma, intervalo de Wilson.\n"
           f"Ressalva: amostra pequena => intervalo largo. Acerto aqui deve seguir a regra do case (mesmo tema, pai ou filho).\n")
    (pasta / "previsao.txt").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "sortear":
        sortear(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100)
    else:
        calcular(sys.argv[2])
