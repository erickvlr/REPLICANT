"""
/bloquear_canal  — bot não responde nem aprende neste canal
/desbloquear_canal — remove o bloqueio
/canais_bloqueados — lista os canais bloqueados
"""
import discord
from discord import app_commands
from discord.ext import commands
from config.permissions import is_owner
from database.sqlite import execute, fetchall, fetchone


def setup_slash_channel_commands(bot: commands.Bot):

    @bot.tree.command(
        name="bloquear_canal",
        description="[Owner] Bot não responde nem aprende neste canal.",
    )
    @app_commands.describe(canal="Canal que o bot deve ignorar completamente")
    async def bloquear_canal(interaction: discord.Interaction, canal: discord.TextChannel):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "Apenas owners podem bloquear canais.", ephemeral=True
            )
        await execute(
            "INSERT OR IGNORE INTO ignored_channels (channel_id, channel_name, added_by) VALUES (?, ?, ?)",
            (str(canal.id), canal.name, interaction.user.id),
        )
        await interaction.response.send_message(
            f"🔇 Canal {canal.mention} bloqueado. O bot não vai mais responder nem aprender lá.",
            ephemeral=True,
        )

    @bot.tree.command(
        name="desbloquear_canal",
        description="[Owner] Remove o bloqueio de um canal.",
    )
    @app_commands.describe(canal="Canal para desbloquear")
    async def desbloquear_canal(interaction: discord.Interaction, canal: discord.TextChannel):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "Apenas owners podem desbloquear canais.", ephemeral=True
            )
        row = await fetchone("SELECT 1 FROM ignored_channels WHERE channel_id=?", (str(canal.id),))
        if not row:
            return await interaction.response.send_message(
                f"Canal {canal.mention} não estava bloqueado.", ephemeral=True
            )
        await execute("DELETE FROM ignored_channels WHERE channel_id=?", (str(canal.id),))
        await interaction.response.send_message(
            f"🔊 Canal {canal.mention} desbloqueado. O bot pode responder lá novamente.",
            ephemeral=True,
        )

    @bot.tree.command(
        name="canais_bloqueados",
        description="[Owner] Lista todos os canais onde o bot está silenciado.",
    )
    async def canais_bloqueados(interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "Apenas owners podem ver essa lista.", ephemeral=True
            )
        rows = await fetchall("SELECT channel_id, channel_name FROM ignored_channels ORDER BY added_at")
        if not rows:
            return await interaction.response.send_message(
                "Nenhum canal bloqueado no momento.", ephemeral=True
            )
        linhas = [f"🔇 <#{row['channel_id']}> (`{row['channel_name']}`)" for row in rows]
        embed = discord.Embed(
            title="Canais Bloqueados",
            description="\n".join(linhas),
            color=0xED4245,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
