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
- Busca artes automaticamente na pasta `04_Estratégia/_Artes/YYYY-MM/DD-MM.jpg`
- Extrai o Google Drive File ID via `xattr com.google.drivefs.item-id` (metadado macOS)
- Constrói URL de embed: `https://drive.google.com/uc?export=view&id=FILE_ID`
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
- Cards individuais por post: data, formato com cor, arte inline, texto, legenda, botões
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

O script detecta automaticamente seções com datas no formato `#### DD/MM`.

---

## Convenção de artes

```
04_Estratégia/
└── _Artes/
    └── YYYY-MM/
        ├── DD-MM.jpg          ← post único no dia
        ├── DD-MM-1.jpg        ← primeiro post do dia (quando há dois)
        └── DD-MM-2.jpg        ← segundo post do dia
```

**Formatos aceitos:** `.jpg`, `.jpeg`, `.png`, `.webp`

**Como o script obtém a URL:**
1. Encontra o arquivo por nome (`DD-MM.jpg` com o prefixo da data)
2. Lê o xattr `com.google.drivefs.item-id` (metadado do Google Drive for Desktop no macOS)
3. Constrói `https://drive.google.com/uc?export=view&id=FILE_ID`

**Pré-requisito:** a pasta `_Artes/` precisa estar compartilhada como "qualquer pessoa com o link pode visualizar" no Google Drive.

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

## Como testar com uma arte real

1. Crie a pasta `_Artes/2026-03/` dentro de `04_Estratégia/` do cliente Prisma Especialidades no Google Drive
2. Adicione um arquivo `.jpg` nomeado `25-03.jpg` (post de 25/03)
3. Clique direito na pasta `_Artes/` → Compartilhar → "Qualquer pessoa com o link" → Visualizador
4. No Terminal, rode:
   ```bash
   cd ~/Library/.../forster-aprovacoes
   python3 scripts/gerar_aprovacoes.py --cliente "Prisma" --semana 2026-03-23
   git add . && git commit -m "Teste com arte" && git push
   ```
5. Acesse `https://forster-aprovacoes.netlify.app/aprovacao/prisma-especialidades/` no celular

---

## Possíveis evoluções

- **Notificação automática:** integrar com Z-API ou Twilio para enviar o WhatsApp automaticamente (sem a Silvana copiar e colar)
- **Dashboard de status:** página interna mostrando quais clientes aprovaram a semana e quais ainda não responderam
- **Lembretes automáticos:** reenviar o link para clientes que não aprovaram após X dias
- **Histórico de aprovações:** página por cliente mostrando aprovações de meses anteriores
- **Domínio personalizado:** `aprovacoes.forsterfilmes.com.br` em vez de `forster-aprovacoes.netlify.app`
