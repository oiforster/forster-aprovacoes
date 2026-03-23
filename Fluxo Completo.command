#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Forster Filmes — Fluxo Completo de Aprovações
#  Valida → Sobe ao YouTube → Gera páginas → Publica
#  Duplo clique para rodar.
# ─────────────────────────────────────────────────────────────

REPO="$HOME/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK/Agência/_Interno/forster-aprovacoes"
SCRIPTS="$REPO/scripts"

clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   FORSTER FILMES — Fluxo Completo de Aprovações"
echo "   Validar → YouTube → Gerar páginas → Publicar"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── QUAL CLIENTE? ────────────────────────────────────
echo "Para qual cliente? (deixe em branco para TODOS)"
echo ""
echo "   1. Óticas Casa Marco"
echo "   2. Colégio Luterano Redentor"
echo "   3. Vanessa Mainardi"
echo "   4. Joele Lerípio"
echo "   5. Micheline Twigger"
echo "   6. Fyber Show Piscinas"
echo "   7. Prisma Especialidades"
echo "   8. Martina Schneider"
echo "   9. Catarata Center"
echo "  10. Baviera Tecnologia"
echo ""
read -p "  Nome ou número (Enter = todos): " CLIENTE_INPUT
echo ""

case "$CLIENTE_INPUT" in
  1) CLIENTE="Óticas Casa Marco" ;;
  2) CLIENTE="Colégio Luterano Redentor" ;;
  3) CLIENTE="Vanessa Mainardi" ;;
  4) CLIENTE="Joele Lerípio" ;;
  5) CLIENTE="Micheline Twigger" ;;
  6) CLIENTE="Fyber Show Piscinas" ;;
  7) CLIENTE="Prisma Especialidades" ;;
  8) CLIENTE="Martina Schneider" ;;
  9) CLIENTE="Catarata Center" ;;
  10) CLIENTE="Baviera Tecnologia" ;;
  "") CLIENTE="" ;;
  *) CLIENTE="$CLIENTE_INPUT" ;;
esac

# ── QUAL MÊS? ─────────────────────────────────────────
echo "Qual mês? (deixe em branco para o mês atual)"
read -p "  YYYY-MM (ex: 2026-04) ou Enter: " MES_INPUT
echo ""

MES_ARG=""
if [ -n "$MES_INPUT" ]; then
  MES_ARG="--mes $MES_INPUT"
fi

CLIENTE_ARG=""
if [ -n "$CLIENTE" ]; then
  CLIENTE_ARG="--cliente \"$CLIENTE\""
fi

# ════════════════════════════════════════════════════
# ETAPA 1 — VALIDAÇÃO
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 1/4 — Validando arquivos..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

eval python3 "$SCRIPTS/validar_arquivos.py" $CLIENTE_ARG $MES_ARG
VALIDACAO_STATUS=$?
echo ""

if [ $VALIDACAO_STATUS -ne 0 ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  ❌ Foram encontrados erros nos arquivos."
  echo ""
  echo "  Corrija os problemas acima e rode novamente."
  echo "  Os erros marcados com ❌ impedem o funcionamento"
  echo "  correto das páginas de aprovação."
  echo ""
  read -p "  Continuar mesmo assim? (s/N): " FORCAR
  echo ""
  if [[ ! "$FORCAR" =~ ^[Ss]$ ]]; then
    echo "  Operação cancelada. Corrija os erros e tente novamente."
    echo ""
    read -p "Pressione Enter para fechar..."
    exit 1
  fi
  echo "  ⚠️  Continuando com erros (você escolheu forçar)."
  echo ""
fi

# ════════════════════════════════════════════════════
# ETAPA 2 — UPLOAD YOUTUBE
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 2/4 — Subindo Reels ao YouTube..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

eval python3 "$SCRIPTS/subir_reels.py" $CLIENTE_ARG $MES_ARG
YOUTUBE_STATUS=$?
echo ""

if [ $YOUTUBE_STATUS -ne 0 ]; then
  echo "  ❌ Erro no upload ao YouTube."
  echo ""
  read -p "  Continuar gerando as páginas mesmo assim? (s/N): " CONTINUAR_YT
  echo ""
  if [[ ! "$CONTINUAR_YT" =~ ^[Ss]$ ]]; then
    echo "  Operação cancelada."
    read -p "Pressione Enter para fechar..."
    exit 1
  fi
fi

# ════════════════════════════════════════════════════
# ETAPA 3 — GERAR PÁGINAS DE APROVAÇÃO
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 3/4 — Gerando páginas de aprovação..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

eval python3 "$SCRIPTS/gerar_aprovacoes.py" $CLIENTE_ARG $MES_ARG
GERAR_STATUS=$?
echo ""

if [ $GERAR_STATUS -ne 0 ]; then
  echo "  ❌ Erro ao gerar páginas."
  read -p "Pressione Enter para fechar..."
  exit 1
fi

# ════════════════════════════════════════════════════
# ETAPA 4 — PUBLICAR
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 4/4 — Publicar no site?"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "  Publicar agora em oiforster.github.io? (S/n): " PUBLICAR
echo ""

if [[ "$PUBLICAR" =~ ^[Nn]$ ]]; then
  echo "  Páginas geradas mas não publicadas."
  echo "  Rode este arquivo novamente para publicar."
else
  echo "  Publicando..."
  cd "$REPO"
  git add .
  git commit -m "Aprovações — $(date '+%d/%m/%Y')"
  git push

  if [ $? -eq 0 ]; then
    echo ""
    echo "  ✅ Site atualizado!"
    echo "  👉 https://oiforster.github.io/forster-aprovacoes"
  else
    echo ""
    echo "  ❌ Erro ao publicar. Tente manualmente:"
    echo "  cd \"$REPO\" && git push"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Fluxo concluído. Copie a mensagem acima"
echo "  e envie no WhatsApp do cliente."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Pressione Enter para fechar..."
