"""
Memória Factual — conhecimento injetado pelos owners.
Busca por relevância usando sobreposição de palavras + scoring por posição
(tópico > tags > conteúdo) para encontrar entradas mesmo com perguntas reformuladas.
"""
import re
import unicodedata
from database.sqlite import execute, fetchall, fetchone

# Sinônimos simples — expande a busca sem depender de embeddings
_SYNONYMS: dict[str, list[str]] = {
    "instalar": ["instalacao", "install", "setup", "configurar", "colocar"],
    "erro":     ["error", "bug", "problema", "falha", "crash", "nao abre", "nao funciona"],
    "salvar":   ["save", "backup", "salvo", "gravar"],
    "mod":      ["modificacao", "modding", "mods", "addon"],
    "jogar":    ["jogo", "game", "jogar", "rodar", "abrir"],
    "onde":     ["local", "pasta", "diretorio", "caminho", "path", "lugar"],
    "como":     ["tutorial", "guia", "passo", "instrucao"],
    "crack":    ["cracked", "pirata", "sem licenca", "offline"],
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode("utf-8")
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", _normalize(text)) if len(w) > 2}


def _expand(words: set[str]) -> set[str]:
    """Adiciona sinônimos ao conjunto de palavras da query."""
    expanded = set(words)
    for w in words:
        for canonical, syns in _SYNONYMS.items():
            if w == canonical or w in syns:
                expanded.add(canonical)
                expanded.update(syns)
    return expanded


def _score(query_words: set[str], row: dict) -> float:
    """
    Score ponderado:
      - Match no tópico  → peso 3
      - Match nas tags   → peso 2
      - Match no content → peso 1
    Normalizado pelo total de palavras da query.
    """
    if not query_words:
        return 0.0
    topic_w   = _words(row["topic"])
    tags_w    = _words(row["tags"] or "")
    content_w = _words(row["content"])

    score = (
        len(query_words & topic_w)   * 3 +
        len(query_words & tags_w)    * 2 +
        len(query_words & content_w) * 1
    )
    return score / len(query_words)


async def add_memory(topic: str, content: str, tags: str, created_by: int) -> int:
    await execute(
        "INSERT INTO factual_memory (topic, content, tags, created_by) VALUES (?, ?, ?, ?)",
        (topic.strip(), content.strip(), tags.strip().lower(), created_by),
    )
    row = await fetchone("SELECT id FROM factual_memory ORDER BY id DESC LIMIT 1")
    return row["id"] if row else -1


async def update_memory(memory_id: int, topic: str, content: str, tags: str):
    await execute(
        "UPDATE factual_memory SET topic=?, content=?, tags=? WHERE id=?",
        (topic.strip(), content.strip(), tags.strip().lower(), memory_id),
    )


async def delete_memory(memory_id: int) -> bool:
    row = await fetchone("SELECT id FROM factual_memory WHERE id=?", (memory_id,))
    if not row:
        return False
    await execute("DELETE FROM factual_memory WHERE id=?", (memory_id,))
    return True


async def list_memories(limit: int = 200) -> list[dict]:
    rows = await fetchall(
        "SELECT id, topic, tags, substr(content,1,120) as preview, created_at "
        "FROM factual_memory ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in rows]


async def retrieve_relevant(user_text: str, limit: int = 4, threshold: float = 0.05) -> str:
    """
    Busca entradas relevantes com scoring ponderado + expansão de sinônimos.
    Retorna bloco de texto pronto para injetar no prompt.
    """
    raw_words  = _words(user_text)
    query_words = _expand(raw_words)
    if not query_words:
        return ""

    rows = await fetchall("SELECT id, topic, content, tags FROM factual_memory")
    scored: list[tuple[float, dict]] = []

    for row in rows:
        s = _score(query_words, dict(row))
        if s >= threshold:
            scored.append((s, dict(row)))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = scored[:limit]

    if not selected:
        return ""

    lines = ["[MEMÓRIA FACTUAL — informação confiável inserida pelos admins, priorize sobre buscas]"]
    for _, entry in selected:
        lines.append(f"• [{entry['topic']}]\n{entry['content']}")
    return "\n\n".join(lines)
