"""Motor de humanização: regras locais + 1–2 passes OpenAI (estilo StealthHumanizer)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from .local_rules import aplicar_regras_locais
from .prompts import montar_system_prompt

RAIZ = Path(__file__).resolve().parents[2]


def _cliente() -> OpenAI:
    load_dotenv(RAIZ / ".env")
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        raise RuntimeError(
            "OPENAI_API_KEY não encontrada. Copie .env.example para .env e preencha."
        )
    return OpenAI(api_key=chave)


def _um_passe(cliente: OpenAI, texto: str, modelo: str, estilo: str) -> str:
    resp = cliente.chat.completions.create(
        model=modelo,
        temperature=0.7,
        messages=[
            {"role": "system", "content": montar_system_prompt(estilo)},
            {"role": "user", "content": texto},
        ],
    )
    conteudo = resp.choices[0].message.content
    if not conteudo or not conteudo.strip():
        raise RuntimeError("OpenAI devolveu texto vazio na humanização.")
    return conteudo.strip()


def humanizar_texto(
    texto: str,
    *,
    nivel: str = "medium",
    estilo: str = "professional",
    modelo: str | None = None,
    passes: int | None = None,
) -> str:
    """Humaniza texto.

    - light: só regras locais (sem API)
    - medium: 1 passe OpenAI + pós-processamento local
    - aggressive: 2 passes OpenAI + local
    """
    load_dotenv(RAIZ / ".env")
    modelo = modelo or os.getenv("OPENAI_HUMANIZE_MODEL", "gpt-4o-mini")
    base = aplicar_regras_locais(texto)

    if nivel == "light":
        return base

    n_passes = passes if passes is not None else (2 if nivel == "aggressive" else 1)
    cliente = _cliente()
    atual = base
    for _ in range(max(1, n_passes)):
        atual = _um_passe(cliente, atual, modelo, estilo)
        atual = aplicar_regras_locais(atual)
    return atual


def humanizar_arquivo(
    entrada: Path,
    saida: Path,
    *,
    nivel: str = "medium",
    estilo: str = "professional",
    modelo: str | None = None,
) -> Path:
    texto = entrada.read_text(encoding="utf-8")
    humano = humanizar_texto(texto, nivel=nivel, estilo=estilo, modelo=modelo)
    saida.parent.mkdir(parents=True, exist_ok=True)
    cabecalho = (
        "<!-- RASCUNHO LOCAL — NÃO ENTREGAR sem autorização explícita do autor. "
        "Gerado pelo humanizador (inspirado em StealthHumanizer). -->\n\n"
    )
    saida.write_text(cabecalho + humano + "\n", encoding="utf-8")
    return saida
