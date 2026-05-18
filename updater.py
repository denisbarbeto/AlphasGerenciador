# Copyright (C) 2025 Denis Garcia Barbeto / Alphas Consultoria Digital
# CNPJ: 40.268.116/0001-20
# GNU General Public License v3 — consulte o arquivo LICENSE.

"""
Auto-Updater do Alphas Gerenciador do Windows.
- Verifica versão no GitHub Releases
- Baixa novo EXE via PowerShell (nativo Windows — não trava)
- Substitui e reinicia o app automaticamente via BAT oculto
"""
import os, sys, json, threading, urllib.request, tempfile, subprocess, socket, time

# ── Configuração ──────────────────────────────────────────────────────────────
GITHUB_USER  = "denisbarbeto"
GITHUB_REPO  = "AlphasGerenciador"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.json")
_NO_WIN      = subprocess.CREATE_NO_WINDOW
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
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(10)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        finally:
            socket.setdefaulttimeout(old)

        tag    = data.get("tag_name", "").lstrip("v")
        body   = data.get("body", "Sem notas de versão.")[:400]
        assets = data.get("assets", [])

        # Prefere AlphasGerenciador.exe (app principal, nunca o Setup)
        exe_url = next((a["browser_download_url"] for a in assets
                        if a.get("name", "") == "AlphasGerenciador.exe"), None)
        if not exe_url:
            exe_url = next((a["browser_download_url"] for a in assets
                            if a.get("name", "").endswith(".exe")
                            and "Setup" not in a.get("name", "")), None)
        if not exe_url:
            return None

        # Pega o tamanho do EXE para a barra de progresso
        exe_size = next((a["size"] for a in assets
                         if a.get("name", "") == "AlphasGerenciador.exe"), 0)

        return {"version": tag, "download_url": exe_url, "exe_size": exe_size,
                "changelog": body, "release_name": data.get("name", f"v{tag}")}
    except:
        return None

def _vtuple(v):
    try:    return tuple(int(x) for x in str(v).split("."))
    except: return (0, 0, 0)

def has_update(remote):
    if not remote: return False
    return _vtuple(remote.get("version", "0")) > _vtuple(get_local_version())

def download_and_install(download_url, progress_cb=None, cancel_event=None,
                         expected_size=0):
    """
    Baixa via PowerShell (nativo Windows) e instala via BAT oculto.
    Usa polling do tamanho do arquivo para mostrar progresso real.
    cancel_event: threading.Event — sete para cancelar.
    """
    try:
        tmp_dir = tempfile.mkdtemp()
        tmp_exe = os.path.join(tmp_dir, "AlphasGerenciador_new.exe")

        if progress_cb: progress_cb(2, "Iniciando download...")

        # ── Download via PowerShell — muito mais confiável que urllib no Windows ──
        ps_cmd = (
            f"$ProgressPreference='SilentlyContinue'; "
            f"Invoke-WebRequest -Uri '{download_url}' "
            f"-OutFile '{tmp_exe}' -UseBasicParsing"
        )
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-WindowStyle", "Hidden", "-Command", ps_cmd],
            creationflags=_NO_WIN,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Polling do tamanho do arquivo para atualizar a barra de progresso
        while proc.poll() is None:
            if cancel_event and cancel_event.is_set():
                proc.terminate()
                return False, "Download cancelado pelo usuário."

            downloaded = os.path.getsize(tmp_exe) if os.path.exists(tmp_exe) else 0
            if expected_size and progress_cb:
                pct = int((downloaded / expected_size) * 85)
                progress_cb(min(pct, 84),
                            f"Baixando... {downloaded/1048576:.1f} / "
                            f"{expected_size/1048576:.1f} MB")
            elif progress_cb and downloaded > 0:
                # Sem tamanho total: mostra MB baixados
                progress_cb(min(50, int(downloaded / (1024*512))),
                            f"Baixando... {downloaded/1048576:.1f} MB")
            time.sleep(0.5)

        if cancel_event and cancel_event.is_set():
            return False, "Download cancelado pelo usuário."

        # Verifica se o download foi bem sucedido
        if proc.returncode != 0 or not os.path.exists(tmp_exe):
            stderr = proc.stderr.read().decode("utf-8", errors="ignore")[:300]
            return False, f"Falha no download: {stderr or 'arquivo não gerado'}"

        size_mb = os.path.getsize(tmp_exe) / 1048576
        if size_mb < 1:
            return False, "Arquivo baixado parece inválido (< 1 MB)."

        if progress_cb: progress_cb(90, f"Baixado {size_mb:.1f} MB — preparando...")

        # ── Modo dev: não substitui o EXE ────────────────────────────────────────
        if not getattr(sys, "frozen", False):
            if progress_cb: progress_cb(100, "Modo dev — baixe manualmente no GitHub.")
            return False, "Modo dev: abra github.com/denisbarbeto/AlphasGerenciador/releases e baixe manualmente."

        current_exe = sys.executable

        # ── BAT oculto: espera o app fechar → copia → reinicia ───────────────────
        bat = (
            "@echo off\r\n"
            "ping 127.0.0.1 -n 5 >nul\r\n"          # espera ~5 segundos
            f'copy /y "{tmp_exe}" "{current_exe}" >nul\r\n'
            f'start "" "{current_exe}"\r\n'
            "del \"%~f0\"\r\n"
        )
        bat_path = os.path.join(tmp_dir, "update.bat")
        with open(bat_path, "w", encoding="mbcs") as f:
            f.write(bat)

        if progress_cb: progress_cb(100, "✅ Pronto! Reiniciando...")

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=_NO_WIN,
            close_fds=True
        )
        return True, "✅ Atualização pronta! O app vai reiniciar em instantes."

    except Exception as e:
        return False, f"Erro: {e}"

def check_async(on_found, on_none=None):
    def _w():
        remote = get_remote_release()
        if has_update(remote): on_found(remote)
        elif on_none:          on_none()
    threading.Thread(target=_w, daemon=True).start()
