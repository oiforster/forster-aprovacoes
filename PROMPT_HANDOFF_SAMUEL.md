# Prompt de continuação — Mac do Samuel

> Copiar o bloco abaixo e colar direto no Claude (Cowork) no Mac do Samuel.
> Última atualização: 2026-03-28

---

```
Estou continuando o desenvolvimento do sistema de aprovações da Forster Filmes.
Aqui está o contexto completo do estado atual.

---

## CONTEXTO DO SISTEMA

O sistema gera páginas HTML estáticas (GitHub Pages) para clientes revisarem e
aprovarem posts e vídeos. O repositório fica em `~/Documents/forster-aprovacoes/`
— NUNCA dentro do Synology ou Google Drive (corrompe o índice git).

Site: https://aprovar.forsterfilmes.com
Repo: https://github.com/oiforster/forster-aprovacoes

---

## ESTADO ATUAL (2026-03-28)

### O que foi feito nesta sessão

1. **Scripts funcionam na máquina da Silvana** — caminhos `/Users/samuelforster/`
   eram fixos no código. Todos os scripts agora usam `Path.home()` e funcionam
   em qualquer Mac (Samuel ou Silvana).

2. **Domínio próprio configurado** — `aprovar.forsterfilmes.com` aponta para o
   GitHub Pages via CNAME. Arquivo `CNAME` adicionado ao repo. DNS configurado
   no GoDaddy (registro CNAME: `aprovar → oiforster.github.io`).
   **Atenção:** se o DNS ainda não foi configurado no GoDaddy, o domínio não
   funciona. Ver instruções abaixo.

3. **URLs limpas** — pasta `aprovacao/` eliminada da URL. Estrutura nova:
   - `aprovar.forsterfilmes.com/catarata/` → aprovação atual
   - `aprovar.forsterfilmes.com/catarata/abril-2026` → biblioteca de entregas
   - Meses da biblioteca salvos como `{mes-ano}/index.html` (sem `.html` na URL)

4. **Slugs personalizados** — dicionário `SLUG_CLIENTES` em `gerar_aprovacoes.py`
   e `gerar_biblioteca.py`. Atualmente só tem `"Catarata Center": "catarata"`.

5. **Mensagem WhatsApp no final** — o `gerar_aprovacoes.py` salva a mensagem em
   `/tmp/forster_whatsapp_msg.txt` e o `Fluxo Completo.command` relê no final,
   depois do push.

6. **Todos os arquivos existentes movidos** — `aprovacao/catarata-center/` →
   `catarata/`, demais clientes movidos para a raiz do repo.

---

## ESTRUTURA DO REPOSITÓRIO (atual)

```
forster-aprovacoes/
├── CNAME                          ← aprovar.forsterfilmes.com
├── template.html                  ← template HTML base
├── [slug-cliente]/                ← uma pasta por cliente
│   ├── index.html                 ← versão mais recente
│   ├── YYYY-MM-DD.html            ← aprovação por período
│   ├── [mes-ano]/index.html       ← biblioteca do mês (URL limpa)
│   └── estado-YYYY-MM.json        ← estado de aprovação (lido pelo JS)
├── scripts/
│   ├── gerar_aprovacoes.py
│   ├── gerar_biblioteca.py
│   ├── subir_reels.py
│   └── validar_arquivos.py
├── Fluxo Completo.command
├── Entrega de Vídeos.command
├── GUIA_SILVANA.md
├── DOCUMENTACAO_TECNICA.md
└── PROMPT_HANDOFF_SAMUEL.md       ← este arquivo
```

---

## DNS GODADDY — verificar se foi feito

O DNS ainda precisa ser configurado manualmente no painel do GoDaddy.
Se `aprovar.forsterfilmes.com` ainda não funcionar, o Samuel precisa:

1. Entrar em godaddy.com → Meus Produtos → DNS ao lado de `forsterfilmes.com`
2. Adicionar registro:
   - Tipo: CNAME
   - Nome: `aprovar`
   - Valor: `oiforster.github.io`
   - TTL: 1 hora
3. Salvar. Pode demorar alguns minutos para propagar.

Verificar se funcionou: `dig aprovar.forsterfilmes.com CNAME`

---

## COMO ADICIONAR SLUG PERSONALIZADO PARA OUTRO CLIENTE

Editar `SLUG_CLIENTES` nos dois scripts:

```python
# Em scripts/gerar_aprovacoes.py E scripts/gerar_biblioteca.py
SLUG_CLIENTES = {
    "Catarata Center": "catarata",
    "Óticas Casa Marco": "oticas",   # ← exemplo de adição
}
```

Depois mover a pasta existente:
```bash
cd ~/Documents/forster-aprovacoes
git mv oticas-casa-marco oticas
git add .
git commit -m "feat: slug personalizado oticas-casa-marco → oticas"
git push
```

---

## COMO RODAR LOCALMENTE PARA TESTAR

```bash
cd ~/Documents/forster-aprovacoes && git pull

# Gerar aprovações do Catarata Center para abril
python3 scripts/gerar_aprovacoes.py --cliente "Catarata Center" --mes 2026-04

# Gerar biblioteca de entregas do Catarata Center
python3 scripts/gerar_biblioteca.py --cliente "Catarata Center" --mes 2026-04

# Publicar
git add . && git commit -m "teste" && git push
```

---

## PROBLEMAS CONHECIDOS

### `chmod +x` perdido após git pull/reset
Synology Drive não preserva permissões Unix. Rodar após qualquer atualização:
```bash
chmod +x ~/Documents/forster-aprovacoes/*.command
```

### git pull travando por arquivos divergentes
```bash
cd ~/Documents/forster-aprovacoes
git fetch origin main
git reset --hard origin/main
```

### YouTube: `invalid_scope`
Deletar `scripts/youtube_token.json` e rodar o script novamente para reautenticar.

### Dependências YouTube não instaladas (Mac da Silvana)
```bash
pip3 install --user google-api-python-client google-auth-oauthlib
```

---

## ARQUIVOS DE REFERÊNCIA

- Documentação técnica completa: `~/Documents/forster-aprovacoes/DOCUMENTACAO_TECNICA.md`
- Guia da Silvana: `~/Documents/forster-aprovacoes/GUIA_SILVANA.md`
- Processo de edição mensal Joele: `~/Library/CloudStorage/SynologyDrive-Agencia/_Interno/Processos/Processo_Edicao_Mensal_Joele.md`
- Processo de edição GLPI: `~/Library/CloudStorage/SynologyDrive-Agencia/_Interno/Processos/Processo_Edicao_GLPI.md`
```
