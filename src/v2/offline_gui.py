"""GUI offline estilo dashboard (pegada anexo01) + tema VicioAI/Método VDE."""

from __future__ import annotations

import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .offline_core import descobrir_raiz, run_offline

# Paleta VicioAI / Método VDE (roxo → magenta)
BG = "#12081F"
PANEL = "#1A102E"
CARD = "#241536"
CARD2 = "#2E1B45"
PURPLE = "#7C3AED"
MAGENTA = "#C026D3"
PINK = "#E879F9"
TEXT = "#F5F3FF"
MUTED = "#C4B5FD"
OK = "#34D399"
WARN = "#FBBF24"
SIDE = "#1C1233"


class MetricCard(ctk.CTkFrame):
    def __init__(self, master, title: str, accent: str = PURPLE, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=18, **kwargs)
        self.accent = accent
        bar = ctk.CTkFrame(self, fg_color=accent, height=4, corner_radius=2)
        bar.pack(fill="x", padx=14, pady=(12, 4))
        self.lbl_title = ctk.CTkLabel(
            self, text=title, text_color=MUTED, font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_title.pack(anchor="w", padx=16, pady=(4, 0))
        self.lbl_value = ctk.CTkLabel(
            self, text="—", text_color=TEXT, font=ctk.CTkFont(size=28, weight="bold")
        )
        self.lbl_value.pack(anchor="w", padx=16, pady=(2, 14))

    def set_value(self, value: str) -> None:
        self.lbl_value.configure(text=value)


class OfflineGui(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("VicioAI · Classificação Offline")
        self.geometry("1180x720")
        self.minsize(1020, 640)
        self.configure(fg_color=BG)
        self.raiz = descobrir_raiz()
        self._running = False

        self._build_header()
        self._build_controls()
        self._build_body()
        self._build_footer()
        self._set_status("Pronto. Escolha o perfil e clique em Iniciar.")

    def _build_header(self) -> None:
        head = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=88)
        head.pack(fill="x")
        head.pack_propagate(False)

        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left", padx=24, pady=16)
        ctk.CTkLabel(
            left,
            text="Classificação",
            text_color=TEXT,
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="VicioAI Case · Offline Benchmark (sem LLM)",
            text_color=MUTED,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w")

        right = ctk.CTkFrame(head, fg_color="transparent")
        right.pack(side="right", padx=24, pady=16)
        ctk.CTkLabel(right, text="Progresso", text_color=MUTED, font=ctk.CTkFont(size=12)).pack(
            anchor="e"
        )
        self.progress = ctk.CTkProgressBar(
            right, width=260, height=10, progress_color=MAGENTA, fg_color=CARD2
        )
        self.progress.pack(anchor="e", pady=(6, 0))
        self.progress.set(0)
        self.lbl_pct = ctk.CTkLabel(right, text="0%", text_color=PINK, font=ctk.CTkFont(size=12))
        self.lbl_pct.pack(anchor="e")

    def _build_controls(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=16)
        bar.pack(fill="x", padx=20, pady=(14, 8))

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(inner, text="Perfil", text_color=MUTED).grid(row=0, column=0, sticky="w")
        self.perfil = ctk.CTkOptionMenu(
            inner,
            values=["Completo (659)", "Amostra rápida (50)", "Smoke (10)"],
            fg_color=CARD2,
            button_color=PURPLE,
            button_hover_color=MAGENTA,
            dropdown_fg_color=CARD,
            width=180,
        )
        self.perfil.set("Completo (659)")
        self.perfil.grid(row=1, column=0, padx=(0, 16), pady=(4, 0))

        ctk.CTkLabel(inner, text="Meta de precisão", text_color=MUTED).grid(
            row=0, column=1, sticky="w"
        )
        self.meta = ctk.CTkEntry(
            inner, width=120, fg_color=CARD2, border_color=PURPLE, text_color=TEXT
        )
        self.meta.insert(0, "≥ 95%")
        self.meta.configure(state="disabled")
        self.meta.grid(row=1, column=1, padx=(0, 16), pady=(4, 0))

        ctk.CTkLabel(inner, text="Modo", text_color=MUTED).grid(row=0, column=2, sticky="w")
        self.modo = ctk.CTkEntry(
            inner, width=160, fg_color=CARD2, border_color=PURPLE, text_color=TEXT
        )
        self.modo.insert(0, "Offline · 0 API")
        self.modo.configure(state="disabled")
        self.modo.grid(row=1, column=2, padx=(0, 16), pady=(4, 0))

        self.btn = ctk.CTkButton(
            inner,
            text="Iniciar",
            width=140,
            height=40,
            corner_radius=20,
            fg_color=MAGENTA,
            hover_color=PURPLE,
            text_color=TEXT,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_start,
        )
        self.btn.grid(row=0, column=3, rowspan=2, padx=(20, 0), sticky="e")
        inner.grid_columnconfigure(4, weight=1)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=8)

        # Sidebar
        side = ctk.CTkFrame(body, fg_color=SIDE, corner_radius=18, width=210)
        side.pack(side="left", fill="y", padx=(0, 12))
        side.pack_propagate(False)
        ctk.CTkLabel(
            side, text="Métricas", text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 8))
        for nome in [
            "Publicar",
            "Revisar",
            "Fora",
            "Holdout prec.",
            "Cobertura",
            "API calls",
            "LLM na decisão",
            "Cache emb.",
        ]:
            row = ctk.CTkFrame(side, fg_color=CARD, corner_radius=12, height=36)
            row.pack(fill="x", padx=12, pady=4)
            row.pack_propagate(False)
            ctk.CTkFrame(row, fg_color=MAGENTA, width=4, corner_radius=2).pack(
                side="left", fill="y", padx=(8, 8), pady=8
            )
            ctk.CTkLabel(row, text=nome, text_color=MUTED, font=ctk.CTkFont(size=12)).pack(
                side="left"
            )

        # Main column
        main = ctk.CTkFrame(body, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True)

        grid = ctk.CTkFrame(main, fg_color="transparent")
        grid.pack(fill="x")
        self.cards: dict[str, MetricCard] = {}
        specs = [
            ("publicar", "Publicar", OK),
            ("revisar", "Revisar", WARN),
            ("fora", "Fora", PURPLE),
            ("holdout", "Holdout precisão", MAGENTA),
            ("cobertura", "Cobertura (eval)", PINK),
            ("api", "Chamadas API", MUTED),
            ("llm", "LLM na decisão", MUTED),
            ("questoes", "Questões", PURPLE),
        ]
        for i, (key, title, accent) in enumerate(specs):
            card = MetricCard(grid, title, accent=accent, width=180, height=100)
            card.grid(row=i // 4, column=i % 4, padx=6, pady=6, sticky="nsew")
            self.cards[key] = card
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1)

        self.cards["api"].set_value("0")
        self.cards["llm"].set_value("Não")
        self.cards["questoes"].set_value("659")

        log_wrap = ctk.CTkFrame(main, fg_color=PANEL, corner_radius=18)
        log_wrap.pack(fill="both", expand=True, pady=(10, 0))
        ctk.CTkLabel(
            log_wrap,
            text="Log de processamento",
            text_color=TEXT,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))
        self.log = ctk.CTkTextbox(
            log_wrap,
            fg_color=CARD,
            text_color=TEXT,
            corner_radius=14,
            font=ctk.CTkFont(family="Consolas", size=13),
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._log("Pronto para executar o benchmark offline.")
        self._log(f"Pasta: {self.raiz}")

    def _build_footer(self) -> None:
        foot = ctk.CTkFrame(self, fg_color="#0A0414", height=64, corner_radius=0)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        left = ctk.CTkFrame(foot, fg_color="transparent")
        left.pack(side="left", padx=20, pady=10)
        ctk.CTkLabel(
            left,
            text="VicioAI",
            text_color=TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="Case classificação de tópicos · inspirado na experiência Método VDE",
            text_color=MUTED,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w")

        ctk.CTkButton(
            foot,
            text="Abrir metodovde.com.br",
            width=180,
            height=32,
            corner_radius=16,
            fg_color=PURPLE,
            hover_color=MAGENTA,
            command=lambda: webbrowser.open("https://metodovde.com.br/"),
        ).pack(side="right", padx=20, pady=14)

        self.status = ctk.CTkLabel(self, text="", text_color=MUTED, font=ctk.CTkFont(size=12))
        self.status.pack(fill="x", padx=24, pady=(0, 8))

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _log(self, msg: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{stamp}] {msg}\n")
        self.log.see("end")

    def _limite(self) -> int | None:
        p = self.perfil.get()
        if "50" in p:
            return 50
        if "10" in p:
            return 10
        return None

    def _on_start(self) -> None:
        if self._running:
            return
        self._running = True
        self.btn.configure(state="disabled", text="Rodando…")
        self.progress.set(0)
        self.lbl_pct.configure(text="0%")
        self._set_status("Executando classificação offline…")
        self._log("=== Início do benchmark offline ===")
        self._log("Nenhuma chamada a OpenAI/Jev/LLM será feita.")

        def worker() -> None:
            try:
                resumo = run_offline(
                    raiz=self.raiz,
                    limite=self._limite(),
                    on_progress=self._on_progress_threadsafe,
                )
                self.after(0, lambda: self._on_done(resumo))
            except Exception as e:
                self.after(0, lambda: self._on_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress_threadsafe(self, msg: str, pct: float, metrics: dict | None) -> None:
        self.after(0, lambda: self._apply_progress(msg, pct, metrics))

    def _apply_progress(self, msg: str, pct: float, metrics: dict | None) -> None:
        self.progress.set(pct)
        self.lbl_pct.configure(text=f"{int(pct * 100)}%")
        self._log(msg)
        if not metrics:
            return
        if "publicar" in metrics:
            self.cards["publicar"].set_value(str(metrics["publicar"]))
        if "revisar" in metrics:
            self.cards["revisar"].set_value(str(metrics["revisar"]))
        if "fora" in metrics:
            self.cards["fora"].set_value(str(metrics["fora"]))
        if "holdout_prec" in metrics and metrics["holdout_prec"] is not None:
            self.cards["holdout"].set_value(f"{metrics['holdout_prec'] * 100:.0f}%")
        if "cobertura_fora_folha" in metrics:
            self.cards["cobertura"].set_value(f"{metrics['cobertura_fora_folha'] * 100:.1f}%")
        if "questoes" in metrics:
            self.cards["questoes"].set_value(str(metrics["questoes"]))
        if "total" in metrics:
            self.cards["questoes"].set_value(str(metrics["total"]))

    def _on_done(self, resumo: dict) -> None:
        self._running = False
        self.btn.configure(state="normal", text="Iniciar")
        dist = resumo.get("distribuicao", {})
        self.cards["publicar"].set_value(str(dist.get("publicar", 0)))
        self.cards["revisar"].set_value(str(dist.get("revisar", 0)))
        self.cards["fora"].set_value(str(dist.get("fora", 0)))
        hold = resumo.get("holdout", {})
        if hold:
            self.cards["holdout"].set_value(f"{hold.get('precisao', 0) * 100:.0f}%")
        self.cards["cobertura"].set_value(f"{resumo.get('cobertura_fora_folha', 0) * 100:.1f}%")
        self.cards["api"].set_value("0")
        self.cards["llm"].set_value("Não")
        self._log("=== Concluído ===")
        self._log(f"Saída: {resumo.get('saida')}")
        self._set_status("Pronto. Artefatos em saida_offline/")
        messagebox.showinfo(
            "VicioAI Offline",
            "Classificação concluída sem LLM.\n\n"
            f"Publicar: {dist.get('publicar', 0)}\n"
            f"Revisar: {dist.get('revisar', 0)}\n"
            f"Pasta: saida_offline/",
        )

    def _on_error(self, err: Exception) -> None:
        self._running = False
        self.btn.configure(state="normal", text="Iniciar")
        self._log(f"ERRO: {err}")
        self._set_status("Falha na execução. Veja o log.")
        messagebox.showerror("Erro", str(err))


def main() -> int:
    app = OfflineGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
