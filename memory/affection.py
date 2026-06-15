from database.sqlite import execute, fetchone

_POSITIVE = {"obrigado", "obg", "vlw", "valeu", "amei", "incrível", "top", "ótimo", "perfeito",
             "muito bom", "boa", "parabéns", "show", "adorei", "grato", "te amo", "você é incrível",
             "vc é ótima", "tá ótima", "tá boa", "funcionou", "resolveu", "ajudou muito"}

_NEGATIVE = {"inútil", "inutil", "burro", "idiota", "lixo", "horrível", "péssimo", "odeio",
             "raiva", "ódio", "fdp", "arrombado", "merda", "bosta"}

def _score_delta(text: str) -> int:
    low = (text or "").lower()
    delta = 0
    for w in _POSITIVE:
        if w in low:
            delta += 2
    for w in _NEGATIVE:
        if w in low:
            delta -= 3
    return delta

async def update_affection(user_id: str, username: str, text: str) -> None:
    delta = _score_delta(text)
    row = await fetchone("SELECT * FROM affection_profiles WHERE user_id=?", (user_id,))
    if row:
        new_score = max(0, min(100, row["affection_score"] + delta))
        positive = row["positive_count"] + (1 if delta > 0 else 0)
        await execute(
            """UPDATE affection_profiles
               SET username=?, interaction_count=interaction_count+1,
                   positive_count=?, affection_score=?,
                   last_seen=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
               WHERE user_id=?""",
            (username, positive, new_score, user_id)
        )
    else:
        initial = max(0, min(100, 10 + delta))
        await execute(
            """INSERT INTO affection_profiles (user_id, username, interaction_count, positive_count, affection_score)
               VALUES (?, ?, 1, ?, ?)""",
            (user_id, username, 1 if delta > 0 else 0, initial)
        )

async def get_affection_context(user_id: str, is_owner_user: bool = False) -> str:
    if is_owner_user:
        return (
            "RELAÇÃO ESPECIAL: Esse usuário é um dos seus donos/criadores. "
            "Trate com carinho, lealdade e respeito máximos. "
            "Pode ser mais expressiva, protetora e pessoal com ele."
        )
    row = await fetchone("SELECT * FROM affection_profiles WHERE user_id=?", (user_id,))
    if not row:
        return ""
    score = row["affection_score"]
    count = row["interaction_count"]
    if score >= 70 or count >= 50:
        return (
            f"AFINIDADE ALTA (score={score}, interações={count}): Você tem uma relação próxima e calorosa "
            f"com {row['username']}. Seja mais afetiva, use o nome dele e demonstre que lembra das interações passadas."
        )
    if score >= 40 or count >= 15:
        return (
            f"AFINIDADE MÉDIA (score={score}, interações={count}): Você conhece bem {row['username']}. "
            f"Seja amigável, natural e um pouco mais pessoal do que com desconhecidos."
        )
    if count >= 3:
        return f"AFINIDADE BAIXA (interações={count}): Você já conversou antes com {row['username']}. Seja simpática."
    return ""
