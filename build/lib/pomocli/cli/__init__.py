"""
src/cli/__init__.py
--------------------
Ponto de entrada do comando CLI global 'pomocli' e 'pommo'.
Inicia a interface de usuario (TUI) hacker/cyberpunk.
"""

from ..tui.app import run_tui


def main() -> None:
    """Ponto de entrada principal da aplicacao CLI."""
    run_tui()


# Alias para compatibilidade com console_scripts
cli = main


if __name__ == "__main__":
    main()
