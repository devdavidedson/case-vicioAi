"""Limpeza de texto e extração leve de leis/artigos (sem LLM)."""

from __future__ import annotations

import html
import re
import unicodedata

STOP = set(
    "para como pela pelo uma uns umas dos das nos nas com por que sao foi ser "
    "tem seu sua ele ela mais mas nao sim sobre entre quando onde apos ate "
    "pelo pela pelos pelas este esta isso aquilo quando segundo conforme".split()
)

LEI_RE = re.compile(
    r"(?:lei|decreto(?:-lei)?|c[oó]digo)\s*"
    r"(?:n[ºo°\.]?\s*)?"
    r"(\d{1,5}(?:\.\d{3})*(?:/\d{2,4})?)",
    re.I,
)
ART_RE = re.compile(r"\bart(?:igo)?\.?\s*(\d+[ºo°a-zA-Z\-]*)", re.I)
CP_RE = re.compile(r"\b(?:c[oó]digo\s+penal|CP)\b", re.I)
CPP_RE = re.compile(r"\b(?:c[oó]digo\s+de\s+processo\s+penal|CPP)\b", re.I)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def limpar_html(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))).strip()


def tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", norm(s)) if len(t) > 2 and t not in STOP]


def texto_questao(q: dict) -> str:
    partes = [
        q.get("enunciado", ""),
        q.get("comando", ""),
        q.get("alternativas", ""),
        q.get("disciplina", ""),
    ]
    return " ".join(p for p in partes if p).strip()


def extrair_leis(texto: str) -> set[str]:
    """Normaliza citações de lei para chaves comparáveis."""
    achados: set[str] = set()
    for m in LEI_RE.finditer(texto):
        num = re.sub(r"[^\d/]", "", m.group(1))
        if num:
            achados.add(f"lei:{num}")
    if CP_RE.search(texto):
        achados.add("lei:cp")
    if CPP_RE.search(texto):
        achados.add("lei:cpp")
    for m in ART_RE.finditer(texto):
        art = norm(m.group(1))
        achados.add(f"art:{art}")
    return achados


def texto_tema(t: dict) -> str:
    return " | ".join(
        p for p in [t.get("caminho", ""), t.get("nome", ""), t.get("descricao", "")] if p
    )
