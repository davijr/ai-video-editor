from __future__ import annotations

import argparse
import sys
from pathlib import Path

from processor import (
    FFmpegNotFoundError,
    VideoProcessingError,
    detect_gpu_video_encoders,
    process_video,
)
from profiles import list_profile_keys


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{size} B"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Edita um unico video usando um script/perfil pre-definido."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Caminho completo do video de entrada.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Pasta de saida dos videos processados (padrao: ./output).",
    )
    parser.add_argument(
        "--profile",
        default="whatsapp_mp4_h264_aac",
        choices=list_profile_keys(),
        help="Perfil/script de edicao a ser executado.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve o arquivo de saida, se ja existir.",
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        help="Ativa encode por GPU (quando encoder suportado estiver disponivel no FFmpeg).",
    )
    parser.add_argument(
        "--gpu-encoder",
        choices=["auto", "h264_nvenc", "h264_amf", "h264_qsv"],
        default="auto",
        help="Encoder GPU para uso com --use-gpu (padrao: auto).",
    )
    parser.add_argument(
        "--list-gpu",
        action="store_true",
        help="Lista encoders GPU H.264 detectados e sai.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_gpu:
        try:
            available = detect_gpu_video_encoders()
        except (FFmpegNotFoundError, VideoProcessingError) as exc:
            print(f"ERRO: {exc}", file=sys.stderr)
            return 1
        if not available:
            print("Nenhum encoder GPU H.264 detectado.")
            return 0
        print("Encoders GPU H.264 detectados:")
        for item in available:
            print(f"- {item.encoder} ({item.label})")
        return 0

    if not args.input:
        parser.error("o argumento --input e obrigatorio quando --list-gpu nao for usado")

    try:
        result = process_video(
            input_path=args.input,
            output_dir=args.output_dir,
            profile_key=args.profile,
            overwrite=args.overwrite,
            use_gpu=args.use_gpu,
            gpu_encoder=None if args.gpu_encoder == "auto" else args.gpu_encoder,
        )
    except (FileNotFoundError, FFmpegNotFoundError, VideoProcessingError, ValueError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print("Processamento concluido com sucesso.")
    print(f"Entrada: {result.input_path}")
    print(f"Saida: {result.output_path}")
    print(f"Tamanho original: {format_bytes(result.original_size_bytes)}")
    print(f"Tamanho final: {format_bytes(result.output_size_bytes)}")
    if result.gpu_encoder:
        print(f"GPU: ativada ({result.gpu_encoder})")
    else:
        print("GPU: desativada (CPU)")
    if result.size_reduction_percent >= 0:
        print(f"Reducao: {result.size_reduction_percent:.2f}%")
    else:
        print(f"Aumento: {abs(result.size_reduction_percent):.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
