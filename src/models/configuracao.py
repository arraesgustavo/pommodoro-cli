"""
pommo/models/configuracao.py
Dataclass leve representando as Configurações globais do pommo.
Há sempre apenas uma linha (id = 1) na tabela correspondente.
"""

from dataclasses import dataclass


@dataclass
class Configuracao:
    tempo_foco: int = 25
    tempo_descanso: int = 5
    tempo_descanso_longo: int = 15
    transicao_automatica: bool = False

    @classmethod
    def from_row(cls, row) -> "Configuracao":
        """Constrói uma Configuracao a partir de um sqlite3.Row."""
        return cls(
            tempo_foco=row["tempo_foco"],
            tempo_descanso=row["tempo_descanso"],
            tempo_descanso_longo=row["tempo_descanso_longo"],
            transicao_automatica=bool(row["transicao_automatica"]),
        )

    def __str__(self) -> str:
        auto = "sim" if self.transicao_automatica else "não"
        return (
            f"Foco: {self.tempo_foco}min | "
            f"Descanso: {self.tempo_descanso}min | "
            f"Descanso longo: {self.tempo_descanso_longo}min | "
            f"Transição automática: {auto}"
        )
