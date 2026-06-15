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
