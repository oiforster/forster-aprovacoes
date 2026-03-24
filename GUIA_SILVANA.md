# Guia de Aprovações — Silvana

Sistema de aprovação de conteúdo da Forster Filmes.
Última atualização: março de 2026 — email de redundância adicionado.

---

## Como funciona (visão geral)

1. Você escreve o conteúdo do mês no Obsidian como sempre
2. A designer entrega as artes na pasta `Posts_Fixos/` com os nomes no padrão correto
3. O Samuel nomeia e finaliza os Reels no Final Cut
4. Duplo clique em `Fluxo Completo.command` — o sistema faz o resto
5. Você copia a mensagem de WhatsApp que aparece no Terminal e manda para o cliente
6. O cliente aprova pelo link no celular
7. A resposta chega formatada no WhatsApp (grupo do cliente ou direto com a Silvana/Samuel)

---

## Estrutura de pastas das artes

As artes ficam dentro da pasta de entrega mensal do cliente, em `Posts_Fixos/`:

```
06_Entregas/
└── 2026-04 Entrega [Cliente]/
    ├── Posts_Fixos/
    │   ├── 07-04.jpg          ← card (post único)
    │   ├── 09-04_1.jpg        ← slide 1 do carrossel de 09/04
    │   ├── 09-04_2.jpg        ← slide 2
    │   └── 09-04_3.jpg        ← slide 3
    └── Videos/
        ├── REEL 01 – Nome do Vídeo.mov
        ├── REEL 01 – Nome do Vídeo (capa).jpg
        └── _youtube.md        ← gerado automaticamente
```

### Nomenclatura das artes

| Tipo | Nome do arquivo | Exemplo |
|------|----------------|---------|
| Post único (card, foto) | `DD-MM.jpg` | `07-04.jpg` |
| Slide 1 de carrossel | `DD-MM_1.jpg` | `09-04_1.jpg` |
| Slide 2 em diante | `DD-MM_N.jpg` | `09-04_2.jpg` |
| Capa de Reel (para YouTube) | `REEL NN – Nome (capa).jpg` | `REEL 01 – Abertura (capa).jpg` |

**Formatos aceitos:** `.jpg`, `.jpeg`, `.png`, `.webp`

> A pasta `Posts_Fixos/` precisa estar compartilhada no Google Drive com "qualquer pessoa com o link pode visualizar". Fazer isso uma vez por cliente na primeira entrega.

---

## Como linkar um Reel a um post

No arquivo de conteúdo mensal, no bloco do post que é um Reel, preencher o campo `**Vídeo:**` com o nome exato do arquivo (sem a extensão `.mov`):

```
#### 28/03 (Sáb) — Reel — Contagem regressiva

**Vídeo:**
REEL 12 – Dia da Mulher

**Legenda:**
Texto da legenda aqui.
```

O nome precisa bater exatamente com o arquivo `.mov` na pasta `Videos/`. O Samuel sobe o vídeo ao YouTube antes de gerar as aprovações — o sistema detecta automaticamente.

---

## Usar o Fluxo Completo

No Finder, navegue até:
`Documents → forster-aprovacoes`

Dê **duplo clique** em `Fluxo Completo.command`.

Uma janela do Terminal abre e faz uma série de perguntas:

**1. Para qual cliente?**
Digite o número da lista ou o nome (parcial aceito). Enter = todos.

**2. Qual mês?**
Digite `2026-04` ou Enter para o mês atual.

**3. Qual período para aprovação?**
```
1. Próxima semana (padrão)
2. Semana atual
3. Período personalizado
```
- Opção `1` ou Enter: gera para a semana que começa na próxima segunda
- Opção `2`: gera para a semana atual (de segunda a domingo)
- Opção `3`: você digita a data de início e fim manualmente (aceita `23/03/2026` ou `2026-03-23`)

**4. Continuar com erros?**
Se algum arquivo de arte estiver faltando ou mal nomeado, o sistema avisa. Você pode corrigir e rodar de novo, ou digitar `s` para continuar mesmo assim (útil quando as artes de datas futuras ainda não chegaram).

**5. Publicar no site?**
Digite `s` ou Enter para publicar. O site atualiza em cerca de 30 segundos.

---

## Mensagem de WhatsApp para o cliente

Após gerar as páginas, o Terminal mostra a mensagem pronta para copiar:

```
Olá! 😊

Aqui estão os posts da semana de *30/03 a 5/04* para aprovação.

👉 https://oiforster.github.io/forster-aprovacoes/aprovacao/oticas-casa-marco/

Você pode aprovar cada post ou pedir ajuste com um toque. Se preferir, tem um botão para aprovar tudo de uma vez.

Qualquer dúvida, é só chamar! 🙌
```

Copie e envie no WhatsApp do cliente.

---

## O que o cliente vê

- Lista de todos os posts do período com data, título e formato
- A arte de cada post (imagem, carrossel ou vídeo)
- A legenda que vai no Instagram
- Botão **✓ Aprovar** ou **✗ Pedir ajuste** em cada post
- Se pedir ajuste: campo de texto para registrar a observação
- Botão geral **Aprovar todos os posts**
- Barra de progresso mostrando quantos já foram respondidos
- Ao finalizar: botão **Enviar aprovações**

Ao clicar "Enviar aprovações":
- A mensagem com todos os status é copiada automaticamente para o clipboard do cliente
- O WhatsApp do grupo do cliente (ou contato da Silvana/Samuel) é aberto
- O cliente cola e envia

Depois de enviar, a página mostra: **"Tudo certo por aqui! Você já enviou suas aprovações desta semana."** — e fica bloqueada para evitar envio duplicado.

### Como o cliente assiste um Reel

Ao tocar na capa do vídeo, um player abre por cima da página (tela cheia, proporção 9:16) com o vídeo rodando direto. Botão ✕ fecha. Funciona no celular e no computador.

---

## Canal de retorno por cliente

| Cliente | Onde a aprovação chega |
|---------|----------------------|
| Óticas Casa Marco | WhatsApp da Silvana (direto) |
| Colégio Luterano Redentor | Grupo WhatsApp |
| Vanessa Mainardi | Grupo WhatsApp |
| Joele Lerípio | WhatsApp do Samuel (direto) |
| Micheline Twigger | Grupo WhatsApp |
| Fyber Show Piscinas | Grupo WhatsApp |
| Prisma Especialidades | Grupo WhatsApp |
| Martina Schneider | Grupo WhatsApp |
| Catarata Center | Grupo WhatsApp |
| Baviera Tecnologia | WhatsApp do Samuel (direto) |

---

## Email de redundância automático

Quando o cliente clica **"Enviar aprovações"**, além da mensagem do WhatsApp, um email é disparado automaticamente para `oiforster@gmail.com`. O cliente não vê isso — acontece em background.

**Para que serve:** garantia de que a Forster Filmes recebe o registro das aprovações mesmo que o cliente esqueça de mandar a mensagem no grupo de WhatsApp.

**O que chega no email:**
- Assunto: `Aprovações — [Cliente] — [Período]`
- Remetente aparece como o nome do cliente
- Resumo completo com ✅ aprovados e ⚠️ ajustes, incluindo as observações do cliente

**Não é necessário nenhuma ação da Silvana** — o sistema cuida disso automaticamente. Se a mensagem do WhatsApp chegar normalmente, o email é só um backup. Se não chegar, o email já está na caixa de entrada.

---

## Estrutura do arquivo de conteúdo mensal

O script lê os dados diretamente do `.md`. A estrutura esperada é a do template em `_Templates/Conteudo_Mensal_Template.md`. Campos obrigatórios:

**Tabela de calendário:**
```markdown
| Data | Formato | Título / Tema | Status |
|------|---------|---------------|--------|
| 07/04 Ter | Card | Título do post | Criado |
| 09/04 Qui | Carrossel | Título do carrossel | Criado |
| 28/03 Sáb | Reel | Contagem regressiva | Criado |
```

**Seções de conteúdo** (padrão `#### DD/MM`):
```markdown
#### 07/04 (Ter) — Card — Título do post

**Texto do card:**
Texto que aparece na arte.

**Legenda:**
Legenda do post no Instagram.

---

#### 09/04 (Qui) — Carrossel — Título

**Slide 1 (Título do slide):**
Texto do slide 1.

**Legenda:**
Legenda do carrossel.

---

#### 28/03 (Sáb) — Reel — Contagem regressiva

**Vídeo:**
REEL 12 – Dia da Mulher

**Legenda:**
Legenda do Reel.
```

---

## Subir apenas os Reels ao YouTube (sem gerar aprovações)

Duplo clique em `Subir Reels YouTube.command`. Seleciona cliente e mês, sobe os vídeos e atualiza o `_youtube.md`.

---

## Gerar apenas as aprovações (sem validação nem YouTube)

Duplo clique em `Gerar Aprovações.command`. Útil quando os Reels já foram subidos e você só quer regar as páginas ou republicar.
