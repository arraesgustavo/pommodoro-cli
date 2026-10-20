"""
src/cli/__init__.py
--------------------
Ponto de entrada do comando CLI 'pommo'.
Inicia a interface de usuario (TUI) hacker/cyberpunk.
"""

from ..tui.app import run_tui


def main() -> None:
    """Ponto de entrada principal da aplicacao CLI."""
    run_tui()


if __name__ == "__main__":
    main()
