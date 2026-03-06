# AI Video Editor

Projeto para editar videos de gameplay (Rocket League), com foco inicial em compactacao para envio no WhatsApp.

## Requisitos

- Windows 11
- Python 3.10+
- `ffmpeg` instalado e disponivel no `PATH`

Documentacao oficial consultada:
- FFmpeg: https://ffmpeg.org/documentation.html
- Python Tkinter: https://docs.python.org/3/library/tkinter.html

## Estrutura

- `edit_one_video.py`: script CLI para editar um unico video.
- `video_editor_gui.py`: interface grafica Windows para processar multiplos videos.
- `profiles.py`: perfis de edicao disponiveis.
- `processor.py`: integracao e execucao do FFmpeg.
- `run_gui.bat`: inicializador rapido da interface.

## Script inicial (1 video)

Compactacao para perfil WhatsApp (`mp4`, `H.264`, `AAC`):

```powershell
python edit_one_video.py --input "C:\videos\gol1.mp4" --output-dir "C:\videos\output" --profile whatsapp_mp4_h264_aac --overwrite
```

Parametros:
- `--input`: caminho do video de entrada.
- `--output-dir`: pasta de saida.
- `--profile`: perfil de edicao (atual: `whatsapp_mp4_h264_aac`).
- `--overwrite`: sobrescreve arquivo de saida, se ja existir.

## Interface grafica (Windows)

Execute:

```powershell
run_gui.bat
```

Fluxo:
1. Selecione a pasta de entrada.
2. A lista de videos sera carregada.
3. Selecione os videos desejados.
4. Escolha o script/perfil pronto.
5. Defina a pasta de saida.
6. Clique em `Executar`.

## Perfil inicial: WhatsApp

Perfil implementado:
- Container: MP4
- Video: `libx264`, `yuv420p`, `crf 27`, `preset medium`, `30 fps`, largura maxima 1280
- Audio: `aac`, `128k`, estereo
- `+faststart` para melhor reproducao em apps de mensagem
