"""Carga de questões, temas e folha-verdade."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .textutil import limpar_html, extrair_leis, texto_questao, texto_tema


def _alts(alt) -> str:
    if isinstance(alt, dict):
        return "; ".join(f"{k}) {limpar_html(v)}" for k, v in alt.items())
    if isinstance(alt, list):
        bits = []
        for x in alt:
            if isinstance(x, dict):
                bits.append(" ".join(map(str, x.values())))
            else:
                bits.append(limpar_html(x))
        return "; ".join(bits)
    return limpar_html(alt)


def carregar_questoes(path: Path) -> list[dict]:
    saida = []
    with open(path, encoding="utf-8") as f:
        for n, linha in enumerate(f, 1):
            if not linha.strip():
                continue
            d = json.loads(linha)
            q = {
                "id": str(d["id"]),
                "enunciado": limpar_html(d.get("enunciado_html")),
                "comando": limpar_html(d.get("comando")),
                "alternativas": _alts(d.get("alternativas")),
                "disciplina": limpar_html(d.get("disciplina_origem")),
                "assunto": limpar_html(d.get("assunto_origem")),
            }
            q["texto"] = texto_questao(q)
            q["leis"] = extrair_leis(q["texto"])
            saida.append(q)
    return saida


def carregar_temas(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    temas: dict[str, dict] = {}
    for r in rows:
        if (r.get("status") or "").strip() != "active":
            continue
        tid = str(r["tema_id"]).strip()
        temas[tid] = {
            "id": tid,
            "nome": (r.get("titulo") or "").strip(),
            "caminho": (r.get("caminho") or "").strip(),
            "descricao": (r.get("descricao") or "").strip(),
            "parent_id": (r.get("parent_id") or "").strip(),
            "nivel": int(r.get("nivel") or 0),
            "disciplina": (r.get("disciplina") or "").strip(),
            "texto": "",
            "leis": set(),
        }
        temas[tid]["texto"] = texto_tema(temas[tid])
        temas[tid]["leis"] = extrair_leis(temas[tid]["texto"])
    return temas


def carregar_folha(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        extras = [e.strip() for e in (r.get("extras_ids") or "").split(";") if e.strip()]
        out.append(
            {
                "id": str(r["id"]).strip(),
                "tema_central_id": (r.get("tema_central_id") or "").strip(),
                "extras_ids": extras,
                "fora": (r.get("fora_da_taxonomia") or "").strip() == "1",
            }
        )
    return out


def caminho_prefixo(a: str, b: str) -> bool:
    """True se a é igual a b ou pai/filho (mesmo ramo)."""
    if not a or not b:
        return False
    return a == b or a.startswith(b + " > ") or b.startswith(a + " > ")


def acerto_publicacao(
    tema_pred: str,
    gold: dict,
    temas: dict[str, dict],
) -> bool:
    """Régua do LEIA-ME: tema central, extra ou nó do mesmo ramo."""
    if gold["fora"]:
        return False
    alvos = [gold["tema_central_id"], *gold["extras_ids"]]
    alvos = [t for t in alvos if t]
    if tema_pred in alvos:
        return True
    cp = temas.get(tema_pred, {}).get("caminho", "")
    for tid in alvos:
        cg = temas.get(tid, {}).get("caminho", "")
        if caminho_prefixo(cp, cg):
            return True
    return False
