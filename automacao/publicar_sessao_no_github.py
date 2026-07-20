"""
Sobe automacao/storage_state.json como segredo criptografado do GitHub
(AVA_STORAGE_STATE) e apaga a copia local em texto puro.

Rodar depois de automacao/capturar_sessao.py, sempre que a sessao
expirar e precisar renovar.
"""
import subprocess
import sys
from pathlib import Path

REPO = "esdraaline/mentor-univesp-com170"
STATE_PATH = Path(__file__).parent / "storage_state.json"


def main():
    if not STATE_PATH.exists():
        print("storage_state.json nao encontrado. Rode capturar_sessao.py primeiro.")
        sys.exit(1)

    result = subprocess.run(
        ["gh", "secret", "set", "AVA_STORAGE_STATE", "--repo", REPO],
        stdin=open(STATE_PATH, "rb"),
    )
    if result.returncode != 0:
        print("Falha ao subir o segredo. A copia local NAO foi apagada.")
        sys.exit(1)

    STATE_PATH.unlink()
    print("Segredo atualizado no GitHub e copia local apagada.")


if __name__ == "__main__":
    main()
