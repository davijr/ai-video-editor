from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from processor import FFmpegNotFoundError, VideoProcessingError, list_videos, process_video
from profiles import PROFILES


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{size} B"


def format_size_change_label(percent: float) -> str:
    if percent >= 0:
        return f"Reducao: {percent:.2f}%"
    return f"Aumento: {abs(percent):.2f}%"


class VideoEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AI Video Editor")
        self.root.geometry("980x680")
        self.root.minsize(900, 620)

        self.input_dir_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value=str(Path.cwd() / "output"))
        self.status_var = tk.StringVar(value="Pronto")
        self.overwrite_var = tk.BooleanVar(value=True)
        self.profile_description_var = tk.StringVar(value="")

        self.profile_items = sorted(PROFILES.values(), key=lambda profile: profile.label.lower())
        self.profile_labels = [profile.label for profile in self.profile_items]
        self.profile_by_label = {profile.label: profile.key for profile in self.profile_items}
        self.profile_description_by_label = {
            profile.label: profile.description for profile in self.profile_items
        }
        self.video_files: list[Path] = []

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)
        self.root.rowconfigure(4, weight=1)

        input_frame = ttk.Frame(self.root, padding=10)
        input_frame.grid(row=0, column=0, sticky="ew")
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Pasta de videos:").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_frame, textvariable=self.input_dir_var).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(input_frame, text="Selecionar", command=self.choose_input_dir).grid(
            row=0, column=2, sticky="e"
        )
        ttk.Button(input_frame, text="Atualizar lista", command=self.refresh_video_list).grid(
            row=0, column=3, sticky="e", padx=(6, 0)
        )

        settings_frame = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        settings_frame.grid(row=1, column=0, sticky="ew")
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Pasta de output:").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings_frame, textvariable=self.output_dir_var).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(settings_frame, text="Selecionar", command=self.choose_output_dir).grid(
            row=0, column=2, sticky="e"
        )
        ttk.Button(settings_frame, text="Ver pasta", command=self.open_output_dir).grid(
            row=0, column=3, sticky="e", padx=(6, 0)
        )

        ttk.Label(settings_frame, text="Script/Perfil:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.profile_combo = ttk.Combobox(
            settings_frame,
            values=self.profile_labels,
            state="readonly",
        )
        self.profile_combo.grid(row=1, column=1, sticky="w", padx=6, pady=(8, 0))
        if self.profile_labels:
            self.profile_combo.set(self.profile_labels[0])
            self._update_profile_description()
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)

        ttk.Checkbutton(
            settings_frame,
            text="Sobrescrever arquivos existentes",
            variable=self.overwrite_var,
        ).grid(row=1, column=2, sticky="w", pady=(8, 0))

        ttk.Label(
            settings_frame,
            textvariable=self.profile_description_var,
            wraplength=640,
        ).grid(row=2, column=1, columnspan=2, sticky="w", padx=6, pady=(4, 0))

        list_controls = ttk.Frame(self.root, padding=(10, 0, 10, 0))
        list_controls.grid(row=2, column=0, sticky="ew")

        ttk.Label(list_controls, text="Videos encontrados:").grid(row=0, column=0, sticky="w")
        ttk.Button(list_controls, text="Selecionar tudo", command=self.select_all).grid(
            row=0, column=1, padx=(12, 4)
        )
        ttk.Button(list_controls, text="Limpar selecao", command=self.clear_selection).grid(
            row=0, column=2
        )

        list_frame = ttk.Frame(self.root, padding=(10, 4, 10, 8))
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.video_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.video_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.video_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.video_listbox.configure(yscrollcommand=scrollbar.set)

        action_frame = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        action_frame.grid(row=4, column=0, sticky="nsew")
        action_frame.columnconfigure(0, weight=1)
        action_frame.rowconfigure(1, weight=1)

        self.run_button = ttk.Button(action_frame, text="Executar selecionados", command=self.run_selected)
        self.run_button.grid(row=0, column=0, sticky="w")
        ttk.Label(action_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="e")

        log_frame = ttk.LabelFrame(action_frame, text="Log de execucao")
        log_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=12, state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

    def choose_input_dir(self) -> None:
        selected = filedialog.askdirectory(title="Selecione a pasta de videos")
        if selected:
            self.input_dir_var.set(selected)
            self.refresh_video_list()

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Selecione a pasta de output")
        if selected:
            self.output_dir_var.set(selected)

    def open_output_dir(self) -> None:
        raw_output_dir = self.output_dir_var.get().strip()
        if not raw_output_dir:
            messagebox.showerror("Erro", "Selecione a pasta de output.")
            return

        output_path = Path(raw_output_dir)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Erro", f"Nao foi possivel criar a pasta: {exc}")
            return

        if not hasattr(os, "startfile"):
            messagebox.showerror("Erro", "Este recurso requer Windows.")
            return

        try:
            os.startfile(str(output_path.resolve()))  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror("Erro", f"Nao foi possivel abrir a pasta: {exc}")

    def refresh_video_list(self) -> None:
        input_dir = self.input_dir_var.get().strip()
        if not input_dir:
            self.video_files = []
            self.video_listbox.delete(0, tk.END)
            return

        self.video_files = list_videos(input_dir)
        self.video_listbox.delete(0, tk.END)
        for video_path in self.video_files:
            self.video_listbox.insert(tk.END, video_path.name)

        self.status_var.set(f"{len(self.video_files)} video(s) carregado(s)")

    def select_all(self) -> None:
        if self.video_files:
            self.video_listbox.select_set(0, tk.END)

    def clear_selection(self) -> None:
        self.video_listbox.selection_clear(0, tk.END)

    def _on_profile_changed(self, _event: object) -> None:
        self._update_profile_description()

    def _update_profile_description(self) -> None:
        label = self.profile_combo.get()
        description = self.profile_description_by_label.get(label, "")
        self.profile_description_var.set(description)

    def run_selected(self) -> None:
        if not self.profile_combo.get():
            messagebox.showerror("Erro", "Nenhum perfil disponivel.")
            return

        input_dir = self.input_dir_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        if not input_dir:
            messagebox.showerror("Erro", "Selecione a pasta de videos.")
            return
        if not output_dir:
            messagebox.showerror("Erro", "Selecione a pasta de output.")
            return

        selected_indices = self.video_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Erro", "Selecione ao menos um video.")
            return

        selected_files = [self.video_files[index] for index in selected_indices]
        profile_key = self.profile_by_label[self.profile_combo.get()]

        self.run_button.configure(state="disabled")
        self.status_var.set("Processando...")
        self._append_log(f"Iniciando processamento de {len(selected_files)} video(s).")

        worker = threading.Thread(
            target=self._process_batch,
            args=(selected_files, Path(output_dir), profile_key, self.overwrite_var.get()),
            daemon=True,
        )
        worker.start()

    def _process_batch(
        self,
        selected_files: list[Path],
        output_dir: Path,
        profile_key: str,
        overwrite: bool,
    ) -> None:
        success_count = 0
        error_count = 0

        for index, input_file in enumerate(selected_files, start=1):
            self.root.after(
                0, lambda i=index, total=len(selected_files), f=input_file: self._append_log(
                    f"[{i}/{total}] Processando: {f.name}"
                )
            )

            try:
                result = process_video(
                    input_path=input_file,
                    output_dir=output_dir,
                    profile_key=profile_key,
                    overwrite=overwrite,
                )
                success_count += 1
                size_summary = (
                    f"Original: {format_bytes(result.original_size_bytes)} | "
                    f"Final: {format_bytes(result.output_size_bytes)} | "
                    f"{format_size_change_label(result.size_reduction_percent)}"
                )
                self.root.after(
                    0,
                    lambda p=result.output_path, s=size_summary: self._append_log(f"OK -> {p} | {s}"),
                )
            except (FFmpegNotFoundError, VideoProcessingError, FileNotFoundError, ValueError) as exc:
                error_count += 1
                self.root.after(0, lambda msg=str(exc): self._append_log(f"ERRO -> {msg}"))

        final_status = f"Concluido. Sucesso: {success_count} | Erros: {error_count}"
        self.root.after(0, lambda: self.status_var.set(final_status))
        self.root.after(0, lambda: self.run_button.configure(state="normal"))

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    app = VideoEditorApp(root)
    try:
        app.refresh_video_list()
        root.mainloop()
    except FFmpegNotFoundError as exc:
        messagebox.showerror("FFmpeg nao encontrado", str(exc))


if __name__ == "__main__":
    main()
