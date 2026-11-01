"""Cérebro D: embeddings (+ leis/kNN/TF-IDF) com gate de publicação por margem.

A escolha do tema usa score combinado.
A decisão publicar/revisar usa sim/margem de embedding calibradas na folha
(para sustentar >=95% nas publicadas).
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np

from .data import acerto_publicacao, caminho_prefixo
from .embeddings import cosseno
from .textutil import tokens


class IndiceLexical:
    def __init__(self, temas: dict[str, dict]):
        self.tema_ids = list(temas.keys())
        self.toks = {t: set(tokens(v["texto"])) for t, v in temas.items()}
        df = Counter(w for s in self.toks.values() for w in s)
        n = max(len(temas), 1)
        self.idf = {w: 1.0 + math.log(n / c) for w, c in df.items()}

    def scores(self, texto: str) -> dict[str, float]:
        qt = set(tokens(texto))
        if not qt:
            return {t: 0.0 for t in self.tema_ids}
        brutos = []
        for tid in self.tema_ids:
            s = self.toks[tid]
            brutos.append(sum(self.idf[w] for w in s & qt))
        mx = max(brutos) if brutos else 0.0
        if mx <= 0:
            return {t: 0.0 for t in self.tema_ids}
        return {tid: brutos[i] / mx for i, tid in enumerate(self.tema_ids)}


class ClassificadorV2:
    def __init__(
        self,
        temas: dict[str, dict],
        tema_vecs: dict[str, np.ndarray],
        questao_vecs: dict[str, np.ndarray],
        folha: list[dict],
        k: int = 7,
    ):
        self.temas = temas
        self.tema_vecs = tema_vecs
        self.questao_vecs = questao_vecs
        self.k = k
        self.lex = IndiceLexical(temas)
        self.protos = [
            (r["id"], r["tema_central_id"], questao_vecs[r["id"]])
            for r in folha
            if (not r["fora"]) and r["tema_central_id"] in temas and r["id"] in questao_vecs
        ]
        self.fora_ids = {r["id"] for r in folha if r["fora"]}
        self.tema_ids = list(tema_vecs.keys())
        mat = np.stack([tema_vecs[t] for t in self.tema_ids])
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._matriz = mat / norms

    def _knn(self, qid: str, qvec: np.ndarray) -> tuple[Counter, float]:
        sims = []
        for pid, tid, pvec in self.protos:
            if pid == qid:
                continue
            sims.append((cosseno(qvec, pvec), tid, pid))
        sims.sort(reverse=True)
        top = sims[: self.k]
        votos: Counter = Counter()
        for sim, tid, _ in top:
            votos[tid] += max(sim, 0.0)
        fora = sum(max(s, 0.0) for s, _, pid in top if pid in self.fora_ids)
        return votos, fora

    def ranquear(self, q: dict) -> list[dict]:
        qvec = self.questao_vecs[q["id"]]
        qn = qvec / (np.linalg.norm(qvec) or 1.0)
        sims = self._matriz @ qn
        knn_votos, fora_prox = self._knn(q["id"], qvec)
        knn_max = max(knn_votos.values()) if knn_votos else 0.0
        lex = self.lex.scores(q["texto"])

        ranked = []
        for i, tid in enumerate(self.tema_ids):
            t = self.temas[tid]
            sim = float(sims[i])
            lei = 0.0
            inter = q["leis"] & t["leis"]
            for x in inter:
                if x.startswith("lei:"):
                    lei += 0.08
                elif x.startswith("art:"):
                    lei += 0.02
            lei = min(lei, 0.25)
            knn = (knn_votos.get(tid, 0.0) / knn_max) * 0.10 if knn_max else 0.0
            if knn == 0 and knn_votos:
                for kt, w in knn_votos.items():
                    if caminho_prefixo(t["caminho"], self.temas[kt]["caminho"]):
                        knn = max(knn, (w / knn_max) * 0.06)
            tfidf = 0.08 * lex.get(tid, 0.0)
            gen = -0.20 if t["nivel"] <= 0 else (0.02 if t["nivel"] >= 2 else 0.0)
            score = sim + lei + knn + tfidf + gen
            ranked.append(
                {
                    "tema_id": tid,
                    "score": score,
                    "sim": sim,
                    "lei": lei,
                    "knn": knn,
                    "tfidf": tfidf,
                    "nivel": t["nivel"],
                    "caminho": t["caminho"],
                    "fora_prox": fora_prox,
                }
            )
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    def _melhores_especificos(self, ranked: list[dict]) -> list[dict]:
        return [r for r in ranked if r["nivel"] >= 1]

    def decidir(
        self,
        q: dict,
        limiar_sim: float,
        limiar_margem: float,
        limiar_fora: float = 0.32,
        exigir_nivel_min: int = 1,
    ) -> dict:
        ranked = self.ranquear(q)
        espec = self._melhores_especificos(ranked)
        if not espec:
            espec = ranked
        top = espec[0]
        second = espec[1] if len(espec) > 1 else ranked[1]
        # Gate de publicação usa similaridade pura de embedding entre os específicos
        emb_sorted = sorted(espec, key=lambda x: x["sim"], reverse=True)
        emb_top = emb_sorted[0]
        emb_second = emb_sorted[1]
        emb_sim = emb_top["sim"]
        emb_margem = emb_top["sim"] - emb_second["sim"]

        # tema escolhido: score combinado, mas se embedding discorda e não é mesmo ramo, fica com emb
        escolhido = top
        if not caminho_prefixo(top["caminho"], emb_top["caminho"]):
            # só troca para emb se o score combinado não estiver claramente na frente
            if top["score"] < emb_top["score"] + 0.05:
                escolhido = emb_top

        extras = [r["tema_id"] for r in espec[1:3]]
        conf = round(max(0.0, min(0.99, emb_sim + emb_margem)), 4)

        # fora
        if emb_top["fora_prox"] >= 0.5 and emb_sim < limiar_fora:
            return {
                "decisao": "fora",
                "tema_central_id": "",
                "extras_ids": [],
                "confianca": conf,
                "motivo": "vizinhos da folha sugerem fora da taxonomia",
                "sim": round(emb_sim, 4),
                "margem": round(emb_margem, 4),
            }

        if escolhido["nivel"] < exigir_nivel_min:
            return {
                "decisao": "revisar",
                "tema_central_id": escolhido["tema_id"],
                "extras_ids": extras,
                "confianca": conf,
                "motivo": "tema genérico demais",
                "sim": round(emb_sim, 4),
                "margem": round(emb_margem, 4),
            }

        publicar = emb_sim >= limiar_sim and emb_margem >= limiar_margem
        # publica o tema do embedding top (mais alinhado ao gate)
        tema_pub = emb_top["tema_id"]
        return {
            "decisao": "publicar" if publicar else "revisar",
            "tema_central_id": tema_pub,
            "extras_ids": [e for e in extras if e != tema_pub][:2],
            "confianca": conf,
            "motivo": ""
            if publicar
            else f"margem/sim insuficientes (sim={emb_sim:.3f}, margem={emb_margem:.3f})",
            "sim": round(emb_sim, 4),
            "margem": round(emb_margem, 4),
        }


def avaliar_limiar(
    clf: ClassificadorV2,
    questoes_por_id: dict[str, dict],
    folha_eval: list[dict],
    limiar_sim: float,
    limiar_margem: float,
    limiar_fora: float,
    exigir_nivel_min: int = 1,
) -> dict:
    pubs: list[bool] = []
    for g in folha_eval:
        d = clf.decidir(
            questoes_por_id[g["id"]], limiar_sim, limiar_margem, limiar_fora, exigir_nivel_min
        )
        if g["fora"]:
            if d["decisao"] == "publicar":
                pubs.append(False)
            continue
        if d["decisao"] == "publicar":
            pubs.append(acerto_publicacao(d["tema_central_id"], g, clf.temas))
    n_pub = len(pubs)
    n_norm = max(len([x for x in folha_eval if not x["fora"]]), 1)
    return {
        "precisao": (sum(pubs) / n_pub) if n_pub else 1.0,
        "cobertura": n_pub / n_norm,
        "n_publicar": n_pub,
        "n_eval": len(folha_eval),
        "acertos_pub": int(sum(pubs)),
    }


def calibrar(
    clf: ClassificadorV2,
    questoes_por_id: dict[str, dict],
    folha_eval: list[dict],
    alvo_precisao: float = 0.95,
) -> dict:
    # pré-compute features de gate
    feats = []
    for g in folha_eval:
        if g["fora"]:
            continue
        ranked = clf.ranquear(questoes_por_id[g["id"]])
        espec = [r for r in ranked if r["nivel"] >= 1] or ranked
        emb = sorted(espec, key=lambda x: x["sim"], reverse=True)
        sim = emb[0]["sim"]
        margem = emb[0]["sim"] - emb[1]["sim"]
        ok = acerto_publicacao(emb[0]["tema_id"], g, clf.temas)
        feats.append((ok, sim, margem))

    melhor = None
    grade = []
    for lim_sim in [i / 100 for i in range(30, 75)]:
        for lim_m in [i / 100 for i in range(0, 16)]:
            pubs = [ok for ok, sim, m in feats if sim >= lim_sim and m >= lim_m]
            if len(pubs) < 3:
                continue
            prec = sum(pubs) / len(pubs)
            cob = len(pubs) / max(len(feats), 1)
            m = {
                "precisao": prec,
                "cobertura": cob,
                "n_publicar": len(pubs),
                "n_eval": len(folha_eval),
                "acertos_pub": int(sum(pubs)),
                "limiar_publicar": lim_sim,  # sim
                "limiar_fora": 0.32,
                "margem_min": lim_m,
                "limiar_sim": lim_sim,
                "limiar_margem": lim_m,
            }
            grade.append(m)
            if prec + 1e-9 >= alvo_precisao:
                if melhor is None or cob > melhor["cobertura"]:
                    melhor = m
    if melhor is None:
        candidatos = [g for g in grade if g["n_publicar"] >= 5]
        melhor = max(candidatos or grade, key=lambda x: (x["precisao"], x["cobertura"]))
    melhor["grade_n"] = len(grade)
    return melhor
