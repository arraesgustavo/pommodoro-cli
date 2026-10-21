"""
src/tui/theme.py
-----------------
Constantes de estilo e ASCII art do pommo.

Tudo que diz respeito a cores, bordas, markup rich e textos fixos
fica centralizado aqui para facil customizacao.
"""

# =========================================================================
# Paleta de cores (nomes de cor do rich / markup)
# =========================================================================

COR_PRIMARIA      = "bright_green"      # verde neon - elementos principais
COR_SECUNDARIA    = "cyan"              # cyan - destaques e titulos
COR_AVISO         = "bright_yellow"     # amarelo - alertas / estados de descanso
COR_PERIGO        = "bright_red"        # vermelho - erros / emergencias
COR_INATIVO       = "grey50"            # cinza - texto apagado / inativo
COR_FUNDO_PAINEL  = "grey11"            # fundo escuro dos paineis

# Estilo dos estados do Pomodoro
ESTILO_POR_ESTADO = {
    "FOCO":            f"bold {COR_PRIMARIA}",
    "DESCANSO_CURTO":  f"bold {COR_AVISO}",
    "DESCANSO_LONGO":  f"bold {COR_AVISO}",
    "PARADO":          f"{COR_INATIVO}",
}

# Cor da barra de progresso por estado
BARRA_COR_POR_ESTADO = {
    "FOCO":            "green",
    "DESCANSO_CURTO":  "yellow",
    "DESCANSO_LONGO":  "yellow",
    "PARADO":          "grey50",
}

# Estilo das bordas dos paineis
BORDA_PADRAO = "bright_green"
BORDA_ALERTA = "bright_yellow"

# =========================================================================
# ASCII Art - cabecalho fixo
# =========================================================================

LOGO = r"""
 ____   ___  __  __ __  __  ___  
|  _ \ / _ \|  \/  |  \/  |/ _ \ 
| |_) | | | | |\/| | |\/| | | | |
|  __/| |_| | |  | | |  | | |_| |
|_|    \___/|_|  |_|_|  |_|\___/ 
"""

SUBTITULO = "[ POMOHACKER // TERMINAL v0.5 ]"

# Linha decorativa separadora
LINHA_DEC = "[bright_green]" + ("=" * 52) + "[/bright_green]"

# =========================================================================
# Labels de estado
# =========================================================================

LABEL_ESTADO = {
    "FOCO":           ">> FOCO ATIVO",
    "DESCANSO_CURTO": ">> DESCANSO CURTO",
    "DESCANSO_LONGO": ">> DESCANSO LONGO",
    "PARADO":         ">> PARADO",
}

# =========================================================================
# Textos do menu de controle
# =========================================================================

MENU_OPCOES = {
    "s": ("[S]", "iniciar"),
    "p": ("[P]", "pausar/retomar"),
    "n": ("[N]", "proximo"),
    "j": ("[J]", "projetos"),
    "e": ("[E]", "stats"),
    "c": ("[C]", "config"),
    "m": ("[M]", "menu/prompt"),
    "q": ("[Q]", "sair"),
}
