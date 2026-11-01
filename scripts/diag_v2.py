from pathlib import Path
from collections import Counter

from src.v2.data import acerto_publicacao, carregar_folha, carregar_questoes, carregar_temas
from src.v2.embeddings import CacheEmbeddings
from src.v2.scorer import ClassificadorV2

RAIZ = Path(__file__).resolve().parents[1]
questoes = carregar_questoes(RAIZ / "dados" / "questoes.jsonl")
temas = carregar_temas(RAIZ / "dados" / "temas.csv")
folha = carregar_folha(RAIZ / "dados" / "folha_verdade.csv")
qmap = {q["id"]: q for q in questoes}
cache = CacheEmbeddings(RAIZ / "artifacts" / "embeddings")
qvecs = cache.obter_muitos(RAIZ, [("questao", q["id"], q["texto"]) for q in questoes])
tvecs = cache.obter_muitos(RAIZ, [("tema", t["id"], t["texto"]) for t in temas.values()])
clf = ClassificadorV2(temas, tvecs, qvecs, folha, k=5)

ok1 = 0
n = 0
scores = []
ranks = []
for g in folha:
    if g["fora"]:
        continue
    n += 1
    ranked = clf.ranquear(qmap[g["id"]])
    scores.append(ranked[0]["score"])
    if acerto_publicacao(ranked[0]["tema_id"], g, temas):
        ok1 += 1
    r = 999
    for i, item in enumerate(ranked):
        if acerto_publicacao(item["tema_id"], g, temas):
            r = i + 1
            break
    ranks.append(r)

print("n", n)
print("top1_ramo", ok1 / n)
print(
    "score mean/p50/p90",
    sum(scores) / len(scores),
    sorted(scores)[len(scores) // 2],
    sorted(scores)[int(len(scores) * 0.9)],
)
print(
    "rank buckets",
    Counter(
        "1" if r == 1 else "2-5" if r <= 5 else "6-20" if r <= 20 else "20+" for r in ranks
    ),
)
