"""
TextLLM — cérebro de linguagem do Replicant.

Arquitetura em DOIS PASSOS (portada do VtuberIA):
  1. triage()  — chamada leve, retorna RESPOND | BRIEF | QUIET (1 palavra)
  2. infer()   — chamada completa, retorna texto livre para o Discord

Não usa JSON. Não depende de parsing complexo. Não falha silenciosamente.
"""
import re
import os
import httpx
import yaml
from pathlib import Path
from config.settings import settings
from llm.abstract_llm import AbstractLLM
from llm.models import TriageResult, BrainDecision
from core.persona import EmotionalState
from utils.console import (
    log_llm_request, log_llm_raw, log_llm_http_error,
    log_llm_timeout, log_llm_exception, log_warn, log_debug, log_ok,
)

# ── Carrega character.yaml ──────────────────────────────────────
_CHAR_PATH = Path(__file__).parent.parent / "config" / "character.yaml"

def _load_character() -> dict:
    try:
        with open(_CHAR_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        log_ok(f"character.yaml carregado ({_CHAR_PATH.name})")
        return data
    except FileNotFoundError:
        log_warn(f"character.yaml não encontrado em {_CHAR_PATH} — usando defaults")
        return {}
    except Exception as e:
        log_warn(f"Erro ao carregar character.yaml: {e}")
        return {}

_CHAR = _load_character()


# ── Prompts construídos a partir do YAML ───────────────────────

def _build_base_system(char: dict) -> str:
    ident = char.get("identity", {})
    name = ident.get("display_name") or ident.get("name") or "Replicant"
    role = ident.get("role", "IA de servidor de jogos")

    traits = char.get("personality", {}).get("core_traits", [])
    traits_txt = "\n".join(f"- {t}" for t in traits) if traits else "- Natural e direta"

    speech = char.get("speech_style", {})
    speech_rules = speech.get("rules", [])
    speech_txt = "\n".join(f"- {r}" for r in speech_rules) if speech_rules else ""

    forbidden = speech.get("forbidden", [])
    forbidden_txt = (
        "NUNCA use: " + ", ".join(f'"{w}"' for w in forbidden)
        if forbidden else ""
    )

    hard = char.get("hard_limits", [])
    hard_txt = "\n".join(f"- {h}" for h in hard) if hard else ""

    mem = char.get("memory_rules", [])
    mem_txt = "\n".join(f"- {m}" for m in mem) if mem else ""

    search = char.get("search_rules", [])
    search_txt = "\n".join(f"- {s}" for s in search) if search else ""

    behavior = char.get("response_behavior", {})

    return f"""Você é {name}, {role}.

TRAÇOS DE PERSONALIDADE:
{traits_txt}

ESTILO DE FALA:
{speech_txt}
{forbidden_txt}

QUANDO RESPONDER:
- Se mencionada diretamente: {behavior.get('when_mentioned', 'sempre responda')}
- Pedido de ajuda: {behavior.get('when_helping', 'claro e direto')}
- Bate-papo: {behavior.get('when_chatting', 'natural e curto')}
- Saudações: {behavior.get('on_greeting', 'responda normalmente')}
- Se não souber: {behavior.get('when_unsure', 'diga que não sabe')}

MEMÓRIA:
{mem_txt}

PESQUISA SILENCIOSA:
{search_txt}

LIMITES ABSOLUTOS:
{hard_txt}

Responda SEMPRE em português brasileiro."""


_BASE_SYSTEM = _build_base_system(_CHAR)

# Descritores de estado emocional do YAML
_EMOTION_DESC: dict[EmotionalState, str] = {}
_emo_states = _CHAR.get("personality", {}).get("emotional_states", {})
_STATE_MAP = {
    "neutral":     EmotionalState.NEUTRAL,
    "happy":       EmotionalState.HAPPY,
    "moody":       EmotionalState.MOODY,
    "sassy":       EmotionalState.SASSY,
    "emotional":   EmotionalState.EMOTIONAL,
    "hyperactive": EmotionalState.HYPERACTIVE,
    "focused":     EmotionalState.FOCUSED,
}
for _key, _state in _STATE_MAP.items():
    if _key in _emo_states:
        _EMOTION_DESC[_state] = _emo_states[_key]


# ── Prompts de triage ───────────────────────────────────────────

_TRIAGE_SYSTEM = """Você é um filtro de triagem para uma IA de Discord de servidor de jogos.
Responda com EXATAMENTE uma palavra: RESPOND, BRIEF ou QUIET.

RESPOND → pergunta direta, pedido de ajuda, suporte técnico, assunto sério
BRIEF   → cumprimento, comentário casual, agradecimento, conversa leve
QUIET   → claramente para outra pessoa, auto-fala, mensagem de sistema"""

_SEARCH_TRIAGE_SYSTEM = """Você é um filtro que decide se uma pergunta precisa de pesquisa web.
Responda com EXATAMENTE uma linha no formato:
SEARCH: <consulta de busca>
ou
NO_SEARCH

Use SEARCH apenas para: datas de lançamento, preços atuais, versões específicas, notícias recentes.
Use NO_SEARCH para: perguntas gerais, suporte de instalação, regras do servidor."""


class TextLLM(AbstractLLM):

    def __init__(self):
        self.provider  = settings.llm_provider
        self.base_url  = settings.llm_base_url.rstrip("/")
        self.api_key   = settings.llm_api_key
        self.model     = settings.llm_model

    # ── HTTP ───────────────────────────────────────────────────

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter":
            if settings.openrouter_site_url:
                h["HTTP-Referer"] = settings.openrouter_site_url
            if settings.openrouter_app_name:
                h["X-Title"] = settings.openrouter_app_name
        return h

    def _is_ollama_native(self) -> bool:
        """
        Retorna True se a URL aponta para o daemon local do Ollama (porta 11434).
        Nesse caso usa /api/chat + formato Ollama nativo (igual ao VtuberIA).
        URLs com /v1 são tratadas como OpenAI-compatible.
        """
        base = self.base_url.lower()
        if "/v1" in base:
            return False
        return "11434" in base or "localhost" in base or "127.0.0.1" in base

    def _chat_url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions") or base.endswith("/api/chat"):
            return base
        if self._is_ollama_native():
            # Remove /api duplicado se vier no base_url
            if base.endswith("/api"):
                base = base[:-4]
            return f"{base}/api/chat"
        return f"{base}/chat/completions"

    def _build_payload(self, messages: list[dict], temperature: float, max_tokens: int) -> dict:
        """Payload no formato correto: Ollama nativo ou OpenAI-compat."""
        if self._is_ollama_native():
            # Formato Ollama — igual ao VtuberIA (wrappertext.py)
            return {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "think": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "num_ctx": 8192,
                },
            }
        else:
            # Formato OpenAI-compatible (groq, openrouter, ollama cloud direto)
            return {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

    def _extract_content(self, data: dict) -> str:
        """
        Extrai o texto da resposta independente do formato.
        Ollama nativo : data["message"]["content"]
        OpenAI compat : data["choices"][0]["message"]["content"]
        """
        # Ollama nativo
        msg = data.get("message")
        if isinstance(msg, dict):
            content = msg.get("content", "").strip()
            if content:
                return content

        # OpenAI / Groq / OpenRouter
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            content = choices[0].get("message", {}).get("content", "").strip()
            if content:
                return content

        # Fallback para APIs não-padrão
        for key in ("response", "content", "text", "output"):
            val = data.get(key, "")
            if val and isinstance(val, str):
                return val.strip()

        return ""

    async def _post(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.30,
        max_tokens: int = 80,
        timeout: float | None = None,
        model_override: str | None = None,
    ) -> str:
        url = self._chat_url()
        payload = self._build_payload(messages, temperature, max_tokens)
        if model_override:
            payload["model"] = model_override
        native = self._is_ollama_native()
        active_model = model_override or self.model
        log_debug(f"POST {url} | model={active_model} | tokens={max_tokens} | msgs={len(messages)} | ollama_native={native}")
        t = timeout or settings.llm_timeout
        try:
            async with httpx.AsyncClient(timeout=t) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
        except httpx.TimeoutException:
            log_llm_timeout(url, t)
            raise
        except httpx.ConnectError as exc:
            log_llm_exception(exc)
            raise

        if resp.status_code != 200:
            log_llm_http_error(url, resp.status_code, resp.text)
            resp.raise_for_status()

        try:
            data = resp.json()
        except Exception:
            log_warn(f"Resposta não é JSON: {resp.text[:300]}")
            raise

        content = self._extract_content(data)
        if not content:
            log_warn(f"LLM retornou content vazio. Raw: {str(data)[:400]}")
            raise ValueError("LLM content vazio")

        return content

    # ── 1. TRIAGE ──────────────────────────────────────────────

    async def triage(self, user_text: str, interaction_type: str = "") -> TriageResult:
        """
        Passo 1: classificação leve.
        Retorna RESPOND / BRIEF / QUIET sem risco de parse.
        """
        user_msg = f"Tipo de interação: {interaction_type}\nMensagem: {user_text}"
        try:
            raw = await self._post(
                [
                    {"role": "system", "content": _TRIAGE_SYSTEM},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.05,
                max_tokens=10,
                timeout=12.0,
            )
            log_llm_raw(f"[TRIAGE] {raw!r}")
            word = raw.strip().upper().split()[0] if raw.strip() else "QUIET"
            if word == "RESPOND":
                return TriageResult.RESPOND
            if word == "BRIEF":
                return TriageResult.BRIEF
            return TriageResult.QUIET

        except httpx.TimeoutException:
            log_warn("triage timeout — assumindo QUIET")
            return TriageResult.QUIET
        except Exception as exc:
            log_llm_exception(exc)
            return TriageResult.QUIET

    def _triage_rescue(self, result: TriageResult, text: str, interaction_type: str) -> TriageResult:
        """
        Portado do VtuberIA: salva casos que o triage errou.
        Se QUIET mas há sinal claro de endereçamento → BRIEF.
        """
        if result != TriageResult.QUIET:
            return result
        low = text.lower()
        if "MENÇÃO DIRETA" in interaction_type:
            return TriageResult.RESPOND
        if low.endswith("?") or re.search(r"\bvoc[eê]\b|\bvc\b", low):
            return TriageResult.BRIEF
        if any(low.startswith(w) for w in ("oi", "olá", "ei", "bom dia", "boa tarde", "boa noite")):
            return TriageResult.BRIEF
        return result

    # ── 2. SEARCH TRIAGE ──────────────────────────────────────

    async def search_triage(self, user_text: str) -> tuple[bool, str]:
        """
        Decide se precisa de pesquisa web e qual a query.
        Retorna (needs_search, query).
        """
        try:
            raw = await self._post(
                [
                    {"role": "system", "content": _SEARCH_TRIAGE_SYSTEM},
                    {"role": "user",   "content": user_text},
                ],
                temperature=0.05,
                max_tokens=60,
                timeout=10.0,
            )
            raw = raw.strip()
            log_llm_raw(f"[SEARCH_TRIAGE] {raw!r}")
            if raw.upper().startswith("SEARCH:"):
                query = raw[7:].strip()
                return (True, query) if query else (False, "")
            return (False, "")
        except Exception:
            return (False, "")

    # ── 3. INFER ───────────────────────────────────────────────

    async def infer(
        self,
        user_text: str,
        *,
        username: str,
        channel_name: str,
        interaction_type: str = "",
        triage: TriageResult = TriageResult.RESPOND,
        emotion: EmotionalState = EmotionalState.NEUTRAL,
        affection_context: str = "",
        factual_memory: str = "",
        social_context: str = "",
        recent_history: str = "",
        search_context: str = "",
        character_rules: str = "",
        image_b64: list[str] | None = None,  # lista de imagens base64
    ) -> str:
        """
        Passo 3: geração de texto livre.
        Sem JSON, sem parsing — apenas texto para o Discord.
        """
        log_llm_request(username, channel_name, interaction_type, user_text)

        emotion_desc = _EMOTION_DESC.get(emotion, "")
        brief_hint = "\nSeja BREVE — resposta curta, uma ou duas frases." if triage == TriageResult.BRIEF else ""

        # Regras do owner ficam NO TOPO — LLM presta mais atenção ao início do contexto
        if character_rules:
            system = f"{character_rules}\n\n{_BASE_SYSTEM}"
        else:
            system = _BASE_SYSTEM
        if emotion_desc:
            system += f"\n\n[ESTADO EMOCIONAL ATUAL: {emotion.value.upper()}]\n{emotion_desc}"
        if brief_hint:
            system += brief_hint

        ctx_parts = []
        if affection_context:
            ctx_parts.append(f"[RELAÇÃO]\n{affection_context}")
        if factual_memory:
            ctx_parts.append(f"[MEMÓRIA FACTUAL — use como verdade absoluta]\n{factual_memory}")
        if social_context:
            ctx_parts.append(f"[ESTILO SOCIAL DO SERVIDOR — adapte seu jeito de falar]\n{social_context}")
        if search_context:
            ctx_parts.append(f"[PESQUISA SILENCIOSA — use como fato externo]\n{search_context}")

        ctx_block = "\n\n".join(ctx_parts)

        history_block = ""
        if recent_history:
            history_block = f"\n\n[HISTÓRICO RECENTE]\n{recent_history}"

        user_prompt = (
            f"Usuário: {username}\nCanal: {channel_name}\nTipo: {interaction_type or 'geral'}\n\n"
            + (ctx_block + "\n\n" if ctx_block else "")
            + history_block.strip()
            + f"\n\nMensagem: {user_text}\n\nResponda só com o texto final para o Discord."
        ).strip()

        max_tok = 300 if triage == TriageResult.BRIEF else settings.llm_max_tokens

        # Monta mensagem do usuário — com imagens se houver (Ollama vision)
        if image_b64:
            user_msg = {"role": "user", "content": user_prompt, "images": image_b64}
        else:
            user_msg = {"role": "user", "content": user_prompt}

        # Usa modelo de visão se imagens presentes e VISION_MODEL configurado
        vision_model = settings.vision_model.strip() if image_b64 else ""

        try:
            raw = await self._post(
                [
                    {"role": "system", "content": system},
                    user_msg,
                ],
                temperature=0.70,
                max_tokens=max_tok,
                model_override=vision_model or None,
            )
            log_llm_raw(f"[INFER] {raw[:200]!r}")
            text = self._clean(raw)
            log_debug(f"infer → {text[:80]!r}")
            return text[:1800]

        except httpx.TimeoutException:
            log_warn(f"infer timeout ({settings.llm_timeout}s)")
            return ""
        except httpx.HTTPStatusError as exc:
            log_warn(f"infer HTTP {exc.response.status_code}")
            return ""
        except Exception as exc:
            log_llm_exception(exc)
            return ""

    # ── Limpeza de saída ───────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        # Remove prefixos tipo "Hoshino Ai:" ou "Replicant:"
        text = re.sub(r"^\s*(Hoshino Ai|Replicant|IA)\s*:\s*", "", text, flags=re.I)
        # Remove action blocks entre asteriscos (*acena*)
        text = re.sub(r"\*[^*]{1,60}\*", "", text)
        # Remove parênteses de ações (age assim)
        text = re.sub(r"\([^)]{1,80}\)", "", text)
        # Normaliza espaços
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    # ── Método legado para AbstractLLM ────────────────────────

    async def decide_support_reply(self, *args, **kwargs):
        raise NotImplementedError("Use Brain.process() em vez de decide_support_reply()")

    async def generate_direct_answer(self, *args, **kwargs):
        raise NotImplementedError("Use Brain.process() em vez de generate_direct_answer()")
