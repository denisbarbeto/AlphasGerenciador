# Copyright (C) 2025 Denis Garcia Barbeto / Alphas Consultoria Digital
# CNPJ: 40.268.116/0001-60
# Este programa é distribuído sob a GNU General Public License v3.
# Consulte o arquivo LICENSE para mais detalhes.

"""
Alphas Gerenciador do Windows — Janela Principal
"""
import sys, os, threading, platform
import tkinter as tk
import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theme   import *
from widgets import StatusBar, ConfirmDialog
import backend as B
import updater as U
from modules.pages import (DashboardPage, UpdatesPage, HistoryPage, CleanerPage,
                            AppsPage, StartupPage, NetworkPage, ServicesPage,
                            RestorePage, BackupPage, GodModePage)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR BUTTON
# ══════════════════════════════════════════════════════════════════════════════
class SidebarBtn(ctk.CTkFrame):
    def __init__(self, parent, icon, label, key, on_click):
        super().__init__(parent, fg_color="transparent", cursor="hand2")
        self.key      = key
        self._on_click = on_click
        self._active  = False

        self._bg = ctk.CTkFrame(self, fg_color="transparent", corner_radius=8)
        self._bg.pack(fill="x", padx=6, pady=1)

        self._icon_lbl = ctk.CTkLabel(self._bg, text=icon, font=("Segoe UI", 18),
                                       width=36, text_color=ORANGE)
        self._icon_lbl.pack(side="left", padx=(10,4), pady=8)
        self._text_lbl = ctk.CTkLabel(self._bg, text=label, font=("Segoe UI", 12),
                                       text_color=TEXT_WHITE, anchor="w")
        self._text_lbl.pack(side="left", fill="x", expand=True)

        for w in [self, self._bg, self._icon_lbl, self._text_lbl]:
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>",    self._hover_on)
            w.bind("<Leave>",    self._hover_off)

    def _click(self, _=None):   self._on_click(self.key)
    def _hover_on(self, _=None):
        if not self._active: self._bg.configure(fg_color="#2A3F6E")
    def _hover_off(self, _=None):
        if not self._active: self._bg.configure(fg_color="transparent")

    def set_active(self, val: bool):
        self._active = val
        if val:
            self._bg.configure(fg_color=ORANGE)
            self._text_lbl.configure(font=("Segoe UI",12,"bold"), text_color=TEXT_WHITE)
            self._icon_lbl.configure(text_color=TEXT_WHITE)
        else:
            self._bg.configure(fg_color="transparent")
            self._text_lbl.configure(font=("Segoe UI",12), text_color=TEXT_WHITE)
            self._icon_lbl.configure(text_color=ORANGE)


# ══════════════════════════════════════════════════════════════════════════════
# JANELA DE UPDATE
# ══════════════════════════════════════════════════════════════════════════════
class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent, remote_info):
        super().__init__(parent)
        self.title("Atualização Disponível")
        self.geometry("500x340")
        self.resizable(False, False)
        self.configure(fg_color=BG_CARD)
        self.grab_set()
        self._remote  = remote_info
        self._running = False
        self._build()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, height=70, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkFrame(hdr, height=3, fg_color=SUCCESS, corner_radius=0).pack(fill="x")
        ctk.CTkLabel(hdr, text="🔄  Nova Versão Disponível!",
                     font=("Segoe UI",15,"bold"), text_color=TEXT_WHITE).pack(pady=14)

        # Info
        ver_local  = U.get_local_version()
        ver_remote = self._remote.get("version","?")
        ctk.CTkLabel(self, text=f"Versão atual:  {ver_local}   →   Nova versão:  {ver_remote}",
                     font=("Segoe UI",12,"bold"), text_color=BLUE).pack(pady=(16,4))

        # Changelog
        log_frame = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=8)
        log_frame.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(log_frame, text="O que há de novo:",
                     font=("Segoe UI",10,"bold"), text_color=TEXT_MID).pack(anchor="w",padx=10,pady=(6,2))
        ctk.CTkLabel(log_frame,
                     text=self._remote.get("changelog","Melhorias e correções."),
                     font=("Segoe UI",10), text_color=TEXT_MID,
                     wraplength=440, justify="left").pack(anchor="w",padx=10,pady=(0,8))

        # Progress
        self._status = ctk.CTkLabel(self, text="", font=("Segoe UI",10), text_color=TEXT_MID)
        self._status.pack(pady=(8,2))
        self._bar = ctk.CTkProgressBar(self, width=440, height=8,
                                        fg_color="#E2E8F0", progress_color=SUCCESS)
        self._bar.pack()
        self._bar.set(0)

        # Botões
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=16)
        ctk.CTkButton(btns, text="Agora não", width=110, height=38,
                      fg_color="transparent", hover_color=BG_HOVER,
                      text_color=TEXT_MID, border_width=1, border_color="#CBD5E0",
                      corner_radius=8, font=("Segoe UI",11),
                      command=self.destroy).pack(side="left", padx=8)
        self._install_btn = ctk.CTkButton(btns, text="⬇  Baixar e Instalar",
                                           width=180, height=38,
                                           fg_color=SUCCESS, hover_color="#276749",
                                           text_color=TEXT_WHITE,
                                           corner_radius=8, font=("Segoe UI",12,"bold"),
                                           command=self._do_update)
        self._install_btn.pack(side="left", padx=8)

    def _do_update(self):
        if self._running: return
        self._running = True
        self._install_btn.configure(state="disabled", text="Baixando...")
        url = self._remote.get("download_url","")

        def _work():
            ok, msg = U.download_and_install(url, self._on_progress)
            self.after(0, lambda: self._finished(ok, msg))

        threading.Thread(target=_work, daemon=True).start()

    def _on_progress(self, pct, msg):
        self.after(0, lambda: [self._bar.set(pct/100), self._status.configure(text=msg)])

    def _finished(self, ok, msg):
        if ok:
            self._status.configure(text=msg, text_color=SUCCESS)
            self.after(2000, self.master.destroy)
        else:
            self._status.configure(text=msg, text_color=DANGER)
            self._install_btn.configure(state="normal", text="Tentar novamente")
            self._running = False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
class AlphasApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Alphas Consultoria Digital — Gerenciador do Windows")
        self.geometry("1280x800")
        self.minsize(1024, 640)
        self.configure(fg_color=BG_MAIN)

        self._hw           = {}
        self._inst_cache   = []
        self._disk_info    = {}
        self._remote_info  = None   # info do update se disponível

        self._build_layout()
        self._build_sidebar()
        self._build_topbar()
        self._build_pages()
        self._build_footer()

        self.switch_page("dashboard")
        self.after(300,  self._boot_scan)
        self.after(4000, self._check_update)   # verifica update 4s após abrir

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    def _build_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=SIDEBAR_W, fg_color=BG_SIDEBAR, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.right = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.right.pack(side="left", fill="both", expand=True)

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        # Logo
        logo = ctk.CTkFrame(self.sidebar, fg_color="#142038", corner_radius=0, height=86)
        logo.pack(fill="x")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="⚙", font=("Segoe UI",32), text_color=ORANGE
                     ).pack(side="left", padx=(14,4), pady=16)
        tf = ctk.CTkFrame(logo, fg_color="transparent")
        tf.pack(side="left", pady=16)
        ctk.CTkLabel(tf, text="Alphas Consultoria Digital",
                     font=("Segoe UI",11,"bold"), text_color=TEXT_WHITE).pack(anchor="w")
        ctk.CTkLabel(tf, text="Gerenciador do Windows",
                     font=("Segoe UI",9), text_color="#8BA3C7").pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#2A3F6E").pack(fill="x", padx=12, pady=4)

        # Nav
        nav = [
            ("🏠","Visão Geral",      "dashboard"),
            ("🔄","Drivers & Updates","updates"),
            ("📋","Histórico Updates","history"),
            ("🧹","Limpeza",          "cleaner"),
            ("📦","Programas",        "apps"),
            ("🚀","Inicialização",    "startup"),
            ("🌐","Rede & DNS",       "network"),
            ("⚙", "Serviços",         "services"),
            ("🛡", "Restauração",      "restore"),
            ("💾","Backup",           "backup"),
            ("👑","Modo Deus",        "godmode"),
        ]
        self._nav_btns = {}
        nav_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent",
                                             scrollbar_button_color=BG_SIDEBAR,
                                             scrollbar_button_hover_color="#2A3F6E")
        nav_scroll.pack(fill="both", expand=True, padx=0, pady=4)
        for icon, label, key in nav:
            btn = SidebarBtn(nav_scroll, icon, label, key, self.switch_page)
            btn.pack(fill="x")
            self._nav_btns[key] = btn

        # Botão de update (oculto por padrão)
        self._update_btn = ctk.CTkButton(
            nav_scroll,
            text="🔄  Atualização Disponível!",
            fg_color=SUCCESS, hover_color="#276749",
            text_color=TEXT_WHITE, font=("Segoe UI",11,"bold"),
            height=36, corner_radius=8,
            command=self._show_update_dialog
        )
        # não empacota ainda — só aparece quando houver update

        # ── Rodapé sidebar ──
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#2A3F6E").pack(fill="x", padx=12, pady=(8,4))

        ctk.CTkLabel(self.sidebar,
                     text="Software Licenciado e Patenteado por",
                     font=("Segoe UI",10), text_color="#8BA3C7",
                     justify="center").pack(pady=(4,0))
        ctk.CTkLabel(self.sidebar,
                     text="Alphas Consultoria Digital",
                     font=("Segoe UI",11,"bold"), text_color=ORANGE,
                     justify="center").pack(pady=(0,2))
        ctk.CTkLabel(self.sidebar,
                     text="Denis Garcia Barbeto\nCNPJ: 40.268.116/0001-60",
                     font=("Segoe UI",9), text_color="#5A7A9E",
                     justify="center").pack(pady=(0,4))
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#2A3F6E").pack(fill="x", padx=12, pady=(0,4))

        admin_ok  = is_admin()
        admin_col = "#4ADE80" if admin_ok else WARNING
        admin_txt = "✔  Administrador" if admin_ok else "⚠  Sem privilégios admin"
        ctk.CTkLabel(self.sidebar, text=admin_txt, font=("Segoe UI",10),
                     text_color=admin_col).pack(pady=(4,2))
        if not admin_ok:
            ctk.CTkButton(self.sidebar, text="Reiniciar como Admin",
                          fg_color=ORANGE, hover_color=ORANGE_DARK,
                          text_color=TEXT_WHITE, font=("Segoe UI",10),
                          height=28, corner_radius=6,
                          command=self._restart_admin
                          ).pack(padx=12, pady=(2,8), fill="x")
        else:
            ctk.CTkFrame(self.sidebar, height=8, fg_color="transparent").pack()

    # ── TOPBAR ────────────────────────────────────────────────────────────────
    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(self.right, height=50, fg_color=BG_CARD, corner_radius=0)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)
        ctk.CTkFrame(self.topbar, height=3, fg_color=ORANGE, corner_radius=0).pack(fill="x", side="top")

        self._page_title = ctk.CTkLabel(self.topbar, text="",
                                         font=("Segoe UI",15,"bold"), text_color=BLUE)
        self._page_title.pack(side="left", padx=20)

        # Versão local
        ver = U.get_local_version()
        ctk.CTkLabel(self.topbar, text=f"v{ver}",
                     font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="right", padx=8)

        self._progress = ctk.CTkProgressBar(self.topbar, width=180, height=6,
                                              mode="indeterminate",
                                              fg_color="#E2E8F0", progress_color=ORANGE)
        self._progress.pack(side="right", padx=8, pady=22)
        self._progress.set(0)
        self._progress_lbl = ctk.CTkLabel(self.topbar, text="",
                                           font=("Segoe UI",10), text_color=TEXT_LIGHT)
        self._progress_lbl.pack(side="right", padx=4)

    # ── PAGES ─────────────────────────────────────────────────────────────────
    def _build_pages(self):
        self.content = ctk.CTkFrame(self.right, fg_color=BG_MAIN, corner_radius=0)
        self.content.pack(fill="both", expand=True)
        self.pages = {
            "dashboard": DashboardPage(self.content, self),
            "updates":   UpdatesPage(self.content, self),
            "history":   HistoryPage(self.content, self),
            "cleaner":   CleanerPage(self.content, self),
            "apps":      AppsPage(self.content, self),
            "startup":   StartupPage(self.content, self),
            "network":   NetworkPage(self.content, self),
            "services":  ServicesPage(self.content, self),
            "restore":   RestorePage(self.content, self),
            "backup":    BackupPage(self.content, self),
            "godmode":   GodModePage(self.content, self),
        }
        self.dashboard = self.pages["dashboard"]

    # ── FOOTER ────────────────────────────────────────────────────────────────
    def _build_footer(self):
        footer = ctk.CTkFrame(self.right, height=26, fg_color="#E2E8F0", corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.status = StatusBar(footer)
        self.status.pack(fill="x")

    # ── NAVEGAÇÃO ─────────────────────────────────────────────────────────────
    PAGE_TITLES = {
        "dashboard":"🏠  Visão Geral",
        "updates":  "🔄  Drivers & Windows Update",
        "history":  "📋  Histórico de Atualizações",
        "cleaner":  "🧹  Limpeza do Sistema",
        "apps":     "📦  Programas Instalados",
        "startup":  "🚀  Inicialização do Windows",
        "network":  "🌐  Rede & DNS",
        "services": "⚙   Serviços do Windows",
        "restore":  "🛡   Pontos de Restauração",
        "backup":   "💾  Backup",
        "godmode":  "👑  Modo Deus — God Mode",
    }

    def switch_page(self, key):
        for p in self.pages.values(): p.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self._page_title.configure(text=self.PAGE_TITLES.get(key,""))
        for k, btn in self._nav_btns.items():
            btn.set_active(k == key)

    # ── STATUS ────────────────────────────────────────────────────────────────
    def set_busy(self, msg="Aguarde..."):
        self._progress_lbl.configure(text=msg)
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self.status.set(msg)

    def set_idle(self, msg="Pronto"):
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(0)
        self._progress_lbl.configure(text="")
        self.status.set(msg)

    # ── AUTO-UPDATE ───────────────────────────────────────────────────────────
    def _check_update(self):
        U.check_async(
            on_found = self._on_update_found,
            on_none  = None
        )

    def _on_update_found(self, remote_info):
        self._remote_info = remote_info
        # Mostra botão verde na sidebar (thread-safe via after)
        self.after(0, self._show_update_btn)

    def _show_update_btn(self):
        ver = self._remote_info.get("version","?")
        self._update_btn.configure(text=f"🔄  Versão {ver} disponível!")
        self._update_btn.pack(fill="x", padx=6, pady=(4,6))
        # Pisca 3x para chamar atenção
        self._blink_btn(6)

    def _blink_btn(self, times):
        if times <= 0: return
        col = "#276749" if times % 2 == 0 else SUCCESS
        self._update_btn.configure(fg_color=col)
        self.after(500, lambda: self._blink_btn(times - 1))

    def _show_update_dialog(self):
        if self._remote_info:
            UpdateDialog(self, self._remote_info)

    # ── BOOT SCAN ─────────────────────────────────────────────────────────────
    def _boot_scan(self):
        self.set_busy("Inicializando sistema...")
        def _work():
            self._hw = B.get_hardware()
            self.after(0, lambda: self.dashboard.update_hw(self._hw))
            pend = B.get_pending_updates()
            self._inst_cache = B.get_installed_updates()
            disk = B.get_disk_usage()
            self._disk_info = disk
            self.after(0, lambda: self.dashboard.update_cards(
                pend, self._inst_cache, disk.get("total_temp_mb",0)))
            self.after(0, lambda: self.set_idle(
                f"Pronto — {len(pend)} atualização(ões) pendente(s)"))
        threading.Thread(target=_work, daemon=True).start()

    def _restart_admin(self):
        try:
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None,"runas",sys.executable," ".join(sys.argv),None,1)
            self.destroy()
        except: pass


if __name__ == "__main__":
    app = AlphasApp()
    app.mainloop()
