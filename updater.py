# Copyright (C) 2025 Denis Garcia Barbeto / Alphas Consultoria Digital
# CNPJ: 40.268.116/0001-20
# GNU General Public License v3 — consulte o arquivo LICENSE.

"""
Auto-Updater do Alphas Gerenciador do Windows.
- Verifica versão no GitHub Releases
- Baixa novo EXE se disponível
- Substitui e reinicia o app automaticamente
- Sem janelas PowerShell piscando
"""
import os, sys, json, threading, urllib.request, tempfile, shutil, subprocess

# ── Configuração ──────────────────────────────────────────────────────────────
GITHUB_USER  = "denisbarbeto"
GITHUB_REPO  = "AlphasGerenciador"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.json")
# ─────────────────────────────────────────────────────────────────────────────

def get_local_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("version", "0.0.0")
    except:
        return "0.0.0"

def get_remote_release():
    try:
        req = urllib.request.Request(RELEASES_API, headers={
            "User-Agent": "AlphasGerenciador-Updater/1.0",
            "Accept":     "application/vnd.github.v3+json"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        tag    = data.get("tag_name", "").lstrip("v")
        body   = data.get("body", "Sem notas de versão.")[:400]
        assets = data.get("assets", [])

        exe_url = next((a["browser_download_url"] for a in assets
                        if a.get("name","").endswith(".exe")), None)
        if not exe_url:
            return None

        return {"version": tag, "download_url": exe_url,
                "changelog": body, "release_name": data.get("name", f"v{tag}")}
    except:
        return None

def _vtuple(v):
    try:    return tuple(int(x) for x in str(v).split("."))
    except: return (0,0,0)

def has_update(remote):
    if not remote: return False
    return _vtuple(remote.get("version","0")) > _vtuple(get_local_version())

def download_and_install(download_url, progress_cb=None):
    try:
        tmp_dir = tempfile.mkdtemp()
        tmp_exe = os.path.join(tmp_dir, "AlphasGerenciador_new.exe")

        if progress_cb: progress_cb(5, "Conectando ao servidor...")

        req = urllib.request.Request(download_url,
                                     headers={"User-Agent":"AlphasGerenciador-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(tmp_exe, "wb") as f:
                while True:
                    block = resp.read(8192)
                    if not block: break
                    f.write(block)
                    downloaded += len(block)
                    if total and progress_cb:
                        pct = int((downloaded / total) * 85)
                        progress_cb(pct, f"Baixando... {downloaded/1048576:.1f} MB")

        if progress_cb: progress_cb(90, "Preparando instalação...")

        if not getattr(sys, "frozen", False):
            if progress_cb: progress_cb(100, "Modo dev — baixe manualmente.")
            return True, "Em modo dev."

        current_exe = sys.executable

        # BAT oculto: aguarda fechar → copia → reinicia
        bat = f"""@echo off
ping 127.0.0.1 -n 3 >nul
copy /y "{tmp_exe}" "{current_exe}" >nul
start "" "{current_exe}"
del "%~f0"
"""
        bat_path = os.path.join(tmp_dir, "update.bat")
        with open(bat_path, "w") as f:
            f.write(bat)

        if progress_cb: progress_cb(100, "Reiniciando com nova versão...")

        subprocess.Popen(["cmd.exe", "/c", bat_path],
                         creationflags=subprocess.CREATE_NO_WINDOW,
                         close_fds=True)
        return True, "Atualização instalada! Reiniciando..."

    except Exception as e:
        return False, f"Erro: {e}"

def check_async(on_found, on_none=None):
    def _w():
        remote = get_remote_release()
        if has_update(remote): on_found(remote)
        elif on_none:          on_none()
    threading.Thread(target=_w, daemon=True).start()
