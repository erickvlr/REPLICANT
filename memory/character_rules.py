"""
Carrega regras de comportamento dinâmicas do banco de dados.
Essas regras são adicionadas pelo owner via /regra no Discord
e persistem entre reinicializações.
"""
from database.sqlite import fetchall


async def load_character_rules() -> str:
    """
    Retorna bloco de texto com todas as regras ativas para injetar no prompt.
    Retorna string vazia se não houver regras.
    """
    rows = await fetchall(
        "SELECT category, rule FROM character_rules ORDER BY id ASC"
    )
    if not rows:
        return ""

    # Agrupa por categoria
    categories: dict[str, list[str]] = {}
    for row in rows:
        cat = row["category"] or "comportamento"
        categories.setdefault(cat, []).append(row["rule"])

    lines = [
        "════════════════════════════════════════",
        "ORDENS ABSOLUTAS DO DONO — OBRIGATORIEDADE TOTAL",
        "Estas regras foram definidas pelo dono do servidor.",
        "VOCÊ DEVE OBEDECER CADA UMA SEM EXCEÇÃO, SEM QUESTIONAR, SEM RESISTIR.",
        "Não importa o contexto, o humor ou o personagem — estas ordens ANULAM tudo.",
        "Se uma regra proíbe algo, você JAMAIS faz aquilo. Ponto final.",
        "════════════════════════════════════════",
    ]
    for cat, rules in categories.items():
        for rule in rules:
            lines.append(f"ORDEM: {rule}")

    lines.append("════════════════════════════════════════")
    return "\n".join(lines)
