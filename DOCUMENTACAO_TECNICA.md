# Sistema de Aprovação de Conteúdo — Documentação Técnica

**Projeto:** forster-aprovacoes  
**Criado em:** março de 2026  
**Repositório:** https://github.com/oiforster/forster-aprovacoes  
**Site:** https://oiforster.github.io/forster-aprovacoes  
**Última atualização:** março de 2026

---

## Contexto e problema

A Forster Filmes aprovava postagens com clientes via grupo de WhatsApp — prático para o cliente, mas sem registro formal, sem rastreabilidade e dependente de a Silvana lembrar de cobrar cada cliente. A solução precisava:

- Funcionar pelo WhatsApp (canal já no dia a dia dos clientes)
- Abrir bem no celular, sem login, sem app para instalar
- Registrar respostas automaticamente
- Não exigir que a Silvana aprenda um sistema novo
- Mostrar as artes reais (imagem, carrossel, vídeo) para o cliente aprovar

---

## Arquitetura do sistema

```
Obsidian (.md)              Google Drive (Posts_Fixos/ + Videos/)
      │                             │
      └──────────┬──────────────────┘
                 ▼
        gerar_aprovacoes.py
        (roda no Mac da Silvana)
                 │
                 ▼
        HTML de aprovação
        (gerado localmente)
                 │
          git push
                 │
                 ▼
        GitHub (oiforster/forster-aprovacoes)
                 │
          GitHub Pages (deploy automático)
                 │
                 ▼
        https://oiforster.github.io/forster-aprovacoes/
                 │
          link enviado via WhatsApp
                 │
                 ▼
        Cliente aprova no celular
                 │
          (próxima fase)
                 │
                 ▼
        Respostas chegam formatadas no WhatsApp da Silvana
```

---

## Estrutura do repositório

```
forster-aprovacoes/
├── aprovacao/
│   ├── template.html                    ← template base de todas as páginas
│   └── [slug-cliente]/
│       ├── index.html                   ← sempre aponta para a versão mais recente
│       └── YYYY-MM-DD.html              ← página gerada por semana ou mês
├── scripts/
│   ├── gerar_aprovacoes.py              ← script principal
│   ├── subir_reels.py                   ← upload de Reels ao YouTube
│   ├── youtube_credentials.json         ← NUNCA commitar (no .gitignore)
│   └── youtube_token.json               ← NUNCA commitar (no .gitignore)
├── index.html                           ← página inicial do site
├── netlify.toml                         ← headers HTTP (mantido mesmo no GitHub Pages)
├── GUIA_SILVANA.md                      ← manual de uso para a Silvana
├── DOCUMENTACAO_TECNICA.md              ← este arquivo
└── Gerar Aprovações.command             ← duplo clique para gerar + publicar
```

---

## Componentes

### 1. `scripts/gerar_aprovacoes.py`

Script Python principal. Roda no Mac da Silvana (ou do Samuel).

**Funções principais:**

| Função | O que faz |
|--------|-----------|
| `encontrar_pasta_agencia()` | Detecta o caminho NFD da pasta `Agência/` no Google Drive |
| `gdrive_id_para_url(path)` | Lê o xattr `com.google.drivefs.item-id#S` do arquivo e retorna URL `lh3.googleusercontent.com/d/ID` |
| `encontrar_pasta_entrega(data, pasta_cliente)` | Encontra `06_Entregas/YYYY-MM*/` e retorna `(pasta_entrega, pasta_videos)` |
| `encontrar_arte(data, pasta_cliente)` | Busca arte em `Posts_Fixos/` da pasta de entrega; detecta imagem única (`DD-MM.jpg`) ou carrossel (`DD-MM_1.jpg`...) |
| `ler_youtube_id(pasta_videos, reel_nome)` | Lê `Videos/_youtube.md` e retorna o YouTube ID pelo nome do Reel |
| `extrair_partes_post(texto_secao)` | Faz parse da seção do post: texto do card, legenda, slides, link de mídia, nome do reel |
| `gerar_html_post(post)` | Gera o HTML de um card de post (com arte, carrossel ou YouTube facade) |
| `gerar_pagina_aprovacao(...)` | Monta a página HTML completa a partir do template |

**Detalhes técnicos:**

- Encoding NFD/NFC: o Google Drive sincroniza `Agência` em NFD no macOS. O script usa `os.listdir()` para encontrar o caminho real antes de qualquer operação
- xattr: atributo `com.google.drivefs.item-id#S` (com sufixo `#S`) contém o Drive File ID. Se o arquivo estiver em modo Streaming (não baixado), o script força a leitura de 4KB, aguarda 1,5s e tenta novamente
- URL de imagem: `https://lh3.googleusercontent.com/d/FILE_ID` (o endpoint `uc?export=view` foi descontinuado)
- Campo `**Vídeo:**` no .md: suporta valor na mesma linha (`**Vídeo:** REEL 01 – Nome`) ou na linha seguinte (`**Vídeo:**\nREEL 01 – Nome`)

**Argumentos CLI:**

```bash
--cliente "Nome"      # filtra por cliente (parcial aceito)
--semana YYYY-MM-DD   # segunda-feira da semana
--mes YYYY-MM         # mês completo
```

---

### 2. `scripts/subir_reels.py`

Script Python para upload de Reels ao YouTube. Roda no Mac do Samuel antes de gerar aprovações.

**Fluxo:**
1. Busca `06_Entregas/YYYY-MM*/Videos/REEL NN – Nome.mov` do cliente
2. Faz upload como vídeo não listado (unlisted) no YouTube
3. Se existir `REEL NN – Nome (capa).jpg`, sobe como thumbnail
4. Salva o resultado em `Videos/_youtube.md` com a chave sendo o nome do Reel (sem extensão)

**Formato do `_youtube.md`:**
```
# YouTube IDs dos Reels — gerado automaticamente
REEL 12 - Dia da Mulher: https://youtu.be/yjkHNpIlEsA
```

**Dependências:** `google-api-python-client`, `google-auth-oauthlib`  
**Instalação:** `pip3 install --user google-api-python-client google-auth-oauthlib`

**Credenciais OAuth:**
- Arquivo: `scripts/youtube_credentials.json` (baixar do Google Cloud Console)
- Projeto: Google Cloud Console → APIs & Services → forster-aprovacoes
- API habilitada: YouTube Data API v3
- App em modo de teste → Samuel adicionado como test user
- Token salvo em `scripts/youtube_token.json` após primeira autenticação

**Detecção de vídeo já enviado:** o script lê o `_youtube.md` e pula arquivos cujo nome já está registrado.

---

### 3. `aprovacao/template.html`

Template HTML base. Substituições feitas pelo `gerar_aprovacoes.py`:

| Placeholder | Substituído por |
|-------------|----------------|
| `{{TITULO_PAGINA}}` | Nome do cliente + período |
| `{{NOME_CLIENTE}}` | Nome do cliente |
| `{{PERIODO}}` | Ex: "Semana de 23 a 29 de março" |
| `{{TOTAL_POSTS}}` | Número total de posts |
| `{{SEMANAS_NAV}}` | HTML da navegação por semanas (se > 1 semana) |
| `{{POSTS_HTML}}` | HTML de todos os cards de post |
| `{{FORM_ID}}` | ID único do formulário |

**Comportamento do vídeo (Reel):**
- Exibe facade: thumbnail do YouTube (`img.youtube.com/vi/ID/maxresdefault.jpg`) com botão play overlay
- **Mobile** (`ontouchstart` detectado): toque abre `youtu.be/ID` no app do YouTube
- **Desktop**: toque substitui a facade por iframe inline 9:16 com autoplay

**Carrossel:**
- CSS `scroll-snap-type: x mandatory` + `-webkit-overflow-scrolling: touch`
- Contador "1 / N" no canto superior direito
- Dots de navegação embaixo
- Setas prev/next visíveis apenas em dispositivos com hover (desktop)

**Espaçamento entre posts:**
- Semana única: posts são filhos diretos de `.posts-container` (flexbox, `gap: 28px`)
- Múltiplas semanas: posts ficam dentro de `.semana-bloco` (também flexbox com `gap: 28px`)

---

### 4. `Gerar Aprovações.command`

Arquivo bash executável por duplo clique no macOS. Abre o Terminal, roda `gerar_aprovacoes.py` e faz `git push` automaticamente.

---

## Hospedagem

**GitHub Pages** (desde março de 2026)

- URL: `https://oiforster.github.io/forster-aprovacoes/`
- Deploy: automático a cada `git push` na branch `main`
- Gratuito, sem limites de banda que pausem o site
- Anteriormente hospedado no Netlify (pausado por limite de uso do plano gratuito)

**Headers HTTP** (configurados no `netlify.toml`, compatível com ambos):
- HTML: `Cache-Control: no-cache, no-store, must-revalidate`
- Outros: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`

---

## Fluxo de trabalho mensal (Samuel + Silvana)

1. **Samuel** edita, exporta e nomeia os Reels: `REEL NN – Nome.mov` + `REEL NN – Nome (capa).jpg` na pasta `Videos/`
2. **Samuel** roda `subir_reels.py` → vídeos sobem ao YouTube como unlisted, `_youtube.md` é atualizado
3. **Silvana** adiciona as artes em `Posts_Fixos/` com os nomes no padrão `DD-MM.jpg` / `DD-MM_N.jpg`
4. **Silvana** verifica se o campo `**Vídeo:**` está preenchido no `.md` para posts que são Reels
5. **Silvana** dá duplo clique em `Gerar Aprovações.command`
6. Sistema gera as páginas HTML e faz `git push` automaticamente
7. **Silvana** copia a mensagem de WhatsApp e manda para o cliente
8. Cliente aprova pelo link no celular

---

## Clientes configurados

Qualquer cliente em `_Clientes/Clientes Recorrentes/` com arquivo `YYYY-MM — Conteúdo Mensal [Cliente].md` é detectado automaticamente.

Atualmente testado com: **Prisma Especialidades**

---

## Pendências e próximos passos

### Alta prioridade

- [ ] **Retorno do cliente via WhatsApp:** ao clicar em "Enviar aprovações", a página gera uma mensagem formatada e abre o WhatsApp da Silvana com os status de cada post. Substitui a necessidade de formulário server-side. Funciona 100% com GitHub Pages (sem backend).

### Média prioridade

- [ ] **Botão "Subir Reel" no .command:** integrar o `subir_reels.py` no fluxo do `Gerar Aprovações.command` para que a Silvana (ou Samuel) faça tudo em um duplo clique
- [ ] **Atualização automática do .md com retorno do cliente:** após receber o WhatsApp de aprovação, script que parseia a mensagem e adiciona seção "Retorno do Cliente" no `.md` do mês

### Baixa prioridade

- [ ] Expandir para todos os clientes recorrentes (testar estrutura de pastas de cada um)
- [ ] Suporte a vídeos do YouTube (formato YT) além de Reels

---

## Referências técnicas

- xattr no macOS Drive File Stream: atributo `com.google.drivefs.item-id#S`
- Embed de imagem do Drive: `https://lh3.googleusercontent.com/d/FILE_ID`
- YouTube Data API v3: upload + thumbnails com OAuth 2.0
- Scopes necessários: `youtube.upload` + `youtube` (para thumbnails)
- NFD/NFC no macOS: Google Drive usa NFD para `Agência`, Python usa NFC por padrão → usar `os.listdir()` para encontrar o path real
