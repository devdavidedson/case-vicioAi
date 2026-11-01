"""Gera o pacote/executável offline para o recrutador.

Uso (na raiz do repo, com venv ativo):
  pip install pyinstaller
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

    # Garante dados e cache presentes
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

    # Entry script simples (evita -m em frozen)
    entry = work / "run_offline.py"
    entry.write_text(
        "from src.v2.offline_app import main\nraise SystemExit(main())\n",
        encoding="utf-8",
    )

    sep = ";" if sys.platform.startswith("win") else ":"
    add_data = [
        f"{RAIZ / 'dados'}{sep}dados",
        f"{RAIZ / 'artifacts' / 'embeddings'}{sep}artifacts/embeddings",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "CaseVicioOffline",
        "--onedir",
        "--console",
        "--paths",
        str(RAIZ),
        f"--add-data={add_data[0]}",
        f"--add-data={add_data[1]}",
        "--hidden-import=numpy",
        "--collect-submodules=numpy",
        str(entry),
    ]
    print("Rodando:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=RAIZ)

    built = RAIZ / "dist" / "CaseVicioOffline"
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(built, OUT)

    # Copia também dados/artifacts ao lado do exe (mais fácil de inspecionar)
    shutil.copytree(RAIZ / "dados", OUT / "dados", dirs_exist_ok=True)
    (OUT / "artifacts" / "embeddings").mkdir(parents=True, exist_ok=True)
    for f in (RAIZ / "artifacts" / "embeddings").iterdir():
        if f.is_file():
            shutil.copy2(f, OUT / "artifacts" / "embeddings" / f.name)

    guia = OUT / "LEIA-ME_RECRUTADOR.txt"
    guia.write_text(
        """CASE VICIO IA — PACOTE OFFLINE PARA O RECRUTADOR
================================================

O que é
-------
Executável que reproduz a classificação de 659 questões
SEM chamar modelo de linguagem e SEM precisar de internet/API.

Como testar
-----------
1. Abra a pasta CaseVicio_Offline_Recrutador
2. Dê duplo clique em CaseVicioOffline.exe
3. Aguarde o resumo no terminal
4. Veja os arquivos em saida_offline\\

Arquivos gerados
----------------
- publicacao.csv  → decisão por questão (publicar/revisar/fora)
- previsao.txt    → precisão/cobertura previstas
- resumo.txt      → visão rápida para análise humana

O que NÃO faz
-------------
- Não chama OpenAI, Jev, ChatGPT ou qualquer LLM
- Não precisa de chave de API
- Não altera a internet (roda 100% local)

Conteúdo embutido
-----------------
- dados/ (questões, temas, folha-verdade)
- artifacts/embeddings/ (vetores já gerados e versionados)

Régua do case: das publicadas, >=95% devem estar certas.
""",
        encoding="utf-8",
    )

    # Atalho bat
    (OUT / "ABRIR_TESTE_OFFLINE.bat").write_text(
        "@echo off\r\ncd /d \"%~dp0\"\r\nCaseVicioOffline.exe\r\n",
        encoding="utf-8",
    )

    print(f"\nOK → {OUT}")
    print("Envie a pasta inteira (ou zip) ao recrutador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
