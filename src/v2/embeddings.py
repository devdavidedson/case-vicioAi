"""Embeddings OpenAI com cache versionado em disco (gerados antes da decisão)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

MODELO_PADRAO = "text-embedding-3-small"
BATCH = 64


def _cliente(raiz: Path):
    """Import preguiçoso: modo offline não precisa do SDK OpenAI."""
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(raiz / ".env")
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        raise RuntimeError("OPENAI_API_KEY ausente no .env")
    return OpenAI(api_key=chave)


def _hash_texto(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


class CacheEmbeddings:
    def __init__(self, pasta: Path, modelo: str = MODELO_PADRAO):
        self.pasta = pasta
        self.modelo = modelo
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.meta_path = pasta / "meta.json"
        self.vecs_path = pasta / "vetores.npz"
        self.index_path = pasta / "indice.json"
        self._vecs: dict[str, np.ndarray] = {}
        self._carregar()

    def _carregar(self) -> None:
        if self.index_path.exists() and self.vecs_path.exists():
            indice = json.loads(self.index_path.read_text(encoding="utf-8"))
            data = np.load(self.vecs_path)
            for chave, nome in indice.items():
                if nome in data:
                    self._vecs[chave] = data[nome]
            meta = {}
            if self.meta_path.exists():
                meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
            if meta.get("modelo") and meta["modelo"] != self.modelo:
                # modelo mudou: mantém cache antigo sob outras chaves, gera novas
                pass

    def salvar(self) -> None:
        if not self._vecs:
            return
        indice = {}
        arrays = {}
        for i, (chave, vec) in enumerate(self._vecs.items()):
            nome = f"v{i}"
            indice[chave] = nome
            arrays[nome] = vec.astype(np.float32)
        np.savez_compressed(self.vecs_path, **arrays)
        self.index_path.write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
        self.meta_path.write_text(
            json.dumps(
                {
                    "modelo": self.modelo,
                    "dim": int(next(iter(self._vecs.values())).shape[0]),
                    "n": len(self._vecs),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def chave(self, kind: str, oid: str, texto: str) -> str:
        return f"{self.modelo}:{kind}:{oid}:{_hash_texto(texto)}"

    def obter_muitos(
        self,
        raiz: Path,
        itens: list[tuple[str, str, str]],
        force: bool = False,
        offline: bool = False,
    ) -> dict[str, np.ndarray]:
        """itens: lista de (kind, id, texto). Retorna mapa id -> vetor.

        offline=True: nunca chama API; exige vetores já no cache.
        """
        faltam_txt: list[tuple[str, str]] = []  # (cache_key, texto)
        mapa_id_chave: dict[str, str] = {}
        for kind, oid, texto in itens:
            ck = self.chave(kind, oid, texto)
            mapa_id_chave[oid] = ck
            if force or ck not in self._vecs:
                faltam_txt.append((ck, texto))

        # dedup por cache key
        uniq: dict[str, str] = {}
        for ck, texto in faltam_txt:
            uniq[ck] = texto
        pendentes = list(uniq.items())

        if pendentes:
            if offline:
                raise RuntimeError(
                    f"Modo offline: faltam {len(pendentes)} embeddings no cache. "
                    "Rode antes: python -m src.v2.pipeline_v2"
                )
            cliente = _cliente(raiz)
            for i in range(0, len(pendentes), BATCH):
                lote = pendentes[i : i + BATCH]
                textos = [t if t.strip() else " " for _, t in lote]
                resp = cliente.embeddings.create(model=self.modelo, input=textos)
                for (ck, _), item in zip(lote, resp.data):
                    self._vecs[ck] = np.array(item.embedding, dtype=np.float32)
            self.salvar()

        return {oid: self._vecs[mapa_id_chave[oid]] for kind, oid, texto in itens}


def cosseno(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
