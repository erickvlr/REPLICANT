from enum import Enum


class EmotionalState(str, Enum):
    NEUTRAL    = "neutral"      # padrão — calma, direta
    HAPPY      = "happy"        # animada, curiosa, humor fluindo
    MOODY      = "moody"        # seca, objetiva, curta
    SASSY      = "sassy"        # afiada, provocadora
    EMOTIONAL  = "emotional"    # aberta, sincera, tocada
    HYPERACTIVE= "hyperactive"  # agitada, entusiasmada
    FOCUSED    = "focused"      # analítica, modo suporte técnico
