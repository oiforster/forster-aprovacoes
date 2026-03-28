# Sistema de Aprovação de Conteúdo — Documentação Técnica

**Projeto:** forster-aprovacoes
**Criado em:** março de 2026
**Repositório:** https://github.com/oiforster/forster-aprovacoes
**Site:** https://aprovar.forsterfilmes.com
**Última atualização:** 2026-03-28 — Domínio próprio; URLs limpas; slugs personalizados; imagens copiadas pro repo; layout cronológico sem tabs de semana; biblioteca separada em `/entregas/`; auto-sync em todos os `.command`; fix: comentários HTML no `.md` não vazam mais para a página

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
Obsidian (.md)              Synology Drive (Videos/ + _youtube.md)
      │                             │
      └──────────┬──────────────────┘
                 │
       ┌─────────┴──────────────────────┐
       ▼                                ▼
Fluxo Completo.command       Entrega de Vídeos.command
(conteúdo recorrente)        (clientes pontuais ou entrega avulsa)
       │                                │
 ┌─────┼──────────┐                     ├── subir_reels.py (YouTube)
 ▼     ▼          ▼                     └── gerar_aprovacoes.py (HTML)
valid  subir   gerar                              │
_arq   _reels  _aprov                            ↓ fallback se sem .md:
                                        gerar_para_cliente_reels()
                                        (lê _youtube.md diretamente)
       └──────────┴─────────────────────┘
                 │
          git push automático
                 │
                 ▼
        GitHub Pages
        oiforster.github.io/forster-aprovacoes/
                 │
          link enviado via WhatsApp
          (preview com og:image = thumbnail YouTube)
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
├── CNAME                                ← domínio: aprovar.forsterfilmes.com
├── template.html                        ← template base de todas as páginas
├── [slug-cliente]/                      ← uma pasta por cliente (primeiro nível da URL)
│   ├── index.html                       ← sempre aponta para a versão mais recente
│   ├── YYYY-MM-DD.html                  ← aprovação por semana/período (recorrentes)
│   ├── YYYY-MM.html                     ← entrega pontual via _youtube.md
│   ├── [mes-ano]/
│   │   └── index.html                   ← biblioteca do mês (URL limpa sem .html)
│   └── estado-YYYY-MM.json             ← estado de aprovação de cada post (lido pelo JS)
├── scripts/
│   ├── gerar_aprovacoes.py              ← gerador de páginas de aprovação
│   ├── gerar_biblioteca.py              ← gerador de biblioteca de entregas
│   ├── subir_reels.py                   ← upload de Reels ao YouTube
│   ├── validar_arquivos.py              ← validação de artes e nomes antes de gerar
│   ├── youtube_credentials.json         ← NUNCA commitar (no .gitignore)
│   └── youtube_token.json               ← NUNCA commitar (no .gitignore)
├── index.html                           ← página inicial do site
├── GUIA_SILVANA.md                      ← manual de uso para a Silvana
├── DOCUMENTACAO_TECNICA.md              ← este arquivo
├── PROMPT_HANDOFF_SAMUEL.md             ← prompt de contexto para o Claude do Samuel
├── Fluxo Completo.command               ← tudo em um duplo clique (clientes recorrentes)
└── Entrega de Vídeos.command            ← YouTube + página + publicar (pontuais e avulsos)
```

**Estrutura de URLs:**
```
aprovar.forsterfilmes.com/                               ← índice geral
aprovar.forsterfilmes.com/catarata/                      ← aprovação mais recente (index.html)
aprovar.forsterfilmes.com/catarata/2026-04-01            ← aprovação de abril (por período)
aprovar.forsterfilmes.com/catarata/entregas/             ← biblioteca de entregas (índice)
aprovar.forsterfilmes.com/catarata/entregas/abril-2026   ← biblioteca de abril
aprovar.forsterfilmes.com/fyber-show-piscinas/           ← outro cliente (slug automático)
```

**Estrutura de arquivos no repo por cliente:**
```
{slug}/
├── index.html          ← aprovação mais recente (atualizado a cada geração)
├── YYYY-MM-DD.html     ← aprovação por período (permanente)
├── estado-YYYY-MM.json ← estado de aprovação (lido pelo JS via GitHub raw)
├── artes/              ← imagens copiadas do Synology (quando xattr não disponível)
│   ├── DD-MM.jpg
│   └── DD-MM_N.jpg
└── entregas/           ← biblioteca de entregas (gerada por gerar_biblioteca.py)
    ├── index.html      ← índice de meses
    └── abril-2026/
        └── index.html  ← página de download do mês
```

---

## Componentes

### 1. `Fluxo Completo.command`

Arquivo bash executável por duplo clique. Encadeia as 4 etapas do processo:

0. **Auto-sync** — `git fetch origin main` + compara hashes + `git reset --hard` se desatualizado
1. **Dependências** — verifica e instala google-api-python-client etc. (com `--break-system-packages` para Homebrew Python)
2. **Validação** — `validar_arquivos.py` normaliza nomes de artes + verifica se estão na pasta
3. **YouTube** — `subir_reels.py` sobe os Reels como unlisted e atualiza o `_youtube.md`
4. **Geração** — `gerar_aprovacoes.py` gera os HTMLs de aprovação
5. **Publicação** — `git add . && git commit && git push` (pergunta antes de publicar)

**Opções interativas:**
- Qual cliente? (número, nome parcial ou Enter para todos)
- Qual período?
  - `1` Próxima semana (padrão)
  - `2` Semana atual
  - `3` Período personalizado (inserir início e fim em DD/MM/AAAA ou AAAA-MM-DD)
  - `4` Mês completo (inserir YYYY-MM)
- O mês é inferido automaticamente do período (só pergunta na opção 1)
- Em caso de erro na validação: continuar mesmo assim? (s/N)
- Em caso de erro no YouTube: continuar gerando páginas? (s/N)
- Publicar no site? (S/n)

**Normalização automática de artes:** na etapa de validação, `validar_arquivos.py` renomeia arquivos em `Posts_Fixos/` para o padrão limpo (`DD-MM.jpg`, `DD-MM_1.jpg`). Remove espaços, acentos, parênteses e dia da semana. Move slides de subpastas para a raiz.

**Busca de artes cross-mês:** tanto o validador quanto o gerador procuram artes em todas as pastas de entrega, não só na do mês do post. Cobre casos de períodos que cruzam meses (ex: 31/03 a 09/04 com artes em pastas de março e abril).

**Fallback de .md cross-mês:** quando o período inclui um mês para o qual não existe `.md` de Conteúdo Mensal, o sistema tenta o mês anterior (ex: posts de abril no `.md` de março).

**Atenção:** após cada `git reset --hard` ou atualização do repositório, o macOS pode perder o bit de execução. Nesse caso, rodar no Terminal:
```bash
chmod +x ~/Documents/forster-aprovacoes/*.command
```

---

### 1b. `Entrega de Vídeos.command`

Arquivo bash executável por duplo clique. Voltado para entrega de vídeos avulsos ou de clientes pontuais. Não inclui validação de artes.

**Etapas:**
1. **Sincronização** — `git fetch origin main && git reset --hard origin/main`
2. **Synology links** — `gerar_links_synology.py` cria links de download para `.mov` e frames no Synology; salva `_synology.md` na pasta `Videos/`
3. **YouTube** — `subir_reels.py` sobe os Reels como unlisted
4. **Geração** — `gerar_aprovacoes.py` gera a página com botões de download e galeria de frames
5. **Publicação** — pergunta antes de fazer `git add . && git commit && git push`

**Opções interativas:**
- Qual cliente? (lista recorrentes + pontuais detectados em `Clientes Pontuais/`)
- Qual mês? (YYYY-MM ou Enter para o atual)
- Continuar se Synology falhar? (s/N)
- Continuar se YouTube falhar? (s/N)
- Publicar no site? (S/n)

**Diferença do `Fluxo Completo.command`:** sem etapa de validação de artes; inclui clientes pontuais; inclui etapa de links Synology; não tem menu de período (usa mês).

**Ambos os `.command` fazem auto-sync** antes de qualquer operação — garantem que Samuel e Silvana sempre rodem a versão mais recente do repositório.

**Ambos instalam dependências automaticamente** (google-api-python-client etc.) com `--break-system-packages` para compatibilidade com Homebrew Python.

---

### 1c. `scripts/gerar_links_synology.py`

Gera links de compartilhamento público no Synology DSM para todos os `.mov` e frames de uma entrega. Salva em `_synology.md` na pasta `Videos/` do cliente.

**Fluxo:**
1. Lê `scripts/synology_config.json` (gitignored) para obter credenciais e paths
2. Autentica na API FileStation (`SYNO.API.Auth`) via rede local (fallback: DDNS)
3. Encontra os `.mov` em `06_Entregas/YYYY-MM*/Videos/`
4. Encontra os frames em `Videos/Frames/`
5. Para cada arquivo não listado no `_synology.md` existente, chama `SYNO.FileStation.Sharing/create`
6. Cria também um link para a pasta `Frames/` inteira (`FRAMES_FOLDER`)
7. Escreve/atualiza `_synology.md` com todos os links
8. Faz logout

**`_synology.md` — formato:**
```
# Links de download — Synology — gerado automaticamente

REEL 01 – Nome do Vídeo: https://forsterfilmes.synology.me:5001/d/s/SHARE_ID/
REEL 02 – Outro Vídeo: https://forsterfilmes.synology.me:5001/d/s/SHARE_ID/

FRAMES_FOLDER: https://forsterfilmes.synology.me:5001/d/s/FOLDER_ID/
FRAME_frame_01.jpg: https://forsterfilmes.synology.me:5001/d/s/SHARE_ID/
FRAME_frame_02.jpg: https://forsterfilmes.synology.me:5001/d/s/SHARE_ID/
```

**`scripts/synology_config.json` (gitignored — nunca commitar):**
```json
{
  "host_local":      "https://192.168.2.25:5001",
  "host_external":   "https://forsterfilmes.synology.me:5001",
  "username":        "guest",
  "password":        "...",
  "nas_base_path":   "/Claude Cowork/Agência",
  "local_sync_name": "SynologyDrive-Agencia"
}
```

**Path mapping:** path local `~/Library/CloudStorage/SynologyDrive-Agencia/X` → NAS path `/Claude Cowork/Agência/X` (volume1 implícito na API FileStation).

**Argumentos CLI:**
```bash
--cliente "Nome"    # nome do cliente
--mes YYYY-MM       # mês (padrão: atual)
--pontual           # busca em Clientes Pontuais primeiro
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

Script principal. Lê os arquivos `.md` de Conteúdo Mensal e gera as páginas HTML. Tem fallback para clientes pontuais que não têm calendário editorial.

**Funções principais:**

| Função | O que faz |
|--------|-----------|
| `encontrar_pasta_agencia()` | Prioriza Synology Drive; fallback para Google Drive (legado); usa `Path.home()` — funciona em qualquer Mac |
| `encontrar_arquivo_mensal(cliente, ano_mes, agencia_path)` | Busca o `.md` de Conteúdo Mensal em Recorrentes e Pontuais |
| `gdrive_id_para_url(path)` | Lê o xattr `com.google.drivefs.item-id#S` e retorna URL `lh3.googleusercontent.com/d/ID` |
| `encontrar_arte(data, pasta_cliente, output_dir=None)` | Busca arte em `Posts_Fixos/`. Tenta: (1) xattr/Drive URL, (2) `_links.md`, (3) copia o arquivo para `{slug}/artes/` no repo e retorna URL relativa |
| `ler_youtube_id(pasta_videos, reel_nome)` | Lê `Videos/_youtube.md` e retorna YouTube ID pelo nome do Reel |
| `parse_conteudo_mensal(arquivo, datas, pasta_estrategia, output_dir)` | Parse do `.md`: extrai posts do período; passa `output_dir` para `encontrar_arte()` |
| `gerar_pagina_aprovacao(...)` | Monta a página HTML; todos os posts em ordem cronológica (sem tabs de semana) |
| `gerar_para_cliente_reels(cliente, ano_mes, ...)` | Fallback para pontuais: gera página direto do `_youtube.md`, sem calendário |

**Estratégia de imagens (ordem de prioridade):**
1. xattr `com.google.drivefs.item-id#S` → URL `lh3.googleusercontent.com` (Mac do Samuel com Google Drive)
2. `_links.md` na pasta `Posts_Fixos/` → URL manual (qualquer Mac)
3. Cópia local para `{slug}/artes/` no repo → URL relativa (funciona em qualquer Mac, inclusive o da Silvana)

**Argumentos CLI:**
```bash
--cliente "Nome"     # filtra por cliente (parcial aceito; busca em Recorrentes e Pontuais)
--semana YYYY-MM-DD  # segunda-feira da semana
--mes YYYY-MM        # mês completo
--inicio YYYY-MM-DD  # início do período personalizado
--fim YYYY-MM-DD     # fim do período personalizado
```

**Layout:** uma página por período (mês ou semana personalizada), posts em ordem cronológica, sem navegação por semanas.

**Comentários HTML no `.md`:** o parser interrompe a leitura de uma seção ao encontrar `<!--`. Isso permite incluir notas internas (como instruções para o Claude da Silvana) no final do arquivo sem que vazem para a página de aprovação.

**Synology vs Google Drive:** quando os arquivos estão no SynologyDrive, o script pula xattr (não existe no Synology) e vai direto para cópia local — sem warnings. xattr só é tentado para arquivos em paths do Google Drive.

**Nomes limpos no repo:** ao copiar artes para o repo, os nomes são normalizados para `DD-MM.jpg` / `DD-MM_N.jpg` — sem espaços, acentos ou parênteses que quebrariam URLs no GitHub Pages.

**Fallback para clientes pontuais:** quando o cliente não está em `CLIENTES_RECORRENTES` e não tem `.md` de Conteúdo Mensal, usa `gerar_para_cliente_reels()` que lê `_youtube.md` diretamente.

---

### 4. `scripts/subir_reels.py`

Upload de Reels ao YouTube como unlisted. Roda no Mac do Samuel.

**Fluxo:**
1. Busca a pasta do cliente em `Clientes Recorrentes` e depois em `Clientes Pontuais`
2. Dentro da pasta do cliente, busca `06_Entregas/YYYY-MM*/Videos/REEL NN – Nome.mov`
3. Faz upload como vídeo não listado (unlisted)
4. Se existir `REEL NN – Nome (capa).jpg`, sobe como thumbnail
5. Salva em `Videos/_youtube.md` com a chave sendo o nome do Reel (sem extensão)
6. Pula arquivos cujo nome já está registrado no `_youtube.md`

**Atenção — clientes pontuais com estrutura não-padrão:**
O script encontra a pasta do cliente em Pontuais, mas ainda espera a estrutura `06_Entregas/` dentro dela. Se o cliente pontual usar uma estrutura diferente (ex: `2026-03 - Entrega Cliente/01 - Reels/`), o upload vai ser silenciosamente pulado. Nesses casos, o `Entrega de Vídeos.command` ainda funciona se os vídeos já estiverem no `_youtube.md` de uma upload anterior. Para novos clientes pontuais, criar a pasta `06_Entregas/YYYY-MM/Videos/` seguindo o padrão.

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
| `{{OG_TITLE}}` | Título para preview no WhatsApp/redes (ex: "Aprovação — Cliente — Março de 2026") |
| `{{OG_DESCRIPTION}}` | Descrição para preview (convite para aprovar) |
| `{{OG_IMAGE}}` | URL da thumbnail do YouTube do primeiro vídeo/reel (`maxresdefault.jpg`) |
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

## Slugs de cliente (URLs personalizadas)

Por padrão, o nome do cliente é convertido automaticamente para slug URL-safe:
`"Fyber Show Piscinas"` → `fyber-show-piscinas`

Para URLs mais curtas, existe um dicionário de sobrescritas em `gerar_aprovacoes.py` e `gerar_biblioteca.py`:

```python
SLUG_CLIENTES = {
    "Catarata Center": "catarata",
    # Adicionar outros conforme necessário:
    # "Óticas Casa Marco": "oticas",
}
```

Para adicionar ou alterar um slug:
1. Editar `SLUG_CLIENTES` nos **dois scripts** (`gerar_aprovacoes.py` e `gerar_biblioteca.py`)
2. Fazer `git mv` da pasta antiga para a nova: `git mv oticas-casa-marco oticas`
3. Rodar o fluxo normalmente — os novos arquivos já serão gerados no caminho novo
4. Commitar e publicar

**Atenção:** mudar o slug de um cliente que já tem link enviado ao cliente vai quebrar o link antigo. Fazer a mudança antes de enviar o link do mês, ou comunicar o novo endereço.

---

## Hospedagem

**GitHub Pages com domínio próprio** (desde março de 2026)

- URL: `https://aprovar.forsterfilmes.com`
- Repositório: `oiforster/forster-aprovacoes`
- Domínio configurado via `CNAME` no repo + registro CNAME no GoDaddy (`aprovar → oiforster.github.io`)
- Deploy: automático a cada `git push` na branch `main`
- Gratuito, sem pausa por limite de banda
- URL legada `oiforster.github.io/forster-aprovacoes` redireciona automaticamente (GitHub faz o redirect)

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
O Synology Drive (assim como o Google Drive) não preserva permissões Unix. Após qualquer `git reset --hard` ou clone novo, rodar `chmod +x` manualmente nos `.command`:
```bash
chmod +x ~/Documents/forster-aprovacoes/*.command
```

### git corrompido — repositório dentro de pasta sincronizada
Repositório git dentro de pasta sincronizada (Synology Drive, Google Drive) entre dois Macs corrompeu o índice repetidamente. **Solução definitiva (março/2026):** repositório migrado para `~/Documents/forster-aprovacoes` em cada Mac — pasta local, fora de qualquer sync automático. GitHub é a única fonte de verdade compartilhada.

**Regra:** todo `git add/commit/push` deve ser feito a partir de `~/Documents/forster-aprovacoes`, nunca de dentro do Synology Drive.

### Fluxo git padrão (ambos os Macs)
Antes de começar qualquer trabalho no repositório, puxar as atualizações:
```bash
cd ~/Documents/forster-aprovacoes && git pull
```

Após gerar ou editar arquivos:
```bash
cd ~/Documents/forster-aprovacoes && git add ARQUIVO && git commit -m "descrição" && git push
```

### `git pull` travando por arquivos não rastreados ou branches divergentes
Se travar, forçar sincronização com o remoto:
```bash
cd ~/Documents/forster-aprovacoes
git fetch origin main
git reset --hard origin/main
```

### Clientes pontuais sem estrutura `06_Entregas/`
O `subir_reels.py` encontra o cliente em `Clientes Pontuais/` mas ainda espera `06_Entregas/` dentro da pasta. Se o cliente usar outra estrutura, o upload é pulado silenciosamente. Nesse caso, fazer upload manual e criar o `_youtube.md` na pasta de vídeos. O `gerar_aprovacoes.py` lê o `_youtube.md` independentemente da estrutura de pastas.

### Synology: `synology_config.json` não encontrado após clone/reset
O arquivo é gitignored e não é commitado. Se o script não encontrar o arquivo, ele cria um template e encerra. Edite o arquivo gerado preenchendo a senha e rode novamente.

### Synology: erro de permissão ao criar link (código 105 ou 119)
O usuário `guest` pode não ter permissão de criar links de compartilhamento. No DSM: Control Panel → User & Group → guest → edite permissões ou crie um usuário dedicado com acesso à pasta `Claude Cowork` e direito de compartilhamento.

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
- NFD/NFC no macOS: tanto Google Drive quanto Synology Drive podem usar NFD → `encontrar_pasta_agencia()` usa `Path.exists()` direto no Synology (path sem acentos) e `os.listdir()` para fallback no Google Drive
- Open Graph: `og:image` usa `https://img.youtube.com/vi/{ID}/maxresdefault.jpg` — thumbnail 1280×720 gerada automaticamente pelo YouTube; sem necessidade de upload manual
- Bash arrays para paths com espaços: `ARGS=(); ARGS+=(--key "val"); cmd "${ARGS[@]}"`
- `git reset --hard origin/main` vs `git pull`: o reset é mais robusto para scripts automatizados pois não falha com arquivos não rastreados; use pull apenas em workflows interativos onde o histórico local precisa ser preservado
