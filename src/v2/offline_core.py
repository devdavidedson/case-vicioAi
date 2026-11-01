"""Motor compartilhado do teste offline (console e GUI). Sem LLM/API."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

from .data import acerto_publicacao, carregar_folha, carregar_questoes, carregar_temas
from .embeddings import MODELO_PADRAO, CacheEmbeddings
from .pipeline_v2 import escrever_previsao, escrever_publicacao, split_folha
from .scorer import ClassificadorV2, avaliar_limiar, calibrar

ProgressCb = Callable[[str, float, dict | None], None]


def descobrir_raiz() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def recurso(raiz: Path, *parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        cand = Path(sys._MEIPASS).joinpath(*parts)
        if cand.exists():
            return cand
    return raiz.joinpath(*parts)


def resolver_caminhos(raiz: Path | None = None) -> tuple[Path, Path, Path, Path]:
    raiz = raiz or descobrir_raiz()
    saida = raiz / "saida_offline"
    dados = recurso(raiz, "dados")
    emb = recurso(raiz, "artifacts", "embeddings")
    if not (dados / "questoes.jsonl").exists():
        dados = raiz / "dados"
    if not (emb / "vetores.npz").exists():
        emb = raiz / "artifacts" / "embeddings"
    return raiz, saida, dados, emb


def run_offline(
    *,
    raiz: Path | None = None,
    limite: int | None = None,
    on_progress: ProgressCb | None = None,
) -> dict:
    """Executa classificação offline. on_progress(msg, pct_0a1, metrics_parciais)."""

    def prog(msg: str, pct: float, metrics: dict | None = None) -> None:
        if on_progress:
            on_progress(msg, max(0.0, min(1.0, pct)), metrics)

    raiz, saida, dados, emb_dir = resolver_caminhos(raiz)
    saida.mkdir(parents=True, exist_ok=True)

    obrig = [
        dados / "questoes.jsonl",
        dados / "temas.csv",
        dados / "folha_verdade.csv",
        emb_dir / "vetores.npz",
        emb_dir / "indice.json",
    ]
    faltando = [str(p) for p in obrig if not p.exists()]
    if faltando:
        raise FileNotFoundError("Pacote incompleto. Faltam:\n- " + "\n- ".join(faltando))

    prog("Carregando questões, temas e folha-verdade…", 0.05)
    questoes = carregar_questoes(dados / "questoes.jsonl")
    if limite:
        questoes = questoes[:limite]
    temas = carregar_temas(dados / "temas.csv")
    folha = carregar_folha(dados / "folha_verdade.csv")
    qmap = {q["id"]: q for q in questoes}
    ids_q = {q["id"] for q in questoes}
    folha = [r for r in folha if r["id"] in ids_q]
    prog(
        f"{len(questoes)} questões | {len(temas)} temas | {len(folha)} na folha",
        0.12,
        {"questoes": len(questoes), "temas": len(temas)},
    )

    prog("Carregando embeddings do cache (sem rede)…", 0.18)
    cache = CacheEmbeddings(emb_dir, MODELO_PADRAO)
    qvecs = cache.obter_muitos(
        raiz, [("questao", q["id"], q["texto"]) for q in questoes], offline=True
    )
    tvecs = cache.obter_muitos(
        raiz, [("tema", t["id"], t["texto"]) for t in temas.values()], offline=True
    )
    prog(
        f"Cache OK — {MODELO_PADRAO} | 0 chamadas a LLM/API",
        0.28,
        {"embeddings": len(qvecs) + len(tvecs)},
    )

    prog("Calibrando limiar (meta ≥ 95% nas publicadas)…", 0.35)
    clf = ClassificadorV2(temas, tvecs, qvecs, folha, k=7)
    folha_norm = [g for g in folha if not g["fora"]]
    if len(folha) >= 4:
        _, holdout = split_folha(folha)
    else:
        holdout = list(folha)
    cal = calibrar(clf, qmap, folha_norm, alvo_precisao=0.95)
    params = {
        "limiar_sim": cal.get("limiar_sim", cal["limiar_publicar"]),
        "limiar_margem": cal.get("limiar_margem", cal["margem_min"]),
        "limiar_fora": cal.get("limiar_fora", 0.32),
        "n_treino": len(folha),
        "n_holdout": len(holdout),
    }
    hold_m = avaliar_limiar(
        clf, qmap, holdout, params["limiar_sim"], params["limiar_margem"], params["limiar_fora"], 1
    )
    while hold_m["precisao"] < 0.95 and params["limiar_margem"] < 0.10:
        params["limiar_margem"] = round(params["limiar_margem"] + 0.01, 2)
        hold_m = avaliar_limiar(
            clf, qmap, holdout, params["limiar_sim"], params["limiar_margem"], params["limiar_fora"], 1
        )
    cal_final = avaliar_limiar(
        clf,
        qmap,
        [g for g in folha if not g["fora"]],
        params["limiar_sim"],
        params["limiar_margem"],
        params["limiar_fora"],
        1,
    )
    prog(
        f"Limiares: sim≥{params['limiar_sim']:.3f} margem≥{params['limiar_margem']:.3f}",
        0.45,
        {
            "prec_folha": cal_final["precisao"],
            "holdout_prec": hold_m["precisao"],
        },
    )

    prog("Classificando questões (CPU local)…", 0.50)
    decisoes = {}
    n = len(questoes)
    for i, q in enumerate(questoes, 1):
        decisoes[q["id"]] = clf.decidir(
            q, params["limiar_sim"], params["limiar_margem"], params["limiar_fora"], 1
        )
        if i % 25 == 0 or i == n:
            dist = Counter(d["decisao"] for d in decisoes.values())
            prog(
                f"Classificadas {i}/{n}…",
                0.50 + 0.35 * (i / n),
                {
                    "publicar": dist.get("publicar", 0),
                    "revisar": dist.get("revisar", 0),
                    "fora": dist.get("fora", 0),
                    "progresso": i,
                    "total": n,
                },
            )

    dist = Counter(d["decisao"] for d in decisoes.values())
    ids_folha = {r["id"] for r in folha}
    fora_folha = [q for q in questoes if q["id"] not in ids_folha]
    n_pub_eval = sum(1 for q in fora_folha if decisoes[q["id"]]["decisao"] == "publicar")

    checaveis = []
    for r in folha:
        d = decisoes[r["id"]]
        if d["decisao"] != "publicar":
            continue
        if r["fora"]:
            checaveis.append(False)
        else:
            checaveis.append(acerto_publicacao(d["tema_central_id"], r, temas))

    prog("Gravando artefatos em saida_offline/…", 0.90)
    escrever_publicacao(saida / "publicacao.csv", questoes, decisoes)
    escrever_previsao(
        saida / "previsao.txt",
        {**cal_final, **params},
        hold_m,
        n_pub_eval,
        max(len(fora_folha), 1),
        params,
    )

    resumo = {
        "quando": datetime.now().isoformat(timespec="seconds"),
        "modo": "offline_sem_llm",
        "modelo_embeddings_cache": MODELO_PADRAO,
        "llm_na_decisao": False,
        "chamadas_api": 0,
        "distribuicao": dict(dist),
        "params": params,
        "folha_publicadas_checaveis": {
            "n": len(checaveis),
            "acertos": int(sum(checaveis)),
            "precisao": (sum(checaveis) / len(checaveis)) if checaveis else None,
        },
        "holdout": hold_m,
        "calibracao_folha": cal_final,
        "cobertura_fora_folha": n_pub_eval / max(len(fora_folha), 1),
        "saida": str(saida),
    }
    (saida / "resumo.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    linhas = [
        "RESUMO — Case Vicio IA (offline)",
        f"Data: {resumo['quando']}",
        "Modo: OFFLINE — 0 chamadas a LLM/API",
        f"Publicar: {dist.get('publicar', 0)} | Revisar: {dist.get('revisar', 0)} | Fora: {dist.get('fora', 0)}",
        f"Cobertura (fora da folha): {resumo['cobertura_fora_folha']:.1%}",
        f"Holdout precisão: {hold_m['precisao']:.1%} ({hold_m['acertos_pub']}/{hold_m['n_publicar']})",
        f"Pasta: {saida}",
    ]
    (saida / "resumo.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    prog("Concluído.", 1.0, {
        "publicar": dist.get("publicar", 0),
        "revisar": dist.get("revisar", 0),
        "fora": dist.get("fora", 0),
        "holdout_prec": hold_m["precisao"],
        "cobertura_fora_folha": resumo["cobertura_fora_folha"],
        "prec_checavel": resumo["folha_publicadas_checaveis"]["precisao"],
    })
    return resumo
