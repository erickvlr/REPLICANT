import discord
from discord.ext import commands
from config.settings import settings
from bot.events import register_events
from bot.prefix_embeds import setup_prefix_embed_commands
from bot.prefix_help import setup_prefix_help_commands
from bot.slash_embeds import setup_slash_embed_commands
from bot.slash_memory import setup_slash_memory_commands
from bot.slash_channels import setup_slash_channel_commands
from bot.slash_presence import setup_slash_presence_commands
from bot.slash_pub import setup_slash_pub_commands
from bot.slash_regras import setup_slash_regras_commands
from utils.console import log_ok, log_warn, print_runtime_table


def build_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    intents.dm_messages = True

    bot = commands.Bot(
        command_prefix=settings.bot_prefix,
        intents=intents,
        help_command=None,
    )

    # Registra todos os handlers e comandos
    register_events(bot)
    setup_prefix_embed_commands(bot)
    setup_prefix_help_commands(bot)
    setup_slash_embed_commands(bot)
    setup_slash_memory_commands(bot)
    setup_slash_channel_commands(bot)
    setup_slash_presence_commands(bot)
    setup_slash_pub_commands(bot)
    setup_slash_regras_commands(bot)

    @bot.event
    async def on_ready():
        log_ok(f"Logado como {bot.user}")

        try:
            synced = await bot.tree.sync()
            log_ok(f"Slash commands sincronizados globalmente ({len(synced)} cmds)")
        except Exception as e:
            log_warn(f"Sync global falhou: {e}")

        print_runtime_table(str(bot.user))

    return bot
