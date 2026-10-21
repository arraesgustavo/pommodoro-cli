"""
src/alerts/__init__.py
-----------------------
Pacote de alertas do pommo.
Exporta a interface publica: AlertManager e as funcoes de disparo.
"""

from .notifications import (
    AlertManager,
    tocar_som,
    notificar_desktop,
    alertar_fim_sessao,
)

__all__ = [
    "AlertManager",
    "tocar_som",
    "notificar_desktop",
    "alertar_fim_sessao",
]
