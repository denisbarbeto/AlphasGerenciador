"""
Todas as páginas/módulos do Alphas Gerenciador do Windows.
Cada classe é uma aba do painel lateral.
"""
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import customtkinter as ctk
import threading, webbrowser, os, subprocess
from theme import *
from widgets import *
import backend as B


# ══════════════════════════════════════════════════════════════════════════════
# BASE PAGE
# ══════════════════════════════════════════════════════════════════════════════
class BasePage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.app = app

    def run_async(self, fn, *args, done_cb=None, status="Aguarde..."):
        self.app.set_busy(status)
        def _work():
            result = fn(*args)
            self.after(0, lambda: self._done(result, done_cb))
        threading.Thread(target=_work, daemon=True).start()

    def _done(self, result, cb):
        self.app.set_idle()
        if cb: cb(result)

    def _header(self, icon, title, subtitle=""):
        h = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=72)
        h.pack(fill="x")
        h.pack_propagate(False)
        ctk.CTkLabel(h, text=icon, font=("Segoe UI", 28)).pack(side="left", padx=(20,8), pady=12)
        tf = ctk.CTkFrame(h, fg_color="transparent")
        tf.pack(side="left", fill="y", pady=12)
        ctk.CTkLabel(tf, text=title, font=("Segoe UI", 16, "bold"), text_color=BLUE).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(tf, text=subtitle, font=("Segoe UI", 11), text_color=TEXT_LIGHT).pack(anchor="w")
        return h

    def _toolbar(self, parent):
        tb = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=0, height=48)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        return tb

    def _table_header(self, parent, cols):
        hdr = ctk.CTkFrame(parent, fg_color="#EDF2F7", corner_radius=0, height=32)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for txt, w in cols:
            ctk.CTkLabel(hdr, text=txt, width=w, font=("Segoe UI",10,"bold"),
                         text_color=TEXT_MID, anchor="w").pack(side="left", padx=6)
        return hdr


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD / VISÃO GERAL
# ══════════════════════════════════════════════════════════════════════════════
class DashboardPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        self._header("🏠", "Visão Geral", "Resumo do sistema e ações rápidas")
        body = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        body.pack(fill="both", expand=True)

        # Cards de resumo
        card_row = ctk.CTkFrame(body, fg_color="transparent")
        card_row.pack(fill="x", padx=20, pady=(16,8))
        self._cards = {}
        for i, (icon, lbl, key, color) in enumerate([
            ("🔄","Drivers Pendentes","drivers", ORANGE),
            ("⬆","Win Updates","updates", BLUE_LIGHT),
            ("🧹","Temp (MB)","temp", SUCCESS),
            ("⚠","Críticos","critical", DANGER),
        ]):
            c = ctk.CTkFrame(card_row, fg_color=BG_CARD, corner_radius=10)
            c.grid(row=0, column=i, padx=6, sticky="ew")
            card_row.columnconfigure(i, weight=1)
            top = ctk.CTkFrame(c, fg_color=color, corner_radius=10, height=4)
            top.pack(fill="x")
            ctk.CTkLabel(c, text=icon, font=("Segoe UI",26)).pack(pady=(12,2))
            val = ctk.CTkLabel(c, text="—", font=("Segoe UI",24,"bold"), text_color=color)
            val.pack()
            ctk.CTkLabel(c, text=lbl, font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(pady=(0,14))
            self._cards[key] = val

        # Botões rápidos
        section_title(body, "Ações Rápidas")
        btn_grid = ctk.CTkFrame(body, fg_color="transparent")
        btn_grid.pack(fill="x", padx=20, pady=(0,16))
        quick = [
            ("🔄  Verificar Updates", lambda: self.app.switch_page("updates")),
            ("🧹  Limpar Sistema",    lambda: self.app.switch_page("cleaner")),
            ("📌  Criar Restauração", self._create_restore),
            ("👑  Modo Deus",         lambda: self.app.switch_page("godmode")),
        ]
        for i,(lbl,cmd) in enumerate(quick):
            orange_btn(btn_grid, lbl, command=cmd, width=180, height=40).grid(row=0,column=i,padx=6,pady=4)
            btn_grid.columnconfigure(i, weight=1)

        # HW info
        section_title(body, "Hardware Detectado")
        self._hw_card = card(body)
        self._hw_card.pack(fill="x", padx=20, pady=(0,12))
        self._hw_lbl = ctk.CTkLabel(self._hw_card, text="Detectando...",
                                     font=("Consolas",11), text_color=TEXT_MID,
                                     justify="left", anchor="w")
        self._hw_lbl.pack(fill="x", padx=16, pady=14)

        # Ferramentas do Windows
        section_title(body, "Ferramentas do Windows e Acessórios")
        tools_grid = ctk.CTkFrame(body, fg_color="transparent")
        tools_grid.pack(fill="x", padx=20, pady=(0,20))
        TOOLS = [
            ("🖥  Gerenc. Dispositivos",  "devmgmt.msc"),
            ("💿  Gerenc. de Disco",       "diskmgmt.msc"),
            ("⚙   Serviços",              "services.msc"),
            ("📋  Visualiz. de Eventos",  "eventvwr"),
            ("🔧  Configuração do Sistema","msconfig"),
            ("🛡   Firewall",             "WF.msc"),
            ("📊  Monitor de Desempenho", "perfmon"),
            ("🗂   Programas e Recursos",  "appwiz.cpl"),
            ("👤  Contas de Usuário",      "netplwiz"),
            ("🌐  Opções de Internet",     "inetcpl.cpl"),
            ("📝  Editor de Registro",    "regedit"),
            ("🧹  Limpeza de Disco",      "cleanmgr"),
        ]
        for col in range(4): tools_grid.columnconfigure(col, weight=1)
        for idx, (lbl, cmd) in enumerate(TOOLS):
            r, c = divmod(idx, 4)
            ctk.CTkButton(tools_grid, text=lbl, font=("Segoe UI",11),
                          fg_color=BG_CARD, hover_color=BG_HOVER,
                          text_color=TEXT_DARK, border_width=1, border_color="#CBD5E0",
                          height=36, corner_radius=6, anchor="w",
                          command=lambda cm=cmd: B.open_god_mode_item(cm)
                          ).grid(row=r, column=c, padx=4, pady=3, sticky="ew")

    def update_hw(self, hw):
        lines=[]
        o=hw.get("os",{})
        lines.append(f"🖥  SO           {o.get('name','?')}  (Build {o.get('build','?')})  [{o.get('arch','?')}]")
        c=hw.get("cpu",{})
        lines.append(f"🧠  CPU          {c.get('name','?')}  |  {c.get('cores','?')} núcleos / {c.get('threads','?')} threads  @  {c.get('mhz','?')} MHz")
        for g in hw.get("gpu",[]):
            lines.append(f"🎮  GPU          {g.get('name','?')}  |  Driver {g.get('driver','?')}  |  VRAM {g.get('vram','?')}")
        mb=hw.get("mb",{})
        lines.append(f"🔧  Placa-mãe    {mb.get('vendor','?')} {mb.get('model','?')}  |  BIOS {mb.get('bios','?')} ({mb.get('bios_date','?')})")
        ram=hw.get("ram",{})
        lines.append(f"💾  RAM          {ram.get('total','?')} total  ({len(ram.get('slots',[]))} módulo(s))")
        for d in hw.get("disk",[]):
            lines.append(f"💿  Disco        {d.get('model','?')}  {d.get('size','?')}  [{d.get('interface','?')}]")
        for n in hw.get("net",[])[:2]:
            lines.append(f"🌐  Rede         {n.get('name','?')}")
        for a in hw.get("audio",[])[:1]:
            lines.append(f"🔊  Áudio        {a.get('name','?')}")
        self._hw_lbl.configure(text="\n".join(lines))

    def update_cards(self, pend, inst, temp_mb):
        drv=sum(1 for u in pend if u.get("is_driver"))
        crit=sum(1 for u in pend if "crít" in u.get("severity","").lower())
        self._cards["drivers"].configure(text=str(drv))
        self._cards["updates"].configure(text=str(len(pend)))
        self._cards["temp"].configure(text=f"{temp_mb:.0f}")
        self._cards["critical"].configure(text=str(crit), text_color=DANGER if crit else SUCCESS)

    def _create_restore(self):
        self.run_async(B.create_restore_point, "Alphas Gerenciador — Manual",
                       done_cb=lambda r: self.app.status.set(f"Restauração: {'OK' if r[0] else 'Erro'}"),
                       status="Criando ponto de restauração...")


# ══════════════════════════════════════════════════════════════════════════════
# DRIVERS + WINDOWS UPDATE (pendentes)
# ══════════════════════════════════════════════════════════════════════════════
class UpdatesPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._data = []
        self._vars = {}
        self._build()

    def _build(self):
        self._header("🔄", "Drivers & Windows Update", "Atualizações pendentes e drivers instalados")

        # Tabs
        tab_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=42)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)
        self._tab_var = tk.StringVar(value="pendentes")
        ctk.CTkSegmentedButton(tab_bar,
                                values=["🔄  Pendentes", "🔧  Drivers Instalados"],
                                variable=self._tab_var,
                                font=("Segoe UI",11),
                                selected_color=ORANGE, selected_hover_color=ORANGE_DARK,
                                command=self._switch_tab
                                ).pack(side="left", padx=10, pady=6)

        # Pane pendentes
        self._pane_pending = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        tb = ctk.CTkFrame(self._pane_pending, fg_color=BG_CARD, corner_radius=0, height=48)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        orange_btn(tb, "🔄  Verificar Agora", command=self.scan, width=150).pack(side="left",padx=10,pady=6)
        blue_btn(tb, "☑ Instalar Selecionados", command=self._install_sel, width=180).pack(side="left",padx=4)
        blue_btn(tb, "⬆ Instalar Todos", command=self._install_all, width=140).pack(side="left",padx=4)
        ghost_btn(tb, "☐ Limpar Seleção", command=self._deselect_all, width=130).pack(side="left",padx=4)
        self._count = ctk.CTkLabel(tb, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._count.pack(side="right",padx=16)
        self._scroll = ctk.CTkScrollableFrame(self._pane_pending, fg_color=BG_MAIN)
        self._scroll.pack(fill="both", expand=True, padx=0)

        # Pane drivers instalados
        self._pane_drivers = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        tb2 = ctk.CTkFrame(self._pane_drivers, fg_color=BG_CARD, corner_radius=0, height=48)
        tb2.pack(fill="x")
        tb2.pack_propagate(False)
        orange_btn(tb2, "🔄  Atualizar", command=self._load_drivers, width=130).pack(side="left",padx=10,pady=6)
        self._drv_search = tk.StringVar()
        self._drv_search.trace_add("write", lambda *_: self._filter_drivers())
        ctk.CTkEntry(tb2, textvariable=self._drv_search, placeholder_text="🔍 Buscar driver...",
                     width=240, height=32).pack(side="left",padx=8)
        self._drv_count = ctk.CTkLabel(tb2, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._drv_count.pack(side="right",padx=16)
        self._drv_scroll = ctk.CTkScrollableFrame(self._pane_drivers, fg_color=BG_MAIN)
        self._drv_scroll.pack(fill="both", expand=True)
        self._drv_data = []

        self._pane_pending.pack(fill="both", expand=True)
        self._render([])
        self.after(300, self.scan)

    def _switch_tab(self, val):
        if "Pendentes" in val:
            self._pane_drivers.pack_forget()
            self._pane_pending.pack(fill="both", expand=True)
        else:
            self._pane_pending.pack_forget()
            self._pane_drivers.pack(fill="both", expand=True)
            if not self._drv_data:
                self._load_drivers()

    def _load_drivers(self):
        self.run_async(B.get_drivers_device_manager, done_cb=self._drivers_loaded,
                       status="Lendo drivers do sistema...")

    def _drivers_loaded(self, data):
        self._drv_data = data
        self._filter_drivers()

    def _filter_drivers(self):
        q = self._drv_search.get().lower()
        data = [d for d in self._drv_data if q in d.get("name","").lower()
                or q in d.get("class","").lower() or q in d.get("vendor","").lower()] if q else self._drv_data
        self._render_drivers(data)

    def _render_drivers(self, data):
        for w in self._drv_scroll.winfo_children(): w.destroy()
        if not data:
            ctk.CTkLabel(self._drv_scroll, text="Nenhum driver encontrado.",
                         font=("Segoe UI",13), text_color=TEXT_LIGHT).pack(pady=50)
            self._drv_count.configure(text="0")
            return
        self._table_header(self._drv_scroll, [("Dispositivo",300),("Categoria",120),("Fabricante",160),("Versão",120),("Data",90),("Status",70)])
        # Agrupa por classe
        cats = {}
        for d in data:
            cats.setdefault(d.get("class","Outros"), []).append(d)
        row_idx = 0
        for cat, items in sorted(cats.items()):
            # Cabeçalho de categoria
            cat_row = ctk.CTkFrame(self._drv_scroll, fg_color="#D0DCF0", corner_radius=0, height=28)
            cat_row.pack(fill="x")
            cat_row.pack_propagate(False)
            ctk.CTkLabel(cat_row, text=f"  📁  {cat}  ({len(items)})",
                         font=("Segoe UI",10,"bold"), text_color=BLUE, anchor="w").pack(side="left",padx=10,pady=4)
            for drv in items:
                bg = BG_ROW if row_idx%2==0 else BG_ROW2
                row = ctk.CTkFrame(self._drv_scroll, fg_color=bg, corner_radius=0, height=44)
                row.pack(fill="x")
                row.pack_propagate(False)
                icon = "⚠" if drv.get("status","OK") not in ("OK","") else ("✅" if drv.get("signed") else "⚠")
                ctk.CTkLabel(row, text=f"{icon}  {drv.get('name','?')[:42]}", width=300,
                             font=("Segoe UI",11,"bold"), text_color=TEXT_DARK, anchor="w").pack(side="left",padx=10)
                ctk.CTkLabel(row, text=drv.get("class","—")[:18], width=120,
                             font=("Segoe UI",10), text_color=BLUE_LIGHT).pack(side="left",padx=4)
                ctk.CTkLabel(row, text=drv.get("vendor","—")[:22], width=160,
                             font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
                ctk.CTkLabel(row, text=drv.get("version","—")[:18], width=120,
                             font=("Segoe UI",10), text_color=TEXT_MID).pack(side="left",padx=4)
                ctk.CTkLabel(row, text=drv.get("date","—"), width=90,
                             font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
                st = drv.get("status","OK")
                st_col = SUCCESS if st in ("OK","") else DANGER
                ctk.CTkLabel(row, text=st or "OK", width=70,
                             font=("Segoe UI",10,"bold"), text_color=st_col).pack(side="left",padx=4)
                row_idx += 1
        self._drv_count.configure(text=f"{len(data)} drivers")

    def scan(self):
        self.run_async(B.get_pending_updates, done_cb=self._loaded, status="Verificando atualizações...")

    def _loaded(self, data):
        self._data = data
        self._render(data)
        self.app.dashboard.update_cards(data, self.app._inst_cache,
                                         self.app._disk_info.get("total_temp_mb",0))

    def _render(self, data):
        for w in self._scroll.winfo_children(): w.destroy()
        self._vars = {}
        if not data:
            ctk.CTkLabel(self._scroll, text="✅  Nenhuma atualização pendente! Sistema atualizado.",
                         font=("Segoe UI",14), text_color=SUCCESS).pack(pady=60)
            self._count.configure(text="0 pendentes")
            return

        hdr = ctk.CTkFrame(self._scroll, fg_color="#D0DCF0", corner_radius=0, height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        var_all = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(hdr, text=f"  Todos os dispositivos com driver/update desatualizado(s): ({len(data)})",
                        variable=var_all, font=("Segoe UI",11,"bold"), text_color=BLUE,
                        fg_color=ORANGE, command=lambda: [v.set(var_all.get()) for v in self._vars.values()]
                        ).pack(side="left", padx=10, pady=6)

        for i, upd in enumerate(data):
            uid = upd.get("update_id", str(i))
            bg = BG_ROW if i%2==0 else BG_ROW2
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0, height=ROW_H)
            row.pack(fill="x")
            row.pack_propagate(False)

            var = tk.BooleanVar(value=True)
            self._vars[uid] = var
            ctk.CTkCheckBox(row, text="", variable=var, width=30,
                             checkbox_width=16, checkbox_height=16,
                             fg_color=ORANGE, border_color="#CBD5E0"
                             ).pack(side="left", padx=(10,4))

            icon = "🔧" if upd.get("is_driver") else "🪟"
            ctk.CTkLabel(row, text=icon, font=("Segoe UI",18), width=30).pack(side="left",padx=4)

            info_f = ctk.CTkFrame(row, fg_color="transparent")
            info_f.pack(side="left", fill="both", expand=True, padx=4)
            ctk.CTkLabel(info_f, text=upd.get("title","?")[:80],
                         font=("Segoe UI",12,"bold"), text_color=TEXT_DARK, anchor="w").pack(anchor="w",pady=(8,0))
            badge_row = ctk.CTkFrame(info_f, fg_color="transparent")
            badge_row.pack(anchor="w", pady=(2,4))
            if upd.get("kb"):
                tag_badge(badge_row, upd["kb"], BLUE_LIGHT).pack(side="left",padx=(0,4))
            sev = upd.get("severity","Normal")
            sev_col = DANGER if "crít" in sev.lower() else WARNING if "import" in sev.lower() else SUCCESS
            tag_badge(badge_row, sev, sev_col).pack(side="left",padx=(0,4))
            tag_badge(badge_row, "Driver" if upd.get("is_driver") else "Sistema", BLUE_ACCENT).pack(side="left")

            sz = upd.get("size_mb",0)
            if sz:
                ctk.CTkLabel(row, text=f"{sz} MB", font=("Segoe UI",11),
                             text_color=TEXT_LIGHT, width=70).pack(side="right",padx=4)

            orange_btn(row, "Atualizar", command=lambda u=upd: self._install_one(u),
                       width=90, height=30).pack(side="right", padx=8)

        self._count.configure(text=f"{len(data)} pendentes")

    def _deselect_all(self):
        for v in self._vars.values(): v.set(False)

    def _install_sel(self):
        ids=[uid for uid,v in self._vars.items() if v.get()]
        if not ids: self.app.status.set("Selecione ao menos um item."); return
        upds=[u for u in self._data if u.get("update_id") in ids]
        self._do_install(upds)

    def _install_all(self): self._do_install(self._data)

    def _install_one(self, upd): self._do_install([upd])

    def _do_install(self, upds):
        ext=[u for u in upds if u.get("download_url")]
        ms=[u for u in upds if not u.get("download_url")]
        for u in ext: webbrowser.open(u["download_url"])
        if ms:
            ids=[u["update_id"] for u in ms]
            self.run_async(B.install_updates, ids,
                           done_cb=lambda r: [self.app.status.set("Instalação concluída!"), self.scan()],
                           status=f"Instalando {len(ms)} atualização(ões)...")

    def _build(self):
        self._header("🔄", "Drivers & Windows Update", "Atualizações pendentes detectadas no sistema")
        tb = self._toolbar(self)
        orange_btn(tb, "🔄  Verificar Agora", command=self.scan, width=150).pack(side="left",padx=10,pady=6)
        blue_btn(tb, "☑ Instalar Selecionados", command=self._install_sel, width=180).pack(side="left",padx=4)
        blue_btn(tb, "⬆ Instalar Todos", command=self._install_all, width=140).pack(side="left",padx=4)
        ghost_btn(tb, "☐ Limpar Seleção", command=self._deselect_all, width=130).pack(side="left",padx=4)
        self._count = ctk.CTkLabel(tb, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._count.pack(side="right",padx=16)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        self._scroll.pack(fill="both", expand=True, padx=0)
        self._render([])
        self.after(300, self.scan)

    def scan(self):
        self.run_async(B.get_pending_updates, done_cb=self._loaded, status="Verificando atualizações...")

    def _loaded(self, data):
        self._data = data
        self._render(data)
        self.app.dashboard.update_cards(data, self.app._inst_cache,
                                         self.app._disk_info.get("total_temp_mb",0))

    def _render(self, data):
        for w in self._scroll.winfo_children(): w.destroy()
        self._vars = {}
        if not data:
            ctk.CTkLabel(self._scroll, text="✅  Nenhuma atualização pendente! Sistema atualizado.",
                         font=("Segoe UI",14), text_color=SUCCESS).pack(pady=60)
            self._count.configure(text="0 pendentes")
            return

        # Cabeçalho tipo Driver Easy
        hdr = ctk.CTkFrame(self._scroll, fg_color="#D0DCF0", corner_radius=0, height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        var_all = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(hdr, text=f"  Todos os dispositivos com driver/update desatualizado(s): ({len(data)})",
                        variable=var_all, font=("Segoe UI",11,"bold"), text_color=BLUE,
                        fg_color=ORANGE, command=lambda: [v.set(var_all.get()) for v in self._vars.values()]
                        ).pack(side="left", padx=10, pady=6)

        for i, upd in enumerate(data):
            uid = upd.get("update_id", str(i))
            bg = BG_ROW if i%2==0 else BG_ROW2
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0, height=ROW_H)
            row.pack(fill="x")
            row.pack_propagate(False)

            var = tk.BooleanVar(value=True)
            self._vars[uid] = var
            ctk.CTkCheckBox(row, text="", variable=var, width=30,
                             checkbox_width=16, checkbox_height=16,
                             fg_color=ORANGE, border_color="#CBD5E0"
                             ).pack(side="left", padx=(10,4))

            # Ícone tipo
            icon = "🔧" if upd.get("is_driver") else "🪟"
            ctk.CTkLabel(row, text=icon, font=("Segoe UI",18), width=30).pack(side="left",padx=4)

            # Info
            info_f = ctk.CTkFrame(row, fg_color="transparent")
            info_f.pack(side="left", fill="both", expand=True, padx=4)
            ctk.CTkLabel(info_f, text=upd.get("title","?")[:80],
                         font=("Segoe UI",12,"bold"), text_color=TEXT_DARK, anchor="w").pack(anchor="w",pady=(8,0))
            # Badges
            badge_row = ctk.CTkFrame(info_f, fg_color="transparent")
            badge_row.pack(anchor="w", pady=(2,4))
            if upd.get("kb"):
                tag_badge(badge_row, upd["kb"], BLUE_LIGHT).pack(side="left",padx=(0,4))
            sev = upd.get("severity","Normal")
            sev_col = DANGER if "crít" in sev.lower() else WARNING if "import" in sev.lower() else SUCCESS
            tag_badge(badge_row, sev, sev_col).pack(side="left",padx=(0,4))
            tag_badge(badge_row, "Driver" if upd.get("is_driver") else "Sistema", BLUE_ACCENT).pack(side="left")

            # Tamanho
            sz = upd.get("size_mb",0)
            if sz:
                ctk.CTkLabel(row, text=f"{sz} MB", font=("Segoe UI",11),
                             text_color=TEXT_LIGHT, width=70).pack(side="right",padx=4)

            # Botão
            orange_btn(row, "Atualizar", command=lambda u=upd: self._install_one(u),
                       width=90, height=30).pack(side="right", padx=8)

        self._count.configure(text=f"{len(data)} pendentes")

    def _deselect_all(self):
        for v in self._vars.values(): v.set(False)

    def _install_sel(self):
        ids=[uid for uid,v in self._vars.items() if v.get()]
        if not ids: self.app.status.set("Selecione ao menos um item."); return
        upds=[u for u in self._data if u.get("update_id") in ids]
        self._do_install(upds)

    def _install_all(self): self._do_install(self._data)

    def _install_one(self, upd): self._do_install([upd])

    def _do_install(self, upds):
        ext=[u for u in upds if u.get("download_url")]
        ms=[u for u in upds if not u.get("download_url")]
        for u in ext: webbrowser.open(u["download_url"])
        if ms:
            ids=[u["update_id"] for u in ms]
            self.run_async(B.install_updates, ids,
                           done_cb=lambda r: [self.app.status.set("Instalação concluída!"), self.scan()],
                           status=f"Instalando {len(ms)} atualização(ões)...")


# ══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO DE UPDATES (instaladas)
# ══════════════════════════════════════════════════════════════════════════════
class HistoryPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._data = []
        self._build()

    def _build(self):
        self._header("📋", "Histórico de Atualizações", "Atualizações instaladas no sistema")
        tb = self._toolbar(self)
        orange_btn(tb, "🔄  Atualizar", command=self.load, width=130).pack(side="left",padx=10,pady=6)
        self._search = tk.StringVar()
        self._search.trace_add("write", lambda *_: self._filter())
        ctk.CTkEntry(tb, textvariable=self._search, placeholder_text="🔍 Buscar por nome ou KB...",
                     width=260, height=32).pack(side="left",padx=8)
        self._count = ctk.CTkLabel(tb, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._count.pack(side="right",padx=16)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        self._scroll.pack(fill="both", expand=True)
        self.after(400, self.load)

    def load(self):
        self.run_async(B.get_installed_updates, done_cb=self._loaded, status="Carregando histórico...")

    def _loaded(self, data):
        self._data = data
        self._render(data)

    def _filter(self):
        q = self._search.get().lower()
        filtered = [u for u in self._data if q in u.get("title","").lower() or q in u.get("kb","").lower()]
        self._render(filtered)

    def _render(self, data):
        for w in self._scroll.winfo_children(): w.destroy()
        if not data:
            ctk.CTkLabel(self._scroll, text="Nenhum registro encontrado.",
                         font=("Segoe UI",13), text_color=TEXT_LIGHT).pack(pady=50)
            self._count.configure(text="0")
            return
        self._table_header(self._scroll, [("Nome",380),("KB",90),("Tipo",80),("Data",100),("Ação",120)])
        for i, upd in enumerate(data):
            bg = BG_ROW if i%2==0 else BG_ROW2
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0, height=48)
            row.pack(fill="x")
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=upd.get("title","?")[:65], width=380,
                         font=("Segoe UI",11), text_color=TEXT_DARK, anchor="w").pack(side="left",padx=10)
            kb = upd.get("kb","—")
            ctk.CTkLabel(row, text=kb, width=90, font=("Segoe UI",11,"bold"),
                         text_color=BLUE_LIGHT if kb!="—" else TEXT_LIGHT).pack(side="left",padx=4)
            tp = upd.get("type","Sistema")
            tc = "#6B46C1" if tp=="Driver" else BLUE_LIGHT
            ctk.CTkLabel(row, text=tp, width=80, font=("Segoe UI",10), text_color=tc).pack(side="left",padx=4)
            ctk.CTkLabel(row, text=upd.get("date","?"), width=100,
                         font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
            if kb and kb!="—":
                danger_btn(row, "🗑 Remover", command=lambda u=upd: self._uninstall(u),
                           width=100, height=28).pack(side="right",padx=8)
        self._count.configure(text=f"{len(data)} registros")

    def _uninstall(self, upd):
        dlg = ConfirmDialog(self.app, "Remover Atualização",
                            f"Remover {upd.get('kb','')}?\n{upd.get('title','')}\n\nPode requerer reinicialização.")
        if not dlg.confirmed: return
        self.run_async(B.uninstall_update, upd.get("kb",""),
                       done_cb=lambda r: [self.app.status.set(f"Remoção: {'OK' if r[0] else 'Erro'}"), self.load()],
                       status=f"Removendo {upd.get('kb','')}...")


# ══════════════════════════════════════════════════════════════════════════════
# LIMPEZA
# ══════════════════════════════════════════════════════════════════════════════
class CleanerPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._disk = {}
        self._build()

    def _build(self):
        self._header("🧹", "Limpeza do Sistema", "Libere espaço em disco removendo arquivos desnecessários")
        tb = self._toolbar(self)
        orange_btn(tb, "🔍  Analisar", command=self.analyze, width=120).pack(side="left",padx=10,pady=6)
        orange_btn(tb, "🧹  Limpar Agora", command=self._clean, width=140).pack(side="left",padx=4)
        blue_btn(tb, "🗂  Limpeza de Disco (Windows)", command=B.run_disk_cleanup, width=220).pack(side="left",padx=4)

        body = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        body.pack(fill="both", expand=True)

        # Discos
        section_title(body, "Uso dos Discos")
        self._disk_frame = card(body)
        self._disk_frame.pack(fill="x", padx=20, pady=(0,12))
        self._disk_lbl = ctk.CTkLabel(self._disk_frame, text="Clique em Analisar...",
                                       font=("Segoe UI",12), text_color=TEXT_LIGHT)
        self._disk_lbl.pack(padx=16, pady=14)

        # Temp
        section_title(body, "Pastas Temporárias")
        self._temp_frame = card(body)
        self._temp_frame.pack(fill="x", padx=20, pady=(0,20))
        self._temp_lbl = ctk.CTkLabel(self._temp_frame, text="—",
                                       font=("Consolas",11), text_color=TEXT_MID,
                                       justify="left", anchor="w")
        self._temp_lbl.pack(fill="x", padx=16, pady=14)
        self.after(300, self.analyze)

    def analyze(self):
        self.run_async(B.get_disk_usage, done_cb=self._loaded, status="Analisando disco...")

    def _loaded(self, info):
        self._disk = info
        self.app._disk_info = info
        # Discos
        for w in self._disk_frame.winfo_children(): w.destroy()
        for drv in info.get("drives",[]):
            nm=drv.get("Name","?"); used=drv.get("UsedGB",0); free=drv.get("FreeGB",0); total=drv.get("TotalGB",1)
            pct=used/total if total else 0
            row=ctk.CTkFrame(self._disk_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(row, text=f"💾  Disco {nm}:", width=80, font=("Segoe UI",12,"bold"), text_color=BLUE).pack(side="left")
            ctk.CTkProgressBar(row, width=300, height=14, fg_color="#E2E8F0",
                                progress_color=ORANGE if pct>0.85 else SUCCESS
                                ).pack(side="left",padx=8)
            ctk.CTkLabel(row, text=f"{used:.1f} GB usados / {total:.1f} GB  ({free:.1f} GB livres)",
                         font=("Segoe UI",11), text_color=TEXT_MID).pack(side="left",padx=8)

        # Temp
        lines=[]
        for t in info.get("temp_folders",[]):
            lines.append(f"📁  {t['path']:<55}  {t['mb']:.1f} MB")
        lines.append(f"\n   Total estimado a liberar:  {info.get('total_temp_mb',0):.1f} MB")
        self._temp_lbl.configure(text="\n".join(lines) if lines else "Nenhuma pasta temp encontrada.")
        self.app.status.set(f"Análise concluída — {info.get('total_temp_mb',0):.0f} MB a liberar")

    def _clean(self):
        dlg = ConfirmDialog(self.app, "Limpar Arquivos Temporários",
                            "Remover todos os arquivos temporários?\n\nEsta ação não pode ser desfeita.",
                            ok_text="Limpar", ok_color=ORANGE)
        if not dlg.confirmed: return
        def _do():
            n = B.clean_temp()
            return n
        self.run_async(_do, done_cb=lambda n: [self.app.status.set(f"{n} itens removidos!"), self.analyze()],
                       status="Limpando arquivos temporários...")


# ══════════════════════════════════════════════════════════════════════════════
# PROGRAMAS INSTALADOS
# ══════════════════════════════════════════════════════════════════════════════
class AppsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._data = []
        self._build()

    def _build(self):
        self._header("📦", "Programas Instalados", "Gerencie os programas do seu computador")

        # ── Tabs ──
        tab_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=42)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)
        self._tab_var = tk.StringVar(value="programas")
        ctk.CTkSegmentedButton(tab_bar,
                                values=["📦  Programas", "🪟  Recursos do Windows"],
                                variable=self._tab_var,
                                font=("Segoe UI",11),
                                selected_color=ORANGE, selected_hover_color=ORANGE_DARK,
                                command=self._switch_tab
                                ).pack(side="left", padx=10, pady=6)

        # ── Página Programas ──
        self._pane_apps = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        tb = ctk.CTkFrame(self._pane_apps, fg_color=BG_CARD, corner_radius=0, height=48)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        orange_btn(tb, "🔄  Atualizar Lista", command=self.load, width=150).pack(side="left",padx=10,pady=6)
        self._search = tk.StringVar()
        self._search.trace_add("write", lambda *_: self._filter())
        ctk.CTkEntry(tb, textvariable=self._search, placeholder_text="🔍 Buscar programa...",
                     width=260, height=32).pack(side="left",padx=8)
        self._count = ctk.CTkLabel(tb, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._count.pack(side="right",padx=16)
        self._scroll = ctk.CTkScrollableFrame(self._pane_apps, fg_color=BG_MAIN)
        self._scroll.pack(fill="both", expand=True)

        # ── Página Recursos do Windows ──
        self._pane_features = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        tb2 = ctk.CTkFrame(self._pane_features, fg_color=BG_CARD, corner_radius=0, height=48)
        tb2.pack(fill="x")
        tb2.pack_propagate(False)
        orange_btn(tb2, "🔄  Atualizar", command=self._load_features, width=130).pack(side="left",padx=10,pady=6)
        self._feat_search = tk.StringVar()
        self._feat_search.trace_add("write", lambda *_: self._filter_features())
        ctk.CTkEntry(tb2, textvariable=self._feat_search, placeholder_text="🔍 Buscar recurso...",
                     width=240, height=32).pack(side="left",padx=8)
        self._feat_count = ctk.CTkLabel(tb2, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._feat_count.pack(side="right",padx=16)
        self._feat_scroll = ctk.CTkScrollableFrame(self._pane_features, fg_color=BG_MAIN)
        self._feat_scroll.pack(fill="both", expand=True)
        self._feat_data = []

        self._pane_apps.pack(fill="both", expand=True)
        self.after(500, self.load)

    def _switch_tab(self, val):
        if "Programas" in val:
            self._pane_features.pack_forget()
            self._pane_apps.pack(fill="both", expand=True)
        else:
            self._pane_apps.pack_forget()
            self._pane_features.pack(fill="both", expand=True)
            if not self._feat_data:
                self._load_features()

    def load(self):
        self.run_async(B.get_installed_apps, done_cb=self._loaded, status="Listando programas...")

    def _loaded(self, data):
        self._data = data
        self._render(data)

    def _filter(self):
        q = self._search.get().lower()
        self._render([a for a in self._data if q in a.get("name","").lower()])

    def _render(self, data):
        for w in self._scroll.winfo_children(): w.destroy()
        self._table_header(self._scroll, [("Nome",300),("Versão",110),("Fabricante",180),("Tamanho",80),("Data",90),("",120)])
        for i, app in enumerate(data):
            bg = BG_ROW if i%2==0 else BG_ROW2
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0, height=46)
            row.pack(fill="x")
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=app.get("name","?")[:45], width=300,
                         font=("Segoe UI",11,"bold"), text_color=TEXT_DARK, anchor="w").pack(side="left",padx=10)
            ctk.CTkLabel(row, text=app.get("version","—")[:18], width=110,
                         font=("Segoe UI",10), text_color=TEXT_MID).pack(side="left",padx=4)
            ctk.CTkLabel(row, text=app.get("publisher","—")[:28], width=180,
                         font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
            sz=app.get("size_mb",0)
            ctk.CTkLabel(row, text=f"{sz} MB" if sz else "—", width=80,
                         font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
            ctk.CTkLabel(row, text=app.get("install_date","—")[:10], width=90,
                         font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
            if app.get("uninstall_cmd"):
                danger_btn(row, "🗑 Desinstalar", command=lambda a=app: self._uninstall(a),
                           width=110, height=28).pack(side="right",padx=8)
        self._count.configure(text=f"{len(data)} programas")

    def _uninstall(self, app):
        dlg = ConfirmDialog(self.app, "Desinstalar Programa",
                            f"Desinstalar '{app.get('name','')}'?\n\nEsta ação não pode ser desfeita.")
        if not dlg.confirmed: return
        ok,msg = B.uninstall_app(app.get("uninstall_cmd",""))
        self.app.status.set(f"{'Desinstalação iniciada' if ok else 'Erro: '+msg}")
        if ok: self.after(3000, self.load)

    # ── Recursos do Windows ──────────────────────────────────────────────────
    def _load_features(self):
        self.run_async(B.get_windows_features, done_cb=self._features_loaded,
                       status="Carregando Recursos do Windows...")

    def _features_loaded(self, data):
        self._feat_data = data
        self._filter_features()

    def _filter_features(self):
        q = self._feat_search.get().lower()
        data = [f for f in self._feat_data if q in f.get("display","").lower()] if q else self._feat_data
        self._render_features(data)

    def _render_features(self, data):
        for w in self._feat_scroll.winfo_children(): w.destroy()
        if not data:
            ctk.CTkLabel(self._feat_scroll,
                         text="Nenhum recurso encontrado. Clique em Atualizar.",
                         font=("Segoe UI",13), text_color=TEXT_LIGHT).pack(pady=50)
            self._feat_count.configure(text="0")
            return
        self._table_header(self._feat_scroll, [("Recurso",380),("Nome Interno",200),("Status",90),("Ação",120)])
        for i, feat in enumerate(data):
            bg = BG_ROW if i%2==0 else BG_ROW2
            row = ctk.CTkFrame(self._feat_scroll, fg_color=bg, corner_radius=0, height=46)
            row.pack(fill="x")
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=feat.get("display","?")[:60], width=380,
                         font=("Segoe UI",11,"bold"), text_color=TEXT_DARK, anchor="w").pack(side="left",padx=10)
            ctk.CTkLabel(row, text=feat.get("name","?")[:32], width=200,
                         font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
            enabled = feat.get("enabled", False)
            st_col = SUCCESS if enabled else TEXT_LIGHT
            ctk.CTkLabel(row, text="✅ Ativo" if enabled else "○ Inativo", width=90,
                         font=("Segoe UI",10,"bold"), text_color=st_col).pack(side="left",padx=4)
            if enabled:
                danger_btn(row, "⛔ Desativar",
                           command=lambda f=feat: self._toggle_feature(f, False),
                           width=110, height=28).pack(side="right",padx=8)
            else:
                success_btn(row, "✅ Ativar",
                            command=lambda f=feat: self._toggle_feature(f, True),
                            width=110, height=28).pack(side="right",padx=8)
        self._feat_count.configure(text=f"{len(data)} recursos")

    def _toggle_feature(self, feat, enable):
        name = feat.get("name","")
        action = "Ativando" if enable else "Desativando"
        self.run_async(B.toggle_windows_feature, name, enable,
                       done_cb=lambda r: [
                           self.app.status.set(f"{'OK' if r[0] else 'Erro'}: {name}"),
                           self._load_features()
                       ],
                       status=f"{action} {name}...")


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
class StartupPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._data = []
        self._build()

    def _build(self):
        self._header("🚀", "Inicialização do Windows", "Gerencie programas que iniciam com o Windows")
        tb = self._toolbar(self)
        orange_btn(tb, "🔄  Atualizar", command=self.load, width=130).pack(side="left",padx=10,pady=6)
        blue_btn(tb, "⚙  Gerenciador de Tarefas", command=lambda: os.startfile("taskmgr"), width=180).pack(side="left",padx=4)
        self._count = ctk.CTkLabel(tb, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._count.pack(side="right",padx=16)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        self._scroll.pack(fill="both", expand=True)
        self.after(300, self.load)

    def load(self):
        self.run_async(B.get_startup_items, done_cb=self._loaded, status="Carregando inicialização...")

    def _loaded(self, data):
        self._data = data
        self._render(data)

    def _render(self, data):
        for w in self._scroll.winfo_children(): w.destroy()
        self._table_header(self._scroll, [("Nome",200),("Comando",340),("Escopo",80),("Status",80),("Ação",120)])
        for i, item in enumerate(data):
            bg = BG_ROW if i%2==0 else BG_ROW2
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0, height=52)
            row.pack(fill="x")
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=item.get("name","?")[:30], width=200,
                         font=("Segoe UI",11,"bold"), text_color=TEXT_DARK, anchor="w").pack(side="left",padx=10)
            ctk.CTkLabel(row, text=item.get("command","?")[:55], width=340,
                         font=("Segoe UI",10), text_color=TEXT_LIGHT, anchor="w").pack(side="left",padx=4)
            ctk.CTkLabel(row, text=item.get("scope","?"), width=80,
                         font=("Segoe UI",10), text_color=BLUE_LIGHT).pack(side="left",padx=4)
            enabled = item.get("enabled",True)
            status_col = SUCCESS if enabled else DANGER
            ctk.CTkLabel(row, text="Ativo" if enabled else "Inativo", width=80,
                         font=("Segoe UI",10,"bold"), text_color=status_col).pack(side="left",padx=4)
            if enabled:
                ghost_btn(row, "⛔ Desativar",
                          command=lambda it=item: self._toggle(it, False),
                          width=110, height=28).pack(side="right",padx=8)
            else:
                success_btn(row, "✅ Ativar",
                            command=lambda it=item: self._toggle(it, True),
                            width=110, height=28).pack(side="right",padx=8)
        self._count.configure(text=f"{len(data)} itens")

    def _toggle(self, item, enable):
        B.set_startup_enabled(item["name"], item["scope"], enable)
        self.app.status.set(f"{'Ativado' if enable else 'Desativado'}: {item['name']}")
        self.load()


# ══════════════════════════════════════════════════════════════════════════════
# REDE
# ══════════════════════════════════════════════════════════════════════════════
class NetworkPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._info = {}
        self._build()

    def _build(self):
        self._header("🌐", "Rede & DNS", "Diagnóstico e configuração de rede")
        tb = self._toolbar(self)
        orange_btn(tb, "🔄  Atualizar", command=self.load, width=120).pack(side="left",padx=10,pady=6)
        blue_btn(tb, "🔧  Resetar Rede", command=self._reset_net, width=140).pack(side="left",padx=4)
        blue_btn(tb, "🗑  Limpar DNS Cache", command=self._flush_dns, width=160).pack(side="left",padx=4)
        blue_btn(tb, "📡  Ping Google", command=self._ping, width=130).pack(side="left",padx=4)

        body = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        body.pack(fill="both", expand=True)

        # IP Público
        section_title(body, "Informações de Rede")
        self._ip_card = card(body)
        self._ip_card.pack(fill="x", padx=20, pady=(0,12))
        self._ip_lbl = ctk.CTkLabel(self._ip_card, text="Carregando...",
                                     font=("Consolas",11), text_color=TEXT_MID,
                                     justify="left", anchor="w")
        self._ip_lbl.pack(fill="x", padx=16, pady=14)

        # DNS rápido
        section_title(body, "Alterar DNS Rápido")
        dns_card = card(body)
        dns_card.pack(fill="x", padx=20, pady=(0,12))
        dns_presets = ctk.CTkFrame(dns_card, fg_color="transparent")
        dns_presets.pack(fill="x", padx=16, pady=10)
        presets = [("Google (8.8.8.8)","8.8.8.8","8.8.4.4"),
                   ("Cloudflare (1.1.1.1)","1.1.1.1","1.0.0.1"),
                   ("OpenDNS","208.67.222.222","208.67.220.220"),
                   ("Quad9","9.9.9.9","149.112.112.112")]
        for lbl,p,s in presets:
            blue_btn(dns_presets, lbl, command=lambda pr=p,sc=s: self._set_dns(pr,sc),
                     width=180, height=32).pack(side="left",padx=4)

        # Custom DNS
        custom = ctk.CTkFrame(dns_card, fg_color="transparent")
        custom.pack(fill="x", padx=16, pady=(0,10))
        ctk.CTkLabel(custom, text="DNS Primário:", font=("Segoe UI",11), text_color=TEXT_MID, width=100).pack(side="left")
        self._dns1 = ctk.CTkEntry(custom, width=140, height=30, placeholder_text="8.8.8.8")
        self._dns1.pack(side="left",padx=4)
        ctk.CTkLabel(custom, text="DNS Secundário:", font=("Segoe UI",11), text_color=TEXT_MID, width=110).pack(side="left")
        self._dns2 = ctk.CTkEntry(custom, width=140, height=30, placeholder_text="8.8.4.4")
        self._dns2.pack(side="left",padx=4)
        orange_btn(custom, "Aplicar", command=self._apply_custom_dns, width=90, height=30).pack(side="left",padx=8)

        # Ping resultado
        section_title(body, "Diagnóstico")
        self._ping_card = card(body)
        self._ping_card.pack(fill="x", padx=20, pady=(0,20))
        self._ping_lbl = ctk.CTkLabel(self._ping_card, text="Clique em 'Ping Google' para testar.",
                                       font=("Consolas",11), text_color=TEXT_LIGHT)
        self._ping_lbl.pack(padx=16, pady=14)
        self.after(300, self.load)

    def load(self):
        self.run_async(B.get_network_info, done_cb=self._loaded, status="Carregando info de rede...")

    def _loaded(self, info):
        self._info = info
        lines=[f"🌍  IP Público:     {info.get('ip_public','?')}"]
        for a in info.get("adapters",[]):
            nm=a.get("InterfaceAlias",a.get("InterfaceDescription","?"))
            ip=a.get("IP",a.get("IPv4Address","?"))
            gw=a.get("Gateway","?"); dns=a.get("DNS","?"); sp=a.get("Speed","?"); st=a.get("Status","?")
            lines.append(f"\n📡  Adaptador:     {nm}  [{st}]")
            lines.append(f"    IP:            {ip}")
            lines.append(f"    Gateway:       {gw}")
            lines.append(f"    DNS:           {dns}")
            lines.append(f"    Velocidade:    {sp}")
        self._ip_lbl.configure(text="\n".join(lines))

    def _set_dns(self, primary, secondary):
        adapters=self._info.get("adapters",[])
        if not adapters: self.app.status.set("Nenhum adaptador detectado."); return
        adapter=adapters[0].get("InterfaceAlias","Ethernet")
        self.run_async(B.set_dns, adapter, primary, secondary,
                       done_cb=lambda r: self.app.status.set(f"DNS alterado: {'OK' if r[0] else 'Erro'}"),
                       status="Alterando DNS...")

    def _apply_custom_dns(self):
        p=self._dns1.get().strip(); s=self._dns2.get().strip()
        if not p: return
        self._set_dns(p, s)

    def _flush_dns(self):
        self.run_async(B.flush_dns, done_cb=lambda r: self.app.status.set("DNS cache limpo!"),status="Limpando DNS...")

    def _ping(self):
        self._ping_lbl.configure(text="Pingando google.com...")
        def _do(): return B.run_ping("google.com")
        self.run_async(_do, done_cb=lambda r: self._ping_lbl.configure(text=str(r)[:400]), status="Pingando...")

    def _reset_net(self):
        dlg=ConfirmDialog(self.app,"Resetar Rede","Resetar configurações de rede?\n\nConexão será temporariamente interrompida.",ok_text="Resetar",ok_color=DANGER)
        if not dlg.confirmed: return
        self.run_async(B.reset_network, done_cb=lambda _: self.app.status.set("Rede resetada! Reconecte."),status="Resetando rede...")


# ══════════════════════════════════════════════════════════════════════════════
# SERVIÇOS
# ══════════════════════════════════════════════════════════════════════════════
class ServicesPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._data = []
        self._build()

    def _build(self):
        self._header("⚙", "Serviços do Windows", "Inicie, pare ou desative serviços do sistema")
        tb = self._toolbar(self)
        orange_btn(tb, "🔄  Atualizar", command=self.load, width=120).pack(side="left",padx=10,pady=6)
        self._filter_var = tk.StringVar(value="Todos")
        ctk.CTkSegmentedButton(tb, values=["Todos","Em execução","Parados"],
                                variable=self._filter_var, font=("Segoe UI",11),
                                selected_color=ORANGE, selected_hover_color=ORANGE_DARK,
                                command=lambda _: self._apply_filter()
                                ).pack(side="left",padx=8)
        self._search = tk.StringVar()
        self._search.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(tb, textvariable=self._search, placeholder_text="🔍 Buscar...",
                     width=200, height=32).pack(side="left",padx=8)
        self._count = ctk.CTkLabel(tb, text="", font=("Segoe UI",11), text_color=TEXT_LIGHT)
        self._count.pack(side="right",padx=16)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        self._scroll.pack(fill="both", expand=True)
        self.after(300, self.load)

    def load(self):
        self.run_async(B.get_services, done_cb=self._loaded, status="Carregando serviços...")

    def _loaded(self, data):
        self._data = data
        self._apply_filter()

    def _apply_filter(self):
        filt = self._filter_var.get()
        q = self._search.get().lower()
        data = self._data
        if filt == "Em execução": data=[s for s in data if "run" in s.get("status","").lower()]
        elif filt == "Parados": data=[s for s in data if "stop" in s.get("status","").lower()]
        if q: data=[s for s in data if q in s.get("display","").lower() or q in s.get("name","").lower()]
        self._render(data)

    def _render(self, data):
        for w in self._scroll.winfo_children(): w.destroy()
        self._table_header(self._scroll, [("Nome",220),("Nome Interno",160),("Status",90),("Inicialização",100),("Ações",180)])
        for i, svc in enumerate(data):
            bg = BG_ROW if i%2==0 else BG_ROW2
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0, height=46)
            row.pack(fill="x")
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=svc.get("display","?")[:35], width=220,
                         font=("Segoe UI",11,"bold"), text_color=TEXT_DARK, anchor="w").pack(side="left",padx=10)
            ctk.CTkLabel(row, text=svc.get("name","?")[:25], width=160,
                         font=("Segoe UI",10), text_color=TEXT_LIGHT).pack(side="left",padx=4)
            running = svc.get("running", False) or "Run" in str(svc.get("status",""))
            st_col=SUCCESS if running else DANGER
            ctk.CTkLabel(row, text="▶ Rodando" if running else "■ Parado", width=90,
                         font=("Segoe UI",10,"bold"), text_color=st_col).pack(side="left",padx=4)
            st_map={"Automatic":"Auto","Manual":"Manual","Disabled":"Desativado"}
            st_txt=st_map.get(svc.get("start_type",""),"—")
            ctk.CTkLabel(row, text=st_txt, width=100,
                         font=("Segoe UI",10), text_color=TEXT_MID).pack(side="left",padx=4)
            # Botões ação
            btn_f=ctk.CTkFrame(row, fg_color="transparent")
            btn_f.pack(side="right",padx=6)
            nm=svc.get("name","")
            if running:
                ghost_btn(btn_f,"⏹",command=lambda n=nm: self._action(n,"stop"),width=36,height=26).pack(side="left",padx=1)
                ghost_btn(btn_f,"🔄",command=lambda n=nm: self._action(n,"restart"),width=36,height=26).pack(side="left",padx=1)
            else:
                success_btn(btn_f,"▶",command=lambda n=nm: self._action(n,"start"),width=36,height=26).pack(side="left",padx=1)
            if st_txt!="Desativado":
                danger_btn(btn_f,"🚫",command=lambda n=nm: self._action(n,"disable"),width=36,height=26).pack(side="left",padx=1)
            else:
                blue_btn(btn_f,"✅",command=lambda n=nm: self._action(n,"auto"),width=36,height=26).pack(side="left",padx=1)
        self._count.configure(text=f"{len(data)} serviços")

    def _action(self, name, action):
        labels={"start":"Iniciando","stop":"Parando","restart":"Reiniciando","disable":"Desativando","auto":"Ativando"}
        self.run_async(B.service_action, name, action,
                       done_cb=lambda r: [self.app.status.set(f"{'OK' if r[0] else 'Erro'}: {name}"), self.load()],
                       status=f"{labels.get(action,'Executando')} {name}...")


# ══════════════════════════════════════════════════════════════════════════════
# PONTO DE RESTAURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
class RestorePage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._data=[]
        self._build()

    def _build(self):
        self._header("🛡", "Pontos de Restauração", "Crie e gerencie pontos de restauração do sistema")
        tb=self._toolbar(self)
        orange_btn(tb,"➕  Criar Ponto Agora",command=self._create,width=170).pack(side="left",padx=10,pady=6)
        blue_btn(tb,"🔄  Atualizar Lista",command=self.load,width=140).pack(side="left",padx=4)
        blue_btn(tb,"⚙  Configurar Restauração",command=lambda:B.ps("Start-Process SystemPropertiesProtection",5),width=200).pack(side="left",padx=4)

        body=ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        body.pack(fill="both", expand=True)

        section_title(body,"Criar Novo Ponto")
        c=card(body)
        c.pack(fill="x",padx=20,pady=(0,12))
        f=ctk.CTkFrame(c,fg_color="transparent")
        f.pack(fill="x",padx=16,pady=12)
        ctk.CTkLabel(f,text="Descrição:",font=("Segoe UI",11),text_color=TEXT_MID,width=80).pack(side="left")
        self._desc=ctk.CTkEntry(f,width=300,height=32,placeholder_text="Ex: Antes de instalar driver")
        self._desc.pack(side="left",padx=8)
        orange_btn(f,"Criar",command=self._create,width=90,height=32).pack(side="left",padx=4)

        section_title(body,"Pontos Existentes")
        self._rp_frame=card(body)
        self._rp_frame.pack(fill="x",padx=20,pady=(0,20))
        self._rp_lbl=ctk.CTkLabel(self._rp_frame,text="Carregando...",font=("Segoe UI",11),text_color=TEXT_LIGHT)
        self._rp_lbl.pack(padx=16,pady=14)
        self.after(300,self.load)

    def load(self):
        self.run_async(B.get_restore_points,done_cb=self._loaded,status="Carregando pontos de restauração...")

    def _loaded(self,data):
        self._data=data
        for w in self._rp_frame.winfo_children(): w.destroy()
        if not data:
            ctk.CTkLabel(self._rp_frame,text="Nenhum ponto de restauração encontrado.",
                         font=("Segoe UI",12),text_color=TEXT_LIGHT).pack(padx=16,pady=14)
            return
        self._table_header(self._rp_frame,[("Descrição",320),("Data",160),("Seq",60),("Ação",120)])
        for i,rp in enumerate(data):
            bg=BG_ROW if i%2==0 else BG_ROW2
            row=ctk.CTkFrame(self._rp_frame,fg_color=bg,corner_radius=0,height=46)
            row.pack(fill="x")
            row.pack_propagate(False)
            ctk.CTkLabel(row,text=rp.get("desc","?"),width=320,font=("Segoe UI",11,"bold"),text_color=TEXT_DARK,anchor="w").pack(side="left",padx=10)
            ctk.CTkLabel(row,text=rp.get("date","?"),width=160,font=("Segoe UI",10),text_color=TEXT_MID).pack(side="left",padx=4)
            ctk.CTkLabel(row,text=str(rp.get("seq","")),width=60,font=("Segoe UI",10),text_color=TEXT_LIGHT).pack(side="left",padx=4)
            blue_btn(row,"↩ Restaurar",command=lambda r=rp:self._restore(r),width=100,height=28).pack(side="right",padx=8)

    def _create(self):
        desc=self._desc.get().strip() or "Alphas Gerenciador"
        self.run_async(B.create_restore_point,desc,
                       done_cb=lambda r:[self.app.status.set(f"Ponto criado: {'OK' if r[0] else 'Erro'}"),self.load()],
                       status="Criando ponto de restauração...")

    def _restore(self,rp):
        dlg=ConfirmDialog(self.app,"Restaurar Sistema",
                          f"Restaurar para:\n'{rp.get('desc','')}'\n{rp.get('date','')}\n\nO computador será reiniciado!",
                          ok_text="Restaurar",ok_color=DANGER)
        if not dlg.confirmed: return
        B.restore_to_point(rp["seq"])
        self.app.status.set("Restauração iniciada — PC será reiniciado.")


# ══════════════════════════════════════════════════════════════════════════════
# BACKUP
# ══════════════════════════════════════════════════════════════════════════════
class BackupPage(BasePage):
    def __init__(self,parent,app):
        super().__init__(parent,app)
        self._build()

    def _build(self):
        self._header("💾","Backup","Crie cópias de segurança dos seus arquivos")
        body=ctk.CTkScrollableFrame(self,fg_color=BG_MAIN)
        body.pack(fill="both",expand=True)

        section_title(body,"Backup de Pasta")
        c=card(body)
        c.pack(fill="x",padx=20,pady=(0,12))
        f=ctk.CTkFrame(c,fg_color="transparent")
        f.pack(fill="x",padx=16,pady=10)
        ctk.CTkLabel(f,text="Origem:",font=("Segoe UI",11),text_color=TEXT_MID,width=70).pack(side="left")
        self._src=ctk.CTkEntry(f,width=340,height=32,placeholder_text="C:\\Users\\Usuário\\Documentos")
        self._src.pack(side="left",padx=6)
        ghost_btn(f,"📁 Escolher",command=self._pick_src,width=100,height=32).pack(side="left",padx=4)

        f2=ctk.CTkFrame(c,fg_color="transparent")
        f2.pack(fill="x",padx=16,pady=(0,10))
        ctk.CTkLabel(f2,text="Destino:",font=("Segoe UI",11),text_color=TEXT_MID,width=70).pack(side="left")
        self._dst=ctk.CTkEntry(f2,width=340,height=32,placeholder_text="D:\\Backups")
        self._dst.pack(side="left",padx=6)
        ghost_btn(f2,"📁 Escolher",command=self._pick_dst,width=100,height=32).pack(side="left",padx=4)

        orange_btn(c,"💾  Iniciar Backup",command=self._backup,width=160,height=38).pack(padx=16,pady=(0,12))

        self._result=ctk.CTkLabel(c,text="",font=("Segoe UI",11),text_color=TEXT_MID)
        self._result.pack(padx=16,pady=(0,8))

        section_title(body,"Backup do Windows (Histórico de Arquivos)")
        c2=card(body)
        c2.pack(fill="x",padx=20,pady=(0,12))
        ctk.CTkLabel(c2,text="Configure o Backup integrado do Windows para proteção contínua.",
                     font=("Segoe UI",11),text_color=TEXT_MID).pack(padx=16,pady=8)
        blue_btn(c2,"⚙  Abrir Configurações de Backup do Windows",command=B.open_backup_settings,width=320,height=36).pack(padx=16,pady=(0,14))

        section_title(body,"Dicas de Backup")
        tips=card(body)
        tips.pack(fill="x",padx=20,pady=(0,20))
        for tip in ["✅  Faça backup regularmente (semanal ou mensal)",
                    "✅  Mantenha ao menos 2 cópias em locais diferentes",
                    "✅  Use HD externo ou nuvem (OneDrive, Google Drive)",
                    "✅  Teste restaurar o backup periodicamente",
                    "⚠   Arquivos em uso podem não ser copiados corretamente"]:
            ctk.CTkLabel(tips,text=tip,font=("Segoe UI",11),text_color=TEXT_MID,anchor="w").pack(anchor="w",padx=16,pady=2)
        ctk.CTkFrame(tips,height=8,fg_color="transparent").pack()

    def _pick_src(self):
        d=fd.askdirectory()
        if d: self._src.delete(0,"end"); self._src.insert(0,d)

    def _pick_dst(self):
        d=fd.askdirectory()
        if d: self._dst.delete(0,"end"); self._dst.insert(0,d)

    def _backup(self):
        src=self._src.get().strip(); dst=self._dst.get().strip()
        if not src or not dst: self._result.configure(text="⚠ Informe origem e destino.",text_color=WARNING); return
        self.run_async(B.backup_files,src,dst,
                       done_cb=lambda r:self._result.configure(text=f"{'✅ ' if r[0] else '❌ '}{r[1]}",
                                                                text_color=SUCCESS if r[0] else DANGER),
                       status="Criando backup...")


# ══════════════════════════════════════════════════════════════════════════════
# MODO DEUS
# ══════════════════════════════════════════════════════════════════════════════
class GodModePage(BasePage):
    def __init__(self,parent,app):
        super().__init__(parent,app)
        self._build()

    def _build(self):
        self._header("👑","Modo Deus — God Mode","Acesso a todas as configurações do Windows em um só lugar")
        tb=self._toolbar(self)
        orange_btn(tb,"👑  Criar Pasta God Mode na Área de Trabalho",
                   command=self._create_gm,width=310,height=36).pack(side="left",padx=10,pady=6)
        self._search=tk.StringVar()
        self._search.trace_add("write",lambda *_:self._filter())
        ctk.CTkEntry(tb,textvariable=self._search,placeholder_text="🔍 Buscar configuração...",
                     width=240,height=32).pack(side="left",padx=8)

        body=ctk.CTkScrollableFrame(self,fg_color=BG_MAIN)
        body.pack(fill="both",expand=True)
        self._body=body
        self._render(B.GOD_MODE_ITEMS)

    def _filter(self):
        q=self._search.get().lower()
        filtered=[it for it in B.GOD_MODE_ITEMS if q in it[1].lower() or q in it[0].lower()] if q else B.GOD_MODE_ITEMS
        self._render(filtered)

    def _render(self,items):
        for w in self._body.winfo_children(): w.destroy()
        # Agrupa por categoria
        cats={}
        for cat,name,cmd in items:
            cats.setdefault(cat,[]).append((name,cmd))
        for cat,entries in cats.items():
            section_title(self._body,cat,pady=(14,4))
            grid=ctk.CTkFrame(self._body,fg_color="transparent")
            grid.pack(fill="x",padx=20,pady=(0,4))
            for col in range(4): grid.columnconfigure(col,weight=1)
            for idx,(name,cmd) in enumerate(entries):
                r,c=divmod(idx,4)
                btn=ctk.CTkButton(grid,text=name,font=("Segoe UI",11),
                                  fg_color=BG_CARD,hover_color=BG_HOVER,
                                  text_color=TEXT_DARK,border_width=1,border_color="#CBD5E0",
                                  height=36,corner_radius=6,anchor="w",
                                  command=lambda cm=cmd:B.open_god_mode_item(cm))
                btn.grid(row=r,column=c,padx=4,pady=3,sticky="ew")

    def _create_gm(self):
        ok,path=B.create_god_mode()
        self.app.status.set(f"{'God Mode criado em: '+path if ok else 'Erro: '+path}")
