"""
JoaKApple - interface grafica.

Toolkit para baixar, verificar e descriptografar retorno de oficios
judiciais da Apple.

Autor: Joaquim Ferreira Silva Neto <joaquimfsneto@gmail.com>
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import core

APP_TITLE = "JoaKApple"
APP_DESCRIPTION = "Toolkit para baixar, verificar e descriptografar retorno de ofícios judiciais da Apple"
APP_VERSION = "1.1.0"
AUTHOR_LINE = "Joaquim Ferreira Silva Neto  ·  joaquimfsneto@gmail.com"

ACCENT = "#0F6B62"
ACCENT_HOVER = "#0A4A45"
ACCENT_TINT = "#E4F1EF"
BG_APP = "#EDEAE3"
BG_CARD = "#FBFAF7"
BORDER = "#DEDAD1"
BORDER_SOFT = "#ECE8DF"
TEXT_PRIMARY = "#1C1B18"
TEXT_SECONDARY = "#6B6862"
BADGE_INACTIVE_BG = "#EDEAE3"
LOG_BG = "#1C1B18"
LOG_HEADER_BG = "#26241F"
LOG_TEXT = "#D8D4C8"
LOG_TEXT_DIM = "#7A7669"
DISABLED_BG = "#F5F3EE"
BUTTON_DISABLED_BG = "#C9C5BA"

STATUS_LABELS = {
    "pendente": "Pendente",
    "baixando": "Baixando...",
    "conferindo": "Conferindo hash...",
    "decriptando": "Descriptografando...",
    "hash_invalido": "HASH INVALIDO",
    "erro": "ERRO",
    "cancelado": "Cancelado",
    "concluido": "Concluido",
}

STEP_META = {
    "download": ("1", "Baixar", "Baixa os arquivos do CSV, retomando downloads incompletos automaticamente."),
    "verify": ("2", "Verificar", "Confere o hash SHA256 de cada arquivo contra o valor informado pela Apple."),
    "decrypt": ("3", "Descriptografar", "Usa a senha GPG para descriptografar os arquivos .gpg já conferidos."),
}


class StepCard(ctk.CTkFrame):
    def __init__(self, master, key: str, on_toggle, **kwargs):
        super().__init__(
            master,
            fg_color=ACCENT_TINT,
            border_width=2,
            border_color=ACCENT,
            corner_radius=10,
            **kwargs,
        )
        self.key = key
        num, title, desc = STEP_META[key]
        self.var = tk.BooleanVar(value=True)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 4))

        self.badge = ctk.CTkLabel(
            top, text=num, width=22, height=22, corner_radius=11,
            fg_color=ACCENT, text_color="#FFFFFF",
            font=ctk.CTkFont(family="DejaVu Sans", size=12, weight="bold"),
        )
        self.badge.pack(side="left")

        ctk.CTkLabel(
            top, text=title, text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=14, weight="bold"),
        ).pack(side="left", padx=(8, 0))

        self.switch = ctk.CTkSwitch(
            top, text="", variable=self.var, width=36,
            progress_color=ACCENT, button_color="#FFFFFF",
            command=lambda: on_toggle(self.key),
        )
        self.switch.pack(side="right")

        ctk.CTkLabel(
            self, text=desc, text_color=TEXT_SECONDARY, justify="left",
            wraplength=200, font=ctk.CTkFont(family="DejaVu Sans", size=11),
        ).pack(fill="x", padx=14, pady=(0, 12))

    def set_active(self, active: bool):
        self.configure(
            fg_color=ACCENT_TINT if active else "#FFFFFF",
            border_color=ACCENT if active else BORDER,
        )
        self.badge.configure(
            fg_color=ACCENT if active else BADGE_INACTIVE_BG,
            text_color="#FFFFFF" if active else TEXT_SECONDARY,
        )


class JoaKAppleGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")

        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1040x760")
        self.minsize(880, 620)
        self.configure(fg_color=BG_APP)

        self.update_queue: queue.Queue = queue.Queue()
        self.log_queue: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.entries: list[core.FileEntry] = []
        self.row_by_name: dict[str, str] = {}
        self.step_cards: dict[str, StepCard] = {}

        self.csv_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.passphrase_var = tk.StringVar()
        self.workers_var = tk.StringVar(value="4")
        self.show_pass_var = tk.BooleanVar(value=False)

        self._build_widgets()
        self._poll_queues()

    # ------------------------------------------------------------------ UI

    def _build_widgets(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 6))
        ctk.CTkLabel(
            header, text=APP_TITLE, text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=20, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text=APP_DESCRIPTION, text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=12),
        ).pack(anchor="w")

        # --- Config card ---
        config_card = ctk.CTkFrame(
            self, fg_color=BG_CARD, border_width=1, border_color=BORDER_SOFT, corner_radius=10
        )
        config_card.pack(fill="x", padx=20, pady=8)
        config_card.columnconfigure((0, 1), weight=1)

        self._field(config_card, "Arquivo CSV da Apple", self.csv_path_var, self._pick_csv, row=0, col=0)
        self._field(config_card, "Pasta de destino", self.output_dir_var, self._pick_output_dir, row=0, col=1)

        row2 = ctk.CTkFrame(config_card, fg_color="transparent")
        row2.grid(row=1, column=0, columnspan=2, sticky="we", padx=16, pady=(4, 14))

        pass_col = ctk.CTkFrame(row2, fg_color="transparent")
        pass_col.pack(side="left")
        ctk.CTkLabel(
            pass_col, text="SENHA GPG", text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=10, weight="bold"),
        ).pack(anchor="w")
        pass_row = ctk.CTkFrame(pass_col, fg_color="transparent")
        pass_row.pack(anchor="w", pady=(4, 0))
        self.pass_entry = ctk.CTkEntry(
            pass_row, textvariable=self.passphrase_var, width=220, show="*",
            fg_color="#FFFFFF", border_color=BORDER, text_color=TEXT_PRIMARY,
        )
        self.pass_entry.pack(side="left")
        self.show_pass_check = ctk.CTkCheckBox(
            pass_row, text="mostrar", variable=self.show_pass_var,
            command=self._toggle_password, checkbox_width=16, checkbox_height=16,
            fg_color=ACCENT, text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="DejaVu Sans", size=11),
        )
        self.show_pass_check.pack(side="left", padx=(10, 0))

        workers_col = ctk.CTkFrame(row2, fg_color="transparent")
        workers_col.pack(side="left", padx=(32, 0))
        ctk.CTkLabel(
            workers_col, text="DOWNLOADS SIMULTÂNEOS", text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=10, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkEntry(
            workers_col, textvariable=self.workers_var, width=60,
            fg_color="#FFFFFF", border_color=BORDER, text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(4, 0))

        # --- Pipeline stepper card ---
        steps_card = ctk.CTkFrame(
            self, fg_color=BG_CARD, border_width=1, border_color=BORDER_SOFT, corner_radius=10
        )
        steps_card.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            steps_card, text="ETAPAS DO PIPELINE — ATIVE QUANTAS QUISER", text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=10, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        steps_row = ctk.CTkFrame(steps_card, fg_color="transparent")
        steps_row.pack(fill="x", padx=16, pady=(0, 14))
        steps_row.columnconfigure((0, 1, 2), weight=1)

        for i, key in enumerate(("download", "verify", "decrypt")):
            card = StepCard(steps_row, key, self._on_step_toggle)
            card.grid(row=0, column=i, sticky="nsew", padx=6)
            self.step_cards[key] = card

        # --- Action bar ---
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", padx=20, pady=8)
        self.start_button = ctk.CTkButton(
            action_bar, text="Iniciar", command=self._start,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            corner_radius=8, height=36,
        )
        self.start_button.pack(side="left")
        self.cancel_button = ctk.CTkButton(
            action_bar, text="Cancelar", command=self._cancel, state="disabled",
            fg_color=DISABLED_BG, hover_color=DISABLED_BG, text_color=TEXT_SECONDARY,
            corner_radius=8, height=36, border_width=1, border_color=BORDER,
        )
        self.cancel_button.pack(side="left", padx=8)

        self.progress = ctk.CTkProgressBar(
            action_bar, progress_color=ACCENT, fg_color=BORDER_SOFT, height=8, corner_radius=4,
        )
        self.progress.set(0)
        self.progress.pack(side="left", fill="x", expand=True, padx=14)

        self.summary_var = tk.StringVar(value="")
        ctk.CTkLabel(
            action_bar, textvariable=self.summary_var, text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=12),
        ).pack(side="right")

        # --- Content row: file list + log ---
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=8)

        list_card = ctk.CTkFrame(
            content, fg_color="#FFFFFF", border_width=1, border_color=BORDER_SOFT, corner_radius=10,
        )
        list_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "JoaK.Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
            foreground=TEXT_PRIMARY, rowheight=26, borderwidth=0,
        )
        style.configure(
            "JoaK.Treeview.Heading", background=BG_CARD, foreground=TEXT_SECONDARY,
            font=("TkDefaultFont", 10, "bold"), borderwidth=0,
        )
        style.map("JoaK.Treeview", background=[("selected", ACCENT_TINT)])

        columns = ("arquivo", "status", "detalhes")
        self.tree = ttk.Treeview(list_card, columns=columns, show="headings", style="JoaK.Treeview")
        self.tree.heading("arquivo", text="Arquivo")
        self.tree.heading("status", text="Status")
        self.tree.heading("detalhes", text="Detalhes")
        self.tree.column("arquivo", width=280)
        self.tree.column("status", width=130)
        self.tree.column("detalhes", width=260)
        self.tree.pack(fill="both", expand=True, padx=1, pady=1)

        log_card = ctk.CTkFrame(content, fg_color=LOG_BG, corner_radius=10, width=320)
        log_card.pack(side="left", fill="both", padx=(8, 0))
        log_card.pack_propagate(False)
        ctk.CTkLabel(
            log_card, text="LOG", text_color="#B7B2A6", fg_color=LOG_HEADER_BG,
            font=ctk.CTkFont(family="DejaVu Sans", size=10, weight="bold"), anchor="w", height=32,
        ).pack(fill="x")
        self.log_text = ctk.CTkTextbox(
            log_card, fg_color=LOG_BG, text_color=LOG_TEXT, font=("Consolas", 11),
            wrap="word", activate_scrollbars=True,
        )
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_text.configure(state="disabled")

        # --- Footer ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            footer, text=AUTHOR_LINE, text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="DejaVu Sans", size=10),
        ).pack(side="left")
        ctk.CTkLabel(
            footer, text=f"v{APP_VERSION}", text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="DejaVu Sans", size=10),
        ).pack(side="right")

        self._update_step_state()

    def _field(self, parent, label, variable, command, row, col):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=col, sticky="we", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            wrap, text=label.upper(), text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="DejaVu Sans", size=10, weight="bold"),
        ).pack(anchor="w")
        inner = ctk.CTkFrame(wrap, fg_color="transparent")
        inner.pack(fill="x", pady=(4, 0))
        entry = ctk.CTkEntry(
            inner, textvariable=variable, fg_color="#FFFFFF", border_color=BORDER,
            text_color=TEXT_PRIMARY,
        )
        entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            inner, text="Selecionar…", command=command, width=100,
            fg_color="#FFFFFF", hover_color=BORDER_SOFT, text_color=TEXT_PRIMARY,
            border_width=1, border_color=BORDER, corner_radius=8,
        ).pack(side="left", padx=(8, 0))
        return entry

    def _toggle_password(self):
        self.pass_entry.configure(show="" if self.show_pass_var.get() else "*")

    def _on_step_toggle(self, key):
        self._update_step_state()

    def _update_step_state(self):
        decrypt_on = self.step_cards["decrypt"].var.get()
        pass_state = "normal" if decrypt_on else "disabled"
        self.pass_entry.configure(state=pass_state)
        self.show_pass_check.configure(state=pass_state)

        labels = []
        for key in ("download", "verify", "decrypt"):
            card = self.step_cards[key]
            card.set_active(card.var.get())
            if card.var.get():
                labels.append(STEP_META[key][1])

        if labels:
            self.start_button.configure(
                text="Iniciar — " + " + ".join(labels), state="normal",
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
            )
        else:
            self.start_button.configure(
                text="Selecione ao menos uma etapa", state="disabled",
                fg_color=BUTTON_DISABLED_BG, hover_color=BUTTON_DISABLED_BG,
            )

    def _pick_csv(self):
        path = filedialog.askopenfilename(
            title="Selecione o CSV da Apple", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if path:
            self.csv_path_var.set(path)

    def _pick_output_dir(self):
        path = filedialog.askdirectory(title="Selecione a pasta de destino")
        if path:
            self.output_dir_var.set(path)

    # ------------------------------------------------------------- pipeline

    def _start(self):
        csv_path = self.csv_path_var.get().strip()
        output_dir = self.output_dir_var.get().strip()

        download_on = self.step_cards["download"].var.get()
        verify_on = self.step_cards["verify"].var.get()
        decrypt_on = self.step_cards["decrypt"].var.get()

        if not csv_path:
            messagebox.showerror(APP_TITLE, "Selecione o arquivo CSV da Apple.")
            return
        if not output_dir:
            messagebox.showerror(APP_TITLE, "Selecione a pasta de destino.")
            return
        if not (download_on or verify_on or decrypt_on):
            messagebox.showerror(APP_TITLE, "Selecione ao menos uma etapa (Baixar, Verificar ou Descriptografar).")
            return

        try:
            self.entries = core.load_entries(Path(csv_path))
        except core.PipelineError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        if decrypt_on and any(e.is_encrypted for e in self.entries):
            if not core.check_gpg_available():
                messagebox.showerror(
                    APP_TITLE,
                    "O programa 'gpg' nao foi encontrado no PATH.\n"
                    "Instale o Gpg4win (https://gpg4win.org) e tente novamente,\n"
                    "ou desmarque a opcao 'Descriptografar'.",
                )
                return
            if not self.passphrase_var.get():
                messagebox.showerror(APP_TITLE, "Informe a senha do GPG para descriptografar.")
                return

        try:
            max_workers = max(1, int(self.workers_var.get()))
        except ValueError:
            max_workers = 4

        config = core.PipelineConfig(
            csv_path=Path(csv_path),
            output_dir=Path(output_dir),
            passphrase=self.passphrase_var.get(),
            max_workers=max_workers,
            download=download_on,
            verify=verify_on,
            decrypt=decrypt_on,
        )

        self.tree.delete(*self.tree.get_children())
        self.row_by_name.clear()
        for entry in self.entries:
            row_id = self.tree.insert(
                "", "end", values=(entry.file_name, STATUS_LABELS["pendente"], "")
            )
            self.row_by_name[entry.file_name] = row_id

        self._total_entries = max(1, len(self.entries))
        self._done_entries = 0
        self.progress.set(0)
        self.summary_var.set("")
        self.cancel_event.clear()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(
            state="normal", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF", border_width=0,
        )
        for card in self.step_cards.values():
            card.switch.configure(state="disabled")

        self.worker_thread = threading.Thread(
            target=self._run_worker, args=(config,), daemon=True
        )
        self.worker_thread.start()

    def _run_worker(self, config: core.PipelineConfig):
        def on_update(entry: core.FileEntry) -> None:
            self.update_queue.put(entry)

        def log(message: str) -> None:
            self.log_queue.put(message)

        try:
            summary = core.run_pipeline(
                config, self.entries, on_update, log, cancel_event=self.cancel_event
            )
            self.update_queue.put(summary)
        except core.PipelineError as exc:
            self.update_queue.put(exc)
        except Exception as exc:  # noqa: BLE001 - nunca deixar a thread morrer silenciosa
            self.update_queue.put(exc)

    def _cancel(self):
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.log_queue.put("Cancelamento solicitado pelo usuario...")

    # ------------------------------------------------------------ polling

    def _poll_queues(self):
        drained = 0
        while drained < 200:
            try:
                item = self.update_queue.get_nowait()
            except queue.Empty:
                break
            drained += 1
            self._handle_update_item(item)

        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(message)

        self.after(100, self._poll_queues)

    def _handle_update_item(self, item):
        if isinstance(item, core.FileEntry):
            row_id = self.row_by_name.get(item.file_name)
            if row_id:
                label = STATUS_LABELS.get(item.status, item.status)
                self.tree.item(row_id, values=(item.file_name, label, item.message))
            if item.status in ("concluido", "hash_invalido", "erro", "cancelado"):
                self._done_entries += 1
                self.progress.set(min(1.0, self._done_entries / self._total_entries))
        elif isinstance(item, core.PipelineSummary):
            self.summary_var.set(
                f"Concluídos: {item.concluidos}/{item.total}  ·  "
                f"Hash inválido: {item.hash_invalido}  ·  "
                f"Erros: {item.erros}  ·  "
                f"Cancelados: {item.cancelados}  ·  "
                f"({item.elapsed_seconds:.1f}s)"
            )
            self._reenable_controls()
            if item.erros or item.hash_invalido:
                messagebox.showwarning(
                    APP_TITLE,
                    "Pipeline finalizado com pendencias. Veja a coluna Detalhes e o log "
                    "para os arquivos com erro ou hash invalido.",
                )
            else:
                messagebox.showinfo(APP_TITLE, "Pipeline finalizado com sucesso.")
        elif isinstance(item, Exception):
            self._reenable_controls()
            messagebox.showerror(APP_TITLE, f"Erro fatal no pipeline:\n{item}")

    def _reenable_controls(self):
        self.cancel_button.configure(
            state="disabled", fg_color=DISABLED_BG, hover_color=DISABLED_BG,
            text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER,
        )
        for card in self.step_cards.values():
            card.switch.configure(state="normal")
        self._update_step_state()

    def _append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def main():
    app = JoaKAppleGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
