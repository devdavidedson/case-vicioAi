"""Compara provedores de uma execucao: quanto cada um publica e onde discordam."""
import csv, sys
from collections import Counter
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def ler(p):
    with open(p, encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def main(exec_nome):
    pasta = RAIZ / "runs" / exec_nome
    dados = {d.name: ler(d / "publicacao.csv") for d in sorted(pasta.iterdir()) if d.is_dir() and (d / "publicacao.csv").exists()}
    if not dados:
        sys.exit("Nada para comparar nessa execucao.")
    linhas = [f"# Comparativo da execucao {exec_nome}\n"]
    for nome, d in dados.items():
        c = Counter(r["decisao"] for r in d.values())
        linhas.append(f"- **{nome}**: publicar={c['publicar']} revisar={c['revisar']} fora={c['fora']}")
    with open(pasta / "discordancias.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "provedor_a", "tema_a", "decisao_a", "provedor_b", "tema_b", "decisao_b"])
        for a, b in combinations(dados, 2):
            ids = set(dados[a]) & set(dados[b])
            ig = sum(1 for i in ids if dados[a][i]["tema_id"] == dados[b][i]["tema_id"])
            amb = [i for i in ids if dados[a][i]["decisao"] == dados[b][i]["decisao"] == "publicar"]
            ig_pub = sum(1 for i in amb if dados[a][i]["tema_id"] == dados[b][i]["tema_id"])
            linhas.append(f"- **{a} x {b}**: mesmo tema em {ig}/{len(ids)}; entre as publicadas por ambos, {ig_pub}/{len(amb)} concordam")
            for i in sorted(ids):
                if dados[a][i]["tema_id"] != dados[b][i]["tema_id"]:
                    w.writerow([i, a, dados[a][i]["tema_id"], dados[a][i]["decisao"], b, dados[b][i]["tema_id"], dados[b][i]["decisao"]])
    (pasta / "comparativo.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))
    print("\nSalvo em comparativo.md e discordancias.csv. Historico geral: comparativos/historico.csv")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python src/comparar.py NOME_DA_EXECUCAO")
    main(sys.argv[1])
