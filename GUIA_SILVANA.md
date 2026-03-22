# Guia de Aprovações — Silvana

Sistema de aprovação de conteúdo da Forster Filmes. Este guia cobre tudo que você precisa saber para usar o sistema no dia a dia.

---

## Como funciona (visão geral)

1. Você escreve o conteúdo do mês no Obsidian como sempre fez
2. Quando as artes ficarem prontas, você joga os arquivos numa pasta `_Artes/` com nome no padrão `DD-MM.jpg`
3. Você abre o arquivo `Gerar Aprovações.command` (duplo clique)
4. O sistema gera as páginas e te dá a mensagem de WhatsApp pronta
5. Você copia e manda no WhatsApp do cliente
6. O cliente abre o link no celular, aprova ou pede ajuste, e clica em enviar
7. As respostas chegam no painel do Netlify

---

## Passo a passo semanal

### 1. Escrever o conteúdo no Obsidian

Escreva o arquivo `YYYY-MM — Conteúdo Mensal [Cliente].md` normalmente, com o calendário em tabela:

```
| Data | Formato | Título / Tema | Status |
|------|---------|---------------|--------|
| 07/04 Ter | Card | Texto do card aqui | Criado |
| 08/04 Qua | Carrossel | Título do carrossel | Criado |
```

E as seções de conteúdo detalhado para cada post:

```
#### 07/04 (Ter) — Card — Texto do card aqui

**Texto do card:**
O texto que vai aparecer na arte.

**Legenda:**
A legenda do post no Instagram.
```

> O sistema extrai automaticamente o texto e a legenda para mostrar ao cliente.

---

### 2. Adicionar as artes (quando prontas)

Dentro da pasta `04_Estratégia/` do cliente, crie a pasta `_Artes/YYYY-MM/` e jogue os arquivos com o nome no padrão **DD-MM.jpg**:

```
04_Estratégia/
├── 2026-04 — Conteúdo Mensal Prisma Especialidades.md
└── _Artes/
    └── 2026-04/
        ├── 07-04.jpg    ← arte do post de 07/04
        ├── 08-04.jpg    ← arte do post de 08/04
        └── 09-04.jpg
```

**Regras de nomenclatura:**
- Um post por dia: `07-04.jpg`
- Dois posts no mesmo dia: `07-04-1.jpg` e `07-04-2.jpg`
- Formatos aceitos: `.jpg`, `.jpeg`, `.png`, `.webp`

> **Importante:** a pasta `_Artes/` precisa estar compartilhada no Google Drive com "qualquer pessoa com o link pode visualizar". Faça isso uma vez só por cliente — clique direito na pasta `_Artes/` no Drive → Compartilhar → Qualquer pessoa com o link.

---

### 3. Gerar as páginas de aprovação

Abra o Finder e navegue até:
`Google Drive → Meu Drive → Forster Filmes → CLAUDE_COWORK → Agência → _Interno → forster-aprovacoes`

Dê **duplo clique** em `Gerar Aprovações.command`.

Uma janela do Terminal vai abrir e perguntar:
1. **Para qual cliente?** — Digite o número ou nome, ou pressione Enter para gerar para todos
2. **Qual período?** — Pressione Enter para a próxima semana (padrão)
3. **Publicar no site?** — Digite `S` e Enter

Pronto. O sistema vai mostrar a mensagem de WhatsApp pronta para cada cliente.

---

### 4. Enviar para o cliente

Copie a mensagem que o sistema gerou e mande no WhatsApp do cliente. Exemplo:

> *Olá! 😊*
> *Aqui estão os posts da semana de 7 a 13 de abril para aprovação.*
> *👉 https://forster-aprovacoes.netlify.app/aprovacao/prisma-especialidades/*
> *Você pode aprovar cada post ou pedir ajuste com um toque. Se preferir, tem um botão para aprovar tudo de uma vez.*
> *Qualquer dúvida, é só chamar! 🙌*

---

### 5. Ver as respostas

As aprovações dos clientes ficam registradas no painel do Netlify:

1. Acesse [app.netlify.com](https://app.netlify.com)
2. Clique no projeto `forster-aprovacoes`
3. Vá em **Forms** no menu lateral
4. Clique no formulário do cliente para ver as respostas

Cada resposta mostra: cliente, período, e o status de cada post (aprovado ou pedir ajuste, com o comentário se houver).

---

## Comandos avançados (opcional)

Se quiser rodar direto pelo Terminal (mais rápido quando já sabe o que quer):

```bash
cd ~/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu\ Drive/Forster\ Filmes/CLAUDE_COWORK/Agência/_Interno/forster-aprovacoes

# Próxima semana, todos os clientes
python3 scripts/gerar_aprovacoes.py

# Cliente específico, próxima semana
python3 scripts/gerar_aprovacoes.py --cliente "Prisma"

# Semana específica
python3 scripts/gerar_aprovacoes.py --cliente "Prisma" --semana 2026-04-07

# Mês completo
python3 scripts/gerar_aprovacoes.py --cliente "Prisma" --mes 2026-04

# Publicar
git add . && git commit -m "Aprovações" && git push
```

---

## Dúvidas frequentes

**O cliente disse que não consegue abrir o link.**
Peça para ele tentar no Chrome ou Safari. O link funciona em qualquer celular, sem precisar de login.

**O post apareceu sem a imagem.**
A arte pode não estar na pasta `_Artes/` com o nome correto, ou a pasta não está compartilhada publicamente no Drive. Verifique o nome do arquivo (ex: `07-04.jpg`) e as permissões da pasta.

**O sistema não encontrou posts para um cliente.**
Verifique se o arquivo `YYYY-MM — Conteúdo Mensal [Cliente].md` existe na pasta `04_Estratégia/` do cliente e se tem a tabela de calendário com datas no formato `DD/MM`.

**Preciso gerar a aprovação do mês todo de uma vez.**
Use a opção 3 no `.command` ou o argumento `--mes 2026-04` no Terminal.

**O cliente aprovou tudo pelo WhatsApp mas não usou o link.**
Tudo bem — o link fica disponível para ele usar quando quiser. A aprovação por WhatsApp vale, só não fica registrada no sistema.

---

*Qualquer dúvida, chama o Samuel.*
