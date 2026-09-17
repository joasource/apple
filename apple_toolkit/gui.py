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

import core

APP_TITLE = "JoaKApple"
APP_DESCRIPTION = "Toolkit para baixar, verificar e descriptografar retorno de ofícios judiciais da Apple"
APP_VERSION = "1.0.0"
AUTHOR_LINE = "Joaquim Ferreira Silva Neto  <joaquimfsneto@gmail.com>"

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


class JoaKAppleGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("900x680")
        self.minsize(760, 520)

        self.update_queue: queue.Queue = queue.Queue()
        self.log_queue: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.entries: list[core.FileEntry] = []
        self.row_by_name: dict[str, str] = {}

        self.csv_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.passphrase_var = tk.StringVar()
        self.workers_var = tk.IntVar(value=4)
        self.decrypt_var = tk.BooleanVar(value=True)
        self.show_pass_var = tk.BooleanVar(value=False)

        self._build_widgets()
        self._poll_queues()

    # ------------------------------------------------------------------ UI

    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(header, text=APP_TITLE, font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(header, text=APP_DESCRIPTION, foreground="#666").pack(anchor="w")

        form = ttk.Frame(self)
        form.pack(fill="x", **pad)

        ttk.Label(form, text="Arquivo CSV da Apple:").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.csv_path_var, width=70).grid(row=0, column=1, sticky="we")
        ttk.Button(form, text="Selecionar...", command=self._pick_csv).grid(row=0, column=2, padx=4)

        ttk.Label(form, text="Pasta de destino:").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.output_dir_var, width=70).grid(row=1, column=1, sticky="we")
        ttk.Button(form, text="Selecionar...", command=self._pick_output_dir).grid(row=1, column=2, padx=4)

        ttk.Label(form, text="Senha GPG:").grid(row=2, column=0, sticky="w")
        self.pass_entry = ttk.Entry(form, textvariable=self.passphrase_var, width=40, show="*")
        self.pass_entry.grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(
            form, text="mostrar", variable=self.show_pass_var, command=self._toggle_password
        ).grid(row=2, column=1, sticky="w", padx=(300, 0))

        options = ttk.Frame(form)
        options.grid(row=3, column=1, sticky="w", pady=(4, 0))
        ttk.Label(options, text="Downloads simultaneos:").pack(side="left")
        ttk.Spinbox(options, from_=1, to=16, width=4, textvariable=self.workers_var).pack(
            side="left", padx=(4, 16)
        )
        ttk.Checkbutton(options, text="Descriptografar (.gpg)", variable=self.decrypt_var).pack(
            side="left"
        )

        form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", **pad)
        self.start_button = ttk.Button(buttons, text="Iniciar", command=self._start)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(
            buttons, text="Cancelar", command=self._cancel, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=6)

        self.progress = ttk.Progressbar(buttons, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=10)

        self.summary_var = tk.StringVar(value="")
        ttk.Label(buttons, textvariable=self.summary_var).pack(side="right")

        columns = ("arquivo", "status", "detalhes")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=14)
        self.tree.heading("arquivo", text="Arquivo")
        self.tree.heading("status", text="Status")
        self.tree.heading("detalhes", text="Detalhes")
        self.tree.column("arquivo", width=320)
        self.tree.column("status", width=140)
        self.tree.column("detalhes", width=380)
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=False, padx=8, pady=(0, 4))
        self.log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word")
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Label(footer, text=AUTHOR_LINE, foreground="#555").pack(side="left")

    def _toggle_password(self):
        self.pass_entry.configure(show="" if self.show_pass_var.get() else "*")

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

        if not csv_path:
            messagebox.showerror(APP_TITLE, "Selecione o arquivo CSV da Apple.")
            return
        if not output_dir:
            messagebox.showerror(APP_TITLE, "Selecione a pasta de destino.")
            return

        try:
            self.entries = core.load_entries(Path(csv_path))
        except core.PipelineError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        if self.decrypt_var.get() and any(e.is_encrypted for e in self.entries):
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

        config = core.PipelineConfig(
            csv_path=Path(csv_path),
            output_dir=Path(output_dir),
            passphrase=self.passphrase_var.get(),
            max_workers=max(1, self.workers_var.get()),
            decrypt=self.decrypt_var.get(),
        )

        self.tree.delete(*self.tree.get_children())
        self.row_by_name.clear()
        for entry in self.entries:
            row_id = self.tree.insert(
                "", "end", values=(entry.file_name, STATUS_LABELS["pendente"], "")
            )
            self.row_by_name[entry.file_name] = row_id

        self.progress.configure(maximum=len(self.entries), value=0)
        self.summary_var.set("")
        self.cancel_event.clear()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

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
                self.progress.step(1)
        elif isinstance(item, core.PipelineSummary):
            self.summary_var.set(
                f"Concluidos: {item.concluidos}/{item.total}  "
                f"Hash invalido: {item.hash_invalido}  "
                f"Erros: {item.erros}  "
                f"Cancelados: {item.cancelados}  "
                f"({item.elapsed_seconds:.1f}s)"
            )
            self.start_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            if item.erros or item.hash_invalido:
                messagebox.showwarning(
                    APP_TITLE,
                    "Pipeline finalizado com pendencias. Veja a coluna Detalhes e o log "
                    "para os arquivos com erro ou hash invalido.",
                )
            else:
                messagebox.showinfo(APP_TITLE, "Pipeline finalizado com sucesso.")
        elif isinstance(item, Exception):
            self.start_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            messagebox.showerror(APP_TITLE, f"Erro fatal no pipeline:\n{item}")

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
