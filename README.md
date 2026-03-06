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
- FFmpeg opcoes (`-ss`, `-to`): https://ffmpeg.org/ffmpeg-doc.html
- FFmpeg encoders/codecs: https://ffmpeg.org/ffmpeg-codecs.html
- Python Tkinter: https://docs.python.org/3/library/tkinter.html
- PyInstaller: https://www.pyinstaller.org/en/stable/usage.html
- WM_DROPFILES (Win32): https://learn.microsoft.com/en-us/windows/win32/shell/wm-dropfiles
- DragAcceptFiles (Win32): https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-dragacceptfiles
- SetWindowLongPtrW (Win32): https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptrw
- CallWindowProcW (Win32): https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-callwindowprocw

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
- `--use-gpu`: ativa encode por GPU.
- `--gpu-encoder`: define encoder GPU (`auto`, `h264_nvenc`, `h264_amf`, `h264_qsv`).
- `--list-gpu`: lista encoders GPU detectados pelo FFmpeg.

## Interface grafica (Windows)

Execute:

```powershell
run_gui.bat
```

Fluxo:
1. Selecione a pasta de entrada.
2. A lista de videos sera carregada.
3. Opcional: arraste e solte na janela:
   - uma pasta (carrega videos da pasta),
   - varios videos selecionados,
   - ou apenas um video.
4. Use ordenacao por nome/data e veja colunas com `#`, `Processado`, `Arquivo` e `Data/Hora`.
5. Selecione os videos desejados (contador `Selecionados: X / Y`).
6. Escolha o script/perfil pronto.
7. Defina a pasta de saida.
8. Ative/desative `Usar GPU (aceleracao)` quando desejar.
9. Use `Ver pasta` para abrir rapidamente o output no Explorer.
10. Clique em `Executar`.

Indicador na tela:
- `Fonte: pasta selecionada`
- `Fonte: pasta (arrastar e soltar)`
- `Fonte: lista de arquivos (arrastar e soltar)`

A GUI possui tambem uma barra de menu com caminhos alternativos para as mesmas acoes:
- selecionar entrada/output
- atualizar lista
- selecionar/limpar selecao
- escolher perfil
- executar processamento
- criar atalho na area de trabalho
- ativar/desativar GPU (deteccao automatica)

## Arrastar e soltar (input)

Comportamento suportado:
- Soltar uma pasta: carrega videos da pasta.
- Soltar varios videos: carrega somente os arquivos de video soltos.
- Soltar um unico video: carrega 1 item na lista.
- Itens nao reconhecidos como video sao ignorados e registrados no log.

Observacoes importantes:
- O recurso e Windows-only (implementado via API nativa de janela).
- Se a aplicacao estiver em nivel de privilegio diferente do `explorer.exe` (ex.: app em modo Administrador e Explorer normal), o arrastar e soltar pode falhar por restricoes de UIPI.
- Quando houver alteracao de codigo, gere novamente o executavel com `build_exe.bat` antes de retestar no `.exe`.
- Se houver qualquer falha no drag-and-drop, o fluxo por botoes (`Selecionar` / `Atualizar lista`) continua suportado normalmente.

## Aceleracao por GPU

A aplicacao identifica encoders H.264 de GPU disponiveis no FFmpeg e permite ativar/desativar uso quando quiser.

Encoders detectados automaticamente (quando disponiveis):
- `h264_nvenc` (NVIDIA)
- `h264_amf` (AMD)
- `h264_qsv` (Intel Quick Sync)

Comportamento:
- Toggle desativado: processamento em CPU (comportamento padrao).
- Toggle ativado: usa o encoder GPU detectado com maior prioridade.
- Se nao houver encoder GPU detectado, a execucao exibe erro claro.

## Modo recorte

O recorte foi implementado em modo separado para nao impactar o fluxo de compactacao.

Como abrir:
- Menu `Arquivo > Abrir modo recorte`
- ou menu `Recorte > Abrir modo recorte`

No modo recorte:
1. Selecione qualquer video (de input, output, ou outro caminho no disco).
2. Informe quanto cortar no inicio (segundos).
3. Informe quanto cortar no final (segundos).
4. Defina a pasta de output do recorte.
5. Opcionalmente ative/desative GPU para o recorte.
6. Execute o recorte.

Saida:
- Arquivo gerado como `*_trim.mp4`.
- Log com duracao original/final, tamanho original/final e percentual.

No log de execucao, cada video mostra:
- tamanho original
- tamanho final
- percentual de reducao (ou aumento)

## Historico de execucoes

Cada execucao de compactacao e recorte e registrada em:

- `execution_history.jsonl`

Uso no app:
- A coluna `Processado` indica `Sim` quando aquele arquivo de entrada ja foi processado com sucesso em alguma execucao anterior.
- O indicador e apenas informativo e nao bloqueia reprocessamento.
- A aba `Processados` lista os processamentos com:
  - `Data/Hora`, `Modo`, `Original`, `Saida`
  - `Tam. Original`, `Tam. Final` e `Variacao` (reducao/aumento em percentual)
  - `GPU` (CPU ou encoder usado), `Tempo` (tempo de cada processamento)
  - `Tempo Colecao` (tempo acumulado quando o processamento foi em lote com varios videos)
- Acoes da aba `Processados`:
  - `Recarregar historico`
  - `Tocar original` (abre/toca o arquivo original no player padrao do Windows)
  - `Tocar saida` (abre/toca o arquivo gerado no player padrao do Windows)
- As mesmas acoes de historico tambem estao no menu `Historico`.

## Configuracao persistente do usuario

Ao abrir/fechar novamente, a interface preserva parametros em:

- `user_settings.json`

Arquivo editavel manualmente, com campos:
- `input_dir`
- `output_dir`
- `profile_key`
- `sort_mode`
- `overwrite`
- `gpu_enabled`
- `trim_input_file`
- `trim_output_dir`
- `trim_start_seconds`
- `trim_end_seconds`
- `trim_overwrite`

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
- Para criar atalho na area de trabalho, o caminho recomendado e apos gerar o `.exe`.
- Se o `.exe` nao existir, a GUI cria atalho com fallback para `run_gui.bat`.
- Sempre gere um novo `.exe` apos mudancas no codigo para validar comportamento atualizado.
