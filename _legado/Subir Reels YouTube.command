#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Forster Filmes — Upload de Reels para o YouTube
#  Duplo clique para rodar. Não precisa saber usar o Terminal.
# ─────────────────────────────────────────────────────────────

REPO="$HOME/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK/Agência/_Interno/forster-aprovacoes"
SCRIPT="$REPO/scripts/subir_reels.py"

clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   FORSTER FILMES — Upload de Reels para YouTube"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Os vídeos sobem como NÃO LISTADOS."
echo "  O link vai para o _youtube.md de cada cliente."
echo ""
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
echo ""
read -p "  Mês no formato YYYY-MM (ex: 2026-04): " MES_INPUT
echo ""

MES_ARG=""
if [ -n "$MES_INPUT" ]; then
  MES_ARG="--mes $MES_INPUT"
fi

# ── CONFIRMAÇÃO ───────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$CLIENTE" ]; then
  echo "  Cliente: $CLIENTE"
else
  echo "  Cliente: TODOS"
fi
if [ -n "$MES_INPUT" ]; then
  echo "  Mês: $MES_INPUT"
else
  echo "  Mês: atual"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "  Confirmar e iniciar upload? (S/n): " CONFIRMAR
echo ""

if [[ "$CONFIRMAR" =~ ^[Nn]$ ]]; then
  echo "Cancelado."
  read -p "Pressione Enter para fechar..."
  exit 0
fi

# ── UPLOAD ───────────────────────────────────────────
echo "Iniciando upload..."
echo ""

if [ -n "$CLIENTE" ]; then
  python3 "$SCRIPT" --cliente "$CLIENTE" $MES_ARG
else
  python3 "$SCRIPT" $MES_ARG
fi

STATUS=$?
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $STATUS -ne 0 ]; then
  echo ""
  echo "❌ Ocorreu um erro durante o upload."
  echo "   Verifique se as credenciais do YouTube estão ok."
  echo "   Em caso de dúvida, chama o Samuel."
else
  echo ""
  echo "✅ Upload concluído!"
  echo ""
  echo "   Próximo passo: rodar o Gerar Aprovações.command"
  echo "   para incluir os vídeos nas páginas de aprovação."
fi

echo ""
read -p "Pressione Enter para fechar..."
