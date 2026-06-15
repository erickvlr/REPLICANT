import re
import unicodedata
from database.sqlite import fetchall

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode("utf-8")
    return text.lower().strip()

def trigger_matches(trigger: str, user_text: str) -> bool:
    parts = [p.strip() for p in trigger.split("+") if p.strip()]
    user_text = normalize(user_text).replace("-", " ")

    for part in parts:
        part = normalize(part).replace("-", " ")
        pattern = r"\b" + re.escape(part).replace(r"\ ", r"\s+") + r"\b"
        if not re.search(pattern, user_text):
            return False

    return True

async def find_exact_rule(user_text: str, channel_id: int):
    rows = await fetchall("SELECT * FROM rules")
    for row in rows:
        channels = [int(x) for x in row["channels"].split(",") if x.strip().isdigit()]
        if channels and channel_id not in channels:
            continue

        triggers = [x.strip() for x in row["triggers"].split(",") if x.strip()]
        if any(trigger_matches(t, user_text) for t in triggers):
            return dict(row)

    return None

async def rule_exists_by_name(name: str):
    rows = await fetchall("SELECT * FROM rules WHERE lower(name)=lower(?)", (name,))
    return dict(rows[0]) if rows else None

async def relevant_rules_for_prompt(user_text: str, limit: int = 12) -> str:
    words = set(re.findall(r"\w+", normalize(user_text)))
    rows = await fetchall("SELECT name, triggers FROM rules")

    scored = []
    for row in rows:
        trigger_words = set(re.findall(r"\w+", normalize(row["triggers"])))
        score = len(words & trigger_words)
        if score > 0:
            scored.append((score, row["name"], row["triggers"]))

    scored.sort(reverse=True, key=lambda x: x[0])
    selected = scored[:limit]

    if not selected:
        return ""

    return "\n".join(f"- {name}: {triggers}" for _, name, triggers in selected)
