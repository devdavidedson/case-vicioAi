"""CLI: python -m src.humanize.cli arquivo.md -o saida.md"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print

from .engine import humanizar_arquivo

app = typer.Typer(
    add_completion=False,
    help="Humaniza relatórios Markdown (inspirado no StealthHumanizer).",
)


@app.command()
def run(
    entrada: Path = typer.Argument(..., exists=True, readable=True, help="Arquivo .md de entrada"),
    saida: Optional[Path] = typer.Option(
        None, "--saida", "-o", help="Arquivo de saída (padrão: rascunhos/<nome>_humano.md)"
    ),
    nivel: str = typer.Option(
        "medium",
        "--nivel",
        "-n",
        help="light (só local) | medium (1 passe API) | aggressive (2 passes)",
    ),
    estilo: str = typer.Option("professional", "--estilo", "-e"),
    modelo: Optional[str] = typer.Option(None, "--modelo", "-m"),
) -> None:
    if saida is None:
        raiz = Path(__file__).resolve().parents[2]
        saida = raiz / "rascunhos" / f"{entrada.stem}_humano{entrada.suffix}"
    caminho = humanizar_arquivo(
        entrada, saida, nivel=nivel, estilo=estilo, modelo=modelo
    )
    print(f"[green]OK[/green] humanizado → {caminho}")


if __name__ == "__main__":
    app()
