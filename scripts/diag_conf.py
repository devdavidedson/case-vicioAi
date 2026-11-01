from pathlib import Path

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
clf = ClassificadorV2(temas, tvecs, qvecs, folha, k=7)

ok_s, bad_s, ok_m, bad_m = [], [], [], []
for g in folha:
    if g["fora"]:
        continue
    ranked = clf.ranquear(qmap[g["id"]])
    margem = ranked[0]["score"] - ranked[1]["score"]
    # knn agreement: does knn top match emb top branch?
    knn = ranked[0]["knn"]
    ok = acerto_publicacao(ranked[0]["tema_id"], g, temas)
    # also check if ANY of top3 is correct - for "oracle publish"
    top3_ok = any(acerto_publicacao(r["tema_id"], g, temas) for r in ranked[:3])
    row = (ranked[0]["score"], margem, knn, ranked[0]["sim"], ranked[0]["lei"], top3_ok)
    if ok:
        ok_s.append(row)
    else:
        bad_s.append(row)

print("ok", len(ok_s), "bad", len(bad_s))
print("ok score mean", sum(r[0] for r in ok_s) / len(ok_s))
print("bad score mean", sum(r[0] for r in bad_s) / len(bad_s))
print("ok margem mean", sum(r[1] for r in ok_s) / len(ok_s))
print("bad margem mean", sum(r[1] for r in bad_s) / len(bad_s))
print("ok knn mean", sum(r[2] for r in ok_s) / len(ok_s))
print("bad knn mean", sum(r[2] for r in bad_s) / len(bad_s))
print("ok lei>0", sum(1 for r in ok_s if r[4] > 0) / len(ok_s))
print("bad lei>0", sum(1 for r in bad_s if r[4] > 0) / len(bad_s))

# Sweep: require knn>0 and margem and score
best = None
for min_score in [x / 100 for x in range(40, 95)]:
    for min_marg in [0.0, 0.02, 0.04, 0.06, 0.08, 0.1]:
        for need_knn in [False, True]:
            pubs = []
            for g in folha:
                if g["fora"]:
                    continue
                ranked = clf.ranquear(qmap[g["id"]])
                margem = ranked[0]["score"] - ranked[1]["score"]
                if ranked[0]["score"] < min_score or margem < min_marg:
                    continue
                if need_knn and ranked[0]["knn"] <= 0:
                    continue
                ok = acerto_publicacao(ranked[0]["tema_id"], g, temas)
                pubs.append(ok)
            if not pubs:
                continue
            prec = sum(pubs) / len(pubs)
            cob = len(pubs) / 92
            if prec >= 0.95 and (best is None or cob > best[0]):
                best = (cob, prec, min_score, min_marg, need_knn, len(pubs))
print("best>=95", best)

# looser 0.90
best90 = None
for min_score in [x / 100 for x in range(40, 95)]:
    for min_marg in [0.0, 0.02, 0.04, 0.06, 0.08]:
        for need_knn in [False, True]:
            pubs = []
            for g in folha:
                if g["fora"]:
                    continue
                ranked = clf.ranquear(qmap[g["id"]])
                margem = ranked[0]["score"] - ranked[1]["score"]
                if ranked[0]["score"] < min_score or margem < min_marg:
                    continue
                if need_knn and ranked[0]["knn"] <= 0:
                    continue
                ok = acerto_publicacao(ranked[0]["tema_id"], g, temas)
                pubs.append(ok)
            if not pubs:
                continue
            prec = sum(pubs) / len(pubs)
            cob = len(pubs) / 92
            if prec >= 0.90 and (best90 is None or cob > best90[0]):
                best90 = (cob, prec, min_score, min_marg, need_knn, len(pubs))
print("best>=90", best90)
