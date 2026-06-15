import traceback
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from config.settings import settings

console = Console()

def print_banner():
    name = settings.app_name
    version = settings.app_version
    art = f"""
[bold cyan]██████╗ ███████╗██████╗ ██╗     ██╗ ██████╗ █████╗ ███╗   ██╗████████╗[/bold cyan]
[bold magenta]██╔══██╗██╔════╝██╔══██╗██║     ██║██╔════╝██╔══██╗████╗  ██║╚══██╔══╝[/bold magenta]
[bold cyan]██████╔╝█████╗  ██████╔╝██║     ██║██║     ███████║██╔██╗ ██║   ██║[/bold cyan]
[bold magenta]██╔══██╗██╔══╝  ██╔═══╝ ██║     ██║██║     ██╔══██║██║╚██╗██║   ██║[/bold magenta]
[bold cyan]██║  ██║███████╗██║     ███████╗██║╚██████╗██║  ██║██║ ╚████║   ██║[/bold cyan]
[bold magenta]╚═╝  ╚═╝╚══════╝╚═╝     ╚══════╝╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝[/bold magenta]
[bold white]{name}[/bold white] [cyan]v{version}[/cyan]
"""
    console.print(Panel.fit(art, border_style="cyan", title="[bold magenta]BOOT[/bold magenta]"))

def log_info(msg: str):
    console.print(f"[bold cyan][INFO][/bold cyan] {msg}")

def log_ok(msg: str):
    console.print(f"[bold green][OK][/bold green] {msg}")

def log_warn(msg: str):
    console.print(f"[bold yellow][WARN][/bold yellow] {msg}")

def log_error(msg: str):
    console.print(f"[bold red][ERRO][/bold red] {msg}")

def log_debug(msg: str):
    if settings.log_level.upper() == "DEBUG":
        console.print(f"[dim][DEBUG] {msg}[/dim]")

# ── Logs específicos do cérebro ──────────────────────────────

def log_llm_request(username: str, channel: str, interaction_type: str, text: str):
    console.print(
        f"[bold blue][CÉREBRO][/bold blue] "
        f"[cyan]{username}[/cyan] → [yellow]{channel}[/yellow] "
        f"[dim]({interaction_type})[/dim] | [white]{text[:80]!r}[/white]"
    )

def log_llm_raw(raw: str):
    console.print(f"[dim][LLM-RAW] {raw[:400]!r}[/dim]")

def log_llm_decision(intent: str, confidence: float, needs_search: bool, reason: str):
    color = "green" if intent == "answer" else "yellow" if intent != "ignore" else "dim"
    console.print(
        f"[bold {color}][LLM-DECISÃO][/bold {color}] "
        f"intent=[bold]{intent}[/bold] "
        f"conf=[bold]{confidence:.2f}[/bold] "
        f"search={needs_search} "
        f"| {reason[:100]}"
    )

def log_llm_http_error(url: str, status: int, body: str):
    console.print(f"[bold red][LLM-HTTP {status}][/bold red] URL: {url}")
    console.print(f"[red]  Resposta: {body[:500]}[/red]")

def log_llm_timeout(url: str, timeout: float):
    console.print(f"[bold yellow][LLM-TIMEOUT][/bold yellow] Sem resposta em {timeout}s | {url}")

def log_llm_json_error(raw: str, exc: Exception):
    console.print(f"[bold red][LLM-JSON][/bold red] Não foi possível parsear JSON da resposta da LLM.")
    console.print(f"[red]  Raw: {raw[:600]!r}[/red]")
    console.print(f"[red]  Erro: {exc}[/red]")

def log_llm_exception(exc: Exception):
    console.print(f"[bold red][LLM-ERRO][/bold red] {type(exc).__name__}: {exc}")
    console.print(f"[red]{traceback.format_exc(limit=6)}[/red]")

def log_reply_sent(username: str, interaction_type: str, confidence: float, answer_preview: str):
    console.print(
        f"[bold green][RESPOSTA][/bold green] "
        f"→ [cyan]{username}[/cyan] "
        f"[dim]({interaction_type} | conf={confidence:.2f})[/dim] "
        f"[white]{answer_preview[:60]!r}[/white]"
    )

def log_reply_blocked(reason: str, confidence: float, min_conf: float):
    console.print(
        f"[bold yellow][BLOQUEADO][/bold yellow] "
        f"conf={confidence:.2f} < min={min_conf} | {reason}"
    )

def print_runtime_table(bot_name: str):
    table = Table(title="Replicant Runtime", show_header=True, header_style="bold magenta")
    table.add_column("Item")
    table.add_column("Valor")
    table.add_row("Bot", bot_name)
    table.add_row("LLM Provider", settings.llm_provider)
    table.add_row("LLM Model", settings.llm_model)
    table.add_row("LLM Endpoint", settings.llm_base_url)
    table.add_row("Database", settings.database_path)
    table.add_row("Owners", f"{len(settings.owner_ids)} configurado(s)")
    console.print(table)
