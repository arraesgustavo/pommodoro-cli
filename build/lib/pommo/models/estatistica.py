"""
src/models/estatistica.py
--------------------------
Dataclass para agregacao de metricas de produtividade por projeto.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EstatisticaProjeto:
    """
    Agregacao de estatisticas de foco por projeto.

    Atributos:
        projeto_id:           ID unico do projeto.
        nome:                 Nome do projeto.
        categoria:            Categoria/tag atribuida ao projeto.
        pomodoros_estimados:  Meta de pomodoros estimada.
        pomodoros_realizados: Quantidade real de sessoes de foco concluidas.
        tempo_foco_minutos:   Tempo total em minutos dedicados ao projeto.
    """

    projeto_id: int
    nome: str
    categoria: Optional[str]
    pomodoros_estimados: int
    pomodoros_realizados: int
    tempo_foco_minutos: int

    @property
    def tempo_formatado(self) -> str:
        """Formata o tempo total em horas e minutos (ex: '2h 15m' ou '45m')."""
        horas = self.tempo_foco_minutos // 60
        minutos = self.tempo_foco_minutos % 60
        if horas > 0:
            return f"{horas}h {minutos:02d}m"
        return f"{minutos}m"

    @property
    def progresso_percentual(self) -> float:
        """Calcula o percentual atingido em relacao ao estimado."""
        if self.pomodoros_estimados <= 0:
            return 0.0
        return min(100.0, (self.pomodoros_realizados / self.pomodoros_estimados) * 100.0)

    @classmethod
    def from_row(cls, row) -> "EstatisticaProjeto":
        """Instancia a partir de uma linha retornada pelo sqlite3."""
        return cls(
            projeto_id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            pomodoros_estimados=row["pomodoros_estimados"],
            pomodoros_realizados=row["pomodoros_realizados"],
            tempo_foco_minutos=row["tempo_foco_minutos"],
        )
