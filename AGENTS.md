# AGENTS.md

## Diretrizes permanentes para AI coding agents

1. Planejamento
- Definir plano de acao antes de qualquer implementacao.
- Revisar riscos e trade-offs antes de editar codigo.

2. Fontes de referencia
- Consultar sempre documentacao oficial da stack utilizada.
- Quando a ferramenta Context7 estiver disponivel, preferir seu uso para consulta de docs.

3. Implementacao
- Considerar `ffmpeg` como ferramenta principal para processamento de video.
- Implementar de forma incremental e valida a cada etapa.

4. Fechamento de tarefa
- Rodar 3 ciclos de verificacao para detectar problemas, bugs e issues criticos.
- Registrar mini relatorio de verificacao com resultados e riscos residuais.
- Realizar commit e push ao final de cada execucao.

5. Produtividade
- Priorizar recursos de execucao em background quando isso acelerar validacoes e build.
