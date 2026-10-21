"""
pommo/models/sessao.py
Dataclass leve representando uma Sessão de Pomodoro.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

TipoSessao = Literal["foco", "descanso_curto", "descanso_longo"]


@dataclass
class Sessao:
    duracao_minutos: int
    tipo: TipoSessao
    projeto_id: Optional[int] = None
    data_hora: Optional[datetime] = None
    id: Optional[int] = field(default=None, repr=False)

    @classmethod
    def from_row(cls, row) -> "Sessao":
        """Constrói uma Sessao a partir de um sqlite3.Row."""
        raw_dt = row["data_hora"]
        if isinstance(raw_dt, str):
            data_hora = datetime.fromisoformat(raw_dt)
        else:
            data_hora = raw_dt

        return cls(
            id=row["id"],
            projeto_id=row["projeto_id"],
            duracao_minutos=row["duracao_minutos"],
            tipo=row["tipo"],
            data_hora=data_hora,
        )

    def __str__(self) -> str:
        dt_str = self.data_hora.strftime("%Y-%m-%d %H:%M") if self.data_hora else "?"
        proj = f" | projeto #{self.projeto_id}" if self.projeto_id else ""
        return f"[{dt_str}] {self.tipo} — {self.duracao_minutos} min{proj}"
