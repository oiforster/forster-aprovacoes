#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Forster Filmes — Gerador de Aprovações
#  Duplo clique para rodar. Não precisa saber usar o Terminal.
# ─────────────────────────────────────────────────────────────

REPO="$HOME/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK/Agência/_Interno/forster-aprovacoes"
SCRIPT="$REPO/scripts/gerar_aprovacoes.py"

clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   FORSTER FILMES — Gerador de Aprovações"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── QUAL CLIENTE? ────────────────────────────────────
echo "Para qual cliente? (deixe em branco para TODOS)"
echo ""
echo "  Clientes disponíveis:"
echo "  1. Óticas Casa Marco"
echo "  2. Colégio Luterano Redentor"
echo "  3. Vanessa Mainardi"
echo "  4. Joele Lerípio"
echo "  5. Micheline Twigger"
echo "  6. Fyber Show Piscinas"
echo "  7. Prisma Especialidades"
echo "  8. Martina Schneider"
echo "  9. Catarata Center"
echo " 10. Baviera Tecnologia"
echo ""
read -p "  Nome ou número (Enter = todos): " CLIENTE_INPUT
echo ""

# Converte número para nome
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

# ── QUAL PERÍODO? ─────────────────────────────────────
echo "Qual período gerar?"
echo ""
echo "  1. Próxima semana (padrão)"
echo "  2. Semana específica"
echo "  3. Mês completo"
echo ""
read -p "  Opção (Enter = próxima semana): " PERIODO_OP
echo ""

PERIODO_ARG=""
case "$PERIODO_OP" in
  2)
    read -p "  Segunda-feira da semana (YYYY-MM-DD): " SEMANA
    PERIODO_ARG="--semana $SEMANA"
    ;;
  3)
    read -p "  Mês (YYYY-MM, ex: 2026-04): " MES
    PERIODO_ARG="--mes $MES"
    ;;
  *)
    PERIODO_ARG=""
    ;;
esac

# ── GERA AS PÁGINAS ──────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -n "$CLIENTE" ]; then
  python3 "$SCRIPT" --cliente "$CLIENTE" $PERIODO_ARG
else
  python3 "$SCRIPT" $PERIODO_ARG
fi

if [ $? -ne 0 ]; then
  echo ""
  echo "❌ Ocorreu um erro. Chama o Samuel."
  read -p "Pressione Enter para fechar..."
  exit 1
fi

# ── PUBLICAR NO SITE? ────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "Publicar no site agora? (S/n): " PUBLICAR
echo ""

if [[ "$PUBLICAR" =~ ^[Nn]$ ]]; then
  echo "OK! As páginas foram geradas mas não publicadas ainda."
  echo "Quando quiser publicar, rode este arquivo novamente."
else
  echo "Publicando..."
  cd "$REPO"
  git add .
  git commit -m "Aprovações — $(date '+%d/%m/%Y')"
  git push
  echo ""
  echo "✅ Site atualizado em https://oiforster.github.io/forster-aprovacoes"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "Pressione Enter para fechar..."
