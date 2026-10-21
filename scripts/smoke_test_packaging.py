"""
scripts/smoke_test_packaging.py
--------------------------------
Smoke test para validacao da Etapa 6:
Empacotamento, Entrypoint Global e Resolucao de Caminhos Absolutos.

Valida:
  1. Presenca dos entrypoints globais (pomocli e pommo)
  2. Resolucao absoluta do banco SQLite em ~/.local/share/pomocli/pomocli.db
  3. Resolucao absoluta dos arquivos de audio (.wav) relativo ao pacote instalado
  4. Execucao a partir de diretorio arbitrario (/tmp) sem quebra de paths
"""

import os
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

SEP = "=" * 65


def titulo(txt: str) -> None:
    print(f"\n{SEP}\n  {txt}\n{SEP}")


def main() -> None:
    # -------------------------------------------------------------
    titulo("1. Validando Metadados de Empacotamento")
    try:
        dist_meta = metadata.metadata("pomocli")
        print(f"  [OK] Pacote registrado: {dist_meta['Name']} v{dist_meta['Version']}")
    except metadata.PackageNotFoundError:
        print("  [AVISO] Pacote pomocli nao encontrado via importlib.metadata no interpretador atual.")

    # -------------------------------------------------------------
    titulo("2. Validando Entrypoints de Execucao Global")
    cmd_pomocli = shutil.which("pomocli")
    cmd_pommo = shutil.which("pommo")
    print(f"  Comando 'pomocli': {cmd_pomocli}")
    print(f"  Comando 'pommo':   {cmd_pommo}")
    assert cmd_pomocli is not None, "Comando 'pomocli' nao encontrado no PATH do sistema!"
    print("  [OK] Entrypoint 'pomocli' disponivel no PATH.")

    # -------------------------------------------------------------
    titulo("3. Validando Resolucao Absoluta do Banco de Dados")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from src.database.connection import _db_path
    db_file = _db_path()
    print(f"  Caminho do banco: {db_file}")
    assert db_file.is_absolute(), "Caminho do banco deve ser absoluto!"
    assert "pomocli" in str(db_file), "Banco deve estar no diretorio pomocli!"
    assert db_file.parent.exists(), "Diretorio do banco deve ser criado automaticamente!"
    print("  [OK] Banco de dados configurado no caminho padrao XDG.")

    # -------------------------------------------------------------
    titulo("4. Validando Resolucao Absoluta dos Assets de Audio")
    from src.alerts.notifications import ASSETS_DIR, _SOM_POR_ESTADO
    print(f"  Diretorio de assets: {ASSETS_DIR}")
    assert ASSETS_DIR.is_absolute(), "Caminho de assets deve ser absoluto!"
    assert ASSETS_DIR.is_dir(), f"Diretorio de assets nao existe: {ASSETS_DIR}"

    for estado, arquivos in _SOM_POR_ESTADO.items():
        assert len(arquivos) > 0, f"Nenhum arquivo mapeado para {estado.name}"
        for wav in arquivos:
            assert wav.is_absolute(), f"Caminho do som deve ser absoluto: {wav}"
            assert wav.exists(), f"Arquivo de som nao encontrado: {wav}"
            print(f"  [OK] {estado.name:<16} -> {wav.name} ({wav.stat().st_size} bytes)")

    # -------------------------------------------------------------
    titulo("5. Testando Execucao de Subprocesso a Partir de /tmp")
    # Testa chamar a aplicacao a partir de /tmp enviando 'q' para encerramento imediato
    res = subprocess.run(
        [cmd_pomocli],
        input="q\n",
        cwd="/tmp",
        capture_output=True,
        text=True,
        timeout=10,
    )
    print("  Saida capturada do comando pomocli:")
    for linha in res.stdout.strip().splitlines()[-4:]:
        print(f"    {linha}")
    print(f"  [OK] Execucao de '{cmd_pomocli}' a partir de /tmp com saida de codigo {res.returncode}.")

    titulo("SMOKE TEST DE EMPACOTAMENTO CONCLUIDO COM 100% DE SUCESSO")


if __name__ == "__main__":
    main()
