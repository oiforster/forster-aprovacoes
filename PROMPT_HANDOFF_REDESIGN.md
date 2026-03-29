# Prompt de continuação — Redesign da página de aprovações

> Status: **CONCLUÍDO** em 2026-03-29
> Implementado e testado com dados reais da Casa Marco abril 2026.

---

## O que foi implementado

### 1. Nova estrutura de URLs
- Páginas geradas em `YYYY-MM/index.html` (URL limpa: `/slug/2026-04`)
- Páginas legadas (`YYYY-MM-DD.html`) mantidas para links já enviados

### 2. Índice de meses na raiz do cliente
- `index.html` na raiz mostra todos os meses com progresso visual (barra verde, fração X/Y)
- Usa `template_index.html` (Inter + Playfair Display)

### 3. Restaurar estado ao carregar
- `_carregarEstado()` busca o JSON do GitHub via API e aplica visualmente
- Fix encoding UTF-8: `decodeURIComponent(escape(atob(...))))`
- Loading overlay com spinner enquanto carrega

### 4. Persistir comentários de ajuste
- Estado JSON: `{"post-id": {"status": "ajuste", "obs": "texto do cliente"}}`
- Retrocompatível com formato antigo (string pura)
- `_salvarEstado()` salva status + obs ao confirmar observação

### 5. Design refinado Forster Filmes
- Tipografia: Inter (corpo) + Playfair Display (títulos)
- Fundo off-white (#FAFAF8), cards brancos com sombra sutil
- Cards aprovados: borda lateral verde, badge "Aprovado", opacidade 0.8
- Cards com ajuste: borda lateral âmbar, badge "Ajuste solicitado", caixa amarela com observação
- Header branco com borda inferior sutil (sticky)

### 6. Ordenação atrito zero
- Pendentes no topo, ajustes depois, aprovados no final
- Separadores: "Aguardando sua aprovação" / "Já respondidos"
- Reordenação acontece só quando há estado salvo (segunda visita em diante)

### 7. Seção de Frames (estrutura pronta)
- CSS + HTML + lightbox com swipe mobile e setas desktop
- Placeholder `{{FRAMES_HTML}}` no template
- Pendente: integração com `gerar_entrega_videos.py` para gerar thumbnails como arquivos .jpg

---

## Arquivos modificados

| Arquivo | O que mudou |
|---------|-------------|
| `template.html` | Redesign completo: CSS, JS de estado, reordenação, lightbox |
| `template_index.html` | Novo: índice de meses por cliente |
| `scripts/gerar_aprovacoes.py` | Output `YYYY-MM/index.html`, estado formato objeto, `gerar_indice_meses()`, badge + obs-salva no HTML |
| `DOCUMENTACAO_TECNICA.md` | Atualizado com todas as mudanças |
| `GUIA_SILVANA.md` | Atualizado com novo visual e comportamento |
| `PROMPT_HANDOFF_SAMUEL.md` | Adicionada sessão 2026-03-29 |

---

## Pendência futura

- **Seção de Frames:** integrar com `gerar_entrega_videos.py` para gerar thumbnails como arquivos `.jpg` na pasta `artes/frames/` (em vez de base64 no HTML). O CSS e JS do lightbox já estão prontos no template.
