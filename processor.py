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
    gpu_encoder: str | None
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
    gpu_encoder: str | None
    original_duration_seconds: float
    output_duration_seconds: float
    trim_start_seconds: float
    trim_end_seconds: float
    original_size_bytes: int
    output_size_bytes: int
    size_reduction_percent: float


@dataclass(frozen=True)
class GPUEncoderInfo:
    encoder: str
    provider: str
    label: str


GPU_ENCODER_CANDIDATES = {
    "h264_nvenc": GPUEncoderInfo(
        encoder="h264_nvenc",
        provider="NVIDIA",
        label="NVIDIA NVENC (GPU)",
    ),
    "h264_amf": GPUEncoderInfo(
        encoder="h264_amf",
        provider="AMD",
        label="AMD AMF (GPU)",
    ),
    "h264_qsv": GPUEncoderInfo(
        encoder="h264_qsv",
        provider="Intel",
        label="Intel Quick Sync (GPU/IGPU)",
    ),
}
GPU_PRIORITY = ("h264_nvenc", "h264_amf", "h264_qsv")


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


def detect_gpu_video_encoders() -> list[GPUEncoderInfo]:
    ffmpeg = find_ffmpeg_executable()
    command = [ffmpeg, "-hide_banner", "-encoders"]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise VideoProcessingError(
            "Falha ao listar encoders do FFmpeg.\n"
            f"Comando: {' '.join(command)}\n"
            f"Saida de erro:\n{completed.stderr.strip()}"
        )

    output = completed.stdout.lower()
    found: list[GPUEncoderInfo] = []
    for encoder_name in GPU_PRIORITY:
        if encoder_name in output:
            found.append(GPU_ENCODER_CANDIDATES[encoder_name])
    return found


def get_preferred_gpu_encoder() -> GPUEncoderInfo | None:
    available = detect_gpu_video_encoders()
    if not available:
        return None
    return available[0]


def get_gpu_status_message() -> str:
    available = detect_gpu_video_encoders()
    if not available:
        return "GPU: nao detectada para encode H.264"
    labels = ", ".join(item.label for item in available)
    return f"GPU: disponivel ({labels})"


def _strip_cpu_video_encoder_args(args: tuple[str, ...]) -> list[str]:
    remove_next_value_for = {"-c:v", "-preset", "-crf"}
    result: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        if token in remove_next_value_for:
            index += 2
            continue
        result.append(token)
        index += 1
    return result


def _get_gpu_video_encoder_args(encoder: str) -> list[str]:
    if encoder == "h264_nvenc":
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-cq",
            "28",
            "-rc",
            "vbr",
        ]
    if encoder == "h264_amf":
        return [
            "-c:v",
            "h264_amf",
            "-quality",
            "balanced",
            "-usage",
            "transcoding",
        ]
    if encoder == "h264_qsv":
        return [
            "-c:v",
            "h264_qsv",
            "-global_quality",
            "27",
        ]
    raise ValueError(f"Encoder GPU nao suportado: {encoder}")


def _build_profile_output_args(
    profile_args: tuple[str, ...],
    use_gpu: bool,
    gpu_encoder: str | None,
) -> tuple[list[str], str | None]:
    if not use_gpu:
        return list(profile_args), None

    selected_gpu_encoder = gpu_encoder
    if not selected_gpu_encoder:
        preferred = get_preferred_gpu_encoder()
        if not preferred:
            raise VideoProcessingError(
                "GPU ativada, mas nenhum encoder H.264 de GPU foi detectado no FFmpeg."
            )
        selected_gpu_encoder = preferred.encoder

    stripped = _strip_cpu_video_encoder_args(profile_args)
    gpu_args = _get_gpu_video_encoder_args(selected_gpu_encoder)
    return [*stripped, *gpu_args], selected_gpu_encoder


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
    use_gpu: bool = False,
    gpu_encoder: str | None = None,
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
    output_args, selected_gpu_encoder = _build_profile_output_args(
        profile_args=profile.ffmpeg_args,
        use_gpu=use_gpu,
        gpu_encoder=gpu_encoder,
    )

    command = [
        ffmpeg,
        "-hide_banner",
        overwrite_flag,
        "-i",
        str(input_file),
        *output_args,
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
        gpu_encoder=selected_gpu_encoder,
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
    use_gpu: bool = False,
    gpu_encoder: str | None = None,
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
    cpu_video_args: tuple[str, ...] = (
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
    )
    output_args, selected_gpu_encoder = _build_profile_output_args(
        profile_args=cpu_video_args,
        use_gpu=use_gpu,
        gpu_encoder=gpu_encoder,
    )

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
        *output_args,
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
        gpu_encoder=selected_gpu_encoder,
        original_duration_seconds=original_duration,
        output_duration_seconds=output_duration,
        trim_start_seconds=trim_start_seconds,
        trim_end_seconds=trim_end_seconds,
        original_size_bytes=original_size_bytes,
        output_size_bytes=output_size_bytes,
        size_reduction_percent=size_reduction_percent,
    )
