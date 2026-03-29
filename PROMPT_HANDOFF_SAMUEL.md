# Prompt de continuação — Mac do Samuel

> Copiar o bloco abaixo e colar direto no Claude no Mac do Samuel.
> Última atualização: 2026-03-29

---

```
Estou continuando o desenvolvimento do sistema de aprovações da Forster Filmes.
Aqui está o contexto completo do estado atual.

---

## REPOSITÓRIO

Pasta local: ~/Documents/forster-aprovacoes
GitHub: https://github.com/oiforster/forster-aprovacoes
Site: https://aprovar.forsterfilmes.com

NUNCA mover o repositório para dentro do Synology ou Google Drive — corrompe o índice git.

Antes de qualquer coisa:
cd ~/Documents/forster-aprovacoes && git pull

---

## O QUE FOI FEITO (sessão 2026-03-28 — Mac da Silvana)

### 1. Scripts funcionam em qualquer Mac
Todos os caminhos fixos `/Users/samuelforster/` foram substituídos por `Path.home()`.
O `Fluxo Completo.command` agora roda no Mac da Silvana sem erros.

### 2. Domínio próprio
- Arquivo `CNAME` adicionado ao repo com `aprovar.forsterfilmes.com`
- DNS configurado no GoDaddy (CNAME: `aprovar → oiforster.github.io`)
- **Pendente:** confirmar o domínio em github.com/oiforster/forster-aprovacoes → Settings → Pages → Custom domain
  (digitar `aprovar.forsterfilmes.com` e salvar para o GitHub emitir o certificado SSL)

### 3. Nova estrutura de URLs (sem /aprovacao/ na URL)
OUTPUT_DIR movido de `aprovacao/` para a raiz do repo.
Todos os arquivos existentes movidos com git mv.

Estrutura atual:
  aprovar.forsterfilmes.com/catarata/                    ← aprovação atual
  aprovar.forsterfilmes.com/catarata/2026-04-01          ← aprovação de abril
  aprovar.forsterfilmes.com/catarata/entregas/           ← biblioteca (índice)
  aprovar.forsterfilmes.com/catarata/entregas/abril-2026 ← vídeos de abril

### 4. Slugs personalizados
Dicionário SLUG_CLIENTES em gerar_aprovacoes.py e gerar_biblioteca.py:
  "Catarata Center" → "catarata"
Para adicionar outro slug: editar os dois scripts + git mv da pasta.

### 5. Imagens copiadas para o repo
encontrar_arte() tem três camadas de fallback:
  1. xattr do Google Drive → URL lh3.googleusercontent.com (funciona no Mac do Samuel)
  2. _links.md manual → URL fornecida manualmente
  3. Cópia local → arquivo copiado para {slug}/artes/ e servido pelo GitHub Pages

A camada 3 foi adicionada para funcionar na máquina da Silvana (sem Google Drive montado).
No Mac do Samuel, a camada 1 continua funcionando normalmente.

### 6. Layout cronológico
Removidas as tabs de semana. Todos os posts aparecem em ordem cronológica numa página única por mês.

### 7. Biblioteca separada da aprovação
gerar_biblioteca.py agora salva em {slug}/entregas/ para não sobrescrever o index.html de aprovação.

### 8. Mensagem WhatsApp no final do fluxo
gerar_aprovacoes.py salva a mensagem em /tmp/forster_whatsapp_msg.txt.
Fluxo Completo.command relê e exibe no final, depois do git push.

### 9. Template movido
template.html estava em aprovacao/template.html → movido para a raiz do repo.

---

## ESTRUTURA DE ARQUIVOS POR CLIENTE

{slug}/
├── index.html              ← ÍNDICE DE MESES com progresso visual (gerado automaticamente)
├── YYYY-MM/
│   └── index.html          ← aprovação do mês (URL limpa: /slug/2026-04)
├── YYYY-MM-DD.html         ← aprovação legada (links já enviados — mantido)
├── estado-YYYY-MM.json     ← estado de aprovação (formato: {"post-id": {"status": "aprovado", "obs": "..."}})
├── artes/                  ← imagens copiadas do Synology (fallback sem xattr)
│   └── DD-MM.jpg
└── entregas/               ← gerado por gerar_biblioteca.py
    ├── index.html
    └── abril-2026/
        └── index.html

---

## O QUE FOI FEITO (sessão 2026-03-28 — Mac do Samuel)

### 10. Auto-sync em todos os .command
Ambos os `.command` agora fazem `git fetch` + comparação de hashes antes de rodar.
Se estiver desatualizado, faz `git reset --hard origin/main` automaticamente.
Garantia de que Samuel e Silvana sempre rodem a versão mais recente.

### 11. Fix: comentários HTML vazando na página
O parser do `gerar_aprovacoes.py` agora interrompe a leitura de uma seção ao encontrar `<!--`.
Resolvia o bug em que as notas internas do template (bloco de instruções para o Claude) apareciam no último post da página.

### 12. URL corrigida no Entrega de Vídeos.command
Trocada `oiforster.github.io/forster-aprovacoes` por `aprovar.forsterfilmes.com`.

---

## O QUE FOI FEITO (sessão 2026-03-29 — Redesign)

### 13. Redesign completo da página de aprovação
- Tipografia: Inter (corpo) + Playfair Display (títulos)
- Fundo off-white (#FAFAF8), cards com borda lateral colorida (verde/âmbar)
- Badges de status: "Aprovado" (verde) e "Ajuste solicitado" (âmbar)
- Caixa amarela com observação do cliente nos posts com ajuste

### 14. Persistência de estado com observações
- Estado JSON migrado de `"post-id": "aprovado"` para `"post-id": {"status": "aprovado", "obs": "..."}`
- `_carregarEstado()` busca do GitHub ao abrir a página e aplica visualmente
- Fix encoding UTF-8: `decodeURIComponent(escape(atob(...)))` para acentos corretos
- Observações preenchidas automaticamente na textarea + caixa amarela

### 15. Reordenação automática
- Pendentes no topo, ajustes depois, aprovados no final
- Separadores visuais: "Aguardando sua aprovação" e "Já respondidos"
- Loading overlay enquanto busca estado do GitHub

### 16. Nova estrutura de URLs
- Páginas geradas em `YYYY-MM/index.html` (URL limpa: `/slug/2026-04`)
- `index.html` na raiz do cliente agora é um ÍNDICE DE MESES com progresso visual
- Novo arquivo `template_index.html` para o índice
- Páginas legadas (YYYY-MM-DD.html) mantidas para links já enviados

---

## PENDÊNCIAS PARA O SAMUEL

### Prioridade alta

1. ~~**Ativar SSL do domínio próprio**~~ ✅ DNS configurado, aguardando propagação + cadeado verde. Quando aparecer, marcar "Enforce HTTPS".

2. **Instalar dependências YouTube no Mac da Silvana** (se ela precisar subir Reels)
   pip3 install --user google-api-python-client google-auth-oauthlib

3. **Testar o Fluxo Completo no Mac do Samuel**
   Rodar para Catarata Center, mês 2026-04, período 01/04 a 30/04.
   Verificar se as imagens aparecem via xattr (camada 1, mais eficiente que a cópia local).

### Quando houver vídeos para entregar

4. **Gerar biblioteca de entregas**
   Após exportar e registrar os vídeos no _youtube.md:
   python3 scripts/gerar_biblioteca.py --cliente "Catarata Center" --mes 2026-04

   URL resultante: aprovar.forsterfilmes.com/catarata/entregas/abril-2026

---

## COMO RODAR MANUALMENTE

# Aprovação mensal completa
python3 scripts/gerar_aprovacoes.py --cliente "Catarata Center" --inicio 2026-04-01 --fim 2026-04-30

# Biblioteca de entregas
python3 scripts/gerar_biblioteca.py --cliente "Catarata Center" --mes 2026-04

# Publicar
git add . && git commit -m "Catarata Center — aprovações abril 2026" && git push

---

## PROBLEMAS CONHECIDOS

### chmod +x perdido após git pull/reset
chmod +x ~/Documents/forster-aprovacoes/*.command

### git pull travando
git fetch origin main && git reset --hard origin/main

### YouTube: invalid_scope
Deletar scripts/youtube_token.json e reautenticar.

### Imagens aparecem no repo mas não no site
Verificar se o commit incluiu os arquivos de artes/:
git show --stat HEAD | grep artes

---

## ARQUIVOS DE REFERÊNCIA

- Documentação técnica completa: ~/Documents/forster-aprovacoes/DOCUMENTACAO_TECNICA.md
- Guia da Silvana: ~/Documents/forster-aprovacoes/GUIA_SILVANA.md
- Processo edição Joele: ~/Library/CloudStorage/SynologyDrive-Agencia/_Interno/Processos/Processo_Edicao_Mensal_Joele.md
- Processo edição GLPI: ~/Library/CloudStorage/SynologyDrive-Agencia/_Interno/Processos/Processo_Edicao_GLPI.md
- Padrão SSDs: ~/Library/CloudStorage/SynologyDrive-Agencia/_Interno/Processos/Padrao_SSDs_Producao.md
```
