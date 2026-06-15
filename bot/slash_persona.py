"""
slash_persona.py — Comandos para o owner moldar o comportamento da IA em tempo real.

/regra   — adiciona uma regra de comportamento persistente
/regras  — lista todas as regras ativas
/del_regra — remove uma regra por ID
"""
import discord
from discord import app_commands
from database.sqlite import execute, fetchall, fetchone
from config.permissions import is_owner
from utils.console import log_ok, log_warn


def setup_slash_persona_commands(bot):

    # ── /regra ────────────────────────────────────────────────────
    @bot.tree.command(name="regra", description="Adiciona uma regra de comportamento permanente para a IA")
    @app_commands.describe(
        regra="Descreva como a IA deve se comportar (ex: 'sempre responda com kk no final')",
        categoria="Categoria: comportamento | fala | gestos | relacao (padrão: comportamento)",
    )
    async def regra_cmd(
        interaction: discord.Interaction,
        regra: str,
        categoria: str = "comportamento",
    ):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ Só o owner pode adicionar regras.", ephemeral=True)
            return

        await execute(
            "INSERT INTO character_rules (category, rule, added_by) VALUES (?, ?, ?)",
            (categoria.lower().strip(), regra.strip(), interaction.user.id),
        )
        log_ok(f"Regra de personagem adicionada por {interaction.user}: {regra[:60]}")
        await interaction.response.send_message(
            f"✅ **Regra salva!**\n> {regra}\n\nCategoria: `{categoria}` — Ativa imediatamente.",
            ephemeral=True,
        )

    # ── /regras ───────────────────────────────────────────────────
    @bot.tree.command(name="regras", description="Lista todas as regras de comportamento ativas")
    async def regras_cmd(interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ Só o owner pode ver as regras.", ephemeral=True)
            return

        rows = await fetchall(
            "SELECT id, category, rule, added_at FROM character_rules ORDER BY id ASC"
        )
        if not rows:
            await interaction.response.send_message("📭 Nenhuma regra cadastrada ainda.", ephemeral=True)
            return

        lines = ["**📋 Regras de Comportamento Ativas**\n"]
        for row in rows:
            lines.append(f"`#{row['id']}` [{row['category']}] {row['rule']}")

        text = "\n".join(lines)
        # Divide se for muito grande
        if len(text) > 1900:
            text = text[:1900] + "\n..."

        await interaction.response.send_message(text, ephemeral=True)

    # ── /del_regra ────────────────────────────────────────────────
    @bot.tree.command(name="del_regra", description="Remove uma regra de comportamento pelo ID")
    @app_commands.describe(id="ID da regra (use /regras para ver os IDs)")
    async def del_regra_cmd(interaction: discord.Interaction, id: int):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ Só o owner pode remover regras.", ephemeral=True)
            return

        row = await fetchone("SELECT rule FROM character_rules WHERE id=?", (id,))
        if not row:
            await interaction.response.send_message(f"❌ Regra #{id} não encontrada.", ephemeral=True)
            return

        await execute("DELETE FROM character_rules WHERE id=?", (id,))
        log_ok(f"Regra #{id} removida por {interaction.user}")
        await interaction.response.send_message(
            f"🗑️ Regra `#{id}` removida:\n> {row['rule']}",
            ephemeral=True,
        )
