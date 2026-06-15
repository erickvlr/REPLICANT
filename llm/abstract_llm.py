"""
AbstractLLM — interface base para implementações de LLM.
A nova arquitetura usa TextLLM.triage() + TextLLM.infer() diretamente.
Este arquivo mantém a interface legada para compatibilidade.
"""
from abc import ABC
from llm.models import LLMDecision, BrainDecision


class AbstractLLM(ABC):
    """Classe base. Métodos legados mantidos como no-ops."""

    async def decide_support_reply(self, *args, **kwargs) -> LLMDecision:
        raise NotImplementedError("Use Brain.process()")

    async def generate_direct_answer(self, *args, **kwargs) -> str:
        raise NotImplementedError("Use Brain.process()")
