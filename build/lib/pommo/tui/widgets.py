"""
src/tui/widgets.py
-------------------
Funcoes de renderizacao de componentes visuais isolados (rich Renderables).

Cada funcao retorna um objeto renderizavel pelo rich (Panel, Table, etc.)
sem efeitos colaterais - puro dado visual.
"""

from __future__ import annotations

from rich.align import Align
from rich.columns import Columns
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from ..models.estatistica import EstatisticaProjeto
from ..timer.states import PomodoroState
from .theme import (
    BARRA_COR_POR_ESTADO,
    BORDA_PADRAO,
    COR_INATIVO,
    COR_PRIMARIA,
    COR_SECUNDARIA,
    ESTILO_POR_ESTADO,
    LABEL_ESTADO,
    LINHA_DEC,
    LOGO,
    MENU_OPCOES,
    SUBTITULO,
)


# =========================================================================
# Cabecalho
# =========================================================================


def render_header() -> Panel:
    """
    Renderiza o cabecalho ASCII art com o logo e subtitulo do app.

    Returns:
        Panel do rich pronto para impressao.
    """
    logo_text = Text(LOGO, style=f"bold {COR_PRIMARIA}", justify="center")
    sub_text  = Text(SUBTITULO, style=f"bold {COR_SECUNDARIA}", justify="center")

    conteudo = Text.assemble(logo_text, "\n", sub_text)

    return Panel(
        Align.center(conteudo),
        border_style=BORDA_PADRAO,
        padding=(0, 2),
    )


# =========================================================================
# Painel de estado atual
# =========================================================================


def render_estado(
    state: PomodoroState,
    ciclos_foco: int,
    total_ciclos: int,
    projeto_nome: str | None,
    pausado: bool,
) -> Panel:
    """
    Renderiza o painel central com o estado atual do timer.

    Args:
        state:        Estado atual do PomodoroEngine.
        ciclos_foco:  Ciclos de foco ja concluidos neste grupo.
        total_ciclos: Total de ciclos antes do descanso longo (ex: 4).
        projeto_nome: Nome do projeto ativo ou None.
        pausado:      True se o timer estiver pausado.

    Returns:
        Panel do rich.
    """
    nome_estado = state.name
    label = LABEL_ESTADO.get(nome_estado, nome_estado)
    estilo = ESTILO_POR_ESTADO.get(nome_estado, COR_PRIMARIA)

    # Linha de estado
    linha_estado = Text(label, style=estilo, justify="center")

    # Indicador de pausa
    if pausado and state is not PomodoroState.PARADO:
        linha_estado.append("  [ PAUSADO ]", style="blink bold bright_yellow")

    # Ciclos graficos: [#][#][ ][ ]
    ciclo_str = _render_ciclos(ciclos_foco, total_ciclos)
    linha_ciclos = Text(f"Ciclo: {ciclo_str}", style=COR_SECUNDARIA, justify="center")

    # Projeto ativo
    if projeto_nome:
        proj_str = f"Projeto: {projeto_nome}"
        linha_proj = Text(proj_str, style=f"italic {COR_SECUNDARIA}", justify="center")
    else:
        linha_proj = Text("Projeto: (nenhum)", style=COR_INATIVO, justify="center")

    # Monta o conteudo
    tabela = Table.grid(padding=(0, 1))
    tabela.add_row(Align.center(linha_estado))
    tabela.add_row(Align.center(Text(" ")))
    tabela.add_row(Align.center(linha_ciclos))
    tabela.add_row(Align.center(linha_proj))

    return Panel(
        tabela,
        title="[bold bright_green]STATUS[/bold bright_green]",
        border_style=BORDA_PADRAO,
        padding=(1, 4),
    )


def _render_ciclos(concluidos: int, total: int) -> str:
    """Retorna string visual dos ciclos: ex '[#][#][ ][ ]'."""
    blocos = []
    for i in range(total):
        blocos.append("[#]" if i < concluidos else "[ ]")
    return " ".join(blocos)


# =========================================================================
# Barra de progresso do timer
# =========================================================================


def render_timer(
    segundos_restantes: int,
    segundos_total: int,
    state: PomodoroState,
) -> Panel:
    """
    Renderiza o painel da barra de progresso do timer.

    Args:
        segundos_restantes: Segundos ainda restantes.
        segundos_total:     Duracao total da sessao em segundos.
        state:              Estado atual (define a cor da barra).

    Returns:
        Panel do rich.
    """
    nome_estado = state.name
    cor_barra   = BARRA_COR_POR_ESTADO.get(nome_estado, "green")

    # Calcula progresso (0.0 a 1.0); evita divisao por zero
    if segundos_total > 0:
        progresso = 1.0 - (segundos_restantes / segundos_total)
    else:
        progresso = 0.0

    # Formata o tempo restante
    mins, secs = divmod(max(0, segundos_restantes), 60)
    tempo_str = f"{mins:02d}:{secs:02d}"

    barra = ProgressBar(
        total=100,
        completed=int(progresso * 100),
        width=None,   # usa toda a largura disponivel
        style=f"on {cor_barra}",
        complete_style=cor_barra,
        finished_style=cor_barra,
        pulse=state is PomodoroState.PARADO,
    )

    label_tempo = Text(
        f"  {tempo_str} restante",
        style=f"bold {cor_barra}",
    )

    grade = Table.grid(padding=0)
    grade.add_row(barra)
    grade.add_row(label_tempo)

    return Panel(
        grade,
        title="[bold bright_green]TIMER[/bold bright_green]",
        border_style=BORDA_PADRAO,
        padding=(1, 2),
    )


# =========================================================================
# Menu de controles
# =========================================================================


def render_menu(transicao_automatica: bool) -> Panel:
    """
    Renderiza o painel de teclas de controle.

    Args:
        transicao_automatica: Se True, oculta a opcao [N]ext.

    Returns:
        Panel do rich.
    """
    itens = []
    for key, (label, descricao) in MENU_OPCOES.items():
        # Esconde [N]ext se a transicao for automatica
        if key == "n" and transicao_automatica:
            continue
        tecla_text = Text(label, style=f"bold {COR_PRIMARIA}")
        desc_text  = Text(f" {descricao}", style=COR_INATIVO)
        itens.append(Text.assemble(tecla_text, desc_text))

    cols = Columns(itens, equal=True, expand=True)

    return Panel(
        cols,
        title="[bold bright_green]CONTROLES[/bold bright_green]",
        border_style=BORDA_PADRAO,
        padding=(0, 2),
    )


# =========================================================================
# Painel de log / mensagens
# =========================================================================


def render_log(mensagens: list[str], max_linhas: int = 4) -> Panel:
    """
    Renderiza um painel de log com as ultimas mensagens do sistema.

    Args:
        mensagens:  Lista de strings (mais recente por ultimo).
        max_linhas: Quantas linhas exibir no maximo.

    Returns:
        Panel do rich.
    """
    ultimas = mensagens[-max_linhas:]
    texto = Text()
    for msg in ultimas:
        texto.append(f" > {msg}\n", style=COR_INATIVO)

    return Panel(
        texto,
        title="[bold bright_green]LOG[/bold bright_green]",
        border_style=f"dim {BORDA_PADRAO}",
        padding=(0, 1),
    )


# =========================================================================
# Lista de projetos (para selecao)
# =========================================================================


def render_lista_projetos(projetos: list, ativo_id: int | None = None) -> Table:
    """
    Renderiza a tabela de projetos para selecao interativa.

    Args:
        projetos:  Lista de objetos Projeto.
        ativo_id:  ID do projeto atualmente selecionado (destaque).

    Returns:
        Table do rich.
    """
    tabela = Table(
        show_header=True,
        header_style=f"bold {COR_SECUNDARIA}",
        border_style=BORDA_PADRAO,
        show_lines=True,
    )
    tabela.add_column("#",         style="dim", width=5, justify="right")
    tabela.add_column("Nome",      style=COR_PRIMARIA)
    tabela.add_column("Categoria", style=COR_SECUNDARIA)
    tabela.add_column("Pomodoros", justify="center")

    for proj in projetos:
        is_ativo = proj.id == ativo_id
        estilo_linha = f"bold {COR_PRIMARIA}" if is_ativo else ""
        marcador = "*" if is_ativo else ""
        tabela.add_row(
            f"{proj.id}{marcador}",
            proj.nome,
            proj.categoria or "-",
            str(proj.pomodoros_estimados),
            style=estilo_linha,
        )

    return tabela


# =========================================================================
# Dashboard de Estatisticas
# =========================================================================


def _gerar_mini_barra(percentual: float, largura: int = 6) -> str:
    """Gera uma barra de caracteres ASCII/Hacker representando o progresso."""
    if percentual <= 0:
        preenchido = 0
    else:
        preenchido = min(largura, int(round((percentual / 100.0) * largura)))
    vazio = largura - preenchido
    return f"[{'=' * preenchido}{' ' * vazio}] {int(round(percentual))}%"


def render_dashboard_estatisticas(
    estatisticas: list[EstatisticaProjeto],
    resumo: dict[str, int],
) -> Panel:
    """
    Renderiza a visualizacao completa do Dashboard de Estatisticas.

    Exibe tabela hacker detalhada por projeto com comparativo de estimados vs
    realizados e tempo acumulado, alem de totalizadores consolidados.

    Args:
        estatisticas: Lista de metricas agregadas por projeto.
        resumo:       Dicionario com totais consolidados.

    Returns:
        Panel do rich estilizado.
    """
    # Tabela principal com estetica hacker (bordas cyan, textos verde/branco)
    tabela = Table(
        show_header=True,
        header_style=f"bold {COR_SECUNDARIA}",
        border_style="cyan",
        show_lines=True,
    )
    tabela.add_column("#", style="dim", width=4, justify="right")
    tabela.add_column("Projeto", style=f"bold {COR_PRIMARIA}")
    tabela.add_column("Categoria", style=COR_SECUNDARIA)
    tabela.add_column("Est.", justify="center", style="white", width=5)
    tabela.add_column("Realiz.", justify="center", style=f"bold {COR_PRIMARIA}", width=7)
    tabela.add_column("Progresso", justify="center", style="bright_yellow", width=12)
    tabela.add_column("Tempo Foco", justify="right", style=f"bold {COR_PRIMARIA}", width=10)

    if estatisticas:
        for est in estatisticas:
            barra = _gerar_mini_barra(est.progresso_percentual, largura=5)
            tabela.add_row(
                str(est.projeto_id),
                est.nome,
                est.categoria or "-",
                str(est.pomodoros_estimados),
                str(est.pomodoros_realizados),
                barra,
                est.tempo_formatado,
            )
    else:
        tabela.add_row(
            "-",
            "[dim]Nenhum projeto cadastrado no banco.[/dim]",
            "-",
            "-",
            "-",
            "-",
            "-",
        )

    # Painel de resumo geral
    min_totais = resumo.get("tempo_foco_minutos", 0)
    horas_totais = min_totais // 60
    resto_min = min_totais % 60
    tempo_total_str = f"{horas_totais}h {resto_min:02d}m" if horas_totais > 0 else f"{resto_min}m"

    tabela_resumo = Table.grid(padding=(0, 3), expand=True)
    tabela_resumo.add_column(style=f"bold {COR_SECUNDARIA}", justify="left")
    tabela_resumo.add_column(style=f"bold {COR_SECUNDARIA}", justify="right")

    tabela_resumo.add_row(
        f"Projetos Cadastrados: [bold {COR_PRIMARIA}]{resumo.get('total_projetos', 0)}[/bold {COR_PRIMARIA}]",
        f"Pomodoros Concluidos: [bold {COR_PRIMARIA}]{resumo.get('total_pomodoros', 0)}[/bold {COR_PRIMARIA}]",
    )
    tabela_resumo.add_row(
        f"Tempo Total em Foco:  [bold {COR_PRIMARIA}]{tempo_total_str}[/bold {COR_PRIMARIA}]",
        f"Pomodoros sem Projeto: [bold bright_yellow]{resumo.get('pomodoros_sem_projeto', 0)}[/bold bright_yellow]",
    )

    painel_resumo = Panel(
        tabela_resumo,
        title="[bold bright_green]RESUMO CONSOLIDADO[/bold bright_green]",
        border_style=BORDA_PADRAO,
        padding=(0, 2),
    )

    # Monta conteudo completo
    grade_completa = Table.grid(padding=(1, 0))
    grade_completa.add_row(tabela)
    grade_completa.add_row(painel_resumo)

    return Panel(
        grade_completa,
        title="[bold bright_green]DASHBOARD DE ESTATISTICAS // POMOHACKER[/bold bright_green]",
        border_style=BORDA_PADRAO,
        padding=(1, 2),
    )
