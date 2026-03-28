#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Forster Filmes — Fluxo Completo de Aprovações
#  Valida → Sobe ao YouTube → Gera páginas → Publica
#  Duplo clique para rodar.
# ─────────────────────────────────────────────────────────────

REPO="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$REPO/scripts"

cd "$REPO" || { echo "❌ Erro ao acessar a pasta do repositório."; exit 1; }

clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ⬇️  SINCRONIZANDO COM A EQUIPE (GitHub)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git fetch origin main 2>/dev/null
LOCAL=$(git rev-parse HEAD 2>/dev/null)
REMOTE=$(git rev-parse origin/main 2>/dev/null)
if [ "$LOCAL" != "$REMOTE" ]; then
  echo "  Atualizando para a versão mais recente..."
  git reset --hard origin/main
  echo "  ✅ Atualizado."
else
  echo "  ✅ Já está na versão mais recente."
fi
echo ""

# ── DEPENDÊNCIAS ─────────────────────────────────────
python3 - <<'DEPEOF'
import importlib, importlib.util, subprocess, sys

PACOTES =[
    ("googleapiclient", "google-api-python-client"),
    ("google_auth_oauthlib", "google-auth-oauthlib"),
    ("google.auth.transport.requests", "google-auth-httplib2"),
]

def modulo_instalado(mod):
    try:
        return importlib.util.find_spec(mod) is not None
    except (ModuleNotFoundError, ValueError):
        return False

faltando =[(mod, pkg) for mod, pkg in PACOTES if not modulo_instalado(mod)]

if faltando:
    print("  Instalando dependências...")
    for mod, pkg in faltando:
        print(f"    → {pkg}")
        resultado = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "--break-system-packages", pkg],
            capture_output=True, text=True
        )
        if resultado.returncode != 0:
            print(f"  ❌ Erro ao instalar {pkg}:")
            print(resultado.stderr.strip())
            sys.exit(1)
    print("  ✅ Dependências instaladas.\n")
DEPEOF

DEP_STATUS=$?
if [ $DEP_STATUS -ne 0 ]; then
  read -p "Pressione Enter para fechar..."
  exit 1
fi

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

# ── QUAL PERÍODO? ────────────────────────────────────
echo "Qual período para aprovação?"
echo ""
echo "   1. Próxima semana (padrão)"
echo "   2. Semana atual"
echo "   3. Período personalizado"
echo "   4. Mês completo"
echo ""
read -p "  Escolha (1/2/3/4) ou Enter para padrão: " PERIODO_OPCAO
echo ""

PERIODO_INICIO=""
PERIODO_FIM=""

# Função auxiliar para normalizar DD/MM/AAAA → YYYY-MM-DD
normalizar_data() {
  local d="$1"
  if [[ "$d" == *"/"* ]]; then
    python3 -c "
p = '$d'.split('/')
print(f'{p[2]}-{int(p[1]):02d}-{int(p[0]):02d}')
"
  else
    echo "$d"
  fi
}

case "$PERIODO_OPCAO" in
  2)
    # Semana atual: segunda-feira desta semana
    SEGUNDA_ATUAL=$(python3 -c "
from datetime import date, timedelta
hoje = date.today()
segunda = hoje - timedelta(days=hoje.weekday())
domingo = segunda + timedelta(days=6)
print(segunda.strftime('%Y-%m-%d'), domingo.strftime('%Y-%m-%d'))
")
    PERIODO_INICIO=$(echo $SEGUNDA_ATUAL | awk '{print $1}')
    PERIODO_FIM=$(echo $SEGUNDA_ATUAL | awk '{print $2}')
    echo "  📅 Semana atual: $PERIODO_INICIO a $PERIODO_FIM"
    echo ""
    ;;
  3)
    read -p "  Data de início (DD/MM/AAAA ou AAAA-MM-DD): " INI_INPUT
    read -p "  Data de fim    (DD/MM/AAAA ou AAAA-MM-DD): " FIM_INPUT
    PERIODO_INICIO=$(normalizar_data "$INI_INPUT")
    PERIODO_FIM=$(normalizar_data "$FIM_INPUT")
    echo "  📅 Período: $PERIODO_INICIO a $PERIODO_FIM"
    echo ""
    ;;
  4)
    # Mês completo
    read -p "  Qual mês? (YYYY-MM, ex: 2026-04) ou Enter para o atual: " MES_COMPLETO_INPUT
    if [ -z "$MES_COMPLETO_INPUT" ]; then
      MES_COMPLETO_INPUT=$(date '+%Y-%m')
    fi
    ANO_MES="$MES_COMPLETO_INPUT"
    PERIODO_INICIO="${ANO_MES}-01"
    # Último dia do mês
    PERIODO_FIM=$(python3 -c "
import calendar
ano, mes = '${ANO_MES}'.split('-')
ultimo = calendar.monthrange(int(ano), int(mes))[1]
print(f'{ano}-{mes}-{ultimo:02d}')
")
    echo "  📅 Mês completo: $PERIODO_INICIO a $PERIODO_FIM"
    echo ""
    ;;
  *)
    echo "  📅 Próxima semana (padrão)"
    echo ""
    ;;
esac

# ── QUAL MÊS? (inferido automaticamente se não informado) ──
# Se o período define datas explícitas, infere o mês da data de início
MES_INPUT=""
if [ -n "$PERIODO_INICIO" ]; then
  MES_INPUT=$(echo "$PERIODO_INICIO" | cut -d'-' -f1-2)
fi

# Se não tem período definido (opção 1 — próxima semana), pergunta o mês
if [ -z "$MES_INPUT" ]; then
  echo "Qual mês? (deixe em branco para o mês atual)"
  read -p "  YYYY-MM (ex: 2026-04) ou Enter: " MES_INPUT
  echo ""
fi

# Monta array de argumentos (trata espaços corretamente)
ARGS=()
if [ -n "$CLIENTE" ]; then
  ARGS+=(--cliente "$CLIENTE")
fi
if [ -n "$MES_INPUT" ]; then
  ARGS+=(--mes "$MES_INPUT")
fi
if [ -n "$PERIODO_INICIO" ] && [ -n "$PERIODO_FIM" ]; then
  ARGS+=(--inicio "$PERIODO_INICIO" --fim "$PERIODO_FIM")
fi

# ════════════════════════════════════════════════════
# ETAPA 1 — VALIDAÇÃO
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 1/4 — Validando arquivos..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 "$SCRIPTS/validar_arquivos.py" "${ARGS[@]}"
VALIDACAO_STATUS=$?
echo ""

if [ $VALIDACAO_STATUS -ne 0 ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  ❌ Foram encontrados erros nos arquivos."
  echo ""
  echo "  Corrija os problemas acima e rode novamente."
  echo "  Os erros ❌ impedem o funcionamento correto"
  echo "  das páginas de aprovação."
  echo ""
  read -p "  Continuar mesmo assim? (s/N): " FORCAR
  echo ""
  if [[ ! "$FORCAR" =~ ^[Ss]$ ]]; then
    echo "  Operação cancelada."
    echo ""
    read -p "Pressione Enter para fechar..."
    exit 1
  fi
  echo "  ⚠️  Continuando com erros."
  echo ""
fi

# ════════════════════════════════════════════════════
# ETAPA 2 — UPLOAD YOUTUBE
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 2/4 — Subindo Reels ao YouTube..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 "$SCRIPTS/subir_reels.py" "${ARGS[@]}"
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

python3 "$SCRIPTS/gerar_aprovacoes.py" "${ARGS[@]}"
GERAR_STATUS=$?
echo ""

if [ $GERAR_STATUS -ne 0 ]; then
  echo "  ❌ Erro ao gerar páginas."
  read -p "Pressione Enter para fechar..."
  exit 1
fi

# ════════════════════════════════════════════════════
# ETAPA 3b — ATUALIZAR BIBLIOTECA DE ENTREGAS
# (gera páginas de download com aprovação liberada)
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 3b — Atualizando biblioteca de entregas..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Monta args para a biblioteca (cliente e mês, sem período)
ARGS_BIB=()
if [ -n "$CLIENTE" ]; then
  ARGS_BIB+=(--cliente "$CLIENTE")
fi
if [ -n "$MES_INPUT" ]; then
  ARGS_BIB+=(--mes "$MES_INPUT")
fi

python3 "$SCRIPTS/gerar_biblioteca.py" "${ARGS_BIB[@]}"
echo ""

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
else
  echo "  Publicando..."
  cd "$REPO"
  git add .
  git commit -m "Aprovações — $(date '+%d/%m/%Y')"
  git push

  if [ $? -eq 0 ]; then
    echo ""
    echo "  ✅ Site atualizado!"
    echo "  👉 https://aprovar.forsterfilmes.com"
  else
    echo ""
    echo "  ❌ Erro ao publicar. Tente manualmente:"
    echo "  cd \"$REPO\" && git push"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📱 MENSAGEM PARA ENVIAR NO WHATSAPP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if [ -f /tmp/forster_whatsapp_msg.txt ]; then
  cat /tmp/forster_whatsapp_msg.txt
  rm /tmp/forster_whatsapp_msg.txt
else
  echo "  (mensagem não encontrada — veja acima na Etapa 3)"
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Pressione Enter para fechar..."
