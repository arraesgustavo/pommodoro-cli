"""
scripts/smoke_test_alerts.py
-----------------------------
Smoke test do modulo de alertas (Etapa 3).

Testa de forma isolada:
  1. notificar_desktop() - dispara um pop-up real via notify-send
  2. tocar_som()         - toca os 4 arquivos de audio via paplay
  3. alertar_fim_sessao()- dispara pop-up + som para cada estado
  4. AlertManager        - integra com um PomodoroEngine falso (mock)

Uso:
    python scripts/smoke_test_alerts.py [--sem-som] [--sem-desktop]

Flags:
    --sem-som       Pula todos os testes de audio
    --sem-desktop   Pula todos os testes de pop-up
"""

import sys
import time
import logging

# Adiciona a raiz do projeto ao path para imports relativos funcionarem
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alerts.notifications import (
    AlertManager,
    ASSETS_DIR,
    alertar_fim_sessao,
    notificar_desktop,
    tocar_som,
)
from src.timer.states import PomodoroState

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

# ---------------------------------------------------------------------------
# Flags de controle
# ---------------------------------------------------------------------------
TESTAR_SOM     = "--sem-som"     not in sys.argv
TESTAR_DESKTOP = "--sem-desktop" not in sys.argv

SEP = "=" * 60


def titulo(texto: str) -> None:
    print(f"\n{SEP}\n  {texto}\n{SEP}")


# ---------------------------------------------------------------------------
# 1. Notificacao de desktop
# ---------------------------------------------------------------------------
titulo("1. notificar_desktop()")
if TESTAR_DESKTOP:
    print("  Enviando pop-up de teste...")
    notificar_desktop(
        "[ POMMO ] Smoke Test",
        "Sistema de notificacoes funcionando!",
        urgencia="low",
        timeout_ms=4000,
    )
    print("  Pop-up enviado. Verifique seu ambiente de notificacoes.")
else:
    print("  [PULADO] --sem-desktop ativo.")


# ---------------------------------------------------------------------------
# 2. Tocar sons individualmente
# ---------------------------------------------------------------------------
titulo("2. tocar_som() - todos os arquivos de audio")
if TESTAR_SOM:
    sons = list(ASSETS_DIR.glob("*.wav"))
    if not sons:
        print("  [AVISO] Nenhum .wav encontrado em:", ASSETS_DIR)
        print("  Execute: python scripts/gerar_assets.py")
    else:
        for wav in sorted(sons):
            print(f"  Tocando: {wav.name}")
            tocar_som([wav])
            time.sleep(0.1)  # pequena pausa entre sons
        print("  Sons tocados com sucesso.")
else:
    print("  [PULADO] --sem-som ativo.")


# ---------------------------------------------------------------------------
# 3. alertar_fim_sessao() para cada estado
# ---------------------------------------------------------------------------
titulo("3. alertar_fim_sessao() - todos os estados")
estados_testados = [
    PomodoroState.FOCO,
    PomodoroState.DESCANSO_CURTO,
    PomodoroState.DESCANSO_LONGO,
]
for estado in estados_testados:
    print(f"  Alertando fim de: {estado.name}")
    alertar_fim_sessao(
        estado,
        som=TESTAR_SOM,
        desktop=TESTAR_DESKTOP,
    )
    time.sleep(0.2)  # pausa para sequenciar os alertas

print("  alertar_fim_sessao() concluido para todos os estados.")


# ---------------------------------------------------------------------------
# 4. AlertManager com engine mock
# ---------------------------------------------------------------------------
titulo("4. AlertManager.conectar() com engine mock")


class EngineStub:
    """Stub minimo que simula PomodoroEngine apenas para testes de callback."""

    on_session_end = None


# AlertManager so aceita PomodoroEngine real; verificamos o TypeError esperado
stub = EngineStub()
try:
    AlertManager().conectar(stub)
    print("  [FALHOU] Deveria ter levantado TypeError para tipo errado!")
    sys.exit(1)
except TypeError as exc:
    print(f"  [OK] TypeError esperado para tipo invalido: {exc}")

# Importa o engine real e conecta sem iniciar asyncio
from src.timer.engine import PomodoroEngine  # noqa: E402

engine_real = PomodoroEngine()

# Registra um callback pre-existente para verificar o encadeamento
log_chamadas: list[PomodoroState] = []
engine_real.on_session_end = lambda s: log_chamadas.append(s)

mgr = AlertManager(som=TESTAR_SOM, desktop=TESTAR_DESKTOP, volume=0.8)
mgr.conectar(engine_real)
print(f"  AlertManager conectado: {mgr}")

# Simula a chamada do callback como o engine faria
print("  Simulando on_session_end(FOCO)...")
engine_real.on_session_end(PomodoroState.FOCO)

assert PomodoroState.FOCO in log_chamadas, "Callback pre-existente nao foi chamado!"
print(f"  [OK] Callback anterior encadeado corretamente. log={log_chamadas}")

# Desconecta e verifica
mgr.desconectar(engine_real)
assert engine_real.on_session_end is None, "on_session_end deveria ser None apos desconectar!"
print("  [OK] desconectar() funcionou corretamente.")


# ---------------------------------------------------------------------------
# Resultado final
# ---------------------------------------------------------------------------
titulo("SMOKE TEST CONCLUIDO COM SUCESSO")
print("  Modulo src/alerts/notifications.py operacional.\n")
