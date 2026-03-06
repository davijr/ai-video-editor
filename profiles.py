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


PROFILES: dict[str, VideoProfile] = {
    WHATSAPP_MP4_H264_AAC.key: WHATSAPP_MP4_H264_AAC,
}


def list_profile_keys() -> list[str]:
    return sorted(PROFILES.keys())


def get_profile(key: str) -> VideoProfile:
    if key not in PROFILES:
        available = ", ".join(list_profile_keys())
        raise ValueError(f"Perfil '{key}' invalido. Perfis disponiveis: {available}")
    return PROFILES[key]
