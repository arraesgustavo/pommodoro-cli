"""
scripts/smoke_test.py
Script de validação rápida da camada de banco de dados.
Execute com:  python scripts/smoke_test.py

NÃO é parte do pacote instalável; serve apenas para verificação manual.
"""

import sys
from pathlib import Path

# Garante que o pacote local seja encontrado sem instalação
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pommo.database import (
    init_db,
    criar_projeto,
    listar_projetos,
    buscar_projeto,
    deletar_projeto,
    registrar_sessao,
    listar_sessoes,
    ler_configuracao,
    atualizar_configuracao,
)

SEP = "-" * 50


def secao(titulo: str) -> None:
    print(f"\n{SEP}\n▶  {titulo}\n{SEP}")


def main() -> None:
    secao("Inicializando banco")
    init_db()
    print("  OK — banco inicializado em ~/.local/share/pommo/pommo.db")

    # Configuração 
    secao("Lendo configuração padrão")
    cfg = ler_configuracao()
    print(" ", cfg)

    secao("Atualizando configuração")
    cfg = atualizar_configuracao(tempo_foco=30, transicao_automatica=True)
    print(" ", cfg)

    # Projetos
    secao("Criando projetos")
    p1 = criar_projeto("pommo-cli", categoria="dev", pomodoros_estimados=10)
    p2 = criar_projeto("Estudos de Algoritmos", categoria="estudo", pomodoros_estimados=5)
    print(" ", p1)
    print(" ", p2)

    secao("Listando projetos")
    for p in listar_projetos():
        print(" ", p)

    secao("Buscando projeto por id")
    found = buscar_projeto(p1.id)
    print(" ", found)

    # Sessões 
    secao("Registrando sessões")
    s1 = registrar_sessao(30, "foco", projeto_id=p1.id)
    s2 = registrar_sessao(5, "descanso_curto")
    s3 = registrar_sessao(15, "descanso_longo", projeto_id=p2.id)
    print(" ", s1)
    print(" ", s2)
    print(" ", s3)

    secao("Listando sessões (todas)")
    for s in listar_sessoes():
        print(" ", s)

    secao("Listando sessões de foco")
    for s in listar_sessoes(tipo="foco"):
        print(" ", s)

    # Deleção 
    secao("Deletando projeto #2")
    ok = deletar_projeto(p2.id)
    print(f"  Deletado: {ok}")
    print("  Projetos restantes:")
    for p in listar_projetos():
        print("   ", p)

    # A sessão s3 vinculada ao projeto deletado deve ter projeto_id = NULL
    secao("Sessões após deleção do projeto (projeto_id deve ser NULL)")
    for s in listar_sessoes():
        print(" ", s)

    print(f"\n{'═'*50}")
    print("  Smoke test concluído com sucesso! ✔")
    print(f"{'═'*50}\n")


if __name__ == "__main__":
    main()
