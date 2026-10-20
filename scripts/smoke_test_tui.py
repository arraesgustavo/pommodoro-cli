"""
scripts/smoke_test_tui.py
--------------------------
Smoke test automatizado da Interface TUI (Etapa 4).

Testa:
  1. Criacao e integracao dos componentes visuais (Widgets)
  2. Inicializacao do PomodoroTUI
  3. Acoes assincronas de controle: iniciar, pausar, retomar, avancar
  4. Vinculacao de projeto ativo com o banco de dados
  5. Renderizacao completa dos estados: PARADO, FOCO, DESCANSO, PAUSADO
  6. Encerramento limpo do motor

Uso:
    python scripts/smoke_test_tui.py
"""

import asyncio
import io
import sys
from pathlib import Path

# Garante importacao do projeto local
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from src.database.connection import init_db
from src.database.repository import atualizar_configuracao, criar_projeto, listar_projetos
from src.models.projeto import Projeto
from src.timer.states import PomodoroState
from src.tui.app import PomodoroTUI
from src.tui.theme import (
    BORDA_PADRAO,
    COR_PRIMARIA,
    COR_SECUNDARIA,
    LOGO,
    MENU_OPCOES,
    SUBTITULO,
)
from src.tui.widgets import (
    render_estado,
    render_header,
    render_lista_projetos,
    render_log,
    render_menu,
    render_timer,
)

SEP = "=" * 60


def titulo(txt: str) -> None:
    print(f"\n{SEP}\n  {txt}\n{SEP}")


async def main() -> None:
    titulo("1. Testando Widgets Individuais")
    string_io = io.StringIO()
    console = Console(file=string_io, width=80, force_terminal=True)

    header = render_header()
    assert header is not None
    console.print(header)
    print("  [OK] render_header()")

    estado_panel = render_estado(
        state=PomodoroState.FOCO,
        ciclos_foco=1,
        total_ciclos=4,
        projeto_nome="Matrix Protocol (#42)",
        pausado=False,
    )
    assert estado_panel is not None
    console.print(estado_panel)
    print("  [OK] render_estado()")

    timer_panel = render_timer(
        segundos_restantes=1200,
        segundos_total=1500,
        state=PomodoroState.FOCO,
    )
    assert timer_panel is not None
    console.print(timer_panel)
    print("  [OK] render_timer()")

    menu_panel = render_menu(transicao_automatica=False)
    assert menu_panel is not None
    console.print(menu_panel)
    print("  [OK] render_menu()")

    log_panel = render_log(
        mensagens=["Inicializando...", "Sessao de foco ativa."],
        max_linhas=4,
    )
    assert log_panel is not None
    console.print(log_panel)
    print("  [OK] render_log()")

    # -------------------------------------------------------------
    titulo("2. Inicializando Banco e PomodoroTUI")
    init_db()
    atualizar_configuracao(
        tempo_foco=25,
        tempo_descanso=5,
        tempo_descanso_longo=15,
        transicao_automatica=False,
    )
    tui = PomodoroTUI(console=console)
    assert tui.engine is not None
    assert tui.alert_mgr is not None
    print("  [OK] PomodoroTUI instanciado com motor e AlertManager conectados.")

    # -------------------------------------------------------------
    titulo("3. Testando Acoes Assincronas do Motor via TUI")

    # Iniciar
    print("  Executando acao_iniciar()...")
    await tui.acao_iniciar()
    await asyncio.sleep(0.3)
    assert tui.engine.state is PomodoroState.FOCO
    print(f"  [OK] Timer iniciado. Estado atual: {tui.engine.state.name}")

    # Pausar
    print("  Executando acao_pausar_retomar() -> Pausar...")
    await tui.acao_pausar_retomar()
    await asyncio.sleep(0.1)
    assert tui.engine.pausado is True
    print("  [OK] Timer pausado com sucesso.")

    # Retomar
    print("  Executando acao_pausar_retomar() -> Retomar...")
    await tui.acao_pausar_retomar()
    await asyncio.sleep(0.1)
    assert tui.engine.pausado is False
    print("  [OK] Timer retomado com sucesso.")

    # Avancar manualmente
    print("  Executando acao_avancar()...")
    await tui.acao_avancar()
    await asyncio.sleep(0.3)
    assert tui.engine.state in (
        PomodoroState.DESCANSO_CURTO,
        PomodoroState.DESCANSO_LONGO,
    )
    print(f"  [OK] Avanco realizado. Novo estado: {tui.engine.state.name}")

    # -------------------------------------------------------------
    titulo("4. Testando Vinculacao com Banco de Dados e Projetos")
    proj = criar_projeto(
        nome="Cyber Security Audit",
        categoria="Infosec",
        pomodoros_estimados=8,
    )
    tui.projeto_ativo = proj
    tui.engine.projeto_id = proj.id

    todos_projetos = listar_projetos()
    tabela_projetos = render_lista_projetos(todos_projetos, ativo_id=proj.id)
    assert tabela_projetos is not None
    console.print(tabela_projetos)
    print(f"  [OK] Projeto #{proj.id} '{proj.nome}' vinculado e tabela renderizada.")

    # -------------------------------------------------------------
    titulo("5. Renderizacao Completa da View Hacker")
    view_completa = tui._gerar_view()
    console.print(view_completa)
    saida = string_io.getvalue()
    assert "POMOHACKER" in saida
    assert "Cyber Security Audit" in saida
    print("  [OK] Layout hacker completo renderizado com sucesso sem erros.")

    # -------------------------------------------------------------
    titulo("6. Encerramento Limpo")
    await tui.engine.stop()
    assert tui.engine.state is PomodoroState.PARADO
    print("  [OK] Motor parado com sucesso.")

    titulo("SMOKE TEST DA TUI CONCLUIDO COM 100% DE SUCESSO")


if __name__ == "__main__":
    asyncio.run(main())
