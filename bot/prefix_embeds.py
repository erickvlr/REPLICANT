import discord
from discord.ext import commands
from config.settings import settings
from config.permissions import is_owner
from database.sqlite import execute

DEMO_TEXT = '''Somente Jogos Aba Steam

Para mudar linguagem do seu jogo para português brasileiro, segue os passos abaixo:

📁 Como mudar o idioma do seu jogo:

1️⃣ Vá até a pasta do seu jogo;
2️⃣ Procure a pasta chamada: steam_settings
3️⃣ Abra o arquivo chamado: config.user.ini
4️⃣ ADICIONE uma nova linha para a linguagem: language=brazilian
5️⃣ Salve o arquivo com o atalho Ctrl + S
6️⃣ Pronto! Reinicie seu jogo, e ele estará em português brasileiro.

Se isso não funcionar, você pode tentar abrir o arquivo com o Notepad++ e salvá-lo da mesma forma.

Lembre-se de apenas adicionar uma nova linha para a linguagem: language=brazilian
'''

class EmbedModalView(discord.ui.View):
    def __init__(self, author_id: int, canal_id: int):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.canal_id = canal_id

    @discord.ui.button(label="Enviar tutorial demo", style=discord.ButtonStyle.success, emoji="📘")
    async def send_demo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Esse painel não é seu.", ephemeral=True)
        canal = interaction.guild.get_channel(self.canal_id)
        if not canal:
            return await interaction.response.send_message("❌ Canal não encontrado.", ephemeral=True)
        embed = discord.Embed(title="Somente Jogos Aba Steam", description=DEMO_TEXT[:4000], color=settings.embed_color)
        embed.set_footer(text=f"Criado por {interaction.user.display_name}")
        await canal.send(embed=embed)
        await interaction.response.send_message(f"✅ Embed demo enviado em {canal.mention}.", ephemeral=True)

def setup_prefix_embed_commands(bot: commands.Bot):
    @bot.command(name="criarembed", aliases=["embed", "tutorial"])
    async def criarembed(ctx: commands.Context, canal: discord.TextChannel | None = None, *, titulo: str = "Somente Jogos Aba Steam"):
        if not is_owner(ctx.author.id):
            return await ctx.reply("❌ Sem permissão.", mention_author=False)
        canal = canal or ctx.channel
        texto = DEMO_TEXT
        embed = discord.Embed(title=titulo[:256], description=texto[:4000], color=settings.embed_color)
        embed.set_footer(text=f"Criado por {ctx.author.display_name}")
        video_url = ""
        image_url = ""
        files = []
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            content_type = attachment.content_type or ""
            if content_type.startswith("image/"):
                image_url = attachment.url
                embed.set_image(url=attachment.url)
            elif content_type.startswith("video/"):
                video_url = attachment.url
                embed.add_field(name="🎥 Vídeo de demonstração", value=f"[Clique aqui para assistir]({attachment.url})", inline=False)
                files.append(await attachment.to_file())
            else:
                return await ctx.reply("❌ Anexo inválido. Envie imagem ou vídeo.", mention_author=False)
        await canal.send(embed=embed)
        for file in files:
            await canal.send(content="🎥 Demonstração:", file=file)
        await execute(
            "INSERT OR REPLACE INTO embed_templates (name, title, description, video_url, image_url, created_by) VALUES (?, ?, ?, ?, ?, ?)",
            (titulo.lower(), titulo, texto, video_url, image_url, ctx.author.id)
        )
        await ctx.reply(f"✅ Embed enviado em {canal.mention}.", mention_author=False)

    @bot.command(name="embeddemo")
    async def embeddemo(ctx: commands.Context, canal: discord.TextChannel | None = None):
        if not is_owner(ctx.author.id):
            return await ctx.reply("❌ Sem permissão.", mention_author=False)
        canal = canal or ctx.channel
        await ctx.reply(f"Painel aberto para enviar o tutorial demo em {canal.mention}.", view=EmbedModalView(ctx.author.id, canal.id), mention_author=False)
