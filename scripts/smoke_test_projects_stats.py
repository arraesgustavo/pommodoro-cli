"""
scripts/smoke_test_projects_stats.py
-------------------------------------
Smoke test para validacao da Etapa 5:
Gestao de Projetos, Relatorios e Estatisticas.

Valida:
  1. Criacao, listagem, busca e exclusao de projetos via repository
  2. Gravacao de sessoes vinculadas ao projeto com duracao e data/hora
  3. Agregacoes SQL de estatisticas por projeto (JOIN Projetos x Sessoes)
  4. Agregacoes de resumo consolidado geral
  5. Renderizacao da tabela hacker do Dashboard de Estatisticas com Rich
"""

import asyncio
import io
import sys
from pathlib import Path

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from src.database.connection import init_db
from src.database.repository import (
    buscar_projeto,
    criar_projeto,
    deletar_projeto,
    listar_projetos,
    listar_sessoes,
    obter_estatisticas_projetos,
    obter_resumo_estatisticas,
    registrar_sessao,
)
from src.models.estatistica import EstatisticaProjeto
from src.timer.engine import PomodoroEngine
from src.timer.states import PomodoroState
from src.tui.widgets import (
    render_dashboard_estatisticas,
    render_lista_projetos,
)

SEP = "=" * 65


def titulo(txt: str) -> None:
    print(f"\n{SEP}\n  {txt}\n{SEP}")


async def main() -> None:
    string_io = io.StringIO()
    console = Console(file=string_io, width=80, force_terminal=True)

    # -------------------------------------------------------------
    titulo("1. Testando Operacoes de Gestao de Projetos")
    init_db()

    # Criar
    nome_proj = "Cyber-Infiltration Unit"
    cat_proj = "RedTeam"
    meta_pomodoros = 6
    proj = criar_projeto(nome=nome_proj, categoria=cat_proj, pomodoros_estimados=meta_pomodoros)
    assert proj.id is not None
    print(f"  [OK] Projeto criado: #{proj.id} '{proj.nome}' [{proj.categoria}] - Meta: {proj.pomodoros_estimados}")

    # Buscar
    buscado = buscar_projeto(proj.id)
    assert buscado is not None
    assert buscado.nome == nome_proj
    print(f"  [OK] Projeto buscado por ID #{proj.id} com sucesso.")

    # Listar
    todos = listar_projetos()
    assert any(p.id == proj.id for p in todos)
    print(f"  [OK] Projeto listado entre os {len(todos)} projetos existentes.")

    # Renderizar tabela de projetos
    tab_proj = render_lista_projetos(todos, ativo_id=proj.id)
    assert tab_proj is not None
    console.print(tab_proj)
    print("  [OK] Tabela de listagem de projetos renderizada com sucesso.")

    # -------------------------------------------------------------
    titulo("2. Testando Integracao Sessao-Projeto via PomodoroEngine")
    engine = PomodoroEngine()
    engine.projeto_id = proj.id
    engine._state = PomodoroState.FOCO

    # Simula fim natural do ciclo de foco
    print(f"  Finalizando ciclo de foco vinculado ao projeto #{proj.id}...")
    await engine._ao_fim_da_sessao()

    # Registra uma sessao adicional diretamente para validar acumulacao
    registrar_sessao(duracao_minutos=30, tipo="foco", projeto_id=proj.id)

    # Verifica persistencia
    sessoes_proj = listar_sessoes(projeto_id=proj.id, tipo="foco")
    assert len(sessoes_proj) >= 2, f"Esperadas pelo menos 2 sessoes de foco, encontradas {len(sessoes_proj)}"
    for s in sessoes_proj:
        assert s.projeto_id == proj.id
        assert s.tipo == "foco"
        assert s.duracao_minutos > 0
        assert s.data_hora is not None
    print(f"  [OK] {len(sessoes_proj)} sessoes de foco persistidas com duracao, tipo e data/hora.")

    # -------------------------------------------------------------
    titulo("3. Testando Agregacao SQL e Dashboard de Estatisticas")
    todas_stats = obter_estatisticas_projetos()
    assert len(todas_stats) > 0

    stats_alvo = next((s for s in todas_stats if s.projeto_id == proj.id), None)
    assert stats_alvo is not None, f"Estatisticas nao encontradas para projeto #{proj.id}"
    print(f"  [OK] Agregacao do projeto #{proj.id}:")
    print(f"       - Pomodoros estimados:  {stats_alvo.pomodoros_estimados}")
    print(f"       - Pomodoros realizados: {stats_alvo.pomodoros_realizados}")
    print(f"       - Tempo total em foco:  {stats_alvo.tempo_formatado} ({stats_alvo.tempo_foco_minutos} min)")
    print(f"       - Progresso atingido:   {stats_alvo.progresso_percentual:.1f}%")
    assert stats_alvo.pomodoros_realizados >= 2
    assert stats_alvo.tempo_foco_minutos >= 55

    resumo = obter_resumo_estatisticas()
    print("  [OK] Resumo geral consolidado:")
    print(f"       - Total de projetos:         {resumo['total_projetos']}")
    print(f"       - Total de pomodoros:        {resumo['total_pomodoros']}")
    print(f"       - Minutos totais em foco:    {resumo['tempo_foco_minutos']} min")
    print(f"       - Pomodoros sem projeto:     {resumo['pomodoros_sem_projeto']}")
    assert resumo["total_projetos"] >= 1
    assert resumo["total_pomodoros"] >= 2

    # Renderiza o Dashboard visual completo
    painel_dashboard = render_dashboard_estatisticas(todas_stats, resumo)
    assert painel_dashboard is not None
    console.print(painel_dashboard)
    saida = string_io.getvalue()
    assert "DASHBOARD DE ESTATISTICAS" in saida
    assert "Cyber-Infiltration Unit" in saida
    print("  [OK] Dashboard completo renderizado com estetica hacker.")

    # -------------------------------------------------------------
    titulo("4. Testando Exclusao de Projeto (ON DELETE SET NULL)")
    proj_temporario = criar_projeto(nome="Projeto Descartavel", categoria="Temp", pomodoros_estimados=1)
    registrar_sessao(duracao_minutos=25, tipo="foco", projeto_id=proj_temporario.id)

    deletado = deletar_projeto(proj_temporario.id)
    assert deletado is True
    assert buscar_projeto(proj_temporario.id) is None
    print(f"  [OK] Projeto descartavel #{proj_temporario.id} removido com sucesso.")

    titulo("SMOKE TEST DA ETAPA 5 CONCLUIDO COM 100% DE SUCESSO")


if __name__ == "__main__":
    asyncio.run(main())
