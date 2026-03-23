# Sistema de Aprovação de Conteúdo — Documentação Técnica

**Projeto:** forster-aprovacoes  
**Criado em:** março de 2026  
**Repositório:** https://github.com/oiforster/forster-aprovacoes  
**Site:** https://oiforster.github.io/forster-aprovacoes  
**Última atualização:** março de 2026 — EmailJS adicionado como redundância de notificação

---

## Contexto e problema

A Forster Filmes aprovava postagens com clientes via grupo de WhatsApp — prático para o cliente, mas sem registro formal e dependente de a Silvana cobrar cada resposta. A solução precisava:

- Funcionar pelo WhatsApp (canal já no dia a dia dos clientes)
- Abrir bem no celular, sem login, sem app para instalar
- Mostrar as artes reais (imagem, carrossel, vídeo) para o cliente aprovar
- Não exigir que a Silvana aprenda um sistema novo

---

## Arquitetura do sistema

```
Obsidian (.md)              Google Drive (Posts_Fixos/ + Videos/)
      │                             │
      └──────────┬──────────────────┘
                 ▼
        Fluxo Completo.command
        (duplo clique no Mac)
                 │
        ┌────────┼────────────────┐
        ▼        ▼                ▼
  validar    subir_reels     gerar_aprovacoes
  _arquivos  .py (YouTube)   .py (HTML)
        │        │                │
        └────────┴────────────────┘
                 │
          git push automático
                 │
                 ▼
        GitHub Pages
        oiforster.github.io/forster-aprovacoes/
                 │
          link enviado via WhatsApp
                 │
                 ▼
        Cliente aprova no celular
                 │
                 ▼
        Mensagem formatada → WhatsApp da Silvana (ou grupo)
                 │
                 ├── (automático, silencioso)
                 ▼
        EmailJS → oiforster@gmail.com
        (redundância — dispara mesmo se o cliente não mandar no WhatsApp)
```

---

## Estrutura do repositório

```
forster-aprovacoes/
├── aprovacao/
│   ├── template.html                    ← template base de todas as páginas
│   └── [slug-cliente]/
│       ├── index.html                   ← sempre aponta para a versão mais recente
│       └── YYYY-MM-DD.html              ← página gerada por semana/período
├── scripts/
│   ├── gerar_aprovacoes.py              ← gerador de páginas HTML
│   ├── subir_reels.py                   ← upload de Reels ao YouTube
│   ├── validar_arquivos.py              ← validação de artes e nomes antes de gerar
│   ├── youtube_credentials.json         ← NUNCA commitar (no .gitignore)
│   └── youtube_token.json               ← NUNCA commitar (no .gitignore)
├── index.html                           ← página inicial do site
├── GUIA_SILVANA.md                      ← manual de uso para a Silvana
├── DOCUMENTACAO_TECNICA.md              ← este arquivo
├── Fluxo Completo.command               ← tudo em um duplo clique
├── Subir Reels YouTube.command          ← upload YouTube standalone
└── Gerar Aprovações.command             ← gerar + publicar (sem validação/YouTube)
```

---

## Componentes

### 1. `Fluxo Completo.command`

Arquivo bash executável por duplo clique. Encadeia as 4 etapas do processo:

1. **Validação** — `validar_arquivos.py` verifica se os arquivos de arte estão na pasta e com os nomes corretos
2. **YouTube** — `subir_reels.py` sobe os Reels como unlisted e atualiza o `_youtube.md`
3. **Geração** — `gerar_aprovacoes.py` gera os HTMLs de aprovação
4. **Publicação** — `git add . && git commit && git push` (pergunta antes de publicar)

**Opções interativas:**
- Qual cliente? (número, nome parcial ou Enter para todos)
- Qual mês? (YYYY-MM ou Enter para o atual)
- Qual período?
  - `1` Próxima semana (padrão)
  - `2` Semana atual
  - `3` Período personalizado (inserir início e fim em DD/MM/AAAA ou AAAA-MM-DD)
- Em caso de erro na validação: continuar mesmo assim? (s/N)
- Em caso de erro no YouTube: continuar gerando páginas? (s/N)
- Publicar no site? (S/n)

**Atenção:** após cada `git reset --hard` ou atualização do repositório, o macOS perde o bit de execução (o Google Drive não preserva permissões Unix). Nesse caso, rodar no Terminal:
```bash
chmod +x ~/Library/...forster-aprovacoes/"Fluxo Completo.command"
chmod +x ~/Library/...forster-aprovacoes/"Subir Reels YouTube.command"
chmod +x ~/Library/...forster-aprovacoes/"Gerar Aprovações.command"
```

---

### 2. `scripts/validar_arquivos.py`

Valida os arquivos de arte e vídeo antes de gerar as páginas de aprovação. Cruza o planejamento do `.md` com o que existe fisicamente nas pastas.

**O que verifica:**
- Posts do tipo Card ou Carrossel: existe `DD-MM.jpg` ou `DD-MM_1.jpg`, `DD-MM_2.jpg`... em `Posts_Fixos/`?
- Posts do tipo Reel: existe `REEL NN – Nome.mov` em `Videos/`? O nome bate com o campo `**Vídeo:**` do `.md`?
- Arquivos órfãos: existem arquivos na pasta que não têm post correspondente no `.md`?
- Near-match de nomes de Reel: avisa quando o arquivo usa hífen no lugar de meia-risca (`–`)

**Saída:** ✅ para OK, ❌ para erro, ⚠️ para aviso. Sai com código 1 se houver erros.

**Argumentos CLI:**
```bash
--cliente "Nome"    # filtra por cliente (parcial aceito)
--mes YYYY-MM       # mês (padrão: mês atual)
--inicio YYYY-MM-DD # início do período personalizado
--fim YYYY-MM-DD    # fim do período personalizado
```

---

### 3. `scripts/gerar_aprovacoes.py`

Script principal. Lê os arquivos `.md` de Conteúdo Mensal e gera as páginas HTML.

**Funções principais:**

| Função | O que faz |
|--------|-----------|
| `encontrar_pasta_agencia()` | Detecta o caminho NFD da pasta `Agência/` no Google Drive |
| `gdrive_id_para_url(path)` | Lê o xattr `com.google.drivefs.item-id#S` e retorna URL `lh3.googleusercontent.com/d/ID` |
| `encontrar_arte(data, pasta_cliente)` | Busca arte em `Posts_Fixos/`; detecta card (`DD-MM.jpg`) ou carrossel (`DD-MM_N.jpg`) |
| `ler_youtube_id(pasta_videos, reel_nome)` | Lê `Videos/_youtube.md` e retorna YouTube ID pelo nome do Reel |
| `parse_conteudo_mensal(arquivo, datas)` | Parse do `.md`: extrai posts do período solicitado |
| `gerar_pagina_aprovacao(...)` | Monta a página HTML completa a partir do template |

**Argumentos CLI:**
```bash
--cliente "Nome"     # filtra por cliente (parcial aceito)
--semana YYYY-MM-DD  # segunda-feira da semana
--mes YYYY-MM        # mês completo
--inicio YYYY-MM-DD  # início do período personalizado
--fim YYYY-MM-DD     # fim do período personalizado
```

**Detalhes técnicos:**
- Encoding NFD/NFC: o Google Drive sincroniza `Agência` em NFD no macOS. O script usa `os.listdir()` para encontrar o caminho real
- xattr: `com.google.drivefs.item-id#S` contém o Drive File ID. Se o arquivo estiver em modo Streaming (não baixado), o script força leitura de 4KB, aguarda 1,5s e tenta novamente
- URL de imagem: `https://lh3.googleusercontent.com/d/FILE_ID` (requer pasta `Posts_Fixos/` compartilhada publicamente no Drive)
- Campo `**Vídeo:**`: suporta valor na mesma linha ou na linha seguinte

---

### 4. `scripts/subir_reels.py`

Upload de Reels ao YouTube como unlisted. Roda no Mac do Samuel.

**Fluxo:**
1. Busca `06_Entregas/YYYY-MM*/Videos/REEL NN – Nome.mov` do cliente
2. Faz upload como vídeo não listado (unlisted)
3. Se existir `REEL NN – Nome (capa).jpg`, sobe como thumbnail
4. Salva em `Videos/_youtube.md` com a chave sendo o nome do Reel (sem extensão)
5. Pula arquivos cujo nome já está registrado no `_youtube.md`

**Formato do `_youtube.md`:**
```
# YouTube IDs dos Reels — gerado automaticamente
REEL 12 - Dia da Mulher: https://youtu.be/jjsriyI-KaQ
```

**Credenciais OAuth:**
- Arquivo: `scripts/youtube_credentials.json` (no .gitignore — nunca commitar)
- Projeto: Google Cloud Console → APIs & Services → forster-aprovacoes
- API habilitada: YouTube Data API v3
- Scopes: `youtube.upload` + `youtube` (para thumbnails)
- Token salvo em `scripts/youtube_token.json` após primeira autenticação
- Se der `invalid_scope`: deletar `youtube_token.json` e autenticar de novo

**Argumentos CLI:**
```bash
--cliente "Nome"     # filtra por cliente
--mes YYYY-MM        # mês (padrão: atual)
--inicio YYYY-MM-DD  # início do período personalizado
--fim YYYY-MM-DD     # fim do período personalizado
```

---

### 5. `aprovacao/template.html`

Template HTML base. Substituições feitas pelo `gerar_aprovacoes.py`:

| Placeholder | Substituído por |
|-------------|----------------|
| `{{TITULO_PAGINA}}` | Nome do cliente + período |
| `{{NOME_CLIENTE}}` | Nome do cliente |
| `{{PERIODO}}` | Ex: "Semana de 23 a 29 de março" |
| `{{TOTAL_POSTS}}` | Número total de posts |
| `{{SEMANAS_NAV}}` | HTML da navegação por semanas (se > 1 semana) |
| `{{POSTS_HTML}}` | HTML de todos os cards de post |
| `{{POSTS_META_JSON}}` | JSON com metadados dos posts (para o JS de aprovação) |
| `{{POSTS_ORDEM_JSON}}` | JSON com a ordem dos posts |
| `{{FORM_ID}}` | ID único do formulário |
| `{{WHATSAPP_SILVANA}}` | Número da Silvana (fallback) |
| `{{WHATSAPP_GRUPO}}` | Link do grupo WhatsApp do cliente (ou vazio) |

**Comportamento de vídeo (Reel):**
- Exibe facade: thumbnail do YouTube com botão play overlay
- Ao clicar: abre overlay `position:fixed` com iframe YouTube em autoplay (9:16)
- Botão ✕ fecha o overlay
- Funciona em celular e desktop sem abrir app externo

**Comportamento pós-envio (page lock):**
- Após clicar "Enviar aprovações": `localStorage.setItem('aprovacao:' + pathname, '1')`
- Na próxima visita: mostra tela "Tudo certo por aqui! Você já enviou suas aprovações desta semana."
- Impede que o cliente envie em duplicata por acidente

**Notificação automática por email (EmailJS):**

Ao clicar "Enviar aprovações", além da mensagem do WhatsApp, o sistema dispara silenciosamente um email de redundância via EmailJS. O cliente não vê esse disparo — acontece em background.

| Campo | Valor |
|-------|-------|
| Provedor | EmailJS (plano gratuito — 200 req/mês) |
| Service ID | `service_a00b37r` |
| Template ID | `template_lyk4lff` |
| Public Key | `-xrMYz7vRGvZg8ZOY` |
| Destino | `oiforster@gmail.com` |
| SDK | `cdn.jsdelivr.net/npm/@emailjs/browser@4` |

Variáveis enviadas ao template:

| Variável | Conteúdo |
|----------|---------|
| `title` | "Aprovações — [Cliente] — [Período]" |
| `name` | Nome do cliente |
| `message` | Resumo completo com ✅/⚠️ e observações |
| `email` | Vazio (não requer reply-to) |

Implementação em `template.html`:
- Linha 631–633: SDK carregado e inicializado com a public key
- Linha 722–730: função `enviarEmailSilencioso()` — erros são silenciosos (não interrompem o fluxo)
- Linha 857–858: chamada disparada dentro de `enviarAprovacao()`, antes de qualquer tela aparecer

**Finalidade:** garante que a Forster Filmes receba o registro das aprovações mesmo que o cliente esqueça de enviar a mensagem no grupo de WhatsApp.

**Retorno via WhatsApp por cliente:**

| Cliente | Canal |
|---------|-------|
| Óticas Casa Marco | Número da Silvana (direto) |
| Colégio Luterano Redentor | Grupo WhatsApp |
| Vanessa Mainardi | Grupo WhatsApp |
| Joele Lerípio | Contato direto Samuel |
| Micheline Twigger | Grupo WhatsApp |
| Fyber Show Piscinas | Grupo WhatsApp |
| Prisma Especialidades | Grupo WhatsApp |
| Martina Schneider | Grupo WhatsApp |
| Catarata Center | Grupo WhatsApp |
| Baviera Tecnologia | Contato direto Samuel |

Quando `WHATSAPP_GRUPO` está preenchido: a mensagem de aprovação é copiada para o clipboard e o grupo é aberto. O cliente cola e envia. Quando vazio: abre `wa.me/NUMERO?text=MENSAGEM` com o número da Silvana.

---

## Hospedagem

**GitHub Pages** (desde março de 2026)

- URL: `https://oiforster.github.io/forster-aprovacoes/`
- Deploy: automático a cada `git push` na branch `main`
- Gratuito, sem pausa por limite de banda
- Anteriormente no Netlify (pausado por limite do plano gratuito)

**Limites do GitHub Pages:**
- Armazenamento: recomendado até 1GB por repositório
- Banda: recomendado até 100GB/mês (não pausa o site, apenas aciona revisão do GitHub)
- Deploys: sem limite rígido (recomendado até 10 por hora)
- Não tem o tipo de "pausa automática" que o Netlify tem no plano gratuito

---

## Fluxo de trabalho mensal

1. **Samuel** edita e exporta os Reels: `REEL NN – Nome.mov` + capa na pasta `Videos/`
2. **Silvana** escreve o conteúdo no Obsidian com o campo `**Vídeo:**` preenchido para Reels
3. **Designer** entrega as artes em `Posts_Fixos/` com nomes `DD-MM.jpg` / `DD-MM_N.jpg`
4. **Samuel ou Silvana** dá duplo clique em `Fluxo Completo.command`:
   - Seleciona cliente e período
   - Sistema valida os arquivos
   - Sobe os Reels ao YouTube (se ainda não subidos)
   - Gera as páginas de aprovação
   - Publica no GitHub Pages
5. **Silvana** copia a mensagem do Terminal e manda no WhatsApp do cliente
6. **Cliente** abre o link, aprova ou pede ajuste, clica "Enviar aprovações"
7. Mensagem formatada chega no WhatsApp do grupo do cliente (ou direto com a Silvana/Samuel)

---

## Problemas conhecidos e soluções

### `chmod +x` perdido após git reset
O Google Drive não preserva permissões Unix. Após qualquer `git reset --hard` ou clone novo, rodar `chmod +x` manualmente nos `.command`.

### git corrompido ao operar pela VM do Claude
A VM do Claude escreve objetos git via Google Drive com encoding diferente, corrompendo o índice. **Regra:** todo `git add/commit/push` deve ser feito pelo Terminal do Mac, nunca pela VM.

### `invalid_scope` no YouTube
O token OAuth foi gerado com escopos insuficientes. Deletar `scripts/youtube_token.json` e rodar o script novamente para reautenticar.

### Imagens não carregam para o cliente
A pasta `Posts_Fixos/` precisa estar compartilhada publicamente no Google Drive ("qualquer pessoa com o link pode visualizar"). Configurar uma vez por cliente.

---

## Referências técnicas

- xattr no macOS Drive File Stream: `com.google.drivefs.item-id#S`
- Embed de imagem do Drive: `https://lh3.googleusercontent.com/d/FILE_ID`
- YouTube Data API v3: upload + thumbnails com OAuth 2.0
- Scopes: `youtube.upload` + `youtube`
- NFD/NFC no macOS: Google Drive usa NFD para `Agência` → usar `os.listdir()` para path real
- Bash arrays para paths com espaços: `ARGS=(); ARGS+=(--key "val"); cmd "${ARGS[@]}"`
