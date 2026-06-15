"""
/embed — Cria e envia um embed rico em qualquer canal.

Fluxo:
  1. /embed #canal [video:arquivo] [imagem:arquivo]
  2. Modal: Titulo, Conteudo, Rodape, Cor hex
  3. Prévia EPHEMERAL (só o editor vê): Enviar | Editar | Cancelar
  4. Enviar → embed + vídeo/imagem enviados ao canal como anexo
             Discord renderiza o vídeo como player inline abaixo do embed
"""
import discord
from discord import app_commands
from discord.ext import commands
from config.settings import settings
from config.permissions import is_owner
from database.sqlite import execute


def _parse_color(hex_str: str) -> int:
    hex_str = (hex_str or "").strip().lstrip("#")
    try:
        return int(hex_str, 16)
    except ValueError:
        return settings.embed_color


def _build_embed(titulo: str, conteudo: str, rodape: str, cor: int,
                 image_url: str = "") -> discord.Embed:
    """Monta o embed. Vídeo NÃO entra no embed — é enviado como anexo separado."""
    embed = discord.Embed(
        title=titulo[:256] if titulo else None,
        description=conteudo[:4000],
        color=cor,
    )
    if rodape:
        embed.set_footer(text=rodape[:2048])
    if image_url:
        embed.set_image(url=image_url)
    return embed


class EmbedPreviewView(discord.ui.View):
    def __init__(self, author_id: int, canal: discord.TextChannel,
                 titulo: str, conteudo: str, rodape: str, cor: int,
                 video_attachment, imagem_attachment):
        super().__init__(timeout=600)
        self.author_id       = author_id
        self.canal           = canal
        self.titulo          = titulo
        self.conteudo        = conteudo
        self.rodape          = rodape
        self.cor             = cor
        self.video_attachment  = video_attachment
        self.imagem_attachment = imagem_attachment

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Esse painel não é seu.", ephemeral=True)
            return False
        return True

    # ── Enviar ──────────────────────────────────────────────────
    @discord.ui.button(label="Enviar", style=discord.ButtonStyle.success, emoji="✅")
    async def btn_enviar(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        # Imagem inline no embed via set_image
        if self.imagem_attachment:
            try:
                img_file  = await self.imagem_attachment.to_file()
                image_url = f"attachment://{self.imagem_attachment.filename}"
                embed     = _build_embed(self.titulo, self.conteudo, self.rodape, self.cor, image_url)
                img_files = [img_file]
            except Exception:
                embed     = _build_embed(self.titulo, self.conteudo, self.rodape, self.cor)
                img_files = []
        else:
            embed     = _build_embed(self.titulo, self.conteudo, self.rodape, self.cor)
            img_files = []

        try:
            all_files = list(img_files)
            if self.video_attachment:
                try:
                    all_files.append(await self.video_attachment.to_file())
                except Exception:
                    pass

            # Tudo numa só mensagem — Discord renderiza embed + vídeo colados
            await self.canal.send(
                embed=embed,
                files=all_files if all_files else discord.utils.MISSING,
            )

            await execute(
                "INSERT OR REPLACE INTO embed_templates "
                "(name, title, description, video_url, image_url, created_by) VALUES (?,?,?,?,?,?)",
                (
                    self.titulo.lower()[:100] if self.titulo else "sem-titulo",
                    self.titulo, self.conteudo,
                    self.video_attachment.url if self.video_attachment else "",
                    self.imagem_attachment.url if self.imagem_attachment else "",
                    interaction.user.id,
                ),
            )
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(
                content=f"✅ Embed enviado em {self.canal.mention}!", embed=None, view=self
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Sem permissão para enviar em {self.canal.mention}.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

    # ── Editar ───────────────────────────────────────────────────
    @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="✏️")
    async def btn_editar(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check(interaction):
            return
        modal = EmbedBuilderModal(
            canal=self.canal,
            video_attachment=self.video_attachment,
            imagem_attachment=self.imagem_attachment,
            titulo_default=self.titulo,
            conteudo_default=self.conteudo,
            rodape_default=self.rodape,
            cor_default=f"#{self.cor:06X}",
            original_interaction=interaction,
        )
        await interaction.response.send_modal(modal)

    # ── Cancelar ─────────────────────────────────────────────────
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_cancelar(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check(interaction):
            return
        await interaction.message.delete()


class EmbedBuilderModal(discord.ui.Modal, title="Criar Embed"):
    def __init__(self, canal, video_attachment=None, imagem_attachment=None,
                 titulo_default="", conteudo_default="", rodape_default="",
                 cor_default="", original_interaction=None):
        super().__init__()
        self.canal               = canal
        self.video_attachment    = video_attachment
        self.imagem_attachment   = imagem_attachment
        self.original_interaction = original_interaction

        self.titulo_field = discord.ui.TextInput(
            label="Título",
            placeholder="Título do embed (opcional)",
            default=titulo_default,
            max_length=256,
            required=False,
        )
        self.conteudo_field = discord.ui.TextInput(
            label="Conteúdo",
            style=discord.TextStyle.paragraph,
            placeholder="Texto principal. Suporta markdown do Discord.",
            default=conteudo_default,
            max_length=4000,
            required=True,
        )
        self.rodape_field = discord.ui.TextInput(
            label="Rodapé (opcional)",
            placeholder="Texto pequeno no rodapé",
            default=rodape_default,
            max_length=2048,
            required=False,
        )
        self.cor_field = discord.ui.TextInput(
            label="Cor hex (opcional)",
            placeholder="Ex: #FF5733  — deixe vazio para cor padrão",
            default=cor_default,
            max_length=9,
            required=False,
        )

        self.add_item(self.titulo_field)
        self.add_item(self.conteudo_field)
        self.add_item(self.rodape_field)
        self.add_item(self.cor_field)

    async def on_submit(self, interaction: discord.Interaction):
        titulo   = self.titulo_field.value.strip()
        conteudo = self.conteudo_field.value.strip()
        rodape   = self.rodape_field.value.strip()
        cor      = _parse_color(self.cor_field.value)

        # Preview usa imagem via URL do Discord (CDN) — não precisa baixar o arquivo
        preview_image_url = self.imagem_attachment.url if self.imagem_attachment else ""
        preview_embed = _build_embed(titulo, conteudo, rodape, cor, preview_image_url)

        # Indicador de mídia anexada — só o editor vê na prévia ephemeral
        indicadores = []
        if self.video_attachment:
            indicadores.append("📹 Vídeo anexado")
        if self.imagem_attachment:
            indicadores.append("🖼️ Imagem anexada")
        preview_note = "  •  ".join(indicadores) if indicadores else ""

        view = EmbedPreviewView(
            author_id=interaction.user.id,
            canal=self.canal,
            titulo=titulo,
            conteudo=conteudo,
            rodape=rodape,
            cor=cor,
            video_attachment=self.video_attachment,
            imagem_attachment=self.imagem_attachment,
        )

        content = f"**Prévia** → {self.canal.mention}"
        if preview_note:
            content += f"  |  {preview_note}"

        # Se veio de "Editar", atualiza a mensagem ephemeral existente
        if self.original_interaction:
            try:
                await interaction.response.defer(ephemeral=True)
                await self.original_interaction.edit_original_response(
                    content=content, embed=preview_embed, view=view
                )
                return
            except Exception:
                pass

        # Primeira abertura — envia ephemeral novo
        await interaction.response.send_message(
            content=content,
            embed=preview_embed,
            view=view,
            ephemeral=True,
        )


def setup_slash_embed_commands(bot: commands.Bot):

    @bot.tree.command(
        name="embed",
        description="Cria e envia um embed customizado em qualquer canal.",
    )
    @app_commands.describe(
        canal="Canal onde o embed será enviado",
        video="Vídeo para exibir no embed (será reproduzido inline)",
        imagem="Imagem para exibir dentro do embed",
    )
    async def slash_embed(
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        video: discord.Attachment = None,
        imagem: discord.Attachment = None,
    ):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "Apenas owners podem criar embeds.", ephemeral=True
            )

        if video and not (video.content_type or "").startswith("video/"):
            return await interaction.response.send_message(
                "O parâmetro `video` deve ser um arquivo de vídeo.", ephemeral=True
            )
        if imagem and not (imagem.content_type or "").startswith("image/"):
            return await interaction.response.send_message(
                "O parâmetro `imagem` deve ser um arquivo de imagem.", ephemeral=True
            )

        modal = EmbedBuilderModal(
            canal=canal,
            video_attachment=video,
            imagem_attachment=imagem,
        )
        await interaction.response.send_modal(modal)
