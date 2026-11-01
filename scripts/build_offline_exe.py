"""Gera o pacote/executável offline com GUI VicioAI (pegada dashboard).

Uso:
  python scripts/build_offline_exe.py

Saída: dist/CaseVicio_Offline_Recrutador/
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIST_NAME = "CaseVicio_Offline_Recrutador"
OUT = RAIZ / "dist" / DIST_NAME


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    for p in [
        RAIZ / "dados" / "questoes.jsonl",
        RAIZ / "dados" / "temas.csv",
        RAIZ / "dados" / "folha_verdade.csv",
        RAIZ / "artifacts" / "embeddings" / "vetores.npz",
    ]:
        if not p.exists():
            print(f"Falta: {p}")
            return 1

    work = RAIZ / "build" / "offline_staging"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    entry = work / "run_offline_gui.py"
    entry.write_text(
        "from src.v2.offline_gui import main\nraise SystemExit(main())\n",
        encoding="utf-8",
    )

    sep = ";" if sys.platform.startswith("win") else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "CaseVicioOffline",
        "--onedir",
        "--windowed",
        "--paths",
        str(RAIZ),
        f"--add-data={RAIZ / 'dados'}{sep}dados",
        f"--add-data={RAIZ / 'artifacts' / 'embeddings'}{sep}artifacts/embeddings",
        "--hidden-import=numpy",
        "--hidden-import=customtkinter",
        "--hidden-import=PIL",
        "--collect-submodules=numpy",
        "--collect-all=customtkinter",
        str(entry),
    ]
    print("Rodando:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=RAIZ)

    built = RAIZ / "dist" / "CaseVicioOffline"
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(built, OUT)

    shutil.copytree(RAIZ / "dados", OUT / "dados", dirs_exist_ok=True)
    (OUT / "artifacts" / "embeddings").mkdir(parents=True, exist_ok=True)
    for f in (RAIZ / "artifacts" / "embeddings").iterdir():
        if f.is_file():
            shutil.copy2(f, OUT / "artifacts" / "embeddings" / f.name)

    (OUT / "LEIA-ME_RECRUTADOR.txt").write_text(
        """CASE VICIO AI — EXECUTÁVEL OFFLINE (GUI)
========================================

Visual inspirado em dashboard de benchmark + tema VicioAI / Método VDE
(roxo → magenta). Classificação 100% local, sem LLM.

Como abrir
----------
1. Duplo clique em CaseVicioOffline.exe
   (ou ABRIR_TESTE_OFFLINE.bat)
2. Escolha o perfil (Completo / Amostra / Smoke)
3. Clique em Iniciar
4. Acompanhe métricas e o log
5. Ao terminar, abra a pasta saida_offline\\

Não precisa de internet nem de chave de API.
""",
        encoding="utf-8",
    )
    (OUT / "ABRIR_TESTE_OFFLINE.bat").write_text(
        "@echo off\r\ncd /d \"%~dp0\"\r\nstart \"\" CaseVicioOffline.exe\r\n",
        encoding="utf-8",
    )

    print(f"\nOK → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
