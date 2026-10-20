"""
pommo/database/__init__.py
──────────────────────────
Re-exporta as funções públicas do módulo de banco de dados
para que outros módulos possam importar de `pommo.database` diretamente.
"""

from .connection import get_connection, init_db
from .repository import (
    # Projetos
    criar_projeto,
    listar_projetos,
    buscar_projeto,
    deletar_projeto,
    # Sessões
    registrar_sessao,
    listar_sessoes,
    # Configurações
    ler_configuracao,
    atualizar_configuracao,
)

__all__ = [
    "get_connection",
    "init_db",
    "criar_projeto",
    "listar_projetos",
    "buscar_projeto",
    "deletar_projeto",
    "registrar_sessao",
    "listar_sessoes",
    "ler_configuracao",
    "atualizar_configuracao",
]
