"""
/regras — Painel de gerenciamento de regras estilo Pub's Bot.

Fluxo:
  1. /regras #canal → painel ephemeral com [Criar Regra] [Gerenciar Regras]
  2. Criar Regra → Modal: Nome, Gatilhos, Canais, Resposta (markdown)
  3. Prévia → embed com todos os campos + botões Publicar/Editar/Cancelar
  4. Publicado: embed rico no canal com campos de metadados + conteúdo formatado
  5. Gerenciar → lista paginada com botão Deletar por regra
"""
import discord
from discord import app_commands
from discord.ext import commands
from config.permissions import is_owner
from database.sqlite import execute, fetchall, fetchone


# ── Cores ──────────────────────────────────────────────────────────────────────
_COLOR_RULE  = 0x57F287   # verde
_COLOR_PANEL = 0x5865F2   # blurple


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_rule_embed(nome: str, gatilhos: str, canais: str,
                      resposta: str, attachment_url: str = "") -> discord.Embed:
    embed = discord.Embed(color=_COLOR_RULE)

    meta = []
    meta.append(f"🚀 **Nome:** {nome}" if nome else "🚀 **Nome:** —")
    meta.append(f"🎯 **Gatilhos:** {gatilhos}" if gatilhos else "🎯 **Gatilhos:** —")
    meta.append(f"🌐 **Canais:** {canais}" if canais else "🌐 **Canais:** todos")
    meta.append(f"📎 **Anexo:** {attachment_url}" if attachment_url else "📎 **Anexo:** —")
    embed.description = "\n".join(meta)

    if resposta:
        embed.add_field(name="💬 Resposta:", value=resposta[:1024], inline=False)
        # Se resposta for longa demais para um field, divide em blocos
        rest = resposta[1024:]
        while rest:
            embed.add_field(name="​", value=rest[:1024], inline=False)
            rest = rest[1024:]

    return embed


# ── Painel principal ───────────────────────────────────────────────────────────

class RulesPanelView(discord.ui.View):
    def __init__(self, author_id: int, canal: discord.TextChannel):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.canal     = canal

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Esse painel não é seu.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Criar Regra", style=discord.ButtonStyle.success, emoji="➕")
    async def btn_criar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        await interaction.response.send_modal(
            RuleModal(canal=self.canal, original_interaction=interaction)
        )

    @discord.ui.button(label="Gerenciar Regras", style=discord.ButtonStyle.primary, emoji="🛠️")
    async def btn_gerenciar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        rows = await fetchall("SELECT id, name, triggers FROM rules ORDER BY id ASC")
        if not rows:
            await interaction.edit_original_response(
                content="Nenhuma regra cadastrada ainda.",
                embed=None, view=None,
            )
            return
        view = ManageRulesView(author_id=self.author_id, rows=list(rows), page=0)
        await interaction.edit_original_response(
            content=None,
            embed=view.build_embed(),
            view=view,
        )


# ── Modal de criação/edição ────────────────────────────────────────────────────

class RuleModal(discord.ui.Modal, title="Criar Regra"):
    def __init__(self, canal, rule_id=None,
                 nome_default="", gatilhos_default="",
                 canais_default="", resposta_default="",
                 original_interaction=None):
        super().__init__()
        self.canal                = canal
        self.rule_id              = rule_id
        self.original_interaction = original_interaction

        self.nome_field = discord.ui.TextInput(
            label="Nome da regra",
            placeholder="Ex: pode usar mod",
            default=nome_default,
            max_length=100,
            required=True,
        )
        self.gatilhos_field = discord.ui.TextInput(
            label="Gatilhos (separados por vírgula)",
            placeholder="Ex: usar + mod, instalar mod, baixar mod",
            default=gatilhos_default,
            max_length=500,
            required=True,
        )
        self.canais_field = discord.ui.TextInput(
            label="Canais (opcional — nomes separados por vírgula)",
            placeholder="Ex: dúvidas-suporte, geral  — vazio = todos",
            default=canais_default,
            max_length=300,
            required=False,
        )
        self.resposta_field = discord.ui.TextInput(
            label="Resposta (suporta markdown do Discord)",
            style=discord.TextStyle.paragraph,
            placeholder="**negrito**  `código`  ✅ item\n> citação  ### título",
            default=resposta_default,
            max_length=2000,
            required=True,
        )

        self.add_item(self.nome_field)
        self.add_item(self.gatilhos_field)
        self.add_item(self.canais_field)
        self.add_item(self.resposta_field)

    async def on_submit(self, interaction: discord.Interaction):
        nome     = self.nome_field.value.strip()
        gatilhos = self.gatilhos_field.value.strip()
        canais   = self.canais_field.value.strip()
        resposta = self.resposta_field.value.strip()

        embed = _build_rule_embed(nome, gatilhos, canais, resposta)
        view  = RulePreviewView(
            author_id=interaction.user.id,
            canal=self.canal,
            nome=nome,
            gatilhos=gatilhos,
            canais=canais,
            resposta=resposta,
            rule_id=self.rule_id,
        )
        content = f"**Prévia da regra** → {self.canal.mention}"

        if self.original_interaction:
            try:
                await interaction.response.defer(ephemeral=True)
                await self.original_interaction.edit_original_response(
                    content=content, embed=embed, view=view
                )
                return
            except Exception:
                pass

        await interaction.response.send_message(
            content=content, embed=embed, view=view, ephemeral=True
        )


# ── Preview de regra ───────────────────────────────────────────────────────────

class RulePreviewView(discord.ui.View):
    def __init__(self, author_id, canal, nome, gatilhos, canais, resposta,
                 rule_id=None):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.canal     = canal
        self.nome      = nome
        self.gatilhos  = gatilhos
        self.canais    = canais
        self.resposta  = resposta
        self.rule_id   = rule_id

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Esse painel não é seu.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Publicar", style=discord.ButtonStyle.success, emoji="📢")
    async def btn_publicar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        try:
            # Salva ou atualiza no banco
            if self.rule_id:
                await execute(
                    "UPDATE rules SET name=?, triggers=?, channels=?, reply=? WHERE id=?",
                    (self.nome, self.gatilhos, self.canais, self.resposta, self.rule_id),
                )
            else:
                await execute(
                    "INSERT OR REPLACE INTO rules (name, triggers, channels, reply) VALUES (?,?,?,?)",
                    (self.nome, self.gatilhos, self.canais, self.resposta),
                )

            embed = _build_rule_embed(self.nome, self.gatilhos, self.canais, self.resposta)
            await self.canal.send(embed=embed)

            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(
                content=f"✅ Regra **{self.nome}** publicada em {self.canal.mention}!",
                embed=None, view=self,
            )
        except discord.Forbidden:
            await interaction.followup.send(f"❌ Sem permissão em {self.canal.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

    @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="✏️")
    async def btn_editar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        await interaction.response.send_modal(
            RuleModal(
                canal=self.canal,
                rule_id=self.rule_id,
                nome_default=self.nome,
                gatilhos_default=self.gatilhos,
                canais_default=self.canais,
                resposta_default=self.resposta,
                original_interaction=interaction,
            )
        )

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_cancelar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        await interaction.message.delete()


# ── Gerenciar regras ───────────────────────────────────────────────────────────

_PAGE_SIZE = 5

class ManageRulesView(discord.ui.View):
    def __init__(self, author_id: int, rows: list, page: int = 0):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.rows      = rows
        self.page      = page
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.clear_items()
        start = self.page * _PAGE_SIZE
        page_rows = self.rows[start:start + _PAGE_SIZE]

        for row in page_rows:
            btn = discord.ui.Button(
                label=f"🗑️ {row['name'][:40]}",
                style=discord.ButtonStyle.danger,
                custom_id=f"del_{row['id']}",
            )
            btn.callback = self._make_delete_callback(row['id'], row['name'])
            self.add_item(btn)

        total_pages = max(1, -(-len(self.rows) // _PAGE_SIZE))
        if self.page > 0:
            prev = discord.ui.Button(label="◀ Anterior", style=discord.ButtonStyle.secondary)
            prev.callback = self._make_page_callback(self.page - 1)
            self.add_item(prev)
        if self.page < total_pages - 1:
            nxt = discord.ui.Button(label="Próxima ▶", style=discord.ButtonStyle.secondary)
            nxt.callback = self._make_page_callback(self.page + 1)
            self.add_item(nxt)

    def build_embed(self) -> discord.Embed:
        start = self.page * _PAGE_SIZE
        page_rows = self.rows[start:start + _PAGE_SIZE]
        total_pages = max(1, -(-len(self.rows) // _PAGE_SIZE))

        lines = []
        for row in page_rows:
            trigs = (row['triggers'] or '')[:60]
            lines.append(f"**{row['name']}** — `{trigs}`")

        embed = discord.Embed(
            title=f"🛠️ Regras Cadastradas — Página {self.page+1}/{total_pages}",
            description="\n".join(lines) or "Nenhuma regra.",
            color=_COLOR_PANEL,
        )
        embed.set_footer(text="Clique no botão da regra para deletá-la.")
        return embed

    def _make_delete_callback(self, rule_id: int, rule_name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("Esse painel não é seu.", ephemeral=True)
            await execute("DELETE FROM rules WHERE id=?", (rule_id,))
            self.rows = [r for r in self.rows if r['id'] != rule_id]
            if self.page * _PAGE_SIZE >= len(self.rows) and self.page > 0:
                self.page -= 1
            self._refresh_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        return callback

    def _make_page_callback(self, new_page: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("Esse painel não é seu.", ephemeral=True)
            self.page = new_page
            self._refresh_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        return callback


# ── Setup ──────────────────────────────────────────────────────────────────────

def setup_slash_regras_commands(bot: commands.Bot):

    @bot.tree.command(
        name="regras",
        description="[Owner] Abre o painel de gerenciamento de regras.",
    )
    @app_commands.describe(
        canal="Canal onde as regras serão publicadas",
    )
    async def slash_regras(
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "Apenas owners podem gerenciar regras.", ephemeral=True
            )

        embed = discord.Embed(
            title="⚙️ Painel de Regras",
            description=(
                f"Canal de destino: {canal.mention}\n\n"
                "Use os botões abaixo para criar ou gerenciar regras."
            ),
            color=_COLOR_PANEL,
        )
        await interaction.response.send_message(
            embed=embed,
            view=RulesPanelView(author_id=interaction.user.id, canal=canal),
            ephemeral=True,
        )
