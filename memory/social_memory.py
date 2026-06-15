import re
from database.sqlite import execute, fetchone

EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]")

COMMON_SLANG = {
    "mano", "véi", "vei", "mn", "kk", "kkk", "kkkk", "lol", "brabo", "braba",
    "cringe", "tankei", "tankar", "bugou", "bugado", "mds", "pprt", "slk",
    "tmj", "vlw", "obg", "aff", "carai", "cara", "man"
}

def scope_keys(guild_id: str, channel_id: str, user_id: str) -> dict[str, str]:
    guild_id = guild_id or "dm"
    channel_id = channel_id or "unknown"
    user_id = user_id or "unknown"
    return {
        "guild": f"discord:guild:{guild_id}",
        "channel": f"discord:guild:{guild_id}:channel:{channel_id}",
        "user": f"discord:user:{user_id}",
    }

def detect_tone(text: str) -> str:
    low = (text or "").lower()
    if any(x in low for x in ["erro", "bug", "não consigo", "nao consigo", "ajuda", "travou"]):
        return "pedido de ajuda"
    if any(x in low for x in ["kk", "lol", "kkkk", "haha"]):
        return "zoeira"
    if any(x in low for x in ["valeu", "vlw", "obrigado", "obg"]):
        return "agradecido"
    return "casual"

def detect_energy(text: str) -> str:
    if len(re.findall(r"[!]{2,}", text or "")) or sum(1 for c in text if c.isupper()) > 12:
        return "alta"
    if len(text or "") < 25:
        return "baixa"
    return "media"

def extract_slang(text: str) -> list[str]:
    words = re.findall(r"[\wÀ-ÿ]+", (text or "").lower())
    found = []
    for w in words:
        if w in COMMON_SLANG or (w.startswith("kk") and len(w) <= 8):
            if w not in found:
                found.append(w)
    return found[:12]

def extract_emojis(text: str) -> list[str]:
    emojis = EMOJI_RE.findall(text or "")
    out = []
    for e in emojis:
        if e not in out:
            out.append(e)
    return out[:12]

async def observe_message(*, guild_id: str, channel_id: str, user_id: str, username: str, text: str) -> None:
    if not text.strip():
        return

    await execute(
        "INSERT INTO social_observations (guild_id, channel_id, user_id, username, text) VALUES (?, ?, ?, ?, ?)",
        (guild_id, channel_id, user_id, username, text[:1000])
    )

    keys = scope_keys(guild_id, channel_id, user_id)
    slang = extract_slang(text)
    emojis = extract_emojis(text)
    tone = detect_tone(text)
    energy = detect_energy(text)

    for _, key in keys.items():
        row = await fetchone("SELECT * FROM social_profiles WHERE scope_key=?", (key,))
        if row:
            old_slang = [x for x in (row["slang"] or "").split(",") if x]
            old_emojis = [x for x in (row["emojis"] or "").split(",") if x]
            merged_slang = list(dict.fromkeys(old_slang + slang))[:24]
            merged_emojis = list(dict.fromkeys(old_emojis + emojis))[:24]
            await execute(
                """UPDATE social_profiles
                   SET messages=messages+1, slang=?, emojis=?, dominant_tone=?, energy=?, sample=?, updated_at=CURRENT_TIMESTAMP
                   WHERE scope_key=?""",
                (",".join(merged_slang), ",".join(merged_emojis), tone, energy, text[:240], key)
            )
        else:
            await execute(
                """INSERT INTO social_profiles (scope_key, messages, slang, emojis, dominant_tone, energy, sample)
                   VALUES (?, 1, ?, ?, ?, ?, ?)""",
                (key, ",".join(slang), ",".join(emojis), tone, energy, text[:240])
            )

async def social_context(guild_id: str, channel_id: str, user_id: str) -> str:
    keys = scope_keys(guild_id, channel_id, user_id)
    labels = [("servidor", keys["guild"]), ("canal", keys["channel"]), ("usuário", keys["user"])]
    lines = []
    for label, key in labels:
        row = await fetchone("SELECT * FROM social_profiles WHERE scope_key=?", (key,))
        if not row:
            continue
        lines.append(
            f"{label}: mensagens={row['messages']}; tom={row['dominant_tone']}; energia={row['energy']}; "
            f"gírias={row['slang'] or '-'}; emojis={row['emojis'] or '-'}; exemplo='{row['sample'] or ''}'"
        )
    return "\n".join(lines)
