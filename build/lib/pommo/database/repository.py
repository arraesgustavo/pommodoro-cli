"""
pommo/database/repository.py
Camada de acesso a dados (Repository Pattern).
Todas as operações de banco passam por aqui – nenhuma SQL vaza para outras camadas.

Projetos  → criar, listar, buscar por id, deletar
Sessões   → registrar, listar (com filtros opcionais)
Config    → ler, atualizar
"""

from __future__ import annotations

from typing import Optional

from .connection import get_connection
from ..models.configuracao import Configuracao
from ..models.estatistica import EstatisticaProjeto
from ..models.projeto import Projeto
from ..models.sessao import Sessao, TipoSessao


# =========================================================================
#  PROJETOS
# =========================================================================

def criar_projeto(
    nome: str,
    categoria: Optional[str] = None,
    pomodoros_estimados: int = 0,
) -> Projeto:
    """
    Insere um novo projeto no banco e retorna o objeto com o id preenchido.

    Args:
        nome: Nome do projeto (obrigatório).
        categoria: Tag/categoria livre (opcional).
        pomodoros_estimados: Estimativa de pomodoros para concluir o projeto.

    Returns:
        Instância de :class:`Projeto` com id atribuído.
    """
    sql = """
        INSERT INTO projetos (nome, categoria, pomodoros_estimados)
        VALUES (?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(sql, (nome, categoria, pomodoros_estimados))
        conn.commit()
        projeto = Projeto(
            id=cursor.lastrowid,
            nome=nome,
            categoria=categoria,
            pomodoros_estimados=pomodoros_estimados,
        )
    return projeto


def listar_projetos() -> list[Projeto]:
    """
    Retorna todos os projetos cadastrados, ordenados pelo id.

    Returns:
        Lista de :class:`Projeto`. Pode ser vazia.
    """
    sql = "SELECT * FROM projetos ORDER BY id"
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
    return [Projeto.from_row(r) for r in rows]


def buscar_projeto(projeto_id: int) -> Optional[Projeto]:
    """
    Retorna o projeto com o id fornecido ou ``None`` se não existir.

    Args:
        projeto_id: Identificador primário do projeto.
    """
    sql = "SELECT * FROM projetos WHERE id = ?"
    with get_connection() as conn:
        row = conn.execute(sql, (projeto_id,)).fetchone()
    return Projeto.from_row(row) if row else None


def deletar_projeto(projeto_id: int) -> bool:
    """
    Remove um projeto pelo id.

    As sessões vinculadas terão ``projeto_id`` setado para NULL (ON DELETE SET NULL).

    Args:
        projeto_id: Identificador primário do projeto.

    Returns:
        ``True`` se alguma linha foi afetada, ``False`` caso contrário.
    """
    sql = "DELETE FROM projetos WHERE id = ?"
    with get_connection() as conn:
        cursor = conn.execute(sql, (projeto_id,))
        conn.commit()
    return cursor.rowcount > 0


# =========================================================================
#  SESSÕES
# =========================================================================

def registrar_sessao(
    duracao_minutos: int,
    tipo: TipoSessao,
    projeto_id: Optional[int] = None,
) -> Sessao:
    """
    Registra uma nova sessão concluída.

    Args:
        duracao_minutos: Duração real da sessão em minutos.
        tipo: Um de ``'foco'``, ``'descanso_curto'`` ou ``'descanso_longo'``.
        projeto_id: FK para :class:`Projeto` (opcional).

    Returns:
        Instância de :class:`Sessao` com id e data_hora preenchidos.

    Raises:
        ValueError: Se ``tipo`` não for um valor válido.
    """
    tipos_validos = {"foco", "descanso_curto", "descanso_longo"}
    if tipo not in tipos_validos:
        raise ValueError(f"Tipo inválido: '{tipo}'. Use um de {tipos_validos}.")

    sql = """
        INSERT INTO sessoes (projeto_id, duracao_minutos, tipo)
        VALUES (?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(sql, (projeto_id, duracao_minutos, tipo))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sessoes WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return Sessao.from_row(row)


def listar_sessoes(
    projeto_id: Optional[int] = None,
    tipo: Optional[TipoSessao] = None,
    limite: int = 50,
) -> list[Sessao]:
    """
    Lista sessões com filtros opcionais.

    Args:
        projeto_id: Filtra pelo projeto. ``None`` retorna de todos os projetos.
        tipo: Filtra pelo tipo de sessão. ``None`` retorna todos os tipos.
        limite: Número máximo de registros retornados (padrão 50).

    Returns:
        Lista de :class:`Sessao` ordenada da mais recente para a mais antiga.
    """
    conditions: list[str] = []
    params: list = []

    if projeto_id is not None:
        conditions.append("projeto_id = ?")
        params.append(projeto_id)
    if tipo is not None:
        conditions.append("tipo = ?")
        params.append(tipo)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM sessoes {where} ORDER BY data_hora DESC LIMIT ?"
    params.append(limite)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Sessao.from_row(r) for r in rows]


# =========================================================================
#  CONFIGURAÇÕES
# =========================================================================

def ler_configuracao() -> Configuracao:
    """
    Lê o único registro de configuração (id = 1).

    Returns:
        Instância de :class:`Configuracao` com os valores atuais.
    """
    sql = "SELECT * FROM configuracoes WHERE id = 1"
    with get_connection() as conn:
        row = conn.execute(sql).fetchone()
    if row is None:
        # Não deveria acontecer após init_db(), mas por segurança:
        return Configuracao()
    return Configuracao.from_row(row)


def atualizar_configuracao(
    tempo_foco: Optional[int] = None,
    tempo_descanso: Optional[int] = None,
    tempo_descanso_longo: Optional[int] = None,
    transicao_automatica: Optional[bool] = None,
) -> Configuracao:
    """
    Atualiza apenas os campos fornecidos no registro de configuração.

    Campos não informados (``None``) permanecem inalterados.

    Args:
        tempo_foco: Duração do foco em minutos.
        tempo_descanso: Duração do descanso curto em minutos.
        tempo_descanso_longo: Duração do descanso longo em minutos.
        transicao_automatica: Habilita transição automática entre sessões.

    Returns:
        Instância de :class:`Configuracao` com os valores atualizados.

    Raises:
        ValueError: Se nenhum parâmetro for fornecido.
    """
    campos: dict[str, object] = {}
    if tempo_foco is not None:
        campos["tempo_foco"] = tempo_foco
    if tempo_descanso is not None:
        campos["tempo_descanso"] = tempo_descanso
    if tempo_descanso_longo is not None:
        campos["tempo_descanso_longo"] = tempo_descanso_longo
    if transicao_automatica is not None:
        campos["transicao_automatica"] = int(transicao_automatica)

    if not campos:
        raise ValueError("Nenhum campo fornecido para atualização.")

    set_clause = ", ".join(f"{col} = ?" for col in campos)
    sql = f"UPDATE configuracoes SET {set_clause} WHERE id = 1"

    with get_connection() as conn:
        conn.execute(sql, list(campos.values()))
        conn.commit()

    return ler_configuracao()


# =========================================================================
#  ESTATISTICAS E RELATORIOS
# =========================================================================

def obter_estatisticas_projetos() -> list[EstatisticaProjeto]:
    """
    Retorna estatisticas agregadas de todos os projetos cadastrados.

    Executa um LEFT JOIN entre Projetos e Sessoes (filtrando por tipo='foco')
    para somar pomodoros realizados e duracao total em minutos por projeto.

    Returns:
        Lista de EstatisticaProjeto com os dados agregados.
    """
    sql = """
        SELECT 
            p.id,
            p.nome,
            p.categoria,
            p.pomodoros_estimados,
            COUNT(s.id) AS pomodoros_realizados,
            COALESCE(SUM(s.duracao_minutos), 0) AS tempo_foco_minutos
        FROM projetos p
        LEFT JOIN sessoes s 
            ON p.id = s.projeto_id 
           AND s.tipo = 'foco'
        GROUP BY p.id, p.nome, p.categoria, p.pomodoros_estimados
        ORDER BY p.id
    """
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
    return [EstatisticaProjeto.from_row(r) for r in rows]


def obter_resumo_estatisticas() -> dict[str, int]:
    """
    Retorna totais gerais consolidados do banco de dados.

    Campos retornados:
        total_projetos:         Numero de projetos cadastrados.
        total_pomodoros:        Total geral de sessoes de foco realizadas.
        tempo_foco_minutos:     Soma de minutos de foco (com e sem projeto).
        pomodoros_sem_projeto:  Sessoes de foco realizadas sem projeto vinculado.
    """
    sql_totais = """
        SELECT 
            COUNT(id) AS total_pomodoros,
            COALESCE(SUM(duracao_minutos), 0) AS tempo_foco_minutos
        FROM sessoes
        WHERE tipo = 'foco'
    """
    sql_sem_projeto = """
        SELECT COUNT(id) AS qtd
        FROM sessoes
        WHERE tipo = 'foco' AND projeto_id IS NULL
    """
    sql_projetos = "SELECT COUNT(id) AS qtd FROM projetos"

    with get_connection() as conn:
        totais = conn.execute(sql_totais).fetchone()
        sem_proj = conn.execute(sql_sem_projeto).fetchone()
        projs = conn.execute(sql_projetos).fetchone()

    return {
        "total_projetos": projs["qtd"] if projs else 0,
        "total_pomodoros": totais["total_pomodoros"] if totais else 0,
        "tempo_foco_minutos": totais["tempo_foco_minutos"] if totais else 0,
        "pomodoros_sem_projeto": sem_proj["qtd"] if sem_proj else 0,
    }
