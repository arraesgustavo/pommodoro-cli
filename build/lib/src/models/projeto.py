"""
pommo/models/projeto.py
Dataclass leve representando um Projeto.
Não usa nenhum ORM externo – apenas dataclass + sqlite3 Row.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Projeto:
    nome: str
    categoria: Optional[str] = None
    pomodoros_estimados: int = 0
    id: Optional[int] = field(default=None, repr=False)

    # Construtor alternativo 

    @classmethod
    def from_row(cls, row) -> "Projeto":
        """Constrói um Projeto a partir de um sqlite3.Row."""
        return cls(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            pomodoros_estimados=row["pomodoros_estimados"],
        )

    def __str__(self) -> str:
        cat = f" [{self.categoria}]" if self.categoria else ""
        return f"#{self.id} {self.nome}{cat} (~{self.pomodoros_estimados} pomodoros)"
