"""Regras locais offline (adaptadas de StealthHumanizer/lib/rehumanize.ts).

Rodam sem API: trocam clichês típicos de texto gerado por IA e
ajustam frases longas. Úteis como pré/pós-processamento e fallback.
"""

from __future__ import annotations

import re

# Pares (padrão, substituição) — PT + EN comuns em relatórios de IA
AI_PHRASE_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bFurthermore,?\s*", re.I), "Also, "),
    (re.compile(r"\bMoreover,?\s*", re.I), "Additionally, "),
    (re.compile(r"\bAdditionally,?\s*", re.I), "Also, "),
    (re.compile(r"\bConsequently,?\s*", re.I), "So "),
    (re.compile(r"\bTherefore,?\s*", re.I), "So "),
    (re.compile(r"\bIn conclusion,?\s*", re.I), "Overall, "),
    (re.compile(r"\bIt is important to note that\s*", re.I), "Notably, "),
    (re.compile(r"\bIt is worth noting that\s*", re.I), "Notably, "),
    (re.compile(r"\butilizes?\b", re.I), "uses"),
    (re.compile(r"\bleverages?\b", re.I), "uses"),
    (re.compile(r"\bfacilitates?\b", re.I), "helps"),
    (re.compile(r"\bdemonstrates?\b", re.I), "shows"),
    (re.compile(r"\bcomprehensive\b", re.I), "thorough"),
    (re.compile(r"\bAlém disso,?\s*", re.I), "Também, "),
    (re.compile(r"\bAdemais,?\s*", re.I), "Também, "),
    (re.compile(r"\bPortanto,?\s*", re.I), "Então, "),
    (re.compile(r"\bDessa forma,?\s*", re.I), "Assim, "),
    (re.compile(r"\bÉ importante destacar que\s*", re.I), "Vale notar que "),
    (re.compile(r"\bÉ importante ressaltar que\s*", re.I), "Vale notar que "),
    (re.compile(r"\bNo que tange a\b", re.I), "Sobre"),
    (re.compile(r"\bNo que diz respeito a\b", re.I), "Sobre"),
    (re.compile(r"\butiliza\b", re.I), "usa"),
    (re.compile(r"\bfacilita\b", re.I), "ajuda"),
    (re.compile(r"\bdemonstra\b", re.I), "mostra"),
]


def aplicar_regras_locais(texto: str) -> str:
    """Aplica substituições conservadoras sem chamar modelo."""
    out = texto
    for pattern, repl in AI_PHRASE_REPLACEMENTS:
        out = pattern.sub(repl, out)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r" +\n", "\n", out)
    return out.strip()
