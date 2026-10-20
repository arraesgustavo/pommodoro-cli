"""
src/alerts/notifications.py
----------------------------
Sistema de alertas do pommo: notificacoes de desktop e sons de aviso.

Responsabilidades:
  - Disparar pop-ups nativos via notify-send (libnotify)
  - Tocar arquivos .wav via paplay (PulseAudio/PipeWire)
  - Mapear cada PomodoroState para seu par (mensagem, arquivo de som)
  - Expor AlertManager para ser conectado aos callbacks do PomodoroEngine

Dependencias externas (nativas do Arch Linux):
  - notify-send  -> pacote libnotify
  - paplay       -> pacote libpulse / pipewire-pulse

Uso basico:
    from src.alerts import AlertManager
    from src.timer.engine import PomodoroEngine

    engine = PomodoroEngine()
    mgr = AlertManager()
    mgr.conectar(engine)          # registra os callbacks automaticamente
    await engine.start()
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from ..timer.states import PomodoroState

logger = logging.getLogger(__name__)

# =========================================================================
# Caminhos dos assets de audio
# =========================================================================

# Raiz do projeto: sobe 3 niveis a partir deste arquivo
# src/alerts/notifications.py -> src/alerts -> src -> raiz
_PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = _PROJETO_RAIZ / "assets" / "sounds"

# Mapeamento estado -> arquivo de som
_SOM_POR_ESTADO: dict[PomodoroState, list[Path]] = {
    PomodoroState.FOCO: [
        ASSETS_DIR / "foco_fim.wav",
        ASSETS_DIR / "foco_fim_2.wav",
    ],
    PomodoroState.DESCANSO_CURTO: [
        ASSETS_DIR / "descanso_curto_fim.wav",
    ],
    PomodoroState.DESCANSO_LONGO: [
        ASSETS_DIR / "descanso_longo_fim.wav",
    ],
}

# =========================================================================
# Mapeamento estado -> textos da notificacao desktop
# =========================================================================

# Cada entrada: (titulo, corpo, urgencia)
# urgencia: "low" | "normal" | "critical"  (flag --urgency do notify-send)
_NOTIF_POR_ESTADO: dict[PomodoroState, tuple[str, str, str]] = {
    PomodoroState.FOCO: (
        "[ POMMO ] Foco Encerrado",
        "Sessao de foco concluida. Hora de respirar.",
        "normal",
    ),
    PomodoroState.DESCANSO_CURTO: (
        "[ POMMO ] Descanso Encerrado",
        "Descanso curto finalizado. Prepare-se para focar.",
        "normal",
    ),
    PomodoroState.DESCANSO_LONGO: (
        "[ POMMO ] Descanso Longo Encerrado",
        "Ciclo completo! De volta ao foco.",
        "normal",
    ),
}

# Tempo em milissegundos que o pop-up fica visivelna tela
_NOTIF_TIMEOUT_MS = 6000

# Icone padrao usado no pop-up (nome XDG ou caminho absoluto)
_NOTIF_ICON = "clock"


# =========================================================================
# Funcoes de baixo nivel
# =========================================================================


def notificar_desktop(
    titulo: str,
    corpo: str,
    urgencia: str = "normal",
    timeout_ms: int = _NOTIF_TIMEOUT_MS,
    icon: str = _NOTIF_ICON,
) -> None:
    """
    Dispara um pop-up de notificacao usando notify-send.

    Falha silenciosamente se o notify-send nao estiver disponivel ou se
    nao houver um servidor de notificacoes rodando (ex: ambiente sem GUI).

    Args:
        titulo:     Titulo exibido no pop-up.
        corpo:      Texto do corpo da notificacao.
        urgencia:   Nivel de urgencia: "low", "normal" ou "critical".
        timeout_ms: Tempo de exibicao em milissegundos.
        icon:       Nome do icone XDG ou caminho para arquivo .png/.svg.
    """
    cmd = [
        "notify-send",
        "--urgency", urgencia,
        "--expire-time", str(timeout_ms),
        "--icon", icon,
        titulo,
        corpo,
    ]
    try:
        subprocess.run(
            cmd,
            check=False,           # nao levanta excecao em codigo != 0
            timeout=3,             # evita travar se o dbus demorar
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.debug("Notificacao enviada: %s - %s", titulo, corpo)
    except FileNotFoundError:
        logger.warning("notify-send nao encontrado. Instale o pacote libnotify.")
    except subprocess.TimeoutExpired:
        logger.warning("notify-send excedeu o timeout.")
    except Exception as exc:
        logger.error("Erro inesperado ao enviar notificacao: %s", exc)


def tocar_som(arquivos: list[Path], *, volume: float = 1.0) -> None:
    """
    Toca uma sequencia de arquivos de audio usando paplay.

    Os arquivos sao tocados em ordem, um apos o outro (sequencial).
    Falha silenciosamente se paplay nao estiver disponivel.

    Args:
        arquivos: Lista de Paths para arquivos .wav/.ogg a tocar em sequencia.
        volume:   Volume relativo (0.0 a 1.0). Convertido para percentual
                  do volume da sink padrao via --volume (0-65536).
    """
    # paplay usa volume linear 0-65536 (65536 = 100%)
    vol_linear = int(max(0.0, min(1.0, volume)) * 65536)

    for path in arquivos:
        if not path.exists():
            logger.warning("Arquivo de som nao encontrado: %s", path)
            continue
        cmd = [
            "paplay",
            "--volume", str(vol_linear),
            str(path),
        ]
        try:
            subprocess.run(
                cmd,
                check=False,
                timeout=10,            # cada beep e curto; timeout generoso
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.debug("Som tocado: %s", path.name)
        except FileNotFoundError:
            logger.warning("paplay nao encontrado. Instale pipewire-pulse ou libpulse.")
            return                     # sem paplay nao adianta tentar os proximos
        except subprocess.TimeoutExpired:
            logger.warning("paplay excedeu o timeout para: %s", path.name)
        except Exception as exc:
            logger.error("Erro inesperado ao tocar som %s: %s", path.name, exc)


# =========================================================================
# Funcao de alto nivel
# =========================================================================


def alertar_fim_sessao(
    estado_concluido: PomodoroState,
    *,
    som: bool = True,
    desktop: bool = True,
    volume: float = 1.0,
) -> None:
    """
    Dispara o alerta completo (pop-up + som) ao fim de uma sessao.

    Esta funcao e o ponto de integracao direta com o callback on_session_end
    do PomodoroEngine.

    Args:
        estado_concluido: Estado que acabou de ser concluido.
        som:              Se True, toca o(s) arquivo(s) de audio associados.
        desktop:          Se True, exibe a notificacao no desktop.
        volume:           Volume do audio (0.0 a 1.0).
    """
    if estado_concluido is PomodoroState.PARADO:
        return  # PARADO nao corresponde a fim de sessao real

    if desktop:
        titulo, corpo, urgencia = _NOTIF_POR_ESTADO.get(
            estado_concluido,
            ("[ POMMO ]", "Sessao encerrada.", "normal"),
        )
        notificar_desktop(titulo, corpo, urgencia=urgencia)

    if som:
        arquivos = _SOM_POR_ESTADO.get(estado_concluido, [])
        if arquivos:
            tocar_som(arquivos, volume=volume)


# =========================================================================
# AlertManager - integracao com PomodoroEngine
# =========================================================================


class AlertManager:
    """
    Gerenciador de alertas que se conecta ao PomodoroEngine via callbacks.

    Uso:
        engine = PomodoroEngine()
        mgr = AlertManager(som=True, desktop=True, volume=0.9)
        mgr.conectar(engine)
        await engine.start()

    O AlertManager preserva qualquer callback on_session_end ja registrado
    no engine: ele encadeia o alerta apos o callback existente.

    Atributos configuráveis:
        som      - Habilita alertas sonoros.
        desktop  - Habilita pop-ups de desktop.
        volume   - Volume do audio (0.0 a 1.0).
    """

    def __init__(
        self,
        *,
        som: bool = True,
        desktop: bool = True,
        volume: float = 1.0,
    ) -> None:
        self.som: bool = som
        self.desktop: bool = desktop
        self.volume: float = volume
        self._engine_ref: Optional[object] = None  # ref fraca para debug

    # -----------------------------------------------------------------
    # Conexao com o engine
    # -----------------------------------------------------------------

    def conectar(self, engine: object) -> None:
        """
        Registra os callbacks de alerta no PomodoroEngine fornecido.

        Encadeia o alerta com qualquer on_session_end ja registrado,
        garantindo que nenhum callback pre-existente seja perdido.

        Args:
            engine: Instancia de PomodoroEngine (tipagem generica para
                    evitar importacao circular; verificada em runtime).
        """
        # Importacao tardia para evitar ciclo de importacao
        from ..timer.engine import PomodoroEngine  # noqa: PLC0415

        if not isinstance(engine, PomodoroEngine):
            raise TypeError(
                f"AlertManager.conectar() requer um PomodoroEngine, "
                f"recebeu {type(engine).__name__}."
            )

        self._engine_ref = engine
        callback_anterior = engine.on_session_end  # pode ser None

        def _ao_fim_da_sessao(estado: PomodoroState) -> None:
            # Primeiro executa o callback anterior (ex: log, TUI update)
            if callback_anterior is not None:
                callback_anterior(estado)
            # Depois dispara o alerta
            alertar_fim_sessao(
                estado,
                som=self.som,
                desktop=self.desktop,
                volume=self.volume,
            )

        engine.on_session_end = _ao_fim_da_sessao
        logger.debug(
            "AlertManager conectado ao engine. som=%s desktop=%s volume=%.2f",
            self.som,
            self.desktop,
            self.volume,
        )

    def desconectar(self, engine: object) -> None:
        """
        Remove o callback de alerta do engine, restaurando None.

        Nota: se havia um callback encadeado pre-existente, ele tambem
        sera removido (limitacao do encadeamento por closure).
        Prefira nao reconectar o mesmo engine apos desconectar.

        Args:
            engine: Instancia de PomodoroEngine previamente conectada.
        """
        from ..timer.engine import PomodoroEngine  # noqa: PLC0415

        if not isinstance(engine, PomodoroEngine):
            raise TypeError(
                f"AlertManager.desconectar() requer um PomodoroEngine, "
                f"recebeu {type(engine).__name__}."
            )
        engine.on_session_end = None
        self._engine_ref = None
        logger.debug("AlertManager desconectado do engine.")

    def __repr__(self) -> str:
        return (
            f"<AlertManager som={self.som} desktop={self.desktop} "
            f"volume={self.volume:.2f}>"
        )
