# REPLICANT

# 🤖 IA Inteligente para Discord

REPLICANT é um cérebro de IA modular desenvolvido em Python para servidores Discord, com foco em comunidades de jogos, suporte técnico e automação inteligente.

## ✨ Recursos

- 🧠 IA contextual com memória persistente
- 💬 Aprendizado do estilo do servidor
- 🌐 Compatível com Ollama Cloud, Ollama Local, OpenRouter, Groq e APIs OpenAI-Compatible
- 🔍 Pesquisa silenciosa com proteção contra alucinações
- 📚 Histórico de conversas
- ⚡ Sistema de regras validado pelo código
- 🎨 Embeds personalizados
- 🗄️ SQLite com acesso assíncrono

## Arquitetura

Discord
↓
Router de Mensagens
↓
Brain
├── Memória Social
├── Pesquisa Silenciosa
├── Matcher de Regras
└── TextLLM
↓
Resposta

## Estrutura

```
replicant/
├── bot/
├── brain/
├── config/
├── database/
├── llm/
├── memory/
├── rules/
├── tools/
├── utils/
├── data/
├── main.py
├── requirements.txt
└── .env.example
```

## Configuração

Tudo é configurado pelo `.env`.

Providers suportados:

- Ollama Cloud
- Ollama Local
- OpenRouter
- Groq
- OpenAI Compatible

## Filosofia

A IA pode sugerir ações, porém decisões críticas sempre são validadas pelo código.

## Memória Social

O sistema aprende:

- gírias
- emojis
- tom do servidor
- contexto do canal
- histórico do usuário

sem copiar informações privadas.

## Pesquisa Silenciosa

Quando necessário, o REPLICANT pesquisa automaticamente e responde usando apenas informações confiáveis, evitando inventar fatos.

## Comandos

```
r!help
r!lista
r!criarembed
r!embed
r!tutorial
r!embeddemo
```

## Tecnologias

- Python 3.11+
- discord.py
- httpx
- rich
- SQLite
- asyncio

## Roadmap

- Visão em tempo real
- Plugins
- Dashboard Web
- Streaming de resposta
- MCP
- Multiagentes

## Licença

Projeto experimental para fins educacionais e comunitários.
Desenvolvido por Erickdev 

# 🚀 Instalação

## 1. Clone o repositório

```bash
git clone https://github.com/seuusuario/Replicant.git
cd Replicant
```

## 2. Crie um ambiente virtual

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Instale as dependências

```bash
pip install -r requirements.txt
```

## 4. Configure o arquivo `.env`

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

ou no Windows:

```bash
copy .env.example .env
```

Depois preencha:

- `DISCORD_TOKEN`
- `OWNER_IDS`
- `GUILD_ID`
- `LLM_PROVIDER`
- API Key do provedor escolhido (Ollama Cloud, OpenRouter, Groq ou outro)

## ▶️ Executando

Inicie o bot:

```bash
python main.py
```

Se tudo estiver correto, o console exibirá o banner do **REPLICANT** e o bot ficará online no Discord.

# ⚙️ Configuração

Toda a configuração é centralizada no arquivo `.env`.

Provedores suportados:

- Ollama Cloud
- Ollama Local
- OpenRouter
- Groq
- APIs OpenAI-Compatible

Não é necessário alterar o código para trocar de modelo ou provedor, basta modificar o `.env`.

# 💬 Como usar

Após iniciar o bot:

- Convide-o para o servidor.
- Utilize o prefixo configurado (`r!` por padrão).
- Digite:

```text
r!help
```

para visualizar todos os comandos disponíveis.

O REPLICANT também responde automaticamente quando é mencionado ou quando identifica pedidos de ajuda, utilizando memória social, contexto da conversa e pesquisa silenciosa quando necessário.
