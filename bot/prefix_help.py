import discord
from discord.ext import commands
from config.settings import settings

PREFIX_COMMANDS = [
    ("r!help / r!lista", "Mostra todos os comandos do bot."),
    ("r!criarembed #canal [titulo]", "Cria embed demo. Pode anexar video ou imagem junto."),
    ("r!embed / r!tutorial", "Alias do r!criarembed."),
]

SLASH_EMBED = [
    ("/embed #canal [video] [imagem]",
     "Cria embed rico com previa antes de enviar. Editor com titulo, conteudo, rodape e cor."),
]

SLASH_MEMORY = [
    ("/addinfo jogo:<nome> conteudo:<texto> [tags]",
     "[Owner] Salva info sobre jogo na memoria da IA. Ela usa como verdade absoluta."),
    ("/listinfo [pagina]", "[Owner] Lista entradas da memoria factual."),
    ("/delinfo id:<n>", "[Owner] Remove uma entrada da memoria factual."),
]

SLASH_CHANNELS = [
    ("/bloquear_canal #canal", "[Owner] Bot nao responde nem aprende neste canal."),
    ("/desbloquear_canal #canal", "[Owner] Remove o bloqueio do canal."),
    ("/canais_bloqueados", "[Owner] Lista canais onde o bot esta silenciado."),
]


def build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📚 REPLICANT — Comandos",
        description=(
            f"Prefixo: `{settings.bot_prefix}` | IA com memoria social, "
            "memoria factual e pesquisa silenciosa."
        ),
        color=settings.embed_color,
    )
    embed.add_field(name="━━ Prefixo (r!) ━━", value="​", inline=False)
    for name, desc in PREFIX_COMMANDS:
        embed.add_field(name=f"`{name}`", value=desc, inline=False)

    embed.add_field(name="━━ Embeds ━━", value="​", inline=False)
    for name, desc in SLASH_EMBED:
        embed.add_field(name=f"`{name}`", value=desc, inline=False)

    embed.add_field(name="━━ Memoria Factual ━━", value="​", inline=False)
    for name, desc in SLASH_MEMORY:
        embed.add_field(name=f"`{name}`", value=desc, inline=False)

    embed.add_field(name="━━ Canais ━━", value="​", inline=False)
    for name, desc in SLASH_CHANNELS:
        embed.add_field(name=f"`{name}`", value=desc, inline=False)

    embed.add_field(
        name="🧠 IA Automatica",
        value=(
            "• Mencione o bot uma vez para se registrar — depois ela detecta quando voce fala com ela\n"
            "• Responde quando chamada, em DMs, em pedidos de ajuda\n"
            "• Nao se intromete quando voce fala com outra pessoa\n"
            "• Pesquisa silenciosa quando precisa de info externa"
        ),
        inline=False,
    )
    embed.set_footer(text=f"{settings.app_name} v{settings.app_version}")
    return embed


def setup_prefix_help_commands(bot: commands.Bot):
    bot.remove_command("help")

    @bot.command(name="help", aliases=["ajuda", "comandos"])
    async def help_cmd(ctx: commands.Context):
        await ctx.reply(embed=build_help_embed(), mention_author=False)

    @bot.command(name="lista")
    async def lista_cmd(ctx: commands.Context):
        await ctx.reply(embed=build_help_embed(), mention_author=False)
