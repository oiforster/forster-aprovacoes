#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Forster Filmes — Entrega de Vídeos para Aprovação
#  YouTube → Gera página (Google Drive) → Publica
#  Duplo clique para rodar.
# ─────────────────────────────────────────────────────────────

# Pega a pasta raiz de onde este arquivo .command está salvo
REPO="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$REPO/scripts"

# Entra na pasta do repositório antes de fazer qualquer coisa
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
        resultado = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", pkg],
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
echo "   FORSTER FILMES — Entrega de Vídeos"
echo "   YouTube → Gerar página (Google Drive) → Publicar"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── QUAL CLIENTE? ────────────────────────────────────

# Lê clientes pontuais da pasta (Synology primeiro, GDrive como fallback)
PONTUAIS_LISTA=$(python3 - <<'PYEOF'
import sys
from pathlib import Path

home = Path.home()
cloud = home / 'Library' / 'CloudStorage'

# Synology primeiro, GDrive como fallback
agencia = None
synology = cloud / 'SynologyDrive-Agencia'
if synology.exists():
    agencia = synology
else:
    for gdrive in cloud.iterdir():
        if 'GoogleDrive' in gdrive.name:
            cowork = gdrive / 'Meu Drive' / 'Forster Filmes' / 'CLAUDE_COWORK'
            if cowork.exists():
                for entry in cowork.iterdir():
                    if 'Ag' in entry.name:
                        agencia = entry
                        break
            break

if not agencia:
    sys.exit(0)

pasta_pontuais = agencia / '_Clientes' / 'Clientes Pontuais'
if not pasta_pontuais.exists():
    sys.exit(0)

clientes = sorted([
    e.name for e in pasta_pontuais.iterdir()
    if e.is_dir() and not e.name.startswith('.')
])
for c in clientes:
    print(c)
PYEOF
)

echo "Para qual cliente?"
echo ""
echo "   Recorrentes"
echo "   1.  Óticas Casa Marco"
echo "   2.  Colégio Luterano Redentor"
echo "   3.  Vanessa Mainardi"
echo "   4.  Joele Lerípio"
echo "   5.  Micheline Twigger"
echo "   6.  Fyber Show Piscinas"
echo "   7.  Prisma Especialidades"
echo "   8.  Martina Schneider"
echo "   9.  Catarata Center"
echo "  10.  Baviera Tecnologia"
echo ""
echo "   Pontuais"

# Exibe pontuais numerados a partir de 11
PONTUAL_NUM=11
declare -a PONTUAL_NOMES
if [ -n "$PONTUAIS_LISTA" ]; then
  while IFS= read -r nome; do
    [ -z "$nome" ] && continue
    printf "  %2d.  %s\n" "$PONTUAL_NUM" "$nome"
    PONTUAL_NOMES+=("$nome")
    ((PONTUAL_NUM++))
  done <<< "$PONTUAIS_LISTA"
else
  echo "  (nenhum cliente pontual encontrado)"
fi

echo ""
read -p "  Número: " CLIENTE_INPUT
echo ""

PONTUAL=false

case "$CLIENTE_INPUT" in
  1)  CLIENTE="Óticas Casa Marco" ;;
  2)  CLIENTE="Colégio Luterano Redentor" ;;
  3)  CLIENTE="Vanessa Mainardi" ;;
  4)  CLIENTE="Joele Lerípio" ;;
  5)  CLIENTE="Micheline Twigger" ;;
  6)  CLIENTE="Fyber Show Piscinas" ;;
  7)  CLIENTE="Prisma Especialidades" ;;
  8)  CLIENTE="Martina Schneider" ;;
  9)  CLIENTE="Catarata Center" ;;
  10) CLIENTE="Baviera Tecnologia" ;;
  *)
    # Verifica se é um número dentro da faixa de pontuais
    if [[ "$CLIENTE_INPUT" =~ ^[0-9]+$ ]] && [ "$CLIENTE_INPUT" -ge 11 ]; then
      IDX=$(( CLIENTE_INPUT - 11 ))
      if [ "$IDX" -lt "${#PONTUAL_NOMES[@]}" ]; then
        CLIENTE="${PONTUAL_NOMES[$IDX]}"
        PONTUAL=true
      else
        echo "  ❌ Número inválido."
        read -p "Pressione Enter para fechar..."
        exit 1
      fi
    else
      echo "  ❌ Opção inválida."
      read -p "Pressione Enter para fechar..."
      exit 1
    fi
    ;;
esac

echo "  Cliente: $CLIENTE"
echo ""

# ── QUAL MÊS? ─────────────────────────────────────────
echo "Qual mês? (deixe em branco para o mês atual)"
read -p "  YYYY-MM (ex: 2026-04) ou Enter: " MES_INPUT
echo ""

# ── MONTA ARGUMENTOS ─────────────────────────────────
ARGS_BASE=(--cliente "$CLIENTE")
if [ -n "$MES_INPUT" ]; then
  ARGS_BASE+=(--mes "$MES_INPUT")
fi

ARGS_VIDEOS=("${ARGS_BASE[@]}")
if [ "$PONTUAL" = true ]; then
  ARGS_VIDEOS+=(--pontual)
fi

# ════════════════════════════════════════════════════
# ETAPA 1 — UPLOAD YOUTUBE
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 1/3 — Subindo vídeos ao YouTube..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 "$SCRIPTS/subir_reels.py" "${ARGS_BASE[@]}"
YOUTUBE_STATUS=$?
echo ""

if [ $YOUTUBE_STATUS -ne 0 ]; then
  echo "  ❌ Erro no upload ao YouTube."
  echo ""
  read -p "  Continuar gerando a página mesmo assim? (s/N): " CONTINUAR_YT
  echo ""
  if [[ ! "$CONTINUAR_YT" =~ ^[Ss]$ ]]; then
    echo "  Operação cancelada."
    read -p "Pressione Enter para fechar..."
    exit 1
  fi
fi

# ════════════════════════════════════════════════════
# ETAPA 2 — GERAR PÁGINA DE ENTREGA
# (busca File IDs do Google Drive via xattr automaticamente)
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 2/3 — Gerando página de entrega..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 "$SCRIPTS/gerar_entrega_videos.py" "${ARGS_VIDEOS[@]}"
GERAR_STATUS=$?
echo ""

if [ $GERAR_STATUS -ne 0 ]; then
  echo "  ❌ Erro ao gerar página."
  read -p "Pressione Enter para fechar..."
  exit 1
fi

# ════════════════════════════════════════════════════
# ETAPA 3 — PUBLICAR
# ════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ETAPA 3/3 — Publicar no site?"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "  Publicar agora em oiforster.github.io? (S/n): " PUBLICAR
echo ""

if [[ "$PUBLICAR" =~ ^[Nn]$ ]]; then
  echo "  Página gerada mas não publicada."
else
  echo "  Publicando..."
  cd "$REPO"
  git add .
  git commit -m "Entrega de vídeos — $CLIENTE — $(date '+%d/%m/%Y')"
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
echo "  Pronto! Copie o link e envie no WhatsApp do cliente."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Pressione Enter para fechar..."