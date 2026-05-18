# Copyright (C) 2025 Denis Garcia Barbeto / Alphas Consultoria Digital
# CNPJ: 40.268.116/0001-20
# Este programa é distribuído sob a GNU General Public License v3.
# Consulte o arquivo LICENSE para mais detalhes.

"""
Instalador Wizard — Alphas Gerenciador do Windows
4 etapas: Boas-vindas → Pasta → Instalando → Concluído
"""
import sys, os, shutil, subprocess, threading
import tkinter as tk
import tkinter.filedialog as fd
import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import *

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

APP_NAME     = "Alphas Gerenciador do Windows"
EXE_NAME     = "AlphasGerenciador.exe"
PUBLISHER    = "Alphas Consultoria Digital"
VERSION      = "1.0.0"
DEFAULT_PATH = os.path.join(
    os.environ.get("ProgramFiles", r"C:\Program Files"),
    "AlphasGerenciador"
)

_NO_WIN = subprocess.CREATE_NO_WINDOW


# ── Helpers — todos os subprocessos 100% ocultos ──────────────────────────────
def _ps(cmd):
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-WindowStyle", "Hidden", "-Command", cmd],
            capture_output=True, timeout=30,
            creationflags=_NO_WIN
        )
    except:
        pass


def create_shortcut(target, link_path):
    t = target.replace("\\", "\\\\")
    l = link_path.replace("\\", "\\\\")
    w = os.path.dirname(target).replace("\\", "\\\\")
    _ps(f"""
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('{l}')
$sc.TargetPath = '{t}'
$sc.WorkingDirectory = '{w}'
$sc.Save()
""")


def register_uninstall(install_dir, exe_path):
    key = r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\AlphasGerenciador"
    _ps(f"""
New-Item -Path '{key}' -Force | Out-Null
Set-ItemProperty -Path '{key}' -Name DisplayName    -Value '{APP_NAME}'
Set-ItemProperty -Path '{key}' -Name Publisher       -Value '{PUBLISHER}'
Set-ItemProperty -Path '{key}' -Name DisplayVersion  -Value '{VERSION}'
Set-ItemProperty -Path '{key}' -Name InstallLocation -Value '{install_dir}'
Set-ItemProperty -Path '{key}' -Name UninstallString -Value '"{exe_path}" --uninstall'
Set-ItemProperty -Path '{key}' -Name NoModify        -Value 1 -Type DWord
Set-ItemProperty -Path '{key}' -Name NoRepair        -Value 1 -Type DWord
""")


def exclude_from_defender(path):
    _ps(f'Add-MpPreference -ExclusionPath "{path}" -ErrorAction SilentlyContinue')


# ── Lógica de instalação (thread separada) ────────────────────────────────────
def do_install(install_dir, exe_source, progress_cb, done_cb):
    def _work():
        try:
            progress_cb(8,  "Criando pasta de instalação...")
            os.makedirs(install_dir, exist_ok=True)

            progress_cb(20, f"Copiando {EXE_NAME}...")
            dest_exe = os.path.join(install_dir, EXE_NAME)
            shutil.copy2(exe_source, dest_exe)

            # version.json ao lado do EXE
            base = os.path.dirname(exe_source)
            src_v = os.path.join(base, "version.json")
            if os.path.exists(src_v):
                shutil.copy2(src_v, os.path.join(install_dir, "version.json"))

            progress_cb(40, "Adicionando exceção no Windows Defender...")
            exclude_from_defender(install_dir)

            progress_cb(55, "Criando atalho na Área de Trabalho...")
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            create_shortcut(dest_exe, os.path.join(desktop, f"{APP_NAME}.lnk"))

            progress_cb(70, "Criando atalho no Menu Iniciar...")
            start_menu = os.path.join(
                os.environ.get("APPDATA", ""),
                r"Microsoft\Windows\Start Menu\Programs"
            )
            os.makedirs(start_menu, exist_ok=True)
            create_shortcut(dest_exe, os.path.join(start_menu, f"{APP_NAME}.lnk"))

            progress_cb(85, "Registrando em Programas e Recursos...")
            register_uninstall(install_dir, dest_exe)

            progress_cb(100, "Concluído!")
            done_cb(True, dest_exe)

        except Exception as e:
            done_cb(False, str(e))

    threading.Thread(target=_work, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# WIZARD — 4 etapas
# ══════════════════════════════════════════════════════════════════════════════
STEPS      = ["Boas-vindas", "Pasta", "Instalando", "Concluído"]
PAGE_ORDER = ["welcome", "folder", "installing", "done"]


class InstallerApp(ctk.CTk):
    def __init__(self, exe_source=None):
        super().__init__()
        self.title(f"Instalador — {APP_NAME}")
        self.geometry("580x530")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

        # localiza o EXE principal a ser instalado
        if exe_source:
            self._exe_source = exe_source
        elif getattr(sys, "frozen", False):
            # compilado com PyInstaller: o EXE principal está em sys._MEIPASS
            base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            self._exe_source = os.path.join(base, EXE_NAME)
        else:
            self._exe_source = os.path.join(
                os.path.dirname(__file__), "dist", EXE_NAME
            )

        self._path_var   = tk.StringVar(value=DEFAULT_PATH)
        self._open_after = tk.BooleanVar(value=True)
        self._dest_exe   = None
        self._step       = 0
        self._pages      = {}

        self._build_header()
        self._build_content_area()
        self._build_footer()
        self._build_page_welcome()
        self._build_page_folder()
        self._build_page_installing()
        self._build_page_done()
        self._go_to(0)

    # ── Header fixo (logo + indicador de etapas) ──────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, height=82, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkFrame(hdr, height=3, fg_color=ORANGE, corner_radius=0).pack(fill="x", side="top")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=6)

        # Esquerda — logo
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="⚙", font=("Segoe UI", 30),
                     text_color=ORANGE).pack(side="left", padx=(0, 10))
        tf = ctk.CTkFrame(left, fg_color="transparent")
        tf.pack(side="left")
        ctk.CTkLabel(tf, text="Alphas Consultoria Digital",
                     font=("Segoe UI", 13, "bold"), text_color=TEXT_WHITE).pack(anchor="w")
        ctk.CTkLabel(tf, text=f"Instalador  —  v{VERSION}",
                     font=("Segoe UI", 10), text_color="#8BA3C7").pack(anchor="w")

        # Direita — etapas
        self._step_labels = []
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")
        for i, name in enumerate(STEPS):
            col = ctk.CTkFrame(right, fg_color="transparent")
            col.pack(side="left")
            dot = ctk.CTkLabel(col, text="●", font=("Segoe UI", 11), text_color="#3A5280")
            dot.pack()
            lbl = ctk.CTkLabel(col, text=name, font=("Segoe UI", 8), text_color="#3A5280")
            lbl.pack()
            self._step_labels.append((dot, lbl))
            if i < len(STEPS) - 1:
                ctk.CTkLabel(right, text=" › ", font=("Segoe UI", 11),
                             text_color="#3A5280").pack(side="left", pady=(0, 14))

    def _update_steps(self, step):
        for i, (dot, lbl) in enumerate(self._step_labels):
            if i < step:
                dot.configure(text_color=SUCCESS)
                lbl.configure(text_color=SUCCESS)
            elif i == step:
                dot.configure(text_color=ORANGE)
                lbl.configure(text_color=ORANGE)
            else:
                dot.configure(text_color="#3A5280")
                lbl.configure(text_color="#3A5280")

    # ── Área de conteúdo (troca por etapa) ────────────────────────────────────
    def _build_content_area(self):
        self._content = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self._content.pack(fill="both", expand=True)

    # ── Footer fixo (botões Voltar / Próximo) ─────────────────────────────────
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=BG_CARD, height=68, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        ctk.CTkFrame(footer, height=1, fg_color="#E2E8F0", corner_radius=0).pack(fill="x", side="top")

        btn_area = ctk.CTkFrame(footer, fg_color="transparent")
        btn_area.pack(side="right", padx=24, pady=14)

        self._back_btn = ctk.CTkButton(
            btn_area, text="← Voltar", width=110, height=38,
            fg_color="transparent", hover_color=BG_HOVER,
            text_color=TEXT_MID, border_width=1, border_color="#CBD5E0",
            corner_radius=8, font=("Segoe UI", 12),
            command=self._on_back
        )
        self._back_btn.pack(side="left", padx=(0, 10))

        self._next_btn = ctk.CTkButton(
            btn_area, text="Próximo →", width=155, height=38,
            fg_color=ORANGE, hover_color=ORANGE_DARK,
            text_color=TEXT_WHITE, corner_radius=8,
            font=("Segoe UI", 12, "bold"),
            command=self._on_next
        )
        self._next_btn.pack(side="left")

    # ── Página 1 — Boas-vindas ────────────────────────────────────────────────
    def _build_page_welcome(self):
        p = ctk.CTkFrame(self._content, fg_color=BG_MAIN, corner_radius=0)
        self._pages["welcome"] = p

        ctk.CTkFrame(p, height=20, fg_color="transparent").pack()
        ctk.CTkLabel(p, text="⚙", font=("Segoe UI", 54), text_color=ORANGE).pack()
        ctk.CTkLabel(p, text="Bem-vindo ao Instalador",
                     font=("Segoe UI", 18, "bold"), text_color=BLUE).pack(pady=(8, 2))
        ctk.CTkLabel(p, text=APP_NAME,
                     font=("Segoe UI", 12), text_color=TEXT_MID).pack()

        ctk.CTkFrame(p, height=18, fg_color="transparent").pack()
        card = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=10)
        card.pack(padx=50, fill="x")
        ctk.CTkLabel(
            card,
            text="Este assistente irá instalar o Alphas Gerenciador do Windows\n"
                 "no seu computador. Clique em Próximo para continuar.",
            font=("Segoe UI", 11), text_color=TEXT_MID,
            wraplength=430, justify="center"
        ).pack(pady=18, padx=20)

    # ── Página 2 — Escolha de pasta ───────────────────────────────────────────
    def _build_page_folder(self):
        p = ctk.CTkFrame(self._content, fg_color=BG_MAIN, corner_radius=0)
        self._pages["folder"] = p

        ctk.CTkLabel(p, text="Pasta de Instalação",
                     font=("Segoe UI", 15, "bold"), text_color=BLUE
                     ).pack(anchor="w", padx=32, pady=(22, 4))
        ctk.CTkLabel(p, text="Escolha onde o programa será instalado:",
                     font=("Segoe UI", 11), text_color=TEXT_MID
                     ).pack(anchor="w", padx=32)

        path_row = ctk.CTkFrame(p, fg_color="transparent")
        path_row.pack(fill="x", padx=32, pady=(8, 0))
        ctk.CTkEntry(path_row, textvariable=self._path_var,
                     height=36, font=("Segoe UI", 11)
                     ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            path_row, text="📁 Alterar", width=100, height=36,
            fg_color="transparent", hover_color=BG_HOVER,
            text_color=TEXT_DARK, border_width=1, border_color="#CBD5E0",
            corner_radius=6, font=("Segoe UI", 11),
            command=self._pick_folder
        ).pack(side="left")

        ctk.CTkLabel(p, text="O instalador irá:",
                     font=("Segoe UI", 12, "bold"), text_color=BLUE
                     ).pack(anchor="w", padx=32, pady=(18, 6))
        card = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=10)
        card.pack(fill="x", padx=32)
        for item in [
            "✅  Copiar AlphasGerenciador.exe para a pasta escolhida",
            "✅  Criar atalho na Área de Trabalho",
            "✅  Criar atalho no Menu Iniciar",
            "✅  Adicionar exceção no Windows Defender",
            "✅  Registrar em Programas e Recursos",
        ]:
            ctk.CTkLabel(card, text=item, font=("Segoe UI", 11),
                         text_color=TEXT_MID, anchor="w"
                         ).pack(anchor="w", padx=16, pady=3)
        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()

    # ── Página 3 — Instalando ─────────────────────────────────────────────────
    def _build_page_installing(self):
        p = ctk.CTkFrame(self._content, fg_color=BG_MAIN, corner_radius=0)
        self._pages["installing"] = p

        ctk.CTkFrame(p, height=44, fg_color="transparent").pack()
        ctk.CTkLabel(p, text="Instalando...",
                     font=("Segoe UI", 17, "bold"), text_color=BLUE).pack()
        ctk.CTkLabel(p, text="Por favor aguarde. Não feche esta janela.",
                     font=("Segoe UI", 11), text_color=TEXT_MID).pack(pady=(4, 28))

        self._bar = ctk.CTkProgressBar(p, width=460, height=14,
                                        fg_color="#E2E8F0", progress_color=ORANGE,
                                        corner_radius=7)
        self._bar.pack()
        self._bar.set(0)

        self._pct_lbl = ctk.CTkLabel(p, text="0%",
                                      font=("Segoe UI", 12, "bold"), text_color=ORANGE)
        self._pct_lbl.pack(pady=(6, 4))

        self._status_lbl = ctk.CTkLabel(p, text="",
                                         font=("Segoe UI", 10), text_color=TEXT_MID)
        self._status_lbl.pack()

    # ── Página 4 — Concluído ──────────────────────────────────────────────────
    def _build_page_done(self):
        p = ctk.CTkFrame(self._content, fg_color=BG_MAIN, corner_radius=0)
        self._pages["done"] = p

        ctk.CTkFrame(p, height=20, fg_color="transparent").pack()
        ctk.CTkLabel(p, text="✅", font=("Segoe UI", 52)).pack()
        ctk.CTkLabel(p, text="Instalação Concluída!",
                     font=("Segoe UI", 18, "bold"), text_color=SUCCESS).pack(pady=(8, 4))
        self._done_path_lbl = ctk.CTkLabel(p, text="",
                                            font=("Segoe UI", 10), text_color=TEXT_MID)
        self._done_path_lbl.pack(pady=(0, 20))

        self._open_chk = ctk.CTkCheckBox(
            p,
            text="Iniciar o Alphas Gerenciador agora",
            variable=self._open_after,
            font=("Segoe UI", 12), text_color=TEXT_DARK,
            fg_color=ORANGE, hover_color=ORANGE_DARK,
            checkmark_color=TEXT_WHITE
        )
        self._open_chk.pack()

    # ── Navegação entre etapas ────────────────────────────────────────────────
    def _go_to(self, step):
        self._step = step
        for p in self._pages.values():
            p.pack_forget()
        self._pages[PAGE_ORDER[step]].pack(fill="both", expand=True)
        self._update_steps(step)

        is_installing = step == 2
        is_done       = step == 3

        self._back_btn.configure(
            state="disabled" if is_installing or step == 0 else "normal"
        )

        if is_done:
            self._next_btn.configure(
                text="✔  Concluir", state="normal",
                fg_color=SUCCESS, hover_color="#276749"
            )
        elif is_installing:
            self._next_btn.configure(state="disabled", text="Instalando...",
                                      fg_color=ORANGE)
        elif step == 1:
            self._next_btn.configure(
                text="⚙  Instalar", state="normal",
                fg_color=ORANGE, hover_color=ORANGE_DARK
            )
        else:
            self._next_btn.configure(
                text="Próximo →", state="normal",
                fg_color=ORANGE, hover_color=ORANGE_DARK
            )

    def _on_back(self):
        if self._step > 0 and self._step != 2:
            self._go_to(self._step - 1)

    def _on_next(self):
        if self._step == 0:
            self._go_to(1)
        elif self._step == 1:
            self._start_install()
        elif self._step == 3:
            self._finish()

    def _pick_folder(self):
        self.withdraw()
        try:
            initial = self._path_var.get()
            if not os.path.isdir(initial):
                initial = os.path.expanduser("~")
            d = fd.askdirectory(
                title="Escolha a pasta de instalação",
                initialdir=initial, parent=None, mustexist=False
            )
            if d:
                self._path_var.set(d.replace("/", "\\"))
        finally:
            self.deiconify()
            self.lift()
            self.focus_force()

    def _start_install(self):
        self._go_to(2)
        do_install(
            install_dir = self._path_var.get(),
            exe_source  = self._exe_source,
            progress_cb = self._on_progress,
            done_cb     = self._on_done,
        )

    def _on_progress(self, pct, msg):
        self.after(0, lambda: [
            self._bar.set(pct / 100),
            self._pct_lbl.configure(text=f"{pct}%"),
            self._status_lbl.configure(text=msg),
        ])

    def _on_done(self, ok, info):
        def _ui():
            if ok:
                self._dest_exe = info
                self._done_path_lbl.configure(
                    text=f"Instalado em: {os.path.dirname(info)}"
                )
                self._go_to(3)
            else:
                # Volta para etapa de pasta com mensagem de erro
                self._go_to(1)
                self._status_lbl.configure(
                    text=f"❌  Erro durante instalação: {info}", text_color=DANGER
                )
        self.after(0, _ui)

    def _finish(self):
        if self._open_after.get() and self._dest_exe:
            subprocess.Popen([self._dest_exe], creationflags=_NO_WIN)
        self.destroy()


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    InstallerApp(src).mainloop()
