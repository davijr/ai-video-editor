# AI Video Editor

Projeto para editar videos de gameplay (Rocket League), com foco inicial em compactacao para envio no WhatsApp.

## Requisitos

- Windows 11
- Python 3.10+
- `ffmpeg` instalado e disponivel no `PATH`
- `pyinstaller` (instalado automaticamente pelo `build_exe.bat`)

Documentacao oficial consultada:
- FFmpeg: https://ffmpeg.org/documentation.html
- FFmpeg filtros: https://ffmpeg.org/ffmpeg-filters.html
- Python Tkinter: https://docs.python.org/3/library/tkinter.html
- PyInstaller: https://www.pyinstaller.org/en/stable/usage.html

## Estrutura

- `edit_one_video.py`: script CLI para editar um unico video.
- `video_editor_gui.py`: interface grafica Windows para processar multiplos videos.
- `profiles.py`: perfis de edicao disponiveis.
- `processor.py`: integracao e execucao do FFmpeg.
- `run_gui.bat`: inicializador rapido da interface.
- `build_exe.bat`: gera executavel Windows da GUI (`.exe`).

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

## Perfis de edicao

Perfis implementados:
- Container: MP4
- `whatsapp_mp4_h264_aac`: `libx264`, `crf 27`, max largura 1280, `aac 128k`, `faststart`
- `whatsapp_small_540p`: arquivo mais leve (`960x540`, `crf 30`, `aac 96k`)
- `instagram_reels_1080x1920`: vertical 9:16 (`scale+pad`, `30 fps`)
- `youtube_shorts_1080x1920`: vertical 9:16 (`scale+pad`, `60 fps`)

## Gerar executavel `.exe`

Para empacotar a GUI em um unico executavel Windows:

```powershell
build_exe.bat
```

Saida esperada:

- `dist\AIVideoEditor.exe`

Observacoes:
- O build usa `PyInstaller` com `--onefile --windowed`.
- O `ffmpeg` continua sendo necessario no Windows de destino (PATH ou pasta padrao).
