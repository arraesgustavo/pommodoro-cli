"""
src/timer/engine.py
--------------------
Motor principal do Pomodoro.

Responsabilidades:
  - Gerenciar a maquina de estados (PARADO / FOCO / DESCANSO_*)
  - Contar o tempo restante de cada sessao via asyncio
  - Controlar o ciclo de 4 sessoes de foco -> descanso longo
  - Disparar callbacks de tick e de mudanca de estado
  - Registrar sessoes concluidas no banco de dados
  - Expor metodos de controle: start(), pause(), resume(), stop(), avancar()

Uso basico (sem TUI):

    import asyncio
    from src.timer.engine import PomodoroEngine

    async def main():
        engine = PomodoroEngine()
        engine.on_tick = lambda seg: print(f"Restam {seg}s")
        engine.on_state_change = lambda s: print(f"Novo estado: {s}")
        await engine.start()          # inicia sessao de FOCO
        await asyncio.sleep(99999)    # aguarda (TUI/CLI faria isso)

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from ..database.repository import ler_configuracao, registrar_sessao
from ..models.configuracao import Configuracao
from .states import STATE_LABEL, STATE_TO_TIPO, PomodoroState

logger = logging.getLogger(__name__)

# Tipo dos callbacks expostos ao exterior
OnTickCallback = Callable[[int], None]        # recebe segundos_restantes
OnStateChangeCallback = Callable[[PomodoroState], None]

# Quantas sessoes de foco antes de um descanso longo
CICLO_FOCO = 4


class PomodoroEngine:
    """
    Motor asyncio do timer Pomodoro.

    Atributos publicos (definidos pelo chamador antes de start()):
        on_tick            - chamado a cada segundo com os segundos restantes.
        on_state_change    - chamado quando o estado muda.
        on_session_end     - chamado ao concluir uma sessao (antes da transicao).
        projeto_id         - FK opcional para vincular sessoes ao projeto ativo.

    Atributos de leitura:
        state                 - estado atual (PomodoroState).
        segundos_restantes    - segundos restantes no ciclo atual.
        ciclos_foco           - numero de sessoes de foco concluidas (0-3).
        pausado               - True se o timer estiver pausado.
        proximo_estado_pendente - proximo estado aguardando inicio manual
                                  (transicao manual) ou None.
    """

    # =========================================================================
    # Inicializacao
    # =========================================================================

    def __init__(self) -> None:
        # -- Callbacks (podem ser substituidos antes de start()) --
        self.on_tick: Optional[OnTickCallback] = None
        self.on_state_change: Optional[OnStateChangeCallback] = None
        self.on_session_end: Optional[OnStateChangeCallback] = None

        # -- Projeto ativo (opcional) --
        self.projeto_id: Optional[int] = None

        # -- Estado interno --
        self._state: PomodoroState = PomodoroState.PARADO
        self._segundos_restantes: int = 0
        self._ciclos_foco: int = 0
        self._pausado: bool = False

        # Proximo estado aguardando inicio manual (transicao manual).
        # Fica preenchido quando uma sessao termina com transicao_automatica=False.
        self._proximo_estado_pendente: Optional[PomodoroState] = None

        # Duracao total da sessao em andamento, capturada ao entrar no _loop.
        # Usada para registrar a sessao mesmo que a config mude no meio do ciclo.
        self._duracao_sessao_seg: int = 0

        # -- Controle de concorrencia asyncio --
        self._task: Optional[asyncio.Task] = None
        self._pause_event: asyncio.Event = asyncio.Event()
        self._pause_event.set()  # nao pausado por padrao

        # -- Configuracao (carregada na inicializacao e recarregada a cada ciclo) --
        self._config: Configuracao = Configuracao()

    # =========================================================================
    # Propriedades de leitura
    # =========================================================================

    @property
    def state(self) -> PomodoroState:
        return self._state

    @property
    def segundos_restantes(self) -> int:
        return self._segundos_restantes

    @property
    def ciclos_foco(self) -> int:
        return self._ciclos_foco

    @property
    def pausado(self) -> bool:
        return self._pausado

    @property
    def proximo_estado_pendente(self) -> Optional[PomodoroState]:
        """
        Proximo estado aguardando inicio manual ou None.

        Preenchido quando uma sessao termina com transicao_automatica=False.
        A TUI exibe o prompt "Aperte Enter para iniciar ..." com base nele.
        """
        return self._proximo_estado_pendente

    # =========================================================================
    # API publica de controle
    # =========================================================================

    async def start(self, proximo_estado: Optional[PomodoroState] = None) -> None:
        """
        Inicia o timer.

        Se ja houver uma task rodando ela sera cancelada antes.

        Args:
            proximo_estado: Forca um estado especifico na inicializacao.
                            None usa o estado pendente (transicao manual),
                            se existir; caso contrario comeca em FOCO.
        """
        await self._cancelar_task()
        self._recarregar_config()

        # Transicao manual: se ha um estado pendente, ele e o proximo a rodar.
        if proximo_estado is None:
            proximo_estado = self._proximo_estado_pendente
        self._proximo_estado_pendente = None

        estado_inicial = proximo_estado or PomodoroState.FOCO
        self._segundos_restantes = self._segundos_para_estado(estado_inicial)
        self._mudar_estado(estado_inicial)
        self._task = asyncio.create_task(self._loop())
        logger.debug("Engine iniciada no estado %s", self._state.name)

    async def pause(self) -> None:
        """Pausa o timer sem alterar o estado nem o tempo restante."""
        if self._state is PomodoroState.PARADO or self._pausado:
            return
        self._pausado = True
        self._pause_event.clear()
        logger.debug("Timer pausado em %ds restantes", self._segundos_restantes)

    async def resume(self) -> None:
        """Retoma um timer pausado de onde parou."""
        if not self._pausado:
            return
        self._pausado = False
        self._pause_event.set()
        logger.debug("Timer retomado")

    async def stop(self) -> None:
        """
        Para completamente o timer e vai para PARADO.

        A sessao em andamento NAO e registrada no banco (foi interrompida).
        Qualquer estado pendente de transicao manual tambem e descartado.
        """
        await self._cancelar_task()
        self._proximo_estado_pendente = None
        self._mudar_estado(PomodoroState.PARADO)
        logger.debug("Timer parado manualmente")

    async def avancar(self) -> None:
        """
        Avanca manualmente para o proximo ciclo.

        Util quando transicao_automatica=False e o usuario quer iniciar
        o proximo bloco sem esperar.

        Se o timer estiver PARADO, inicia o estado pendente (se houver)
        ou um novo ciclo de FOCO.
        Se estiver rodando, cancela o ciclo atual, sem registrar sessao
        e avanca para o proximo estado (FOCO -> DESCANSO_CURTO).
        """
        if self._state is PomodoroState.PARADO:
            await self.start()
            return

        # Cancela o loop atual sem incrementar ciclos_foco
        await self._cancelar_task()
        proximo = self._calcular_proximo_estado(concluiu=False)
        self._recarregar_config()
        self._segundos_restantes = self._segundos_para_estado(proximo)
        self._mudar_estado(proximo)
        self._task = asyncio.create_task(self._loop())
        logger.debug("Avancado manualmente para %s", self._state.name)

    # =========================================================================
    # Loop interno asyncio
    # =========================================================================

    async def _loop(self) -> None:
        """
        Corrotina principal: decrementa o tempo a cada segundo,
        respeitando pausas, e lida com o fim de cada sessao.
        """
        duracao_total_seg = self._segundos_para_estado(self._state)

        # Protecao: duracao 0 (config invalida) causaria um loop infinito
        # de tarefas em transicao automatica.
        if duracao_total_seg <= 0:
            logger.warning(
                "Duracao zero para o estado %s - timer permanece parado.",
                self._state.name,
            )
            self._segundos_restantes = 0
            self._mudar_estado(PomodoroState.PARADO)
            return

        self._duracao_sessao_seg = duracao_total_seg
        self._segundos_restantes = duracao_total_seg

        # Intervalo de amostragem interno (100ms).
        # Menor que 1s para que pause() tome efeito rapidamente sem
        # esperar o sleep inteiro terminar.
        _TICK_SLICE = 0.1
        _SLICES_PER_SEC = int(1.0 / _TICK_SLICE)

        try:
            while self._segundos_restantes > 0:
                # -- Bloqueia aqui se estiver pausado --
                await self._pause_event.wait()

                self._disparar_tick(self._segundos_restantes)

                # Dorme em fatias de 100ms verificando a pausa a cada fatia
                for _ in range(_SLICES_PER_SEC):
                    await asyncio.sleep(_TICK_SLICE)
                    # Se foi pausado no meio do segundo, para de contar
                    if not self._pause_event.is_set():
                        # Aguarda o resume antes de continuar o segundo atual
                        await self._pause_event.wait()

                self._segundos_restantes -= 1

            # Ultimo tick (0 segundos)
            self._disparar_tick(0)
            await self._ao_fim_da_sessao()

        except asyncio.CancelledError:
            # Task cancelada por stop() ou avancar(); nao fazer nada.
            logger.debug("Task cancelada para estado %s", self._state.name)

    async def _ao_fim_da_sessao(self) -> None:
        """
        Executado quando o contador chega a zero naturalmente.

        Registra a sessao no banco, dispara on_session_end e decide o
        proximo estado com base na configuracao transicao_automatica:

          - True  -> transiciona direto (FOCO -> DESCANSO e vice-versa)
                     iniciando a contagem do proximo periodo.
          - False -> guarda o proximo estado pendente, vai para PARADO
                     e espera o usuario iniciar o proximo periodo na TUI.
        """
        estado_concluido = self._state

        # Recarrega a config ANTES de decidir: alteracoes feitas no menu de
        # configuracoes valem ja para a transicao que esta prestes a ocorrer.
        self._recarregar_config()

        # Duracao capturada na entrada do _loop. Fallback para a config atual
        # quando _ao_fim_da_sessao e chamada fora do loop (ex: testes).
        seg_totais = self._duracao_sessao_seg or self._segundos_para_estado(
            estado_concluido
        )
        duracao_min = seg_totais // 60 if seg_totais >= 60 else (1 if seg_totais > 0 else 0)
        tipo = STATE_TO_TIPO.get(estado_concluido)

        # Incrementa contador ANTES de decidir proximo estado
        if estado_concluido is PomodoroState.FOCO:
            self._ciclos_foco = (self._ciclos_foco + 1) % CICLO_FOCO

        # Persiste no banco (somente estados mapeados: nao PARADO)
        if tipo:
            try:
                registrar_sessao(
                    duracao_minutos=duracao_min,
                    tipo=tipo,
                    projeto_id=self.projeto_id,
                )
                logger.info("Sessao '%s' de %dmin registrada.", tipo, duracao_min)
            except Exception as exc:
                logger.error("Erro ao registrar sessao: %s", exc)

        # Notifica o exterior
        if self.on_session_end:
            self.on_session_end(estado_concluido)

        # Decide proximo estado
        proximo = self._calcular_proximo_estado(concluiu=True)

        if self._config.transicao_automatica:
            # Ja prepara o contador do novo estado (evita frame em 00:00)
            # e inicia a contagem do descanso/volta ao foco automaticamente.
            self._segundos_restantes = self._segundos_para_estado(proximo)
            self._mudar_estado(proximo)
            self._task = asyncio.create_task(self._loop())
            logger.debug("Transicao automatica para %s", proximo.name)
        else:
            # Transicao manual: guarda o proximo estado (ex: DESCANSO_CURTO)
            # e vai para PARADO. A TUI exibe o prompt de inicio manual.
            self._proximo_estado_pendente = proximo
            self._segundos_restantes = 0
            self._mudar_estado(PomodoroState.PARADO)
            logger.debug(
                "Transicao manual: aguardando o usuario para iniciar %s",
                proximo.name,
            )

    # =========================================================================
    # Calculos e utilitarios internos
    # =========================================================================

    def _recarregar_config(self) -> None:
        """Busca as configuracoes atuais do banco antes de cada ciclo."""
        try:
            self._config = ler_configuracao()
        except Exception as exc:
            logger.warning("Nao foi possivel carregar config do banco: %s", exc)

    def _segundos_para_estado(self, estado: PomodoroState) -> int:
        """Converte o estado atual em duracao em segundos conforme a config."""
        mapa = {
            PomodoroState.FOCO: self._config.tempo_foco,
            PomodoroState.DESCANSO_CURTO: self._config.tempo_descanso,
            PomodoroState.DESCANSO_LONGO: self._config.tempo_descanso_longo,
        }
        return mapa.get(estado, 0) * 60

    def _calcular_proximo_estado(self, *, concluiu: bool) -> PomodoroState:
        """
        Determina o proximo estado com base no estado atual e no contador de ciclos.

        Args:
            concluiu: True se a sessao terminou naturalmente (contador ja
                      foi atualizado). False se foi interrompida/avancada
                      manualmente (contador NAO deve ser alterado aqui).

        Returns:
            Proximo PomodoroState.
        """
        if self._state is PomodoroState.FOCO:
            # ciclos_foco ja foi incrementado se concluiu=True
            # _ciclos_foco == 0 significa que acabou de fechar um grupo de 4
            if concluiu and self._ciclos_foco == 0:
                return PomodoroState.DESCANSO_LONGO
            return PomodoroState.DESCANSO_CURTO
        # Qualquer tipo de descanso -> proxima e FOCO
        return PomodoroState.FOCO

    def _mudar_estado(self, novo: PomodoroState) -> None:
        """Atualiza o estado e dispara o callback on_state_change."""
        anterior = self._state
        self._state = novo
        if anterior != novo:
            logger.debug("Estado: %s -> %s", anterior.name, novo.name)
            if self.on_state_change:
                self.on_state_change(novo)

    def _disparar_tick(self, segundos_restantes: int) -> None:
        """Dispara o callback on_tick com os segundos restantes."""
        if self.on_tick:
            self.on_tick(segundos_restantes)

    async def _cancelar_task(self) -> None:
        """Cancela a task asyncio em execucao, se houver."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    # =========================================================================
    # Representacao
    # =========================================================================

    def __repr__(self) -> str:
        label = STATE_LABEL.get(self._state, self._state.name)
        pausado = " [PAUSADO]" if self._pausado else ""
        return (
            f"<PomodoroEngine estado={label}{pausado} "
            f"restante={self._segundos_restantes}s "
            f"ciclos_foco={self._ciclos_foco}/{CICLO_FOCO}>"
        )
