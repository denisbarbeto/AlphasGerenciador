# Copyright (C) 2025 Denis Garcia Barbeto / Alphas Consultoria Digital
# CNPJ: 40.268.116/0001-60
# GNU General Public License v3 — consulte o arquivo LICENSE.

"""Widgets reutilizáveis do Alphas Gerenciador."""
import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk
from theme import *


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=CARD_RADIUS, **kw)

def section_title(parent, text, pady=(16,6)):
    ctk.CTkLabel(parent, text=text, font=("Segoe UI", 13, "bold"),
                 text_color=BLUE).pack(anchor="w", padx=20, pady=pady)

def tag_badge(parent, text, color=BLUE_ACCENT, text_color=TEXT_WHITE):
    f = ctk.CTkFrame(parent, fg_color=color, corner_radius=4, width=1, height=1)
    ctk.CTkLabel(f, text=text, font=("Segoe UI", 9, "bold"),
                 text_color=text_color).pack(padx=6, pady=1)
    return f

def orange_btn(parent, text, command=None, width=130, height=36, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=ORANGE, hover_color=ORANGE_DARK,
                         text_color=TEXT_WHITE, font=("Segoe UI", 12, "bold"),
                         width=width, height=height, corner_radius=6, **kw)

def blue_btn(parent, text, command=None, width=130, height=36, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=BLUE_LIGHT, hover_color=BLUE,
                         text_color=TEXT_WHITE, font=("Segoe UI", 12),
                         width=width, height=height, corner_radius=6, **kw)

def ghost_btn(parent, text, command=None, width=100, height=32, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color="transparent", hover_color=BG_HOVER,
                         text_color=TEXT_MID, font=("Segoe UI", 11),
                         border_width=1, border_color="#CBD5E0",
                         width=width, height=height, corner_radius=6, **kw)

def danger_btn(parent, text, command=None, width=100, height=32, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=DANGER, hover_color="#C53030",
                         text_color=TEXT_WHITE, font=("Segoe UI", 11),
                         width=width, height=height, corner_radius=6, **kw)

def success_btn(parent, text, command=None, width=100, height=32, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=SUCCESS, hover_color="#276749",
                         text_color=TEXT_WHITE, font=("Segoe UI", 11),
                         width=width, height=height, corner_radius=6, **kw)

def divider(parent, pady=8):
    ctk.CTkFrame(parent, height=1, fg_color="#E2E8F0").pack(fill="x", padx=16, pady=pady)

def info_row(parent, label, value, value_color=TEXT_DARK):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=16, pady=3)
    ctk.CTkLabel(row, text=label, font=("Segoe UI", 11), text_color=TEXT_LIGHT,
                 width=160, anchor="w").pack(side="left")
    ctk.CTkLabel(row, text=str(value), font=("Segoe UI", 11, "bold"),
                 text_color=value_color, anchor="w").pack(side="left")

class StatusBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, height=28, fg_color="#E2E8F0", corner_radius=0)
        self._msg = ctk.CTkLabel(self, text="Pronto", font=("Segoe UI", 10),
                                  text_color=TEXT_LIGHT)
        self._msg.pack(side="left", padx=12)
        ctk.CTkLabel(self, text="Desenvolvido e Criado por Alphas Consultoria Digital",
                     font=("Segoe UI", 10), text_color=TEXT_LIGHT
                     ).pack(side="right", padx=12)
    def set(self, msg): self._msg.configure(text=msg)

class LoadingOverlay(ctk.CTkFrame):
    def __init__(self, parent, msg="Aguarde..."):
        super().__init__(parent, fg_color="#00000066", corner_radius=0)
        inner = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12,
                              width=300, height=120)
        inner.place(relx=.5, rely=.5, anchor="center")
        ctk.CTkLabel(inner, text="⏳  " + msg, font=("Segoe UI", 13),
                     text_color=TEXT_DARK).pack(expand=True)
        bar = ctk.CTkProgressBar(inner, mode="indeterminate", width=240,
                                  fg_color="#E2E8F0", progress_color=ORANGE)
        bar.pack(pady=(0,16))
        bar.start()

class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Confirmar", message="Tem certeza?",
                 ok_text="Confirmar", ok_color=DANGER):
        super().__init__(parent)
        self.title(title)
        self.geometry("440x200")
        self.resizable(False, False)
        self.configure(fg_color=BG_CARD)
        self.confirmed = False
        self.grab_set()
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 14, "bold"),
                     text_color=BLUE).pack(pady=(20,6))
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 11),
                     text_color=TEXT_MID, wraplength=400, justify="center").pack(padx=20)
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(pady=20)
        ghost_btn(f, "Cancelar", command=self.destroy, width=110).pack(side="left", padx=8)
        ctk.CTkButton(f, text=ok_text, fg_color=ok_color, width=110, height=32,
                      corner_radius=6, font=("Segoe UI", 11, "bold"),
                      command=self._ok).pack(side="left", padx=8)
        self.wait_window()

    def _ok(self):
        self.confirmed = True
        self.destroy()
