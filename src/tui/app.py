"""
src/tui/app.py
---------------
Aplicacao principal da TUI (Text User Interface) do pommo.

Combina:
  - Rich Live display para renderizacao continua sem travar o terminal
  - Integracao assincrona com PomodoroEngine e AlertManager
  - Leitura nao-bloqueante de teclado (cbreak + select) no Linux
  - Prompts interativos com rich.prompt para selecao de projetos e menus
  - Estetica hacker/cyberpunk em verde neon e cyan
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import select
import sys
from typing import Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from ..alerts.notifications import AlertManager
from ..database.connection import init_db
from ..database.repository import (
    buscar_projeto,
    criar_projeto,
    deletar_projeto,
    ler_configuracao,
    listar_projetos,
    obter_estatisticas_projetos,
    obter_resumo_estatisticas,
)
from ..models.projeto import Projeto
from ..timer.engine import CICLO_FOCO, PomodoroEngine
from ..timer.states import STATE_LABEL, PomodoroState
from .theme import BORDA_PADRAO, COR_PRIMARIA, COR_SECUNDARIA
from .widgets import (
    render_dashboard_estatisticas,
    render_estado,
    render_header,
    render_lista_projetos,
    render_log,
    render_menu,
    render_timer,
)

logger = logging.getLogger(__name__)


# =========================================================================
# Suporte a leitura nao-bloqueante de teclas no terminal POSIX
# =========================================================================

try:
    import termios
    import tty

    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


class TerminalCbreak:
    """
    Context manager para colocar o terminal em modo cbreak temporariamente.
    Permite ler teclas individuais sem esperar pela tecla Enter.
    """

    def __init__(self) -> None:
        self.fd: Optional[int] = None
        self.old_settings = None

    def __enter__(self) -> "TerminalCbreak":
        if HAS_TERMIOS and sys.stdin.isatty():
            try:
                self.fd = sys.stdin.fileno()
                self.old_settings = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)
            except Exception as exc:
                logger.debug("Nao foi possivel ativar cbreak: %s", exc)
                self.old_settings = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.restore()

    def restore(self) -> None:
        """Restaura as configuracoes normais do terminal."""
        if self.fd is not None and self.old_settings is not None:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception as exc:
                logger.debug("Erro ao restaurar terminal: %s", exc)

    def reapply(self) -> None:
        """Reaplica o modo cbreak apos operacoes de prompt."""
        if self.fd is not None and self.old_settings is not None:
            try:
                tty.setcbreak(self.fd)
            except Exception as exc:
                logger.debug("Erro ao reaplicar cbreak: %s", exc)


def _ler_tecla_nao_bloqueante() -> Optional[str]:
    """
    Verifica se ha caracteres prontos em sys.stdin sem bloquear a thread.
    Retorna o caractere em minusculo ou None.
    """
    if HAS_TERMIOS and sys.stdin.isatty():
        try:
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                ch = sys.stdin.read(1)
                return ch.lower()
        except Exception:
            return None
    elif not sys.stdin.isatty():
        # Em pipes ou testes nao-interativos, le caracteres ou encerra em EOF
        try:
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                ch = sys.stdin.read(1)
                return ch.lower() if ch else "q"
            return "q"
        except Exception:
            return "q"
    return None


# =========================================================================
# Classe Principal da TUI
# =========================================================================


class PomodoroTUI:
    """
    Controlador central da interface de terminal do pommo.

    Gerencia o ciclo de vida do motor, exibicao em tempo real com Live display,
    captura de atalhos e acionamento de menus interativos.
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.engine = PomodoroEngine()
        self.alert_mgr = AlertManager(som=True, desktop=True)

        self.running: bool = True
        self.projeto_ativo: Optional[Projeto] = None
        self.duracao_total: int = 25 * 60
        self.transicao_automatica: bool = False
        self.logs: list[str] = []

        # Inicializa callbacks do motor
        self._configurar_callbacks()

    # =====================================================================
    # Configuracao de Callbacks
    # =====================================================================

    def _configurar_callbacks(self) -> None:
        """Registra os callbacks no motor antes de plugar o AlertManager."""

        def _on_tick(segundos_restantes: int) -> None:
            # O tick atualiza o estado interno do motor; o Live redesenha
            pass

        def _on_state_change(novo_estado: PomodoroState) -> None:
            label = STATE_LABEL.get(novo_estado, novo_estado.name)
            self._adicionar_log(f"Estado alterado para: {label}")
            dur = self.engine._segundos_para_estado(novo_estado)
            if dur > 0:
                self.duracao_total = dur

        def _on_session_end(estado_concluido: PomodoroState) -> None:
            label = STATE_LABEL.get(estado_concluido, estado_concluido.name)
            self._adicionar_log(f"Sessao concluida: {label}")

        self.engine.on_tick = _on_tick
        self.engine.on_state_change = _on_state_change
        self.engine.on_session_end = _on_session_end

        # AlertManager encadeia seu alerta com o callback _on_session_end acima
        self.alert_mgr.conectar(self.engine)

    # =====================================================================
    # Logs da TUI
    # =====================================================================

    def _adicionar_log(self, mensagem: str) -> None:
        """Registra uma mensagem com timestamp no painel de log."""
        agora = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{agora}] {mensagem}")
        if len(self.logs) > 30:
            self.logs.pop(0)

    # =====================================================================
    # Montagem do Layout Hacker
    # =====================================================================

    def _gerar_view(self) -> Group:
        """
        Gera o conjunto completo de paineis rich para exibicao no Live.
        """
        projeto_nome = (
            f"{self.projeto_ativo.nome} (#{self.projeto_ativo.id})"
            if self.projeto_ativo
            else None
        )

        # Se o timer estiver parado e tempo for 0, usa a duracao total de foco
        seg_rest = self.engine.segundos_restantes
        if self.engine.state is PomodoroState.PARADO and seg_rest == 0:
            seg_rest = self.duracao_total

        return Group(
            render_header(),
            render_estado(
                state=self.engine.state,
                ciclos_foco=self.engine.ciclos_foco,
                total_ciclos=CICLO_FOCO,
                projeto_nome=projeto_nome,
                pausado=self.engine.pausado,
            ),
            render_timer(
                segundos_restantes=seg_rest,
                segundos_total=self.duracao_total,
                state=self.engine.state,
            ),
            render_menu(transicao_automatica=self.transicao_automatica),
            render_log(mensagens=self.logs, max_linhas=4),
        )

    # =====================================================================
    # Acoes do Usuario
    # =====================================================================

    async def acao_iniciar(self) -> None:
        """Inicia o ciclo de Pomodoro."""
        if self.engine.state is PomodoroState.PARADO:
            self._adicionar_log("Iniciando timer de foco...")
            await self.engine.start()
        elif self.engine.pausado:
            self._adicionar_log("Retomando timer...")
            await self.engine.resume()
        else:
            self._adicionar_log("Timer ja esta em execucao.")

    async def acao_pausar_retomar(self) -> None:
        """Alterna entre pausado e ativo."""
        if self.engine.state is PomodoroState.PARADO:
            self._adicionar_log("Timer parado. Pressione [S] para iniciar.")
            return

        if self.engine.pausado:
            self._adicionar_log("Retomando contagem.")
            await self.engine.resume()
        else:
            self._adicionar_log("Contagem pausada.")
            await self.engine.pause()

    async def acao_avancar(self) -> None:
        """Avanca para o proximo ciclo manualmente."""
        self._adicionar_log("Avancando manualmente para o proximo ciclo...")
        await self.engine.avancar()

    # =====================================================================
    # Menus Interativos com rich.prompt
    # =====================================================================

    def menu_gestao_projetos(
        self, live: Live, term_cbreak: TerminalCbreak
    ) -> None:
        """
        Pausa o Live display e abre menu completo de gestao de projetos.
        Permite: listar, adicionar novo, deletar e selecionar projeto ativo.
        """
        live.stop()
        term_cbreak.restore()

        while True:
            self.console.clear()
            self.console.print(render_header())

            projetos = listar_projetos()
            ativo_id = self.projeto_ativo.id if self.projeto_ativo else None

            # Painel com opcoes de gestao
            menu_texto = Text()
            menu_texto.append("  [1] Listar projetos cadastrados\n", style="bold cyan")
            menu_texto.append("  [2] Adicionar novo projeto\n", style="bold bright_green")
            menu_texto.append("  [3] Deletar um projeto existente\n", style="bold bright_red")
            menu_texto.append("  [4] Ativar/Selecionar projeto no timer\n", style="bold bright_yellow")
            menu_texto.append("  [0] Desvincular projeto ativo do timer\n", style="dim")
            menu_texto.append("  [V] Voltar ao timer principal\n", style="dim")

            painel = Panel(
                menu_texto,
                title="[bold bright_green]GESTAO DE PROJETOS[/bold bright_green]",
                border_style=BORDA_PADRAO,
                padding=(1, 2),
            )
            self.console.print(painel)

            if self.projeto_ativo:
                self.console.print(
                    f"[dim]Projeto ativo no momento:[/dim] [bold bright_green]{self.projeto_ativo.nome} (#{self.projeto_ativo.id})[/bold bright_green]\n"
                )
            else:
                self.console.print("[dim]Nenhum projeto ativo vinculado ao timer.[/dim]\n")

            opcao = Prompt.ask(
                "[bold cyan]Opcao desejada[/bold cyan]",
                choices=["1", "2", "3", "4", "0", "v", ""],
                default="v",
                show_choices=False,
                console=self.console,
            ).strip().lower()

            if opcao == "1":
                self.console.clear()
                self.console.print(render_header())
                if projetos:
                    self.console.print("\n[bold bright_green]Projetos Cadastrados:[/bold bright_green]\n")
                    self.console.print(render_lista_projetos(projetos, ativo_id=ativo_id))
                else:
                    self.console.print("\n[bright_yellow]Nenhum projeto cadastrado no banco de dados.[/bright_yellow]\n")
                Prompt.ask("\n[dim]Pressione Enter para continuar...[/dim]", default="", show_default=False, console=self.console)

            elif opcao == "2":
                self.console.print("\n[bold bright_green]-- Adicionar Novo Projeto --[/bold bright_green]")
                nome = Prompt.ask("[bold green]Nome do projeto[/bold green]", console=self.console).strip()
                if not nome:
                    self.console.print("[bright_red]Nome obrigatorio. Operacao cancelada.[/bright_red]")
                    Prompt.ask("[dim]Pressione Enter...[/dim]", default="", show_default=False, console=self.console)
                    continue

                categoria = Prompt.ask("[dim]Categoria/Tag (opcional, ex: dev, estudo)[/dim]", default="", console=self.console).strip() or None
                est_str = Prompt.ask("[dim]Estimativa de pomodoros[/dim]", default="0", console=self.console).strip()
                try:
                    est = int(est_str)
                except ValueError:
                    est = 0

                novo = criar_projeto(nome=nome, categoria=categoria, pomodoros_estimados=est)
                self.console.print(f"\n[bold bright_green]Projeto #{novo.id} '{novo.nome}' criado com sucesso![/bold bright_green]")
                ativar = Confirm.ask("Deseja ativar este projeto no timer agora?", default=True, console=self.console)
                if ativar:
                    self.projeto_ativo = novo
                    self.engine.projeto_id = novo.id
                    self._adicionar_log(f"Projeto ativo: {novo.nome} (#{novo.id})")
                else:
                    self._adicionar_log(f"Projeto #{novo.id} '{novo.nome}' criado.")
                Prompt.ask("[dim]Pressione Enter para continuar...[/dim]", default="", show_default=False, console=self.console)

            elif opcao == "3":
                self.console.clear()
                self.console.print(render_header())
                if not projetos:
                    self.console.print("\n[bright_yellow]Nenhum projeto disponivel para deletar.[/bright_yellow]\n")
                    Prompt.ask("[dim]Pressione Enter...[/dim]", default="", show_default=False, console=self.console)
                    continue

                self.console.print("\n[bold bright_red]-- Deletar Projeto --[/bold bright_red]\n")
                self.console.print(render_lista_projetos(projetos, ativo_id=ativo_id))

                id_del = Prompt.ask("\n[bold bright_red]Digite o ID do projeto a deletar (Enter cancela)[/bold bright_red]", default="", show_default=False, console=self.console).strip()
                if id_del.isdigit():
                    pid = int(id_del)
                    proj_alvo = buscar_projeto(pid)
                    if proj_alvo:
                        confirma = Confirm.ask(
                            f"[bold bright_yellow]Tem certeza que deseja deletar o projeto #{pid} '{proj_alvo.nome}'?[/bold bright_yellow]",
                            default=False,
                            console=self.console,
                        )
                        if confirma:
                            deletar_projeto(pid)
                            if self.projeto_ativo and self.projeto_ativo.id == pid:
                                self.projeto_ativo = None
                                self.engine.projeto_id = None
                            self._adicionar_log(f"Projeto #{pid} deletado com sucesso.")
                            self.console.print(f"[bold bright_green]Projeto #{pid} deletado.[/bold bright_green]")
                        else:
                            self.console.print("[dim]Operacao cancelada.[/dim]")
                    else:
                        self.console.print(f"[bright_red]Projeto #{pid} nao encontrado.[/bright_red]")
                    Prompt.ask("[dim]Pressione Enter para continuar...[/dim]", default="", show_default=False, console=self.console)

            elif opcao == "4":
                self.console.clear()
                self.console.print(render_header())
                if not projetos:
                    self.console.print("\n[bright_yellow]Nenhum projeto cadastrado.[/bright_yellow]\n")
                    Prompt.ask("[dim]Pressione Enter...[/dim]", default="", show_default=False, console=self.console)
                    continue

                self.console.print("\n[bold bright_green]Selecione o Projeto para Ativar:[/bold bright_green]\n")
                self.console.print(render_lista_projetos(projetos, ativo_id=ativo_id))

                id_sel = Prompt.ask("\n[bold cyan]Digite o ID do projeto desejado[/bold cyan]", default="", show_default=False, console=self.console).strip()
                if id_sel.isdigit():
                    pid = int(id_sel)
                    proj = buscar_projeto(pid)
                    if proj:
                        self.projeto_ativo = proj
                        self.engine.projeto_id = proj.id
                        self._adicionar_log(f"Projeto ativo: {proj.nome} (#{proj.id})")
                        self.console.print(f"[bold bright_green]Projeto #{proj.id} ativado no timer![/bold bright_green]")
                    else:
                        self.console.print(f"[bright_red]Projeto #{pid} nao encontrado.[/bright_red]")
                    Prompt.ask("[dim]Pressione Enter para continuar...[/dim]", default="", show_default=False, console=self.console)

            elif opcao == "0":
                self.projeto_ativo = None
                self.engine.projeto_id = None
                self._adicionar_log("Projeto desvinculado do timer.")
                self.console.print("[bold bright_green]Projeto desvinculado com sucesso.[/bold bright_green]")
                Prompt.ask("[dim]Pressione Enter para continuar...[/dim]", default="", show_default=False, console=self.console)

            elif opcao in ("v", ""):
                break

        term_cbreak.reapply()
        live.start()

    def tela_estatisticas(
        self, live: Live, term_cbreak: TerminalCbreak
    ) -> None:
        """
        Pausa o Live display e renderiza a tela completa de Dashboard de Estatisticas.
        """
        live.stop()
        term_cbreak.restore()

        self.console.clear()
        self.console.print(render_header())

        # Busca dados consolidados no banco
        estatisticas = obter_estatisticas_projetos()
        resumo = obter_resumo_estatisticas()

        # Renderiza o dashboard estilizado
        painel_stats = render_dashboard_estatisticas(estatisticas=estatisticas, resumo=resumo)
        self.console.print(painel_stats)

        Prompt.ask("\n[dim]Pressione Enter para retornar ao timer principal...[/dim]", default="", show_default=False, console=self.console)

        term_cbreak.reapply()
        live.start()

    async def menu_interativo(
        self, live: Live, term_cbreak: TerminalCbreak
    ) -> None:
        """
        Pausa o Live display e apresenta menu completo de acoes via rich.prompt.
        """
        live.stop()
        term_cbreak.restore()

        self.console.clear()
        self.console.print(render_header())

        menu_texto = Text()
        menu_texto.append("\n  [1 / S] Iniciar timer\n", style="bold bright_green")
        menu_texto.append("  [2 / P] Pausar / Retomar\n", style="bold bright_yellow")
        menu_texto.append("  [3 / N] Avancar para proximo ciclo\n", style="bold cyan")
        menu_texto.append("  [4 / J] Gestao de Projetos (Listar / Criar / Deletar / Ativar)\n", style="bold bright_green")
        menu_texto.append("  [5 / E] Dashboard de Estatisticas\n", style="bold cyan")
        menu_texto.append("  [6 / Q] Sair do pommo\n", style="bold bright_red")
        menu_texto.append("  [V]     Voltar ao painel\n", style="dim")

        painel_menu = Panel(
            menu_texto,
            title="[bold bright_green]MENU PRINCIPAL[/bold bright_green]",
            border_style=BORDA_PADRAO,
            padding=(1, 2),
        )
        self.console.print(painel_menu)

        opcao = Prompt.ask(
            "[bold cyan]Selecione a opcao desejada[/bold cyan]",
            choices=["1", "2", "3", "4", "5", "6", "s", "p", "n", "j", "e", "q", "v", ""],
            default="v",
            show_choices=False,
            console=self.console,
        ).strip().lower()

        if opcao in ("1", "s"):
            await self.acao_iniciar()
        elif opcao in ("2", "p"):
            await self.acao_pausar_retomar()
        elif opcao in ("3", "n"):
            await self.acao_avancar()
        elif opcao in ("4", "j"):
            self.menu_gestao_projetos(live, term_cbreak)
            return
        elif opcao in ("5", "e"):
            self.tela_estatisticas(live, term_cbreak)
            return
        elif opcao in ("6", "q"):
            self.running = False
            self._adicionar_log("Encerrando aplicativo...")

        term_cbreak.reapply()
        live.start()

    # =====================================================================
    # Loop Assincrono Principal
    # =====================================================================

    async def run(self) -> None:
        """
        Executa a TUI com atualizacoes continuas do Live display e
        processamento responsivo de atalhos e acoes.
        """
        # Garante inicializacao do banco
        init_db()

        # Carrega configuracoes atuais
        config = ler_configuracao()
        self.transicao_automatica = config.transicao_automatica
        self.duracao_total = config.tempo_foco * 60

        self._adicionar_log("Terminal cyberpunk ativado. Pronto para focar.")

        with TerminalCbreak() as term_cbreak:
            with Live(
                self._gerar_view(),
                console=self.console,
                refresh_per_second=8,
                screen=False,
                auto_refresh=True,
            ) as live:
                while self.running:
                    # Captura tecla se houver entrada disponivel
                    key = _ler_tecla_nao_bloqueante()

                    if key == "s":
                        await self.acao_iniciar()
                    elif key == "p":
                        await self.acao_pausar_retomar()
                    elif key == "n":
                        await self.acao_avancar()
                    elif key == "j":
                        self.menu_gestao_projetos(live, term_cbreak)
                    elif key == "e":
                        self.tela_estatisticas(live, term_cbreak)
                    elif key in ("m", "\r", "\n", ":"):
                        await self.menu_interativo(live, term_cbreak)
                    elif key in ("q", "\x03"):  # 'q' ou Ctrl+C
                        self.running = False
                        self._adicionar_log("Saindo...")
                        break

                    # Atualiza o frame no Live display
                    live.update(self._gerar_view())

                    # Cede controle para o motor do timer processar ticks/eventos
                    await asyncio.sleep(0.08)

        # Encerramento limpo
        if self.engine.state is not PomodoroState.PARADO:
            await self.engine.stop()

        self.console.print("\n[bold bright_green][ POMMO ] Sessao encerrada. Ate logo![/bold bright_green]\n")


def run_tui() -> None:
    """Ponto de entrada sincrono para execucao da interface TUI."""
    try:
        asyncio.run(PomodoroTUI().run())
    except KeyboardInterrupt:
        print("\n[ POMMO ] Encerrado pelo usuario.")
