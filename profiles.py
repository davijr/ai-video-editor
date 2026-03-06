from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoProfile:
    key: str
    label: str
    description: str
    output_extension: str
    ffmpeg_args: tuple[str, ...]


WHATSAPP_MP4_H264_AAC = VideoProfile(
    key="whatsapp_mp4_h264_aac",
    label="WhatsApp (MP4 H.264 + AAC)",
    description="Compactacao otimizada para envio no WhatsApp.",
    output_extension=".mp4",
    ffmpeg_args=(
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "27",
        "-vf",
        "scale=min(1280\\,iw):-2:flags=lanczos",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.0",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
    ),
)


WHATSAPP_SMALL_540P = VideoProfile(
    key="whatsapp_small_540p",
    label="WhatsApp Leve (540p H.264 + AAC)",
    description="Arquivo menor para envio rapido no WhatsApp, com qualidade reduzida.",
    output_extension=".mp4",
    ffmpeg_args=(
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "30",
        "-vf",
        "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "main",
        "-level",
        "3.1",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
    ),
)


INSTAGRAM_REELS_1080X1920 = VideoProfile(
    key="instagram_reels_1080x1920",
    label="Instagram Reels (1080x1920)",
    description="Converte para formato vertical 9:16 sem cortar o video original.",
    output_extension=".mp4",
    ffmpeg_args=(
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
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
    ),
)


YOUTUBE_SHORTS_1080X1920 = VideoProfile(
    key="youtube_shorts_1080x1920",
    label="YouTube Shorts (1080x1920)",
    description="Formato vertical 9:16 para Shorts, mantendo o conteudo inteiro em pad.",
    output_extension=".mp4",
    ffmpeg_args=(
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "22",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-r",
        "60",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
    ),
)


PROFILES: dict[str, VideoProfile] = {
    WHATSAPP_MP4_H264_AAC.key: WHATSAPP_MP4_H264_AAC,
    WHATSAPP_SMALL_540P.key: WHATSAPP_SMALL_540P,
    INSTAGRAM_REELS_1080X1920.key: INSTAGRAM_REELS_1080X1920,
    YOUTUBE_SHORTS_1080X1920.key: YOUTUBE_SHORTS_1080X1920,
}


def list_profile_keys() -> list[str]:
    return sorted(PROFILES.keys())


def get_profile(key: str) -> VideoProfile:
    if key not in PROFILES:
        available = ", ".join(list_profile_keys())
        raise ValueError(f"Perfil '{key}' invalido. Perfis disponiveis: {available}")
    return PROFILES[key]
