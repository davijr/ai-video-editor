from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
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


def get_app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class VideoEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AI Video Editor")
        self.root.geometry("980x680")
        self.root.minsize(900, 620)
        self.config_path = get_app_base_dir() / "user_settings.json"
        self.startup_warning: str | None = None

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
        self.sort_options = {
            "Nome (A-Z)": "name_asc",
            "Nome (Z-A)": "name_desc",
            "Data mais recente": "date_desc",
            "Data mais antiga": "date_asc",
        }
        self.sort_label_by_mode = {mode: label for label, mode in self.sort_options.items()}
        self.sort_labels = list(self.sort_options.keys())
        self.sort_label_var = tk.StringVar(value=self.sort_labels[0])
        self.profile_menu_var = tk.StringVar(
            value=self.profile_labels[0] if self.profile_labels else ""
        )
        self.selected_count_var = tk.StringVar(value="Selecionados: 0 / 0")
        self.video_files: list[Path] = []
        self.tree_id_to_path: dict[str, Path] = {}
        self._setting_traces_registered = False

        loaded_settings = self._load_user_settings()
        self._apply_user_settings(loaded_settings)

        self._build_ui()
        self._register_setting_traces()
        self._save_user_settings()

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
            selected_label = self.profile_menu_var.get().strip() or self.profile_labels[0]
            if selected_label not in self.profile_by_label:
                selected_label = self.profile_labels[0]
            self.profile_combo.set(selected_label)
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
        list_controls.columnconfigure(6, weight=1)

        ttk.Label(list_controls, text="Videos encontrados:").grid(row=0, column=0, sticky="w")
        ttk.Button(list_controls, text="Selecionar tudo", command=self.select_all).grid(
            row=0, column=1, padx=(12, 4)
        )
        ttk.Button(list_controls, text="Limpar selecao", command=self.clear_selection).grid(
            row=0, column=2
        )
        ttk.Label(list_controls, text="Ordenacao:").grid(row=0, column=3, padx=(14, 4), sticky="e")
        self.sort_combo = ttk.Combobox(
            list_controls,
            values=self.sort_labels,
            textvariable=self.sort_label_var,
            state="readonly",
            width=18,
        )
        self.sort_combo.grid(row=0, column=4, sticky="w")
        self.sort_combo.bind("<<ComboboxSelected>>", self._on_sort_changed)
        ttk.Label(list_controls, textvariable=self.selected_count_var).grid(
            row=0, column=7, sticky="e"
        )

        list_frame = ttk.Frame(self.root, padding=(10, 4, 10, 8))
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.video_tree = ttk.Treeview(
            list_frame,
            columns=("index", "filename", "modified_at"),
            show="headings",
            selectmode="extended",
        )
        self.video_tree.heading("index", text="#")
        self.video_tree.heading("filename", text="Arquivo")
        self.video_tree.heading("modified_at", text="Data/Hora")
        self.video_tree.column("index", width=55, minwidth=45, anchor="center", stretch=False)
        self.video_tree.column("filename", width=560, minwidth=260, anchor="w")
        self.video_tree.column("modified_at", width=200, minwidth=180, anchor="center", stretch=False)
        self.video_tree.grid(row=0, column=0, sticky="nsew")
        self.video_tree.bind("<<TreeviewSelect>>", self._on_tree_selection_changed)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.video_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.video_tree.configure(yscrollcommand=scrollbar.set)

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

        self._build_menu()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        self.root.configure(menu=menu_bar)

        arquivo_menu = tk.Menu(menu_bar, tearoff=0)
        arquivo_menu.add_command(label="Selecionar pasta de videos", command=self.choose_input_dir)
        arquivo_menu.add_command(label="Atualizar lista de videos", command=self.refresh_video_list)
        arquivo_menu.add_separator()
        arquivo_menu.add_command(label="Selecionar pasta de output", command=self.choose_output_dir)
        arquivo_menu.add_command(label="Ver pasta de output", command=self.open_output_dir)
        arquivo_menu.add_separator()
        arquivo_menu.add_command(
            label="Criar atalho na area de trabalho",
            command=self.create_desktop_shortcut,
        )
        arquivo_menu.add_separator()
        arquivo_menu.add_command(label="Sair", command=self.root.destroy)
        menu_bar.add_cascade(label="Arquivo", menu=arquivo_menu)

        selecao_menu = tk.Menu(menu_bar, tearoff=0)
        selecao_menu.add_command(label="Selecionar tudo", command=self.select_all)
        selecao_menu.add_command(label="Limpar selecao", command=self.clear_selection)
        ordenacao_menu = tk.Menu(selecao_menu, tearoff=0)
        for sort_label in self.sort_labels:
            ordenacao_menu.add_radiobutton(
                label=sort_label,
                value=sort_label,
                variable=self.sort_label_var,
                command=self._on_sort_mode_changed,
            )
        selecao_menu.add_cascade(label="Ordenar por", menu=ordenacao_menu)
        menu_bar.add_cascade(label="Selecao", menu=selecao_menu)

        processamento_menu = tk.Menu(menu_bar, tearoff=0)
        processamento_menu.add_checkbutton(
            label="Sobrescrever arquivos existentes",
            variable=self.overwrite_var,
        )

        perfil_menu = tk.Menu(processamento_menu, tearoff=0)
        for profile_label in self.profile_labels:
            perfil_menu.add_radiobutton(
                label=profile_label,
                variable=self.profile_menu_var,
                value=profile_label,
                command=lambda label=profile_label: self._set_profile_label(label),
            )
        processamento_menu.add_cascade(label="Perfil", menu=perfil_menu)
        processamento_menu.add_separator()
        processamento_menu.add_command(label="Executar selecionados", command=self.run_selected)
        menu_bar.add_cascade(label="Processamento", menu=processamento_menu)

    def _register_setting_traces(self) -> None:
        if self._setting_traces_registered:
            return
        self.input_dir_var.trace_add("write", self._on_setting_var_changed)
        self.output_dir_var.trace_add("write", self._on_setting_var_changed)
        self.overwrite_var.trace_add("write", self._on_setting_var_changed)
        self.profile_menu_var.trace_add("write", self._on_setting_var_changed)
        self.sort_label_var.trace_add("write", self._on_setting_var_changed)
        self._setting_traces_registered = True

    def _on_setting_var_changed(self, *_args: object) -> None:
        self._save_user_settings()

    def _load_user_settings(self) -> dict[str, object]:
        if not self.config_path.exists():
            return {}
        try:
            content = self.config_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except OSError as exc:
            self.startup_warning = f"Nao foi possivel ler config: {exc}"
            return {}
        except json.JSONDecodeError as exc:
            self.startup_warning = f"Config invalida em {self.config_path.name}: {exc}"
            return {}

        if not isinstance(data, dict):
            self.startup_warning = f"Config invalida em {self.config_path.name}: raiz deve ser objeto JSON."
            return {}
        return data

    def _apply_user_settings(self, data: dict[str, object]) -> None:
        input_dir = data.get("input_dir")
        output_dir = data.get("output_dir")
        overwrite = data.get("overwrite")
        profile_key = data.get("profile_key")
        sort_mode = data.get("sort_mode")

        if isinstance(input_dir, str):
            self.input_dir_var.set(input_dir)
        if isinstance(output_dir, str):
            self.output_dir_var.set(output_dir)
        if isinstance(overwrite, bool):
            self.overwrite_var.set(overwrite)

        if isinstance(profile_key, str):
            profile = PROFILES.get(profile_key)
            if profile:
                self.profile_menu_var.set(profile.label)
        if isinstance(sort_mode, str):
            sort_label = self.sort_label_by_mode.get(sort_mode)
            if sort_label:
                self.sort_label_var.set(sort_label)

    def _save_user_settings(self) -> None:
        profile_label = self.profile_menu_var.get().strip()
        profile_key = self.profile_by_label.get(profile_label, "")
        sort_mode = self.sort_options.get(self.sort_label_var.get().strip(), "name_asc")
        data = {
            "input_dir": self.input_dir_var.get().strip(),
            "output_dir": self.output_dir_var.get().strip(),
            "profile_key": profile_key,
            "sort_mode": sort_mode,
            "overwrite": bool(self.overwrite_var.get()),
        }
        try:
            self.config_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            self.startup_warning = f"Nao foi possivel salvar config: {exc}"

    @staticmethod
    def _ps_escape(value: str) -> str:
        return value.replace("'", "''")

    def _set_profile_label(self, label: str) -> None:
        if label not in self.profile_by_label:
            return
        self.profile_combo.set(label)
        self._update_profile_description()

    def _get_desktop_path(self) -> Path:
        command = ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode == 0 and completed.stdout.strip():
            return Path(completed.stdout.strip())
        return Path.home() / "Desktop"

    def create_desktop_shortcut(self) -> None:
        if os.name != "nt":
            messagebox.showerror("Erro", "Este recurso requer Windows.")
            return

        base_dir = get_app_base_dir()
        exe_candidates = [base_dir / "AIVideoEditor.exe", base_dir / "dist" / "AIVideoEditor.exe"]
        exe_path = next((path for path in exe_candidates if path.exists() and path.is_file()), None)

        batch_candidates = [base_dir / "run_gui.bat", base_dir.parent / "run_gui.bat"]
        batch_path = next((path for path in batch_candidates if path.exists() and path.is_file()), None)

        target_path = ""
        arguments = ""
        icon_location = ""
        working_directory = str(base_dir)
        guidance = ""

        if exe_path:
            target_path = str(exe_path.resolve())
            icon_location = f"{target_path},0"
            guidance = "Atalho criado para o executavel (.exe)."
        elif batch_path:
            command_shell = os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe")
            target_path = command_shell
            arguments = f'/c "{batch_path.resolve()}"'
            icon_location = f"{command_shell},0"
            working_directory = str(batch_path.resolve().parent)
            guidance = (
                "Executavel nao encontrado. Atalho criado para run_gui.bat. "
                "Recomendado recriar atalho apos gerar o .exe."
            )
        else:
            messagebox.showerror("Erro", "Nao foi encontrado AIVideoEditor.exe nem run_gui.bat.")
            return

        desktop_dir = self._get_desktop_path()
        desktop_dir.mkdir(parents=True, exist_ok=True)
        shortcut_path = desktop_dir / "AI Video Editor.lnk"

        ps_lines = [
            "$WshShell = New-Object -ComObject WScript.Shell",
            f"$Shortcut = $WshShell.CreateShortcut('{self._ps_escape(str(shortcut_path))}')",
            f"$Shortcut.TargetPath = '{self._ps_escape(target_path)}'",
            f"$Shortcut.WorkingDirectory = '{self._ps_escape(working_directory)}'",
            f"$Shortcut.IconLocation = '{self._ps_escape(icon_location)}'",
        ]
        if arguments:
            ps_lines.append(f"$Shortcut.Arguments = '{self._ps_escape(arguments)}'")
        ps_lines.append("$Shortcut.Save()")
        ps_script = "; ".join(ps_lines)

        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip() or "Falha desconhecida."
            messagebox.showerror("Erro", f"Nao foi possivel criar atalho:\n{details}")
            return

        self._append_log(f"Atalho criado: {shortcut_path}")
        messagebox.showinfo("Atalho criado", f"{guidance}\n\nArquivo: {shortcut_path}")

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

    def _on_sort_changed(self, _event: object) -> None:
        self._on_sort_mode_changed()

    def _on_sort_mode_changed(self) -> None:
        self.refresh_video_list()

    def _sorted_videos(self, videos: list[Path]) -> list[Path]:
        sort_mode = self.sort_options.get(self.sort_label_var.get().strip(), "name_asc")
        if sort_mode == "name_desc":
            return sorted(videos, key=lambda path: path.name.lower(), reverse=True)
        if sort_mode == "date_desc":
            return sorted(videos, key=lambda path: path.stat().st_mtime, reverse=True)
        if sort_mode == "date_asc":
            return sorted(videos, key=lambda path: path.stat().st_mtime)
        return sorted(videos, key=lambda path: path.name.lower())

    def _on_tree_selection_changed(self, _event: object) -> None:
        self._update_selected_count()

    def _update_selected_count(self) -> None:
        selected = len(self.video_tree.selection())
        total = len(self.video_files)
        self.selected_count_var.set(f"Selecionados: {selected} / {total}")

    def refresh_video_list(self) -> None:
        input_dir = self.input_dir_var.get().strip()
        self.video_tree.delete(*self.video_tree.get_children())
        self.tree_id_to_path = {}

        if not input_dir:
            self.video_files = []
            self._update_selected_count()
            return

        self.video_files = self._sorted_videos(list_videos(input_dir))
        for index, video_path in enumerate(self.video_files, start=1):
            modified_at = datetime.fromtimestamp(video_path.stat().st_mtime).strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            item_id = self.video_tree.insert(
                "",
                "end",
                values=(index, video_path.name, modified_at),
            )
            self.tree_id_to_path[item_id] = video_path

        self.status_var.set(f"{len(self.video_files)} video(s) carregado(s)")
        self._update_selected_count()

    def select_all(self) -> None:
        if self.video_files:
            self.video_tree.selection_set(self.video_tree.get_children())
        self._update_selected_count()

    def clear_selection(self) -> None:
        self.video_tree.selection_remove(self.video_tree.selection())
        self._update_selected_count()

    def _on_profile_changed(self, _event: object) -> None:
        self._update_profile_description()

    def _update_profile_description(self) -> None:
        label = self.profile_combo.get()
        self.profile_menu_var.set(label)
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

        selected_item_ids = self.video_tree.selection()
        if not selected_item_ids:
            messagebox.showerror("Erro", "Selecione ao menos um video.")
            return

        selected_files = [
            self.tree_id_to_path[item_id]
            for item_id in selected_item_ids
            if item_id in self.tree_id_to_path
        ]
        if not selected_files:
            messagebox.showerror("Erro", "Nao foi possivel mapear os videos selecionados.")
            return
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
        if app.startup_warning:
            messagebox.showwarning("Configuracao", app.startup_warning)
        app.refresh_video_list()
        root.mainloop()
    except FFmpegNotFoundError as exc:
        messagebox.showerror("FFmpeg nao encontrado", str(exc))


if __name__ == "__main__":
    main()
