"""
src/timer/states.py
--------------------
Define o Enum de estados da maquina de estados do Pomodoro
e utilitarios relacionados.
"""

from enum import Enum, auto


class PomodoroState(Enum):
    """
    Estados possiveis do motor do Pomodoro.

    PARADO          - Timer parado ou aguardando acao do usuario.
    FOCO            - Sessao de foco ativa.
    DESCANSO_CURTO  - Descanso curto ativo (entre sessoes de foco comuns).
    DESCANSO_LONGO  - Descanso longo ativo (apos cada 4 sessoes de foco).
    """

    PARADO = auto()
    FOCO = auto()
    DESCANSO_CURTO = auto()
    DESCANSO_LONGO = auto()


# Mapeamento estado -> tipo de sessao para gravar no banco
STATE_TO_TIPO: dict[PomodoroState, str] = {
    PomodoroState.FOCO: "foco",
    PomodoroState.DESCANSO_CURTO: "descanso_curto",
    PomodoroState.DESCANSO_LONGO: "descanso_longo",
}

# Rotulos amigaveis para exibicao na TUI
STATE_LABEL: dict[PomodoroState, str] = {
    PomodoroState.PARADO: "PARADO",
    PomodoroState.FOCO: "FOCO",
    PomodoroState.DESCANSO_CURTO: "DESCANSO CURTO",
    PomodoroState.DESCANSO_LONGO: "DESCANSO LONGO",
}
