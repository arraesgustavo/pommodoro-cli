"""
scripts/smoke_test_timer.py
----------------------------
Validacao rapida do motor do Pomodoro (PomodoroEngine).

Executa dois cenarios:
  1. Transicao MANUAL  - simula 4 ciclos de foco + descasos usando duracao de
                         2 segundos por sessao para nao precisar esperar minutos.
  2. Transicao AUTOMATICA - deixa o engine rolar sozinho por 3 ciclos.

Execute com:
    python scripts/smoke_test_timer.py
"""

import asyncio
import sys
from pathlib import Path

# Garante que o pacote local seja encontrado sem instalacao
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import init_db
from src.database.repository import atualizar_configuracao
from src.timer.engine import PomodoroEngine, CICLO_FOCO
from src.timer.states import PomodoroState, STATE_LABEL

SEP = "=" * 55


def cabecalho(titulo: str) -> None:
    print(f"\n{SEP}\n  {titulo}\n{SEP}")


# =========================================================================
# Cenario 1 - Transicao manual
# =========================================================================

async def cenario_manual() -> None:
    cabecalho("CENARIO 1 - Transicao MANUAL (4 ciclos completos)")

    # Configura duracao de 2s por sessao para o smoke test rodar rapido
    atualizar_configuracao(
        tempo_foco=0,           # 0 min = 0s (usaremos monkey-patch abaixo)
        tempo_descanso=0,
        tempo_descanso_longo=0,
        transicao_automatica=False,
    )

    engine = PomodoroEngine()

    # Monkey-patch: sobrescreve o calculo de segundos para usar 2s fixos
    # (evita depender de minutos reais nos testes)
    def _segundos_fixos(estado: PomodoroState) -> int:
        return 2 if estado != PomodoroState.PARADO else 0

    engine._segundos_para_estado = _segundos_fixos  # type: ignore[method-assign]

    eventos: list[str] = []

    def on_tick(seg: int) -> None:
        pass  # silencioso para nao poluir a saida

    def on_state_change(estado: PomodoroState) -> None:
        label = STATE_LABEL[estado]
        print(f"  >> Estado mudou para: {label}")
        eventos.append(estado.name)

    def on_session_end(estado: PomodoroState) -> None:
        label = STATE_LABEL[estado]
        print(f"  ** Sessao concluida: {label} | ciclos_foco={engine.ciclos_foco}")

    engine.on_tick = on_tick
    engine.on_state_change = on_state_change
    engine.on_session_end = on_session_end

    # Simula 4 sessoes de foco + os descansos correspondentes
    # ciclo: FOCO -> DESCANSO_CURTO x3, depois FOCO -> DESCANSO_LONGO
    num_sessoes = CICLO_FOCO * 2  # 4 focos + 4 descansos
    for i in range(num_sessoes):
        estado_atual = engine.state
        print(f"\n  [Ciclo {i+1}] Iniciando de estado={estado_atual.name}")
        await engine.start(proximo_estado=None if i == 0 else None)
        # Aguarda o timer terminar naturalmente (vai para PARADO)
        while engine.state != PomodoroState.PARADO:
            await asyncio.sleep(0.05)
        print(f"  [Ciclo {i+1}] Timer parou. ciclos_foco={engine.ciclos_foco}")

    print(f"\n  Estados visitados: {' -> '.join(eventos)}")
    print("  Cenario 1 OK!")


# =========================================================================
# Cenario 2 - Transicao automatica
# =========================================================================

async def cenario_automatico() -> None:
    cabecalho("CENARIO 2 - Transicao AUTOMATICA (3 ticks por estado)")

    atualizar_configuracao(transicao_automatica=True)

    engine = PomodoroEngine()

    def _segundos_fixos(estado: PomodoroState) -> int:
        return 2 if estado != PomodoroState.PARADO else 0

    engine._segundos_para_estado = _segundos_fixos  # type: ignore[method-assign]

    estados_visitados: list[str] = []
    sessoes_concluidas: list[str] = []

    def on_state_change(estado: PomodoroState) -> None:
        label = STATE_LABEL[estado]
        print(f"  >> Auto-transicao para: {label}")
        estados_visitados.append(label)

    def on_session_end(estado: PomodoroState) -> None:
        sessoes_concluidas.append(STATE_LABEL[estado])

    engine.on_state_change = on_state_change
    engine.on_session_end = on_session_end

    await engine.start()

    # Aguarda 5 transicoes completas (cada uma leva ~2s)
    await asyncio.sleep(12)
    await engine.stop()

    print(f"\n  Estados visitados : {' -> '.join(estados_visitados)}")
    print(f"  Sessoes concluidas: {sessoes_concluidas}")
    print("  Cenario 2 OK!")


# =========================================================================
# Cenario 3 - Pause / Resume
# =========================================================================

async def cenario_pause_resume() -> None:
    cabecalho("CENARIO 3 - Pause / Resume")

    atualizar_configuracao(transicao_automatica=False)

    engine = PomodoroEngine()

    def _segundos_fixos(estado: PomodoroState) -> int:
        return 10 if estado != PomodoroState.PARADO else 0

    engine._segundos_para_estado = _segundos_fixos  # type: ignore[method-assign]

    ticks: list[int] = []

    def on_tick(seg: int) -> None:
        ticks.append(seg)

    engine.on_tick = on_tick

    await engine.start()
    await asyncio.sleep(2)          # deixa rodar ~2 segundos

    print(f"  Pausando... restam {engine.segundos_restantes}s")
    await engine.pause()
    # Cede o controle para que o loop interno processe o evento de pausa
    await asyncio.sleep(0.25)
    antes = engine.segundos_restantes

    await asyncio.sleep(2)          # 2s pausado - contador nao deve mexer
    depois = engine.segundos_restantes

    assert antes == depois, f"FALHOU: {antes} != {depois} (timer nao pausou!)"
    print(f"  Pausado por 2s: restavam {antes}s antes e {depois}s depois (OK)")

    await engine.resume()
    print("  Retomando...")
    await asyncio.sleep(1)
    print(f"  Restam agora {engine.segundos_restantes}s")
    await engine.stop()

    print("  Cenario 3 OK!")


# =========================================================================
# Cenario 4 - Metodo avancar()
# =========================================================================

async def cenario_avancar() -> None:
    cabecalho("CENARIO 4 - Avanco manual com avancar()")

    atualizar_configuracao(transicao_automatica=False)

    engine = PomodoroEngine()

    def _segundos_fixos(estado: PomodoroState) -> int:
        return 30 if estado != PomodoroState.PARADO else 0

    engine._segundos_para_estado = _segundos_fixos  # type: ignore[method-assign]

    estados: list[str] = []

    def on_state_change(estado: PomodoroState) -> None:
        label = STATE_LABEL[estado]
        print(f"  >> Estado: {label}")
        estados.append(label)

    engine.on_state_change = on_state_change

    await engine.start()
    print(f"  Estado inicial: {STATE_LABEL[engine.state]}")
    await asyncio.sleep(0.2)

    for i in range(3):
        await engine.avancar()
        print(f"  Avanco {i+1}: {STATE_LABEL[engine.state]}")
        await asyncio.sleep(0.2)

    await engine.stop()
    print(f"  Estados visitados: {' -> '.join(estados)}")
    print("  Cenario 4 OK!")


# =========================================================================
# Main
# =========================================================================

async def main() -> None:
    print("\nInicializando banco...")
    init_db()

    # Configura sessoes de 1min para nao poluir o banco com dados reais
    # O monkey-patch nos cenarios acima sobrescreve isso
    atualizar_configuracao(
        tempo_foco=1,
        tempo_descanso=1,
        tempo_descanso_longo=1,
        transicao_automatica=False,
    )

    await cenario_manual()
    await cenario_automatico()
    await cenario_pause_resume()
    await cenario_avancar()

    print(f"\n{'='*55}")
    print("  Todos os cenarios passaram! Timer OK!")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    asyncio.run(main())
