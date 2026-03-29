# Prompt de continuação — Redesign da página de aprovações

> Copiar o bloco abaixo e colar direto no Claude.
> Última atualização: 2026-03-29

---

```
Estou continuando o desenvolvimento do sistema de aprovações da Forster Filmes.
A tarefa agora é o REDESIGN COMPLETO da página de aprovação.

---

## REPOSITÓRIO

Pasta local: ~/Documents/forster-aprovacoes
GitHub: https://github.com/oiforster/forster-aprovacoes
Site: https://aprovar.forsterfilmes.com

Antes de qualquer coisa:
cd ~/Documents/forster-aprovacoes && git pull

---

## PLANO COMPLETO

Ler o plano detalhado em:
~/.claude/plans/majestic-petting-plum.md

Resumo das 7 mudanças:

1. Nova estrutura de URLs: YYYY-MM/index.html em vez de YYYY-MM-DD.html
2. Índice de meses na raiz do cliente (index.html)
3. Restaurar estado ao carregar (fetch estado JSON do GitHub)
4. Persistir comentários de ajuste no JSON
5. Design refinado Forster Filmes (Inter + Playfair, off-white, sombras sutis)
6. Ordenação atrito zero: pendentes no topo, aprovados embaixo
7. Seção de Frames ao final com lightbox e galeria

---

## DADOS REAIS PARA TESTE — Casa Marco Abril 2026

Status recebido do cliente:

✅ 01/04 — Peças clássicas que atravessam o tempo — Aprovado
✅ 03/04 — Frase reflexiva — Ver bem é ver a vida com mais intensidade — Aprovado
✅ 05/04 — Armações animal print — Aprovado
✅ 07/04 — Qual você escolhe? — Aprovado
⚠️ 09/04 — X-Watch Prisma — pulseiras intercambiáveis — Ajuste: "Preciso só confirmar se a bateria dura 7 dias"
⚠️ 11/04 — Mitos e verdades sobre óculos — Ajuste: "Ficou muito bom …. No post 7 como fala de óculos de sol e não transitions, sugiro colocar uma foto dele com dólar, acho que tem a imagem ."
✅ 13/04 — Escolhendo seus óculos de sol — Aprovado
⚠️ 15/04 — Dica: como limpar as lentes do jeito certo — Ajuste: "Na verdade o paninho que vem junto com o óculos ele é só para guardar os óculos para não bater as lentes no estojo. O correto seria borrifar com spray especial ( limpa lentes) e depois lenço mágico, mas a primeira opção seria embaixo da água corrente com um pingo de detergente no dedo e secar com papel macio . o lenço mágico seria a melhor opção se tiver marcas digitais na lente e estiver na rua, para não limpar na camiseta. Mas aí tu vê por favor como coloca"
✅ 17/04 — Mesma armação, duas cores — Aprovado
⚠️ 19/04 — Lentes fotossensíveis: como funcionam — Ajuste: "Talvez colocar ambiente interno ao invés de ambiente fechado"
✅ 21/04 — Clip-on: dois em um no seu estilo — Aprovado
✅ 23/04 — Frase reflexiva — cuide da visão, cuide da vida — Aprovado
✅ 25/04 — Três armações femininas que merecem atenção — Aprovado
⚠️ 27/04 — Como é o atendimento na Casa Marco? — Ajuste: "Sugiro mudar a foto, porque a Graci não é mais nossa funcionária"
✅ 29/04 — Lente filtro azul: tudo que você precisa saber — Aprovado

Usar esses dados para popular o estado JSON e testar a visualização.

---

## ARQUIVOS CRÍTICOS

- template.html — template base de todas as páginas (redesign completo)
- scripts/gerar_aprovacoes.py — gerador de páginas + estado JSON
- scripts/gerar_entrega_videos.py — contém sistema de frames (reutilizar)

---

## IDENTIDADE VISUAL FORSTER FILMES

- Tipografia: Inter (corpo) + Playfair Display (títulos)
- Mesmas fontes das propostas web (repo forster-propostas)
- Cores neutras: fundo off-white (#FAFAF8), cards brancos, sombras sutis
- Acentos funcionais: verde para aprovado, âmbar para ajuste
- Mobile-first, espaçamento generoso, estética editorial

---

## REQUISITOS DO SAMUEL

1. Aprovações devem persistir visualmente ao recarregar a página
2. Comentários de ajuste devem aparecer no card do post
3. Posts pendentes ficam no TOPO (atrito zero)
4. Posts aprovados/ajustados ficam embaixo com visual discreto
5. Seção de Frames no final com lightbox (long-press pra salvar)
6. Índice de meses na raiz do cliente
7. Design refinado, intuitivo, zero atrito
8. Performance: thumbnails como arquivos .jpg, não base64 no HTML
```
