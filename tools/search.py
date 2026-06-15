import re
import time
import httpx
from urllib.parse import quote_plus
from config.settings import settings
from database.sqlite import fetchone, execute

def strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S|re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S|re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

async def cached_search(query: str) -> str:
    query = (query or "").strip()
    if not query or not settings.search_enabled:
        return ""

    row = await fetchone("SELECT result_text, created_at FROM search_cache WHERE query=?", (query,))
    if row and row["result_text"]:
        return row["result_text"]

    result = await web_search(query)
    if result:
        await execute("INSERT OR REPLACE INTO search_cache (query, result_text) VALUES (?, ?)", (query, result[:6000]))
    return result

async def web_search(query: str) -> str:
    provider = settings.search_provider.lower()

    try:
        if provider == "brave" and settings.brave_search_api_key:
            return await brave_search(query)
        if provider == "tavily" and settings.tavily_api_key:
            return await tavily_search(query)
        return await duckduckgo_lite_search(query)
    except Exception as exc:
        return f"[PESQUISA FALHOU] Não foi possível obter resultados confiáveis: {exc}"

async def brave_search(query: str) -> str:
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": settings.brave_search_api_key}
    params = {"q": query, "count": settings.search_max_results, "search_lang": "pt-br"}
    async with httpx.AsyncClient(timeout=settings.search_timeout) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
    results = data.get("web", {}).get("results", [])[:settings.search_max_results]
    lines = [f"[PESQUISA SILENCIOSA] Consulta: {query}"]
    for i, item in enumerate(results, 1):
        lines.append(f"{i}. {item.get('title','Sem título')} — {item.get('description','')} — {item.get('url','')}")
    return "\n".join(lines)

async def tavily_search(query: str) -> str:
    url = "https://api.tavily.com/search"
    payload = {"api_key": settings.tavily_api_key, "query": query, "max_results": settings.search_max_results}
    async with httpx.AsyncClient(timeout=settings.search_timeout) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    results = data.get("results", [])[:settings.search_max_results]
    lines = [f"[PESQUISA SILENCIOSA] Consulta: {query}"]
    for i, item in enumerate(results, 1):
        lines.append(f"{i}. {item.get('title','Sem título')} — {item.get('content','')} — {item.get('url','')}")
    return "\n".join(lines)

async def duckduckgo_lite_search(query: str) -> str:
    # Sem API key. Pode falhar se o provedor bloquear, então o LLM é instruído a não inventar.
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    async with httpx.AsyncClient(timeout=settings.search_timeout, headers={"User-Agent": "Mozilla/5.0"}) as client:
        r = await client.get(url)
        r.raise_for_status()
        html = r.text

    chunks = re.findall(r'<a rel="nofollow" class="result__a".*?href="(.*?)".*?>(.*?)</a>.*?<a class="result__snippet".*?>(.*?)</a>', html, flags=re.S)
    lines = [f"[PESQUISA SILENCIOSA] Consulta: {query}"]
    for i, (url, title, snippet) in enumerate(chunks[:settings.search_max_results], 1):
        lines.append(f"{i}. {strip_html(title)} — {strip_html(snippet)} — {url}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)
