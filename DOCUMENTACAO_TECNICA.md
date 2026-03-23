# Sistema de Aprovação de Conteúdo — Documentação Técnica

**Projeto:** forster-aprovacoes
**Criado em:** março de 2026
**Repositório:** https://github.com/oiforster/forster-aprovacoes
**Site:** https://forster-aprovacoes.netlify.app

---

## Contexto e problema

A Forster Filmes aprovava postagens com clientes via grupo de WhatsApp — prático para o cliente, mas sem registro formal, sem rastreabilidade e dependente de a Silvana lembrar de cobrar cada cliente. A solução precisava:

- Ser no WhatsApp (canal já no dia a dia dos clientes)
- Abrir bem no celular, sem login, sem app para instalar
- Registrar respostas automaticamente
- Não exigir que a Silvana aprenda um sistema novo
- Mostrar as artes reais (não só texto) para o cliente aprovar

---

## Arquitetura do sistema

```
Obsidian (.md)              Google Drive (_Artes/)
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
          deploy automático
                 │
                 ▼
        Netlify (forster-aprovacoes.netlify.app)
                 │
          link enviado via WhatsApp
                 │
                 ▼
        Cliente aprova no celular
                 │
          Netlify Forms
                 │
                 ▼
        Painel Netlify (Silvana consulta)
```

---

## Componentes

### 1. `scripts/gerar_aprovacoes.py`

Script Python principal. Roda no Mac da Silvana.

**O que faz:**
- Detecta automaticamente o caminho da pasta `Agência/` no Google Drive (lida com encoding NFD do macOS)
- Lê os arquivos `YYYY-MM — Conteúdo Mensal [Cliente].md` de cada cliente
- Faz parse da tabela de calendário (extrai data, formato, título, status)
- Faz parse das seções de conteúdo detalhado (texto do card, legenda, slides de carrossel)
- Busca artes automaticamente na pasta `04_Estratégia/_Artes/YYYY-MM/`
- Detecta imagem única (`DD-MM.jpg`) ou carrossel (`DD-MM_1.jpg`, `DD-MM_2.jpg`...)
- Extrai o Google Drive File ID via xattr `com.google.drivefs.item-id#S` (macOS Drive File Stream)
- Se o arquivo estiver em modo Streaming, força leitura para acionar download e tenta de novo
- Constrói URL de embed: `https://lh3.googleusercontent.com/d/FILE_ID`
- Quando há arte, exibe apenas a legenda (o texto do card já está visível na arte)
- Gera HTML de aprovação a partir do `aprovacao/template.html`
- Salva em `aprovacao/[slug-cliente]/[YYYY-MM-DD].html` e `index.html`
- Gera mensagem de WhatsApp pronta para copiar

**Argumentos:**
```bash
--cliente "Nome"      # filtra por cliente (parcial aceito)
--semana YYYY-MM-DD   # segunda-feira da semana
--mes YYYY-MM         # mês completo
--base-url URL        # URL base do Netlify (padrão: forster-aprovacoes.netlify.app)
```

**Dependências:** Python 3 (padrão no macOS), sem pacotes externos.

---

### 2. `aprovacao/template.html`

Template HTML da página de aprovação. Um único arquivo com CSS e JavaScript inline.

**Features:**
- Mobile-first (max-width 440px, otimizado para iPhone)
- Header sticky com nome do cliente, período e barra de progresso
- Botão "Aprovar todos os posts" no topo
- Navegação por semanas (tabs) quando há mais de uma semana
- Cards individuais por post: data, formato com cor, arte inline, legenda, botões
- Arte com proporção 3:4 (padrão Instagram/stories)
- Carrossel de imagens estilo Instagram: scroll-snap nativo no mobile (deslize com o dedo), setas de navegação no desktop, contador "1/5" e pontinhos indicadores
- Campo de texto para comentário ao pedir ajuste
- Botão "Enviar aprovações" habilitado apenas quando todos os posts foram respondidos
- Tela de confirmação após envio
- Formulário Netlify Forms oculto para registro das respostas
- Graceful degradation: imagem com `onerror` esconde o container se não carregar

**Placeholders substituídos pelo script:**
- `{{TITULO_PAGINA}}` — título da aba do browser
- `{{NOME_CLIENTE}}` — nome do cliente no header
- `{{PERIODO}}` — período formatado ("7 a 13 de abril")
- `{{TOTAL_POSTS}}` — número de posts (para o contador de progresso)
- `{{POSTS_HTML}}` — HTML de todos os cards
- `{{SEMANAS_NAV}}` — HTML da navegação de semanas (se houver)
- `{{FORM_ID}}` — ID único do formulário Netlify (`[slug-cliente]-[YYYY-MM-DD]`)

---

### 3. `Gerar Aprovações.command`

Script bash para duplo clique no macOS. Interface amigável para a Silvana.

**Fluxo:**
1. Pergunta para qual cliente (número, nome ou todos)
2. Pergunta o período (próxima semana, semana específica ou mês)
3. Roda o script Python
4. Pergunta se deve publicar (git add + commit + push)

**Para funcionar:** o arquivo precisa ter permissão de execução (`chmod +x`). Já configurado no repositório.

**Para usar:** duplo clique no Finder. Na primeira vez, pode ser necessário ir em Preferências do Sistema → Privacidade e Segurança → permitir execução.

---

### 4. `netlify.toml`

Configuração do Netlify.

```toml
[build]
  publish = "."           # publica a raiz do repositório

[[headers]]               # headers de segurança
  for = "/*"

[[redirects]]             # redireciona /aprovacao/cliente/ → index.html
  from = "/aprovacao/:cliente/"
  to = "/aprovacao/:cliente/index.html"
  status = 200
```

---

### 5. Netlify Forms

Cada página de aprovação tem um formulário oculto registrado no Netlify com o nome `aprovacao-[slug-cliente]-[YYYY-MM-DD]`.

**Campos enviados:**
- `cliente` — nome do cliente
- `periodo` — período da semana
- `resultados` — JSON com `{ post_id: { status, comentario } }` para cada post

**Como consultar:** app.netlify.com → projeto forster-aprovacoes → Forms → selecionar formulário.

---

## Convenção de artes

```
04_Estratégia/
└── _Artes/
    └── YYYY-MM/
        ├── DD-MM.jpg          ← post único (card, reels, vídeo)
        ├── DD-MM_1.jpg        ← slide 1 do carrossel
        ├── DD-MM_2.jpg        ← slide 2 do carrossel
        └── DD-MM_3.jpg        ← slide 3 (quantos slides quiser)
```

**Formatos aceitos:** `.jpg`, `.jpeg`, `.png`, `.webp`

**Como o script obtém a URL (sem configuração manual):**
1. Encontra os arquivos por nome (prefixo `DD-MM`)
2. Lê o xattr `com.google.drivefs.item-id#S` — metadado gravado pelo Google Drive File Stream no macOS para cada arquivo sincronizado
3. Se o arquivo ainda não foi baixado (modo Streaming), força a leitura de 4KB para acionar o download e tenta de novo após 1,5s
4. Constrói `https://lh3.googleusercontent.com/d/FILE_ID`

**Pré-requisito:** a pasta `_Artes/` precisa estar compartilhada como "qualquer pessoa com o link pode visualizar" no Google Drive. Configurar uma vez por cliente.

**Fallback manual (`_links.md`):** se o xattr falhar por algum motivo (arquivo muito recente, Drive não processou ainda), é possível criar um arquivo `_links.md` na pasta `_Artes/YYYY-MM/` com os links individuais:
```
DD-MM: https://drive.google.com/file/d/ID/view
DD-MM_1: https://drive.google.com/file/d/ID1/view
DD-MM_2: https://drive.google.com/file/d/ID2/view
```
O script tenta xattr primeiro e só usa `_links.md` se xattr não retornar nada.

---

## Formato do arquivo .md de conteúdo mensal

O script é compatível com o formato padrão da Forster Filmes. Para funcionar corretamente, o arquivo precisa ter:

### Tabela de calendário (obrigatório)

```markdown
| Data | Formato | Título / Tema | Status |
|------|---------|---------------|--------|
| 07/04 Ter | Card | Título do post | Criado |
| 08/04 Qua | Carrossel | Título do carrossel | Criado |
```

- A data deve estar na primeira coluna no formato `DD/MM` (com ou sem dia da semana)
- O formato (Card, Carrossel, Reels, Vídeo) é detectado por palavras-chave na segunda coluna
- O título vai para o header do card na página de aprovação

### Seções de conteúdo detalhado (recomendado)

```markdown
#### 07/04 (Ter) — Card — Título do post

**Texto do card:**
O texto da arte.

**Legenda:**
A legenda do Instagram.
```

Para carrosseis:

```markdown
#### 08/04 (Qua) — Carrossel — Título

**Slide 1 (capa):**
Texto da capa.

**Slide 2:**
Texto do segundo slide.

**Legenda:**
Legenda do post.
```

> Quando há arte carregada, o script exibe apenas a legenda na página de aprovação — o texto do card e os slides ficam ocultos porque já estão visíveis nas imagens.

---

## Deploy e CI/CD

- **Repositório:** GitHub `oiforster/forster-aprovacoes`
- **Branch principal:** `main`
- **Deploy automático:** qualquer push para `main` aciona rebuild no Netlify
- **Tempo de deploy:** ~30 segundos
- **Free tier Netlify:** suficiente para o volume atual (100GB de banda/mês, formulários com 100 submissions/mês)

---

## Estrutura de pastas do repositório

```
forster-aprovacoes/
├── index.html                          ← página inicial do site
├── netlify.toml                        ← configuração Netlify
├── .gitignore                          ← ignora .DS_Store e __pycache__
├── Gerar Aprovações.command            ← duplo clique para rodar
├── GUIA_SILVANA.md                     ← guia de uso para Silvana
├── DOCUMENTACAO_TECNICA.md             ← este arquivo
├── scripts/
│   └── gerar_aprovacoes.py             ← script principal
└── aprovacao/
    ├── template.html                   ← template HTML
    └── [slug-cliente]/
        ├── index.html                  ← última semana gerada
        └── YYYY-MM-DD.html             ← semanas anteriores
```

---

## Possíveis evoluções

- **Notificação automática:** integrar com Z-API ou Twilio para enviar o WhatsApp automaticamente (sem a Silvana copiar e colar)
- **Dashboard de status:** página interna mostrando quais clientes aprovaram a semana e quais ainda não responderam
- **Lembretes automáticos:** reenviar o link para clientes que não aprovaram após X dias
- **Histórico de aprovações:** página por cliente mostrando aprovações de meses anteriores
- **Domínio personalizado:** `aprovacoes.forsterfilmes.com.br` em vez de `forster-aprovacoes.netlify.app`
