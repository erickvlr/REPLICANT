"""
/pub — Publica mensagem de texto com vídeo no final.

Fluxo:
  1. /pub #canal [video_arquivo:arquivo] [video_link:url]
  2. Modal: Título (opcional), Conteúdo
  3. Prévia ephemeral → Publicar | Editar | Cancelar
  4. Envio: mensagem de texto pura → depois vídeo (link ou arquivo)
"""
import discord
from discord import app_commands
from discord.ext import commands
from config.permissions import is_owner


# ── Preview View ─────────────────────────────────────────────────────────────

class PubPreviewView(discord.ui.View):
    def __init__(self, author_id, canal, titulo, conteudo,
                 video_attachment, video_link, video_label):
        super().__init__(timeout=600)
        self.author_id        = author_id
        self.canal            = canal
        self.titulo           = titulo
        self.conteudo         = conteudo
        self.video_attachment = video_attachment
        self.video_link       = video_link
        self.video_label      = video_label

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Esse painel não é seu.", ephemeral=True)
            return False
        return True

    def _build_text(self) -> str:
        parts = []
        if self.titulo:
            parts.append(f"**{self.titulo}**")
        if self.conteudo:
            parts.append(self.conteudo)
        return "\n".join(parts)

    @discord.ui.button(label="Publicar", style=discord.ButtonStyle.success, emoji="📢")
    async def btn_publicar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        try:
            texto = self._build_text()

            # 1ª mensagem: texto puro
            await self.canal.send(content=texto)

            # 2ª mensagem: label opcional acima do vídeo
            if self.video_label and (self.video_link or self.video_attachment):
                await self.canal.send(content=self.video_label)

            # 3ª mensagem: vídeo — link ou arquivo, o que estiver disponível
            if self.video_link:
                await self.canal.send(content=self.video_link)
            elif self.video_attachment:
                try:
                    vfile = await self.video_attachment.to_file()
                    await self.canal.send(file=vfile)
                except Exception as e:
                    await interaction.followup.send(f"⚠️ Erro ao enviar vídeo: {e}", ephemeral=True)

            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(
                content=f"✅ Publicado em {self.canal.mention}!", embed=None, view=self
            )
        except discord.Forbidden:
            await interaction.followup.send(f"❌ Sem permissão em {self.canal.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

    @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="✏️")
    async def btn_editar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        modal = PubModal(
            canal=self.canal,
            video_attachment=self.video_attachment,
            video_link=self.video_link,
            titulo_default=self.titulo,
            conteudo_default=self.conteudo,
            video_label_default=self.video_label,
            original_interaction=interaction,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_cancelar(self, interaction: discord.Interaction, _btn):
        if not await self._check(interaction):
            return
        await interaction.message.delete()


# ── Modal ─────────────────────────────────────────────────────────────────────

class PubModal(discord.ui.Modal, title="Nova Publicação"):
    def __init__(self, canal, video_attachment=None, video_link=None,
                 titulo_default="", conteudo_default="", video_label_default="",
                 original_interaction=None):
        super().__init__()
        self.canal                = canal
        self.video_attachment     = video_attachment
        self.video_link           = video_link
        self.original_interaction = original_interaction

        self.titulo_field = discord.ui.TextInput(
            label="Título (opcional)",
            placeholder="Aparece em negrito antes do conteúdo",
            default=titulo_default,
            max_length=256,
            required=False,
        )
        self.conteudo_field = discord.ui.TextInput(
            label="Conteúdo (suporta markdown do Discord)",
            style=discord.TextStyle.paragraph,
            placeholder="**negrito**  `código`  ||spoiler||\n1. item  •  - item\n> citação",
            default=conteudo_default,
            max_length=2000,
            required=True,
        )
        self.video_label_field = discord.ui.TextInput(
            label="Label acima do vídeo (opcional)",
            placeholder="Ex: 🎬  ou  # Veja o vídeo  ou  📽️ Tutorial",
            default=video_label_default,
            max_length=100,
            required=False,
        )

        self.add_item(self.titulo_field)
        self.add_item(self.conteudo_field)
        self.add_item(self.video_label_field)

    async def on_submit(self, interaction: discord.Interaction):
        titulo      = self.titulo_field.value.strip()
        conteudo    = self.conteudo_field.value.strip()
        video_label = self.video_label_field.value.strip()

        # Monta prévia de texto
        preview_parts = []
        if titulo:
            preview_parts.append(f"**{titulo}**")
        preview_parts.append(conteudo)
        if video_label and (self.video_link or self.video_attachment):
            preview_parts.append(f"\n{video_label}")
            preview_parts.append("*(vídeo aqui)*")
        preview_text = "\n".join(preview_parts)

        indicadores = []
        if self.video_link:
            indicadores.append("🔗 Link de vídeo")
        elif self.video_attachment:
            indicadores.append("📹 Vídeo anexado")
        nota = "  •  ".join(indicadores)
        content = f"**Prévia** → {self.canal.mention}" + (f"  |  {nota}" if nota else "")

        view = PubPreviewView(
            author_id=interaction.user.id,
            canal=self.canal,
            titulo=titulo,
            conteudo=conteudo,
            video_attachment=self.video_attachment,
            video_link=self.video_link,
            video_label=video_label,
        )

        if self.original_interaction:
            try:
                await interaction.response.defer(ephemeral=True)
                await self.original_interaction.edit_original_response(
                    content=content + f"\n\n{preview_text}", embed=None, view=view
                )
                return
            except Exception:
                pass

        await interaction.response.send_message(
            content=content + f"\n\n{preview_text}",
            view=view,
            ephemeral=True,
        )


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_slash_pub_commands(bot: commands.Bot):

    @bot.tree.command(
        name="pub",
        description="Publica uma mensagem com vídeo no final.",
    )
    @app_commands.describe(
        canal="Canal onde a publicação será enviada",
        video_arquivo="Arquivo de vídeo para postar após o texto",
        video_link="Link do vídeo (YouTube, Streamable, etc.) para postar após o texto",
    )
    async def slash_pub(
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        video_arquivo: discord.Attachment = None,
        video_link: str = None,
    ):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "Apenas owners podem criar publicações.", ephemeral=True
            )

        if video_arquivo and not (video_arquivo.content_type or "").startswith("video/"):
            return await interaction.response.send_message(
                "O parâmetro `video_arquivo` deve ser um arquivo de vídeo.", ephemeral=True
            )

        await interaction.response.send_modal(
            PubModal(
                canal=canal,
                video_attachment=video_arquivo,
                video_link=video_link,
            )
        )
