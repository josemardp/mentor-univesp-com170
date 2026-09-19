# -*- coding: utf-8 -*-
"""
Servidor HTTP seguro para o painel local do Mentor UNIVESP em loopback (127.0.0.1:8790).
"""

import argparse
import http.server
import json
import mimetypes
import os
import posixpath
import socketserver
import sys
import urllib.parse
from pathlib import Path

EXTENSOES_PERMITIDAS = {
    ".html", ".htm", ".js", ".mjs", ".css", ".json",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".wasm", ".map", ".txt", ".pdf"
}

SEGMENTOS_BLOQUEADOS = {
    ".git", ".github", ".vscode", ".claude", "privado", "tmp",
    "tests", "scripts", "__pycache__", "node_modules", "dados_privados"
}


class PainelHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    server_version = "PainelSeguro/1.1"

    def __init__(self, *args, painel_nome="", raiz_dir="", porta=0, **kwargs):
        self.painel_nome = painel_nome
        self.raiz_dir = Path(raiz_dir).resolve()
        self.porta = porta
        self._caminho_aprovado = None
        super().__init__(*args, directory=str(self.raiz_dir), **kwargs)

    def log_message(self, format, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Connection", "close")
        self.end_headers()
        msg = f"HTTP {code}: {message or 'Acesso nao permitido'}\n"
        self.wfile.write(msg.encode("utf-8"))

    def do_GET(self):
        if self.path == "/__painel_info__":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Connection", "close")
            self.end_headers()
            info = {
                "painel": self.painel_nome,
                "raiz": str(self.raiz_dir),
                "pid": os.getpid(),
                "porta": self.porta,
                "status": "ok"
            }
            self.wfile.write(json.dumps(info).encode("utf-8"))
            return

        valido, caminho_fisico = self._validar_caminho(self.path)
        if not valido or not caminho_fisico:
            self.send_error(404, "Arquivo nao encontrado ou acesso bloqueado")
            return

        self._caminho_aprovado = caminho_fisico
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def do_HEAD(self):
        if self.path == "/__painel_info__":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            return

        valido, caminho_fisico = self._validar_caminho(self.path)
        if not valido or not caminho_fisico:
            self.send_error(404, "Arquivo nao encontrado ou acesso bloqueado")
            return

        self._caminho_aprovado = caminho_fisico
        f = self.send_head()
        if f:
            f.close()

    def translate_path(self, path):
        if self._caminho_aprovado:
            return str(self._caminho_aprovado)
        return str(self.raiz_dir / "__nao_existe__")

    def list_directory(self, path):
        self.send_error(403, "Listagem de diretorio desativada")
        return None

    def _validar_caminho(self, path_req):
        parsed = urllib.parse.urlsplit(path_req)
        clean_path = parsed.path

        prev = ""
        decoded = clean_path
        while prev != decoded:
            prev = decoded
            decoded = urllib.parse.unquote(decoded)

        for char in [':', '<', '>', '"', '|', '?', '*', '\x00', '\\']:
            if char in decoded:
                return False, None

        partes = [p for p in decoded.split('/') if p]

        for seg in partes:
            if seg.startswith(".") or seg.endswith(".") or seg.endswith(" "):
                return False, None
            seg_limpo = seg.strip(". ").lower()
            if seg_limpo in SEGMENTOS_BLOQUEADOS or seg_limpo.startswith("."):
                return False, None

        norm = posixpath.normpath(decoded)
        if norm.startswith("..") or norm.startswith("/.."):
            return False, None

        try:
            rel_path = norm.lstrip("/")
            caminho_fisico = (self.raiz_dir / rel_path).resolve()
        except Exception:
            return False, None

        try:
            relativo = caminho_fisico.relative_to(self.raiz_dir)
        except ValueError:
            return False, None

        for part in relativo.parts:
            part_limpa = part.strip(". ").lower()
            if part_limpa.startswith(".") or part_limpa in SEGMENTOS_BLOQUEADOS:
                return False, None

        if caminho_fisico.is_dir():
            index_file = (caminho_fisico / "index.html").resolve()
            if index_file.is_file():
                try:
                    rel_index = index_file.relative_to(self.raiz_dir)
                    for part in rel_index.parts:
                        p_clean = part.strip(". ").lower()
                        if p_clean.startswith(".") or p_clean in SEGMENTOS_BLOQUEADOS:
                            return False, None
                    return True, index_file
                except ValueError:
                    return False, None
            return False, None

        if caminho_fisico.is_file():
            nome = caminho_fisico.name.lower()
            if nome.startswith(".") or nome.endswith(".") or nome.endswith(" "):
                return False, None
            if nome.strip(". ") in SEGMENTOS_BLOQUEADOS:
                return False, None
            ext = caminho_fisico.suffix.lower()
            if ext not in EXTENSOES_PERMITIDAS:
                return False, None
            return True, caminho_fisico

        return False, None


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description="Servidor HTTP seguro para o painel UNIVESP")
    parser.add_argument("--painel", default="univesp", help="Nome identificador do painel")
    parser.add_argument("--porta", type=int, default=8790, help="Porta TCP em 127.0.0.1")
    parser.add_argument("--raiz", default=str(Path(__file__).resolve().parent.parent / "docs"), help="Diretorio raiz a ser servido")
    args = parser.parse_args()

    raiz_path = Path(args.raiz).resolve()
    if not raiz_path.exists() or not raiz_path.is_dir():
        print(f"Erro: Raiz '{args.raiz}' nao existe ou nao e diretorio.", file=sys.stderr)
        sys.exit(1)

    def handler_factory(*h_args, **h_kwargs):
        return PainelHTTPRequestHandler(
            *h_args,
            painel_nome=args.painel,
            raiz_dir=str(raiz_path),
            porta=args.porta,
            **h_kwargs
        )

    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), handler_factory)
    except Exception as e:
        print(f"Erro ao vincular na porta {args.porta}: {e}", file=sys.stderr)
        sys.exit(2)

    print(f"[OK] Servidor '{args.painel}' iniciado em http://127.0.0.1:{args.porta}/ (PID {os.getpid()})")
    sys.stdout.flush()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
