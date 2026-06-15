"""
Slash commands de Memória Factual — somente owners podem gerenciar.

/addinfo  #canal (opcional) → Modal: Tópico, Conteúdo (4000 chars), Tags
/listinfo [pagina]          → Lista paginada com botão Editar/Deletar
/delinfo  id                → Remove por ID
"""
import discord
from discord import app_commands
from discord.ext import commands
from config.permissions import is_owner
from memory.factual import add_memory, update_memory, delete_memory, list_memories


# ── Modal de criação / edição ─────────────────────────────────────────────────

class InfoModal(discord.ui.Modal, title="Adicionar Informação"):
    def __init__(self, topic_default="", content_default="", tags_default="",
                 memory_id=None, original_interaction=None):
        super().__init__()
        self.memory_id            = memory_id
        self.original_interaction = original_interaction

        self.topic_field = discord.ui.TextInput(
            label="Tópico",
            placeholder="Ex: Dark Souls 2 — Save Game  /  Instalação GTA V",
            default=topic_default,
            max_length=200,
            required=True,
        )
        self.content_field = discord.ui.TextInput(
            label="Conteúdo (suporta markdown)",
            style=discord.TextStyle.paragraph,
            placeholder=(
                "Escreva tudo que a IA deve saber sobre esse tópico.\n"
                "Pode incluir passos, erros comuns, links, exemplos...\n"
                "Quanto mais detalhado, melhor a resposta."
            ),
            default=content_default,
            max_length=4000,
            required=True,
        )
        self.tags_field = discord.ui.TextInput(
            label="Tags (palavras-chave, separadas por vírgula)",
            placeholder="Ex: save, backup, corrompido, cloud, ds2",
            default=tags_default,
            max_length=300,
            required=False,
        )

        self.add_item(self.topic_field)
        self.add_item(self.content_field)
        self.add_item(self.tags_field)

    async def on_submit(self, interaction: discord.Interaction):
        topic   = self.topic_field.value.strip()
        content = self.content_field.value.strip()
        tags    = self.tags_field.value.strip()

        if self.memory_id:
            await update_memory(self.memory_id, topic, content, tags)
            mem_id = self.memory_id
            action = "atualizada"
        else:
            mem_id = await add_memory(topic, content, tags, interaction.user.id)
            action = "salva"

        embed = discord.Embed(
            title=f"🧠 Memória Factual — Informação {action.capitalize()}",
            color=0x57F287,
        )
        embed.add_field(name="ID",     value=f"`#{mem_id}`",        inline=True)
        embed.add_field(name="Tópico", value=topic[:256],            inline=True)
        embed.add_field(name="Tags",   value=tags[:256] or "—",      inline=True)
        embed.add_field(name="Conteúdo salvo", value=content[:1000], inline=False)
        embed.set_footer(text=f"Por {interaction.user.display_name}")

        if self.original_interaction:
            try:
                await interaction.response.defer(ephemeral=True)
                await self.original_interaction.edit_original_response(
                    content=None, embed=embed, view=None
                )
                return
            except Exception:
                pass

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ── View de gerenciamento paginado ────────────────────────────────────────────

_PAGE = 8

class ListInfoView(discord.ui.View):
    def __init__(self, author_id: int, rows: list, page: int = 0):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.rows      = rows
        self.page      = page
        self._build()

    def _build(self):
        self.clear_items()
        start     = self.page * _PAGE
        page_rows = self.rows[start:start + _PAGE]
        total     = max(1, -(-len(self.rows) // _PAGE))

        for row in page_rows:
            edit_btn = discord.ui.Button(
                label=f"✏️ #{row['id']} {row['topic'][:30]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"edit_{row['id']}",
                row=0,
            )
            edit_btn.callback = self._edit_cb(row["id"])
            self.add_item(edit_btn)

            del_btn = discord.ui.Button(
                label="🗑️",
                style=discord.ButtonStyle.danger,
                custom_id=f"del_{row['id']}",
                row=0,
            )
            del_btn.callback = self._del_cb(row["id"])
            self.add_item(del_btn)

        nav_row = 4
        if self.page > 0:
            prev = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary, row=nav_row)
            prev.callback = self._page_cb(self.page - 1)
            self.add_item(prev)
        if self.page < total - 1:
            nxt = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary, row=nav_row)
            nxt.callback = self._page_cb(self.page + 1)
            self.add_item(nxt)

    def _embed(self) -> discord.Embed:
        start     = self.page * _PAGE
        page_rows = self.rows[start:start + _PAGE]
        total     = max(1, -(-len(self.rows) // _PAGE))

        lines = []
        for r in page_rows:
            tags = f" `[{r['tags']}]`" if r.get("tags") else ""
            prev = (r.get("preview") or "").replace("\n", " ")[:80]
            lines.append(f"**#{r['id']} — {r['topic'][:50]}**{tags}\n{prev}")

        return discord.Embed(
            title=f"🧠 Memória Factual — {len(self.rows)} entradas  |  Pág. {self.page+1}/{total}",
            description="\n\n".join(lines) or "Vazio.",
            color=0x5865F2,
        )

    def _edit_cb(self, mid: int):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("Não é seu painel.", ephemeral=True)
            from database.sqlite import fetchone
            row = await fetchone("SELECT topic, content, tags FROM factual_memory WHERE id=?", (mid,))
            if not row:
                return await interaction.response.send_message("Entrada não encontrada.", ephemeral=True)
            await interaction.response.send_modal(
                InfoModal(
                    topic_default=row["topic"],
                    content_default=row["content"],
                    tags_default=row["tags"] or "",
                    memory_id=mid,
                    original_interaction=interaction,
                )
            )
        return cb

    def _del_cb(self, mid: int):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("Não é seu painel.", ephemeral=True)
            await delete_memory(mid)
            self.rows = [r for r in self.rows if r["id"] != mid]
            if self.page * _PAGE >= len(self.rows) and self.page > 0:
                self.page -= 1
            self._build()
            await interaction.response.edit_message(embed=self._embed(), view=self)
        return cb

    def _page_cb(self, new_page: int):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("Não é seu painel.", ephemeral=True)
            self.page = new_page
            self._build()
            await interaction.response.edit_message(embed=self._embed(), view=self)
        return cb


# ── Setup ──────────────────────────────────────────────────────────────────────

def setup_slash_memory_commands(bot: commands.Bot):

    @bot.tree.command(
        name="addinfo",
        description="[Owner] Abre o editor para salvar informação na memória da IA.",
    )
    async def addinfo(interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "❌ Apenas owners podem adicionar informações.", ephemeral=True
            )
        await interaction.response.send_modal(InfoModal())


    @bot.tree.command(
        name="listinfo",
        description="[Owner] Lista e gerencia as entradas da memória factual.",
    )
    async def listinfo(interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "❌ Apenas owners podem ver a memória factual.", ephemeral=True
            )
        all_entries = await list_memories(limit=200)
        if not all_entries:
            return await interaction.response.send_message(
                "📭 Nenhuma informação salva ainda. Use `/addinfo` para começar.", ephemeral=True
            )
        view = ListInfoView(author_id=interaction.user.id, rows=all_entries)
        await interaction.response.send_message(embed=view._embed(), view=view, ephemeral=True)


    @bot.tree.command(
        name="delinfo",
        description="[Owner] Remove uma entrada da memória factual pelo ID.",
    )
    @app_commands.describe(id="ID da entrada mostrado no /listinfo")
    async def delinfo(interaction: discord.Interaction, id: int):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "❌ Apenas owners podem remover memórias.", ephemeral=True
            )
        removed = await delete_memory(id)
        if removed:
            await interaction.response.send_message(
                f"🗑️ Entrada `#{id}` removida.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Nenhuma entrada com ID `#{id}`.", ephemeral=True
            )
