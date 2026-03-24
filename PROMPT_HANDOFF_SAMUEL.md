# Prompt de continuação — Mac do Samuel

> Copiar o bloco abaixo e colar direto no Claude (Cowork) no Mac do Samuel.
> Última atualização: 2026-03-24

---

```
Estou continuando o desenvolvimento do sistema de entrega de vídeos da Forster Filmes. Aqui está o contexto completo do que foi feito e o que precisa ser feito agora.

---

## CONTEXTO DO SISTEMA

O sistema gera páginas HTML estáticas (GitHub Pages) para clientes revisarem e aprovarem vídeos. O script principal é `scripts/gerar_entrega_videos.py` dentro do repositório `~/Documents/forster-aprovacoes/`.

O repositório fica em `~/Documents/forster-aprovacoes/` em cada Mac — NUNCA dentro do Synology ou Google Drive, para evitar corrupção do índice git.

---

## O QUE FOI FEITO NAS ÚLTIMAS SESSÕES (não repetir)

1. Script migrado de links Synology para File IDs do Google Drive via `xattr`
2. Frames no lightbox carregam em full-res via `lh3.googleusercontent.com/d/FILE_ID`
3. Botão "Salvar vídeo original":
   - Android/desktop: download direto via `drive.google.com/uc?export=download&id=FILE_ID&confirm=t`
   - iPhone: abre overlay `<video>` com `drive.google.com/uc?id=FILE_ID` como src + hint de long-press para salvar na Galeria
4. Auto-detecção da conta do Google Drive (escaneia `~/Library/CloudStorage/GoogleDrive-*/Meu Drive/Forster Filmes/CLAUDE_COWORK`)
5. Repositório git migrado de `SynologyDrive/_Interno/forster-aprovacoes` para `~/Documents/forster-aprovacoes`
6. `DOCUMENTACAO_TECNICA.md` e `GUIA_SILVANA.md` já estão atualizados no repositório (commit confirmado)
7. Cliente William Dhein: 53/53 frames com URL Drive ✅, REEL 01 com download ✅

---

## DIAGNÓSTICO ATUAL — REELs 02–04 do William Dhein sem botão de download

### Causa raiz identificada

O Google Drive for Desktop **não atribui** o xattr `com.google.drivefs.item-id#S` a arquivos em modo streaming (online-only). O script depende desse xattr para obter o File ID.

### Estado de cada REEL no Google Drive

| Arquivo | Synology | Google Drive | xattr |
|---------|----------|--------------|-------|
| REEL 01 – Quem é o Dr. William.mov | ✅ | ✅ | ✅ funciona |
| REEL 02 – O que é Osteopatia.mov | ✅ | ❌ ausente (apenas capa.jpg chegou) | ❌ |
| REEL 03 - Fisioterapia e Especialidades.mov | ✅ | ✅ (green checkmark) | ❌ sem xattr |
| REEL 04 – Como Funcionam os Atendimentos.mov | ✅ | ✅ (green checkmark) | ❌ sem xattr |

### Pasta de referência

- Synology: `~/Library/CloudStorage/SynologyDrive-Agencia/_Clientes/Clientes Pontuais/William Dhein/2026-03 - Entrega William Dhein/01 - Reels/`
- Google Drive: `~/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK/Agência/_Clientes/Clientes Pontuais/William Dhein/2026-03 - Entrega William Dhein/01 - Reels/`

---

## O QUE FAZER AGORA (em ordem)

### Passo 1 — Forçar xattr nos REELs 03 e 04 (já no Drive)

No Finder, navegar até a pasta `01 - Reels` no **Google Drive** (não no Synology).
Selecionar `REEL 03 - Fisioterapia e Especialidades.mov` e `REEL 04 – Como Funcionam os Atendimentos.mov`.
Clicar com botão direito → procurar opção **"Disponibilizar off-line"** (ou "Make available offline").
Aguardar download completo (ícones de nuvem viram checkmarks verdes com seta para baixo).

Verificar depois:
```bash
xattr -p 'com.google.drivefs.item-id#S' "/Users/samuelforster/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK/Agência/_Clientes/Clientes Pontuais/William Dhein/2026-03 - Entrega William Dhein/01 - Reels/REEL 03 - Fisioterapia e Especialidades.mov"
```

### Passo 2 — Investigar REEL 02 ausente no Google Drive

O arquivo `REEL 02 – O que é Osteopatia.mov` existe no Synology mas NÃO chegou ao Google Drive (só a capa.jpg sincronizou). Verificar no painel do Cloud Sync no DSM do Synology se há erros de sync para esse arquivo.

Se o Cloud Sync não resolver, copiar manualmente o arquivo para forçar a re-sincronização:
no Synology Drive, mover o REEL 02 .mov para fora da pasta e de volta para dentro — isso força o Cloud Sync a reprocessar.

### Passo 3 — Rodar o script e publicar o HTML final

Quando todos os 4 REELs tiverem xattr:

```bash
cd ~/Documents/forster-aprovacoes && git pull && python3 scripts/gerar_entrega_videos.py --cliente "William Dhein" --mes 2026-03 --pontual && git add . && git commit -m "aprovacao: william-dhein 2026-03 todos os reels" && git push
```

### Passo 4 — Testar no iPhone

Abrir no Safari do iPhone:
`https://oiforster.github.io/forster-aprovacoes/aprovacao/william-dhein/2026-03.html`

Tocar em "Salvar vídeo original" em cada REEL. Resultado esperado:
- Overlay escuro com o vídeo carregando
- Texto "Segure o dedo sobre o vídeo para salvar na galeria"
- Long-press → menu do Safari → "Salvar vídeo" → vai para a Galeria de Fotos

### Passo 5 (opcional, recomendado) — Implementar fallback `_gdrive.md`

Adicionar ao script suporte a um arquivo `_gdrive.md` na pasta de vídeos, para especificar File IDs manualmente quando o xattr não está disponível. Formato:

```
# IDs manuais do Google Drive (fallback quando xattr não disponível)
REEL 02 – O que é Osteopatia: FILE_ID_AQUI
REEL 03 - Fisioterapia e Especialidades: FILE_ID_AQUI
REEL 04 – Como Funcionam os Atendimentos: FILE_ID_AQUI
```

Os File IDs são obtidos via Finder → botão direito no arquivo no Google Drive → Compartilhar → Copiar link → extrair o ID da URL (parte após `/d/` ou `id=`).

---

## ARQUIVOS DE REFERÊNCIA IMPORTANTES

- Script principal: `~/Documents/forster-aprovacoes/scripts/gerar_entrega_videos.py`
- Documentação técnica: `~/Documents/forster-aprovacoes/DOCUMENTACAO_TECNICA.md`
- Log de desenvolvimento: `~/Library/CloudStorage/SynologyDrive-Agencia/_Interno/Processos/Entrega_Videos_Desenvolvimento.md`
- Este handoff (Synology): `~/Library/CloudStorage/SynologyDrive-Agencia/_Interno/forster-aprovacoes/PROMPT_HANDOFF_SAMUEL.md`
- Este handoff (repositório): `~/Documents/forster-aprovacoes/PROMPT_HANDOFF_SAMUEL.md`

---

## SE PRECISAR DEPURAR O SCRIPT

```bash
cd ~/Documents/forster-aprovacoes && python3 scripts/gerar_entrega_videos.py --cliente "William Dhein" --mes 2026-03 --pontual
```

O script imprime o status de cada vídeo antes de gerar o HTML. Procurar por ✅ (Drive OK) ou ⚠️ (sem URL Drive).
```
