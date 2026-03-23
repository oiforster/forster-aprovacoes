# Guia de Aprovações — Silvana

Sistema de aprovação de conteúdo da Forster Filmes.
Última atualização: março de 2026.

---

## Como funciona (visão geral)

1. Você escreve o conteúdo do mês no Obsidian como sempre fez
2. Quando as artes ficarem prontas, você joga os arquivos na pasta `Posts_Fixos/` da Entrega do cliente com os nomes no padrão correto
3. Se houver Reels para subir ao YouTube, o Samuel roda o `subir_reels.py` primeiro
4. Você abre o `Gerar Aprovações.command` (duplo clique)
5. O sistema gera as páginas e te dá a mensagem de WhatsApp pronta
6. Você copia e manda no WhatsApp do cliente
7. O cliente abre o link, aprova ou pede ajuste em cada post
8. *(em desenvolvimento)* As respostas chegam formatadas no WhatsApp de volta para você

---

## Estrutura de pastas das artes

As artes ficam dentro da pasta de entrega mensal do cliente, em `Posts_Fixos/`:

```
06_Entregas/
└── 2026-04 Entrega [Cliente]/
    ├── Posts_Fixos/
    │   ├── 07-04.jpg          ← card ou reel (post único)
    │   ├── 09-04_1.jpg        ← slide 1 do carrossel de 09/04
    │   ├── 09-04_2.jpg        ← slide 2
    │   └── 09-04_3.jpg        ← slide 3
    └── Videos/
        ├── REEL 01 – Nome do Vídeo.mov
        ├── REEL 01 – Nome do Vídeo (capa).jpg
        └── _youtube.md        ← gerado automaticamente pelo subir_reels.py
```

### Nomenclatura das artes

| Tipo | Nome do arquivo | Exemplo |
|------|----------------|---------|
| Post único (card, foto) | `DD-MM.jpg` | `07-04.jpg` |
| Slide 1 de carrossel | `DD-MM_1.jpg` | `09-04_1.jpg` |
| Slide 2 de carrossel | `DD-MM_2.jpg` | `09-04_2.jpg` |
| Capa de Reel (só para upload YouTube) | `REEL NN – Nome (capa).jpg` | `REEL 01 – Dia da Mulher (capa).jpg` |

**Formatos aceitos:** `.jpg`, `.jpeg`, `.png`, `.webp`

> A pasta `Posts_Fixos/` precisa estar compartilhada no Google Drive com "qualquer pessoa com o link pode visualizar". Faça isso uma vez por cliente.

---

## Como linkar um Reel a um post no Obsidian

No arquivo de conteúdo mensal, no bloco do post que é um Reel, adicione o campo `**Vídeo:**` com o nome exato do arquivo de vídeo (sem extensão):

```
#### 28/03 (Sáb) — Reel — Contagem regressiva

**Vídeo:**
REEL 12 - Dia da Mulher

**Legenda:**
Texto da legenda aqui.
```

O nome precisa bater exatamente com o arquivo `.mov` na pasta `Videos/`. O Samuel sobe o vídeo ao YouTube antes de você gerar as aprovações — o sistema detecta automaticamente.

---

## Gerar as páginas de aprovação

Navegue no Finder até:
`Google Drive → Meu Drive → Forster Filmes → CLAUDE_COWORK → Agência → _Interno → forster-aprovacoes`

Dê **duplo clique** em `Gerar Aprovações.command`.

Uma janela do Terminal vai abrir e executar o script. Aguarde até ver a mensagem de WhatsApp gerada na tela.

Se quiser gerar apenas para um cliente específico, abra o Terminal e rode:

```bash
python3 ~/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu\ Drive/Forster\ Filmes/CLAUDE_COWORK/Agência/_Interno/forster-aprovacoes/scripts/gerar_aprovacoes.py --cliente "Nome do Cliente" --mes 2026-04
```

---

## Publicar no site

Após gerar as páginas, publique com este comando no Terminal:

```bash
cd ~/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu\ Drive/Forster\ Filmes/CLAUDE_COWORK/Agência/_Interno/forster-aprovacoes && git add . && git commit -m "Aprovações" && git push
```

O site atualiza em cerca de 30 segundos em:
`https://oiforster.github.io/forster-aprovacoes/`

---

## O que o cliente vê

- Lista de todos os posts da semana (ou mês) com data, título e formato
- A arte (imagem, carrossel ou vídeo) de cada post
- A legenda que vai no Instagram
- Botão **✓ Aprovar** ou **✗ Pedir ajuste** em cada post
- Se pedir ajuste: campo de texto + botão "Registrar observação"
- Botão geral **Aprovar todos os posts**
- Barra de progresso mostrando quantos já foram respondidos
- Ao finalizar todos: botão **Enviar aprovações**

### Como o cliente assiste um Reel

- **No celular:** toca na capa → abre direto no app do YouTube
- **No computador:** toca na capa → reproduz inline na página (proporção 9:16)

---

## Estrutura do arquivo de conteúdo mensal

O script lê os dados diretamente do `.md`. A estrutura esperada é:

### Tabela de calendário (obrigatória)

```markdown
| Data | Formato | Título / Tema | Status |
|------|---------|---------------|--------|
| 07/04 Ter | Card | Título do post | Criado |
| 09/04 Qui | Carrossel | Título do carrossel | Criado |
| 28/03 Sáb | Reel | Contagem regressiva | Criado |
```

### Seções de conteúdo detalhado

```markdown
#### 07/04 (Ter) — Card — Título do post

**Texto do card:**
Texto que aparece na arte.

**Legenda:**
Legenda do post no Instagram.

---

#### 09/04 (Qui) — Carrossel — Título do carrossel

**Slide 1 (Título do slide):**
Texto do slide 1.

**Slide 2 (Outro título):**
Texto do slide 2.

**Legenda:**
Legenda do carrossel.

---

#### 28/03 (Sáb) — Reel — Contagem regressiva

**Vídeo:**
REEL 12 - Dia da Mulher

**Legenda:**
Legenda do Reel.
```

> Quando há arte, o texto do card/slides fica oculto (já está visível na arte). Só a legenda aparece.

---

## Próximos passos do sistema

- **Retorno do cliente direto no WhatsApp:** ao enviar aprovações, o cliente vai receber um botão que gera uma mensagem formatada para mandar no WhatsApp da Silvana, com todos os status de aprovação e observações
