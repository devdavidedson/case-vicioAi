"""Demo offline console — ZERO chamada a LLM/API.

Para a interface visual (recomendado): python -m src.v2.offline_gui
"""

from __future__ import annotations

import sys

from .offline_core import run_offline


def pausar() -> None:
    if getattr(sys, "frozen", False) or sys.stdin.isatty():
        try:
            input("\nPressione ENTER para fechar…")
        except EOFError:
            pass


def _cfg_console() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    _cfg_console()
    print("=" * 60)
    print("  Case Vicio IA — Classificador OFFLINE (console)")
    print("  Dica: use a GUI com  python -m src.v2.offline_gui")
    print("=" * 60)

    def on_progress(msg: str, pct: float, metrics) -> None:
        print(f"[{pct:5.0%}] {msg}")

    try:
        resumo = run_offline(on_progress=on_progress)
    except Exception as e:
        print(f"ERRO: {e}")
        pausar()
        return 1

    dist = resumo.get("distribuicao", {})
    print()
    print("OK — teste offline concluído.")
    print(f"Publicar={dist.get('publicar')} Revisar={dist.get('revisar')} Fora={dist.get('fora')}")
    print(f"Saída: {resumo.get('saida')}")
    pausar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
