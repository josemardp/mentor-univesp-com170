# -*- coding: utf-8 -*-
"""Persistência JSON atômica e versionamento do cache."""
import json
import os
import tempfile
from pathlib import Path

from configuracao import DATA_PATH, ESTADO_PATH, VERSAO_CACHE


def preparar_json(caminho: Path, conteudo) -> Path:
    """Cria e sincroniza um temporário único no mesmo volume do destino."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, nome = tempfile.mkstemp(
        prefix=f".{caminho.name}.", suffix=".tmp", dir=str(caminho.parent)
    )
    temporario = Path(nome)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as arquivo:
            json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        return temporario
    except Exception:
        temporario.unlink(missing_ok=True)
        raise


def gravar_json(caminho: Path, conteudo) -> None:
    """Substitui um JSON atomicamente e limpa o temporário em qualquer falha."""
    temporario = preparar_json(caminho, conteudo)
    try:
        os.replace(temporario, caminho)
    finally:
        temporario.unlink(missing_ok=True)


def gravar_snapshot(
    data,
    estado,
    data_path: Path = DATA_PATH,
    estado_path: Path = ESTADO_PATH,
) -> None:
    """Grava cache primeiro e usa ``data.json`` como marcador final."""
    temp_estado = preparar_json(estado_path, estado)
    temp_data = preparar_json(data_path, data)
    try:
        os.replace(temp_estado, estado_path)
        os.replace(temp_data, data_path)
    finally:
        temp_estado.unlink(missing_ok=True)
        temp_data.unlink(missing_ok=True)


def carregar(caminho: Path, padrao, critico: bool = False):
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except Exception as erro:
            mensagem = f"JSON corrompido em {caminho}: {type(erro).__name__}"
            if critico:
                raise RuntimeError(mensagem) from erro
            print(f"::warning::{mensagem}; vou reconstruir esta fonte.")
            return padrao
    return padrao


def normalizar_estado(estado: dict | None) -> dict:
    """Expõe versão de esquema sem descartar caches legados."""
    atual = dict(estado or {})
    atual.setdefault("_schema_version", VERSAO_CACHE)
    return atual
