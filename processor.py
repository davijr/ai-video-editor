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
    original_size_bytes: int
    output_size_bytes: int
    size_reduction_percent: float


@dataclass(frozen=True)
class TrimResult:
    input_path: Path
    output_path: Path
    command: tuple[str, ...]
    stdout: str
    stderr: str
    original_duration_seconds: float
    output_duration_seconds: float
    trim_start_seconds: float
    trim_end_seconds: float
    original_size_bytes: int
    output_size_bytes: int
    size_reduction_percent: float


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


def find_ffprobe_executable() -> str:
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        return ffprobe_path

    ffmpeg_path = Path(find_ffmpeg_executable())
    ffprobe_candidate = ffmpeg_path.with_name("ffprobe.exe")
    if ffprobe_candidate.exists():
        return str(ffprobe_candidate)

    common_paths = [
        Path("C:/ffmpeg/bin/ffprobe.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffprobe.exe"),
        Path("C:/Program Files (x86)/ffmpeg/bin/ffprobe.exe"),
    ]
    for candidate in common_paths:
        if candidate.exists():
            return str(candidate)

    raise FFmpegNotFoundError(
        "FFprobe nao foi encontrado. Instale em https://ffmpeg.org/download.html e adicione no PATH."
    )


def get_video_duration_seconds(input_path: str | Path) -> float:
    input_file = Path(input_path)
    ffprobe = find_ffprobe_executable()

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(input_file),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise VideoProcessingError(
            "Falha ao consultar duracao com FFprobe.\n"
            f"Comando: {' '.join(command)}\n"
            f"Saida de erro:\n{completed.stderr.strip()}"
        )

    raw_duration = completed.stdout.strip()
    try:
        duration = float(raw_duration)
    except ValueError as exc:
        raise VideoProcessingError(f"Duracao invalida retornada pelo FFprobe: {raw_duration}") from exc

    if duration <= 0:
        raise VideoProcessingError("Duracao do video invalida (<= 0).")

    return duration


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


def build_trim_output_path(input_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{input_path.stem}_trim.mp4"


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
    original_size_bytes = input_file.stat().st_size
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

    if not output_file.exists() or not output_file.is_file():
        raise VideoProcessingError("FFmpeg finalizou sem gerar arquivo de saida.")

    output_size_bytes = output_file.stat().st_size
    size_reduction_percent = 0.0
    if original_size_bytes > 0:
        size_reduction_percent = ((original_size_bytes - output_size_bytes) / original_size_bytes) * 100.0

    return ProcessResult(
        input_path=input_file,
        output_path=output_file,
        command=tuple(command),
        stdout=completed.stdout,
        stderr=completed.stderr,
        original_size_bytes=original_size_bytes,
        output_size_bytes=output_size_bytes,
        size_reduction_percent=size_reduction_percent,
    )


def trim_video(
    input_path: str | Path,
    output_dir: str | Path,
    trim_start_seconds: float = 0.0,
    trim_end_seconds: float = 0.0,
    overwrite: bool = False,
) -> TrimResult:
    input_file = Path(input_path)
    if not input_file.exists() or not input_file.is_file():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_file}")

    if trim_start_seconds < 0 or trim_end_seconds < 0:
        raise ValueError("Os valores de recorte (inicio/final) nao podem ser negativos.")

    original_duration = get_video_duration_seconds(input_file)
    if trim_start_seconds + trim_end_seconds >= original_duration:
        raise ValueError(
            "Recorte invalido: soma de inicio e final deve ser menor que a duracao do video."
        )

    output_folder = Path(output_dir)
    output_file = build_trim_output_path(input_file, output_folder)
    original_size_bytes = input_file.stat().st_size

    ffmpeg = find_ffmpeg_executable()
    overwrite_flag = "-y" if overwrite else "-n"
    clip_start = trim_start_seconds
    clip_end = original_duration - trim_end_seconds

    command = [
        ffmpeg,
        "-hide_banner",
        overwrite_flag,
        "-i",
        str(input_file),
        "-ss",
        f"{clip_start:.3f}",
        "-to",
        f"{clip_end:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
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
            "Falha ao recortar video com FFmpeg.\n"
            f"Comando: {' '.join(command)}\n"
            f"Saida de erro:\n{completed.stderr.strip()}"
        )

    if not output_file.exists() or not output_file.is_file():
        raise VideoProcessingError("FFmpeg finalizou sem gerar arquivo de saida do recorte.")

    output_duration = get_video_duration_seconds(output_file)
    output_size_bytes = output_file.stat().st_size
    size_reduction_percent = 0.0
    if original_size_bytes > 0:
        size_reduction_percent = ((original_size_bytes - output_size_bytes) / original_size_bytes) * 100.0

    return TrimResult(
        input_path=input_file,
        output_path=output_file,
        command=tuple(command),
        stdout=completed.stdout,
        stderr=completed.stderr,
        original_duration_seconds=original_duration,
        output_duration_seconds=output_duration,
        trim_start_seconds=trim_start_seconds,
        trim_end_seconds=trim_end_seconds,
        original_size_bytes=original_size_bytes,
        output_size_bytes=output_size_bytes,
        size_reduction_percent=size_reduction_percent,
    )
