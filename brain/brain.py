"""
Brain — orquestrador principal do Replicant.

Fluxo (portado do VtuberIA):
  1. triage()        → RESPOND | BRIEF | QUIET  (chamada leve, 1 palavra)
  2. _triage_rescue  → salva falsos QUIET por heurística
  3. search_triage() → decide se precisa pesquisa silenciosa
  4. web_search()    → executa pesquisa se necessário
  5. infer()         → gera resposta livre (sem JSON)

Emoção é atualizada APÓS cada troca e injetada no próximo infer().
"""
from __future__ import annotations

from llm.text_llm import TextLLM
from llm.models import TriageResult, BrainDecision
from core.emotion_engine import EmotionEngine
from core.persona import EmotionalState
from memory.character_rules import load_character_rules
from utils.console import log_ok, log_warn, log_debug


class Brain:
    """Instância única (singleton por bot) — mantém estado emocional global."""

    def __init__(self):
        self.llm     = TextLLM()
        self.emotion = EmotionEngine()

    # ─────────────────────────────────────────────────────────
    # Método principal
    # ─────────────────────────────────────────────────────────

    async def process(
        self,
        user_text: str,
        *,
        username: str,
        channel_name: str,
        interaction_type: str = "",
        recent_history: str = "",
        social_context: str = "",
        affection_context: str = "",
        factual_memory: str = "",
        search_fn=None,
        image_b64: list[str] | None = None,
    ) -> BrainDecision:
        """
        Processa uma mensagem e retorna BrainDecision.

        `search_fn` é injetado pelo events.py — permite pesquisa silenciosa
        sem acoplamento direto ao módulo de busca.
        """
        result = BrainDecision()

        # ── 1. Triage ─────────────────────────────────────────
        triage = await self.llm.triage(user_text, interaction_type=interaction_type)
        triage = self.llm._triage_rescue(triage, user_text, interaction_type)
        result.triage = triage
        log_debug(f"triage={triage.value} | interaction={interaction_type!r}")

        if triage == TriageResult.QUIET:
            return result  # sai cedo, sem gerar resposta

        # ── 2. Search triage (só para RESPOND) ───────────────
        search_context = ""
        if triage == TriageResult.RESPOND and search_fn:
            needs_search, query = await self.llm.search_triage(user_text)
            if needs_search and query:
                result.needs_search  = True
                result.search_query  = query
                try:
                    sr = await search_fn(query)
                    if sr:
                        search_context = sr
                        log_ok(f"Pesquisa silenciosa: {query!r} → {len(sr)} chars")
                except Exception as exc:
                    log_warn(f"search_fn falhou: {exc}")

        # ── 3. Estado emocional atual ────────────────────────
        emotion: EmotionalState = self.emotion.current()

        # ── 4. Regras de personagem dinâmicas (owner via /regra) ─
        char_rules = await load_character_rules()

        # ── 5. Infer — gera resposta livre ───────────────────
        answer = await self.llm.infer(
            user_text,
            username=username,
            channel_name=channel_name,
            interaction_type=interaction_type,
            triage=triage,
            emotion=emotion,
            affection_context=affection_context,
            factual_memory=factual_memory,
            social_context=social_context,
            recent_history=recent_history,
            search_context=search_context,
            character_rules=char_rules,
            image_b64=image_b64,
        )
        result.answer = answer

        # ── 5. Atualiza emoção depois da troca ───────────────
        self.emotion.update(user_text, answer)

        return result

    # ─────────────────────────────────────────────────────────
    # Legado — mantido para imports antigos em events.py
    # ─────────────────────────────────────────────────────────

    async def decide(self, user_text: str, **kwargs):
        """Legado: delega para process(). Retorna BrainDecision."""
        return await self.process(user_text, **kwargs)

    async def direct_answer(self, user_text: str, **kwargs) -> str:
        """Legado: retorna apenas o texto da resposta."""
        bd = await self.process(user_text, **kwargs)
        return bd.answer
