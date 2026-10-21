"""
pommo/database/connection.py
----------------------------
Gerencia a conexao SQLite e inicializa o schema do banco de dados.
O arquivo do banco fica em ~/.local/share/pomocli/pomocli.db (XDG-compliant).
"""

import os
import shutil
import sqlite3
from pathlib import Path


# =========================================================================
# Localizacao do banco
# =========================================================================

def _db_path() -> Path:
    """
    Retorna o caminho absoluto do arquivo SQLite, criando o diretorio se necessario.
    Segue a especificacao XDG Base Directory para sistemas Linux/Arch.
    Padrao: ~/.local/share/pomocli/pomocli.db
    """
    xdg_data = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(xdg_data) if xdg_data else (Path.home() / ".local" / "share")
    data_dir = base_dir / "pomocli"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file = data_dir / "pomocli.db"

    # Migra dados legados (pommo.db) caso existam e o novo banco ainda nao exista
    legacy_db = base_dir / "pommo" / "pommo.db"
    if not db_file.exists() and legacy_db.exists():
        try:
            shutil.copy2(legacy_db, db_file)
        except Exception:
            pass

    return db_file


# Conexão 

def get_connection() -> sqlite3.Connection:
    """
    Abre (ou reutiliza) a conexão com o banco SQLite.

    Row factory configurada para sqlite3.Row, permitindo acesso por nome
    de coluna nos resultados.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    # Ativa suporte a chaves estrangeiras (desabilitado por padrão no SQLite)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# Schema / Migrations 

_SCHEMA_SQL = """
-- Tabela de Projetos
CREATE TABLE IF NOT EXISTS projetos (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                 TEXT    NOT NULL,
    categoria            TEXT,
    pomodoros_estimados  INTEGER NOT NULL DEFAULT 0
);

-- Tabela de Sessões
CREATE TABLE IF NOT EXISTS sessoes (
    id               INTEGER  PRIMARY KEY AUTOINCREMENT,
    projeto_id       INTEGER  REFERENCES projetos(id) ON DELETE SET NULL,
    duracao_minutos  INTEGER  NOT NULL,
    tipo             TEXT     NOT NULL CHECK(tipo IN ('foco', 'descanso_curto', 'descanso_longo')),
    data_hora        DATETIME NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Tabela de Configurações (sempre uma única linha; id fixo = 1)
CREATE TABLE IF NOT EXISTS configuracoes (
    id                    INTEGER PRIMARY KEY CHECK(id = 1),
    tempo_foco            INTEGER NOT NULL DEFAULT 25,
    tempo_descanso        INTEGER NOT NULL DEFAULT 5,
    tempo_descanso_longo  INTEGER NOT NULL DEFAULT 15,
    transicao_automatica  INTEGER NOT NULL DEFAULT 0   -- 0 = False, 1 = True
);

-- Garante a existência do único registro de configuração
INSERT OR IGNORE INTO configuracoes (id) VALUES (1);
"""


def init_db() -> None:
    """Cria as tabelas (se não existirem) e popula configuração padrão."""
    with get_connection() as conn:
        conn.executescript(_SCHEMA_SQL)
