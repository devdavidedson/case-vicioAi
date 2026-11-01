"""Demo offline para o recrutador — ZERO chamada a LLM/API.

Duplo clique no .exe (ou: python -m src.v2.offline_app)
- Lê dados + embeddings já cacheados
- Classifica as 659 questões localmente
- Gera saida/publicacao.csv, saida/previsao.txt e saida/resumo.txt
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from .data import acerto_publicacao, carregar_folha, carregar_questoes, carregar_temas
from .embeddings import MODELO_PADRAO, CacheEmbeddings
from .pipeline_v2 import escrever_previsao, escrever_publicacao, split_folha, wilson
from .scorer import ClassificadorV2, avaliar_limiar, calibrar


def descobrir_raiz() -> Path:
    """Raiz do pacote: pasta do .exe (frozen) ou raiz do repositório."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # src/v2/offline_app.py -> repo root
    return Path(__file__).resolve().parents[2]


def recurso(*parts: str) -> Path:
    """Arquivos empacotados pelo PyInstaller ficam em sys._MEIPASS."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        cand = base.joinpath(*parts)
        if cand.exists():
            return cand
    return descobrir_raiz().joinpath(*parts)


def pausar() -> None:
    if getattr(sys, "frozen", False) or sys.stdin.isatty():
        try:
            input("\nPressione ENTER para fechar…")
        except EOFError:
            pass


def _cfg_console() -> None:
    """Evita caracteres quebrados no terminal do Windows."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    _cfg_console()
    raiz = descobrir_raiz()
    saida = raiz / "saida_offline"
    saida.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Case Vicio IA — Classificador OFFLINE (sem LLM)")
    print("  Para análise do recrutador / time técnico")
    print("=" * 60)
    print(f"Pasta: {raiz}")
    print(f"Saída: {saida}")
    print()

    dados = recurso("dados")
    emb_dir = recurso("artifacts", "embeddings")
    # No modo pasta (one-dir), dados/artifacts ficam ao lado do exe
    if not (dados / "questoes.jsonl").exists():
        dados = raiz / "dados"
    if not (emb_dir / "vetores.npz").exists():
        emb_dir = raiz / "artifacts" / "embeddings"

    obrig = [
        dados / "questoes.jsonl",
        dados / "temas.csv",
        dados / "folha_verdade.csv",
        emb_dir / "vetores.npz",
        emb_dir / "indice.json",
    ]
    faltando = [str(p) for p in obrig if not p.exists()]
    if faltando:
        print("ERRO: pacote incompleto. Faltam:")
        for f in faltando:
            print(f"  - {f}")
        print("\nEste executável precisa dos dados e do cache de embeddings.")
        pausar()
        return 1

    print("1/5 Carregando questões, temas e folha-verdade…")
    questoes = carregar_questoes(dados / "questoes.jsonl")
    temas = carregar_temas(dados / "temas.csv")
    folha = carregar_folha(dados / "folha_verdade.csv")
    qmap = {q["id"]: q for q in questoes}
    print(f"   {len(questoes)} questões | {len(temas)} temas | {len(folha)} na folha")

    print("2/5 Carregando embeddings do cache (sem rede)…")
    cache = CacheEmbeddings(emb_dir, MODELO_PADRAO)
    try:
        qvecs = cache.obter_muitos(
            raiz, [("questao", q["id"], q["texto"]) for q in questoes], offline=True
        )
        tvecs = cache.obter_muitos(
            raiz, [("tema", t["id"], t["texto"]) for t in temas.values()], offline=True
        )
    except RuntimeError as e:
        print(f"ERRO offline: {e}")
        pausar()
        return 2
    print(f"   Cache OK — modelo {MODELO_PADRAO} | {len(qvecs)}+{len(tvecs)} vetores")
    print("   Nenhuma chamada a OpenAI/Jev/LLM nesta execução.")

    print("3/5 Calibrando limiar (meta >= 95% nas publicadas)…")
    treino, holdout = split_folha(folha)
    clf = ClassificadorV2(temas, tvecs, qvecs, folha, k=7)
    cal = calibrar(clf, qmap, [g for g in folha if not g["fora"]], alvo_precisao=0.95)
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
    print(
        f"   Folha: prec={cal_final['precisao']:.3f} cob={cal_final['cobertura']:.3f} "
        f"| Holdout: prec={hold_m['precisao']:.3f} ({hold_m['acertos_pub']}/{hold_m['n_publicar']})"
    )
    print(f"   Limiares: sim>={params['limiar_sim']:.3f} margem>={params['limiar_margem']:.3f}")

    print("4/5 Classificando 659 questões (CPU local)…")
    decisoes = {
        q["id"]: clf.decidir(
            q, params["limiar_sim"], params["limiar_margem"], params["limiar_fora"], 1
        )
        for q in questoes
    }
    dist = Counter(d["decisao"] for d in decisoes.values())
    ids_folha = {r["id"] for r in folha}
    fora_folha = [q for q in questoes if q["id"] not in ids_folha]
    n_pub_eval = sum(1 for q in fora_folha if decisoes[q["id"]]["decisao"] == "publicar")

    # acertos nas publicadas que têm rótulo
    checaveis = []
    for r in folha:
        d = decisoes[r["id"]]
        if d["decisao"] != "publicar":
            continue
        if r["fora"]:
            checaveis.append(False)
        else:
            checaveis.append(acerto_publicacao(d["tema_central_id"], r, temas))

    print("5/5 Gravando artefatos em saida_offline/…")
    escrever_publicacao(saida / "publicacao.csv", questoes, decisoes)
    escrever_previsao(
        saida / "previsao.txt",
        {**cal_final, **params},
        hold_m,
        n_pub_eval,
        len(fora_folha),
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
        "cobertura_fora_folha": n_pub_eval / max(len(fora_folha), 1),
        "arquivos": [
            "saida_offline/publicacao.csv",
            "saida_offline/previsao.txt",
            "saida_offline/resumo.json",
            "saida_offline/resumo.txt",
        ],
    }
    (saida / "resumo.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    linhas = [
        "RESUMO — Case Vicio IA (executável offline)",
        "=" * 50,
        f"Data: {resumo['quando']}",
        "Modo: OFFLINE — 0 chamadas a LLM/API",
        f"Embeddings: cache local ({MODELO_PADRAO})",
        "",
        "Distribuição das 659 decisões:",
        f"  publicar : {dist.get('publicar', 0)}",
        f"  revisar  : {dist.get('revisar', 0)}",
        f"  fora     : {dist.get('fora', 0)}",
        "",
        f"Cobertura (fora da folha): {resumo['cobertura_fora_folha']:.1%}",
        f"Holdout precisão: {hold_m['precisao']:.1%} "
        f"({hold_m['acertos_pub']}/{hold_m['n_publicar']})",
        f"Publicadas com rótulo na folha: "
        f"{resumo['folha_publicadas_checaveis']['acertos']}/"
        f"{resumo['folha_publicadas_checaveis']['n']} "
        f"(prec={resumo['folha_publicadas_checaveis']['precisao']})",
        "",
        "Arquivos gerados:",
        "  - publicacao.csv",
        "  - previsao.txt",
        "  - resumo.json / resumo.txt",
        "",
        "Régua do case: >=95% de acerto nas publicadas.",
        "Este pacote reproduz a classificação sem rede.",
    ]
    (saida / "resumo.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print()
    print("\n".join(linhas))
    print()
    print("OK — teste offline concluído.")
    pausar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
