from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from profiles import VideoProfile, get_profile


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


class FFmpegNotFoundError(RuntimeError):
    pass


class VideoProcessingError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcessResult:
    input_path: Path
    output_path: Path
    command: tuple[str, ...]
    stdout: str
    stderr: str


def find_ffmpeg_executable() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    common_paths = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
    ]
    for candidate in common_paths:
        if candidate.exists():
            return str(candidate)

    raise FFmpegNotFoundError(
        "FFmpeg nao foi encontrado. Instale em https://ffmpeg.org/download.html e adicione no PATH."
    )


def list_videos(input_dir: str | Path) -> list[Path]:
    base = Path(input_dir)
    if not base.exists() or not base.is_dir():
        return []
    return sorted(
        [path for path in base.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS],
        key=lambda item: item.name.lower(),
    )


def build_output_path(input_path: Path, output_dir: Path, profile: VideoProfile) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{input_path.stem}_{profile.key}{profile.output_extension}"


def process_video(
    input_path: str | Path,
    output_dir: str | Path,
    profile_key: str,
    overwrite: bool = False,
) -> ProcessResult:
    input_file = Path(input_path)
    if not input_file.exists() or not input_file.is_file():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_file}")

    profile = get_profile(profile_key)
    output_folder = Path(output_dir)
    output_file = build_output_path(input_file, output_folder, profile)
    ffmpeg = find_ffmpeg_executable()
    overwrite_flag = "-y" if overwrite else "-n"

    command = [
        ffmpeg,
        "-hide_banner",
        overwrite_flag,
        "-i",
        str(input_file),
        *profile.ffmpeg_args,
        str(output_file),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise VideoProcessingError(
            "Falha ao processar video com FFmpeg.\n"
            f"Comando: {' '.join(command)}\n"
            f"Saida de erro:\n{completed.stderr.strip()}"
        )

    return ProcessResult(
        input_path=input_file,
        output_path=output_file,
        command=tuple(command),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
