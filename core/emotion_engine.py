"""
Motor de emoção simplificado — portado do VtuberIA.
Rastreia estado emocional baseado em palavras-chave e decaimento natural.
"""
import time
from core.persona import EmotionalState

# Keywords → emoção disparada
KEYWORDS: dict[str, list[str]] = {
    "joy":          ["kkk", "kkkk", "haha", "rsrs", "lol", "show", "top", "incrível", "amei",
                     "ótimo", "perfeito", "legal", "massa", "demais", "brabo"],
    "sadness":      ["triste", "chateado", "deprimido", "mal", "difícil", "sozinho", "cansado"],
    "anger":        ["raiva", "ódio", "inutil", "lixo", "idiota", "burro", "pior", "horrível"],
    "trust":        ["obrigado", "obg", "vlw", "valeu", "confia", "tmj", "parceiro"],
    "surprise":     ["nossa", "cara", "serio", "sério", "que", "uau", "wow"],
    "focused":      ["erro", "bug", "como", "instalar", "problema", "ajuda", "crash", "não funciona"],
    "playful":      ["haha", "kk", "brincadeira", "mano", "véi", "cara", "ei"],
}

# Emoção dominante → EmotionalState
_DOMINANT_MAP: dict[str, EmotionalState] = {
    "joy":      EmotionalState.HAPPY,
    "anger":    EmotionalState.MOODY,
    "trust":    EmotionalState.EMOTIONAL,
    "surprise": EmotionalState.HYPERACTIVE,
    "focused":  EmotionalState.FOCUSED,
    "playful":  EmotionalState.SASSY,
    "sadness":  EmotionalState.EMOTIONAL,
}

_DECAY_RATE = 0.08   # por chamada (quanto a emoção volta ao neutro)
_KEYWORD_BOOST = 0.25


class EmotionEngine:
    """
    Motor de emoção leve para Discord.
    Mantém scores por dimensão e decai em direção ao baseline.
    """

    def __init__(self):
        self._scores: dict[str, float] = {k: 0.0 for k in KEYWORDS}
        self._last_update = time.time()
        self.state = EmotionalState.NEUTRAL

    # ── API pública ───────────────────────────────────────────

    def update(self, user_text: str, bot_text: str = "") -> EmotionalState:
        """Atualiza o estado emocional com base nos textos e retorna o novo estado."""
        self._decay()
        combined = f"{user_text} {bot_text}".lower()
        self._score_keywords(combined)
        self.state = self._resolve_state()
        return self.state

    def descriptor(self) -> str:
        """Retorna diretiva de comportamento para o system prompt."""
        return _DESCRIPTORS.get(self.state, "")

    def current(self) -> EmotionalState:
        return self.state

    # ── Internos ─────────────────────────────────────────────

    def _decay(self):
        for k in self._scores:
            self._scores[k] = max(0.0, self._scores[k] - _DECAY_RATE)

    def _score_keywords(self, text: str):
        for emotion, words in KEYWORDS.items():
            for word in words:
                if word in text:
                    self._scores[emotion] = min(1.0, self._scores[emotion] + _KEYWORD_BOOST)

    def _resolve_state(self) -> EmotionalState:
        if not any(v > 0.15 for v in self._scores.values()):
            return EmotionalState.NEUTRAL
        dominant = max(self._scores, key=lambda k: self._scores[k])
        return _DOMINANT_MAP.get(dominant, EmotionalState.NEUTRAL)


# Descritores de comportamento injetados no system prompt
_DESCRIPTORS: dict[EmotionalState, str] = {
    EmotionalState.NEUTRAL:     "Tom neutro, direto e atento.",
    EmotionalState.HAPPY:       "Animada e curiosa. Deixe o humor fluir, seja levemente sarcástica.",
    EmotionalState.MOODY:       "Mais seca e objetiva. Respostas curtas, sem drama.",
    EmotionalState.SASSY:       "Wit afiado, provoque levemente, seja confiante.",
    EmotionalState.EMOTIONAL:   "Aberta, sincera e genuinamente presente no momento.",
    EmotionalState.HYPERACTIVE: "Agitada e entusiasmada. Pode falar um pouco mais.",
    EmotionalState.FOCUSED:     "Modo analítico. Direto ao ponto, foco total no problema técnico.",
}
