"""
events.py — orquestra eventos Discord e aciona o Brain.

Fluxo por mensagem:
  1. Filtra bots, canais bloqueados
  2. Observação passiva (social + afeto)
  3. resolve_reply() → decide se deve responder
  4. Brain.process() → triage + infer (dois passos, sem JSON)
  5. Envia resposta ou descarta conforme TriageResult
"""
import re
import time
import base64
import discord
import httpx
from brain.brain import Brain
from llm.models import TriageResult
from rules.matcher import find_exact_rule, rule_exists_by_name, relevant_rules_for_prompt
from database.sqlite import execute, fetchall, fetchone
from config.settings import settings
from config.permissions import is_owner
from utils.console import (
    log_info, log_warn, log_debug,
    log_reply_sent, log_reply_blocked,
)
from memory.social_memory import observe_message, social_context
from memory.affection import update_affection, get_affection_context
from memory.factual import retrieve_relevant
from memory.character_rules import load_character_rules
from tools.search import cached_search

# Prefixos que o owner pode usar para definir regras no chat
_RULE_PREFIXES = ("regra:", "rule:", "regra -", "regra—")


async def _try_save_rule(message: discord.Message, text: str) -> bool:
    """
    Detecta se a mensagem é uma regra do owner.
    Se sim, salva no banco e retorna True.
    """
    if not is_owner(message.author.id):
        return False

    low = text.lower().strip()
    matched_prefix = None
    for prefix in _RULE_PREFIXES:
        if low.startswith(prefix):
            matched_prefix = prefix
            break

    if not matched_prefix:
        return False

    rule_text = text[len(matched_prefix):].strip()
    if not rule_text:
        return False

    await execute(
        "INSERT INTO character_rules (category, rule, added_by) VALUES (?, ?, ?)",
        ("comportamento", rule_text, message.author.id),
    )
    log_ok(f"Regra salva por {message.author.display_name}: {rule_text[:80]}")
    return True

brain = Brain()
_channel_intervention: dict[int, float] = {}
_replied_ids: set[str] = set()

HELP_TERMS = (
    "erro", "bug", "ajuda", "nao funciona", "não funciona", "travou",
    "crash", "não abre", "nao abre", "como resolver", "como resolve",
    "como instalar", "não consigo", "nao consigo", "problema", "duvida", "dúvida",
)
WAKE_WORDS = ("replicant", "hoshino", "ia", "bot")


# ──────────────────────────────────────────────────────────────
# DB HELPERS
# ──────────────────────────────────────────────────────────────

async def save_history(user_id: int, username: str, channel_id: int,
                       channel_name: str, user_message: str, bot_reply: str):
    await execute(
        "INSERT INTO conversation_history "
        "(user_id, username, channel_id, channel_name, user_message, bot_reply) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, channel_id, channel_name, user_message[:1000], bot_reply[:2000]),
    )

async def recent_history_text(channel_id: int) -> str:
    rows = await fetchall(
        "SELECT username, user_message, bot_reply FROM conversation_history "
        "WHERE channel_id=? ORDER BY id DESC LIMIT ?",
        (channel_id, settings.max_history_messages),
    )
    lines = []
    for row in reversed(rows):
        lines.append(f"{row['username']}: {row['user_message']}")
        lines.append(f"Replicant: {row['bot_reply']}")
    return "\n".join(lines[-settings.max_history_messages:])

async def is_channel_ignored(channel_id: int) -> bool:
    row = await fetchone("SELECT 1 FROM ignored_channels WHERE channel_id=?", (str(channel_id),))
    return row is not None

async def is_user_registered(user_id: str) -> bool:
    row = await fetchone("SELECT 1 FROM registered_users WHERE user_id=?", (user_id,))
    return row is not None

async def register_user(user_id: str, username: str):
    await execute(
        "INSERT OR IGNORE INTO registered_users (user_id, username) VALUES (?, ?)",
        (user_id, username),
    )


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def no_mentions():
    return discord.AllowedMentions.none()

def sanitize_outbound(text: str, source_message=None) -> str:
    out = str(text or "")
    if source_message is not None:
        author = getattr(source_message, "author", None)
        uid = str(getattr(author, "id", "") or "")
        name = str(getattr(author, "display_name", None) or getattr(author, "name", ""))
        if uid and name:
            out = re.sub(rf"<@!?{re.escape(uid)}>", name, out)
    out = re.sub(r"<@!?\d+>", "alguém", out)
    out = re.sub(r"<@&\d+>", "um cargo", out)
    out = out.replace("@everyone", "everyone").replace("@here", "here")
    out = re.sub(r"(?<!\w)@([A-Za-z0-9_\.]{2,32})", r"\1", out)
    return out.strip()

def bot_mentioned(bot, message) -> bool:
    if not bot.user:
        return False
    bid = str(bot.user.id)
    return (
        any(str(getattr(u, "id", "")) == bid for u in getattr(message, "mentions", []) or [])
        or f"<@{bid}>" in message.content
        or f"<@!{bid}>" in message.content
    )

def has_wake_word(text: str) -> bool:
    low = " ".join((text or "").lower().split())
    return any(f" {w} " in f" {low} " or low.startswith(w) for w in WAKE_WORDS)

def has_help_term(text: str) -> bool:
    low = " ".join((text or "").lower().split())
    return len(low) > 8 and any(t in low for t in HELP_TERMS)

def addressing_other_user(message) -> bool:
    for m in getattr(message, "mentions", []) or []:
        bot_id = message.guild.me.id if message.guild else 0
        if m.id != bot_id:
            return True
    if re.match(r"^[A-Za-zÀ-ÿ]{2,20},\s", message.content or ""):
        return True
    return False

def intervention_ok(channel_id: int) -> bool:
    now = time.time()
    last = _channel_intervention.get(channel_id, 0)
    if now - last < 90:
        return False
    _channel_intervention[channel_id] = now
    return True

def looks_directed_at_bot(text: str) -> bool:
    low = (text or "").lower().strip()
    if not low:
        return False
    if low.endswith("?"):
        return True
    if re.search(r"\bvoc[eê]\b|\bvc\b", low):
        return True
    if any(low.startswith(s) for s in ("oi", "olá", "ola", "ei", "e ai", "oie", "hey",
                                        "bom dia", "boa tarde", "boa noite")):
        return True
    if any(w in low for w in ("vlw", "valeu", "obg", "obrigado", "show", "tmj",
                               "kk", "kkk", "haha", "rs", "rsrs")):
        return True
    return False


async def resolve_reply(bot, message, text: str, user_id: str) -> tuple[bool, str]:
    # DM — conversa livre
    if message.guild is None:
        return True, "MENSAGEM DIRETA (DM)"
    # Servidor — só responde se for mencionada diretamente
    if bot_mentioned(bot, message):
        return True, "MENÇÃO DIRETA"
    return False, ""


# ──────────────────────────────────────────────────────────────
# EVENT REGISTRATION
# ──────────────────────────────────────────────────────────────

def register_events(bot):

    @bot.event
    async def on_message(message: discord.Message):
        # ── DIAGNÓSTICO BRUTO — mostra TODA mensagem recebida ──
        try:
            log_info(f"[MSG] {message.author} | bot={message.author.bot} | '{(message.content or '')[:60]}'")
        except Exception:
            pass

        if message.author.bot:
            return

        await bot.process_commands(message)

        text = (message.content or "").strip()
        attachments = list(getattr(message, "attachments", []) or [])

        # Coleta imagens anexadas (para visão do LLM)
        image_attachments = [
            a for a in attachments
            if (a.content_type or "").startswith("image/")
        ]

        if not text and not attachments:
            return

        # Se só tem imagem sem texto, injeta prompt implícito
        if not text and image_attachments:
            text = "O que você vê nessa imagem? Analise e responda com base no que sabe."

        guild_id     = str(getattr(getattr(message, "guild", None), "id", "dm") or "dm")
        channel_id   = getattr(message.channel, "id", 0)
        channel_name = getattr(message.channel, "name", "dm")
        username     = message.author.display_name
        user_id      = str(message.author.id)

        try:
            # ── Detecção de regra do owner ────────────────────
            if await _try_save_rule(message, text):
                return  # regra salva, não processa como conversa normal

            # Canais ignorados
            if await is_channel_ignored(channel_id):
                log_debug(f"Canal {channel_id} ignorado — abortando")
                return

            # Registro automático na primeira menção
            if bot_mentioned(bot, message):
                await register_user(user_id, username)
                log_info(f"Menção direta de {username} ({user_id}) — registrado")

            # Aprendizado passivo sempre
            if text:
                await observe_message(
                    guild_id=guild_id, channel_id=str(channel_id),
                    user_id=user_id, username=username, text=text,
                )
                await update_affection(user_id, username, text)

            # Decide se responde
            should_reply, interaction_type = await resolve_reply(bot, message, text, user_id)
            log_info(f"resolve_reply → should={should_reply} | type={interaction_type!r} | {username}: {text[:50]!r}")
            if not should_reply:
                return

            msg_id = str(message.id)
            if msg_id in _replied_ids:
                return
            _replied_ids.add(msg_id)
            if len(_replied_ids) > 500:
                _replied_ids.clear()

            # ── 1. Regra exata ──────────────────────────────────
            exact_rule = await find_exact_rule(text, channel_id)
            if exact_rule:
                reply = sanitize_outbound(exact_rule["reply"], message)
                await message.reply(reply, mention_author=False, allowed_mentions=no_mentions())
                await save_history(message.author.id, username, channel_id, channel_name, text, reply)
                log_info(f"Regra exata: {exact_rule['name']} | {username}")
                return

            # ── 2. Contextos ─────────────────────────────────────
            owner_user    = is_owner(message.author.id)
            affection_ctx = await get_affection_context(user_id, is_owner_user=owner_user)
            factual_ctx   = await retrieve_relevant(text)
            history       = await recent_history_text(channel_id)
            social        = await social_context(guild_id, str(channel_id), user_id)

            log_info(f"Chamando Brain.process() para {username}...")

            # Baixa imagens como base64 para passar ao LLM (visão)
            image_b64: list[str] = []
            if image_attachments:
                async with httpx.AsyncClient(timeout=15) as hclient:
                    for att in image_attachments[:2]:  # máximo 2 imagens por vez
                        try:
                            resp = await hclient.get(att.url)
                            if resp.status_code == 200:
                                image_b64.append(base64.b64encode(resp.content).decode())
                                log_info(f"Imagem baixada: {att.filename} ({len(resp.content)} bytes)")
                        except Exception as img_err:
                            log_warn(f"Falha ao baixar imagem {att.filename}: {img_err}")

            # ── 3. Brain.process() — triage + infer ─────────────
            decision = await brain.process(
                text,
                username=username,
                channel_name=channel_name,
                interaction_type=interaction_type,
                recent_history=history,
                social_context=social,
                affection_context=affection_ctx,
                factual_memory=factual_ctx,
                search_fn=cached_search,
                image_b64=image_b64 if image_b64 else None,
            )

            log_info(f"Brain retornou: triage={decision.triage.value} | answer={repr(decision.answer[:60]) if decision.answer else 'VAZIO'}")

            # ── 4. Avalia resultado ──────────────────────────────
            if decision.triage == TriageResult.QUIET:
                log_reply_blocked(f"triage=QUIET | {username}: {text[:40]!r}", 0.0, 0.0)
                return

            answer = (decision.answer or "").strip()
            if not answer:
                log_warn(f"Brain triage={decision.triage.value} mas answer VAZIO | {username}")
                return

            answer = sanitize_outbound(answer, message)

            # Servidor → reply com menção (ping) para deixar claro a quem responde
            # DM → mensagem direta sem menção
            if message.guild is not None:
                await message.reply(answer[:1800], mention_author=True)
            else:
                await message.channel.send(answer[:1800], allowed_mentions=no_mentions())

            await save_history(message.author.id, username, channel_id, channel_name, text, answer)
            log_reply_sent(username, interaction_type, 1.0, answer)

        except Exception as _exc:
            import traceback
            log_warn(f"ERRO FATAL em on_message: {_exc}")
            print(traceback.format_exc())
