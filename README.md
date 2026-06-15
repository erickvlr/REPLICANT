# REPLICANT v0.5-clean — Discord AI Brain

Bot Discord com IA para servidor de jogos.

## O que esta versão tem

- Prefix commands `r!`
- IA com memória social passiva
- Pesquisa silenciosa quando a IA não sabe algo
- Regras determinísticas validadas pelo código
- Embed tutorial com vídeo/imagem
- SQLite com trava assíncrona

## Removido nesta versão

- DiscordBox para anexos
- Roteiro por prefix command

## Comandos

```txt
r!help
r!lista
r!criarembed #canal [título]
r!embed #canal [título]
r!tutorial #canal [título]
r!embeddemo #canal
```

## Pesquisa silenciosa

A IA pode pedir pesquisa internamente. O bot pesquisa sem avisar o usuário e depois responde.

Regra anti-alucinação:
- se a pesquisa falhar, a IA deve dizer que não tem dados confiáveis;
- ela não pode inventar fonte, link, versão, preço ou regra.

## Segurança

A IA não executa ações críticas. Ela sugere; o código valida.
Tokens reais não devem ser commitados.
