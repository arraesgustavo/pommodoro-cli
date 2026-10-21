# POMOCLI // Cyberpunk Pomodoro Terminal

```text
 ____   ___  __  __  ___    ____ _     ___ 
|  _ \ / _ \|  \/  |/ _ \  / ___| |   |_ _|
| |_) | | | | |\/| | | | || |   | |    | | 
|  __/| |_| | |  | | |_| || |___| |___ | | 
|_|    \___/|_|  |_|\___/  \____|_____|___|

[ HACKER POMODORO TERMINAL // ARCH LINUX ]
```

Ferramenta CLI de Pomodoro com estetica hacker/cyberpunk construida em Python e Rich para o terminal do Arch Linux.

===============================================================================

## Funcionalidades

- **Interface TUI Reativa**: Renderizada com a biblioteca Rich (Live display nao-bloqueante em verde neon e cyan).
- **Maquina de Estados Assincrona**: Ciclos de Foco (25min), Descanso Curto (5min) e Descanso Longo (15min apos 4 ciclos).
- **Notificacoes Nativas**: Pop-ups no desktop via `notify-send` (libnotify).
- **Efeitos Sonoros**: Alertas de audio sintetizados tocados via `paplay` (PipeWire / PulseAudio).
- **Gestao de Projetos**: Criacao, listagem, remocao e vinculacao de projetos no banco SQLite local.
- **Menu de Configuracoes**: Edicao interativa do tempo de foco, descanso curto/longo e da transicao automatica (manual ou automatica), gravada com UPDATE na tabela `configuracoes`.
- **Dashboard de Estatisticas**: Painel visual com tempo total de foco, pomodoros estimados vs. concluidos e barras de progresso.
- **XDG Compliant**: Banco de dados e configuracoes armazenados automaticamente em `~/.local/share/pomocli/pomocli.db`.

===============================================================================

## Pre-requisitos (Arch Linux)

Para alertas visuais e sonoros no Arch Linux:

```bash
sudo pacman -S libnotify pipewire-pulse python-pipx
```

===============================================================================

## Instalacao

### 1. Metodo Recomendado (Global via pipx no Arch Linux)

O `pipx` e o padrao recomendado no Arch Linux para instalar utilitarios CLI em ambientes isolados sem conflitar com os pacotes do sistema:

```bash
# Na raiz do repositorio:
pipx install --editable .
```

Apos a instalacao, o comando global `pomocli` ficara disponivel imediatamente em qualquer diretorio do seu terminal (em `~/.local/bin/pomocli`).

### 2. Metodo Alternativo (Ambiente Virtual com venv)

Caso prefira rodar em ambiente virtual local de desenvolvimento:

```bash
# Criar e ativar venv
python -m venv .venv
source .venv/bin/activate

# Instalar em modo editavel com dependencias
pip install -e .
```

===============================================================================

## Como Executar

Apos instalar, execute de qualquer diretorio:

```bash
pomocli
```

*(O comando alternativo `pommo` tambem esta disponivel).*

===============================================================================

## Atalhos do Teclado

Durante a execucao da interface, os seguintes comandos respondem instantaneamente sem necessidade de pressionar Enter:

- **[S]** ou **1**: Iniciar o timer de foco
- **[P]** ou **2**: Pausar / Retomar a contagem
- **[N]** ou **3**: Avancar manualmente para o proximo ciclo
- **[J]** ou **4**: Menu de Gestao de Projetos (Adicionar, Listar, Deletar, Selecionar)
- **[E]** ou **5**: Dashboard de Estatisticas e Relatorios
- **[C]** ou **7**: Menu de Configuracoes (tempos de foco/descanso e transicao automatica)
- **[M]**: Menu guiado interativo com prompts
- **Enter**: Abre o menu guiado **ou**, quando o timer esta aguardando o proximo
  periodo (transicao manual), inicia esse periodo (ex: "Aperte Enter para
  iniciar o Descanso")
- **[Q]**: Encerramento limpo e seguro do aplicativo

===============================================================================

## Estrutura do Pacote

- `src/cli`: Ponto de entrada do comando global.
- `src/tui`: Componentes visuais Rich, layout hacker e loop de eventos.
- `src/timer`: Motor assincrono do timer e maquina de estados.
- `src/database`: Camada de acesso a dados SQLite e consultas de agregacao.
- `src/alerts`: Integracao com `notify-send` e `paplay`.
- `src/assets/sounds`: Efeitos sonoros empacotados junto a distribuicao.
- `scripts`: Utilitarios de smoke tests e geracao de assets de audio.
