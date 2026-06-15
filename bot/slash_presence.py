"""
/setpresence — Altera o status e a presença do bot em tempo real.

Permite mudar:
  - Tipo de atividade: jogando, assistindo, ouvindo, competindo, transmitindo
  - Texto da atividade (a "bio" que aparece no perfil)
  - Status online: online, ausente, ocupado, invisível
"""
import discord
from discord import app_commands
from discord.ext import commands
from config.permissions import is_owner

_ACTIVITY_TYPES = {
    "jogando":      discord.ActivityType.playing,
    "assistindo":   discord.ActivityType.watching,
    "ouvindo":      discord.ActivityType.listening,
    "competindo":   discord.ActivityType.competing,
    "transmitindo": discord.ActivityType.streaming,
}

_STATUS_TYPES = {
    "online":    discord.Status.online,
    "ausente":   discord.Status.idle,
    "ocupado":   discord.Status.dnd,
    "invisivel": discord.Status.invisible,
}


def setup_slash_presence_commands(bot: commands.Bot):

    @bot.tree.command(
        name="setpresence",
        description="[Owner] Altera o status e a presença do bot.",
    )
    @app_commands.describe(
        texto="Texto que aparece no perfil do bot (ex: jogos do servidor)",
        tipo="Tipo de atividade: jogando | assistindo | ouvindo | competindo | transmitindo",
        status="Status online: online | ausente | ocupado | invisivel",
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="🎮 Jogando",       value="jogando"),
            app_commands.Choice(name="📺 Assistindo",    value="assistindo"),
            app_commands.Choice(name="🎵 Ouvindo",       value="ouvindo"),
            app_commands.Choice(name="🏆 Competindo",    value="competindo"),
            app_commands.Choice(name="📡 Transmitindo",  value="transmitindo"),
        ],
        status=[
            app_commands.Choice(name="🟢 Online",     value="online"),
            app_commands.Choice(name="🟡 Ausente",    value="ausente"),
            app_commands.Choice(name="🔴 Ocupado",    value="ocupado"),
            app_commands.Choice(name="⚫ Invisível",  value="invisivel"),
        ],
    )
    async def setpresence(
        interaction: discord.Interaction,
        texto: str,
        tipo: str = "jogando",
        status: str = "online",
    ):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "Apenas owners podem alterar a presença do bot.", ephemeral=True
            )

        activity_type = _ACTIVITY_TYPES.get(tipo, discord.ActivityType.playing)
        status_type   = _STATUS_TYPES.get(status, discord.Status.online)

        if tipo == "transmitindo":
            activity = discord.Streaming(name=texto[:128], url="https://twitch.tv/placeholder")
        else:
            activity = discord.Activity(type=activity_type, name=texto[:128])

        await bot.change_presence(status=status_type, activity=activity)

        status_emoji = {
            "online":    "🟢",
            "ausente":   "🟡",
            "ocupado":   "🔴",
            "invisivel": "⚫",
        }.get(status, "🟢")

        tipo_label = {
            "jogando":      "Jogando",
            "assistindo":   "Assistindo",
            "ouvindo":      "Ouvindo",
            "competindo":   "Competindo",
            "transmitindo": "Transmitindo",
        }.get(tipo, "Jogando")

        await interaction.response.send_message(
            f"{status_emoji} Presença atualizada:\n**{tipo_label}** {texto}",
            ephemeral=True,
        )
