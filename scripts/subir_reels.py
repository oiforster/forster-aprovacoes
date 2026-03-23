#!/usr/bin/env python3
"""
Forster Filmes — Upload de Reels para YouTube
Lê vídeos de 06_Entregas/YYYY-MM*/Videos/ e faz upload como não-listados.
Salva os IDs em _youtube.md na mesma pasta para o gerador de aprovações usar.

Uso:
  python3 subir_reels.py                     # mês atual, todos os clientes
  python3 subir_reels.py --cliente "Prisma"  # só um cliente
  python3 subir_reels.py --mes 2026-04       # mês específico
"""

import os
import re
import sys
import unicodedata
import argparse
from datetime import date
from pathlib import Path

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("❌  Dependências não instaladas. Rode:")
    print("    pip3 install google-api-python-client google-auth-oauthlib --break-system-packages")
    sys.exit(1)

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

CREDENTIALS_FILE = Path(__file__).parent / 'youtube_credentials.json'
TOKEN_FILE       = Path(__file__).parent / 'youtube_token.json'

CLIENTES_RECORRENTES = [
    "Óticas Casa Marco",
    "Colégio Luterano Redentor",
    "Vanessa Mainardi",
    "Joele Lerípio",
    "Micheline Twigger",
    "Fyber Show Piscinas",
    "Prisma Especialidades",
    "Martina Schneider",
    "Catarata Center",
    "Baviera Tecnologia",
]

# ─── UTILITÁRIOS ──────────────────────────────────────────────────────────────

def slugify(texto):
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().replace(' ', '-')

def encontrar_pasta_agencia():
    base = Path('/Users/samuelforster/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK')
    for entry in base.iterdir():
        if 'Ag' in entry.name:
            return entry
    raise FileNotFoundError("Pasta Agência não encontrada")

# ─── AUTENTICAÇÃO YOUTUBE ──────────────────────────────────────────────────────

def autenticar_youtube():
    """
    Autentica via OAuth 2.0.
    Na primeira vez: abre o browser para autorização e salva o token.
    Nas próximas: usa o token salvo (renova automaticamente se expirado).
    """
    if not CREDENTIALS_FILE.exists():
        print(f"❌  Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}")
        print("    Baixe o JSON do Google Cloud Console e salve em scripts/youtube_credentials.json")
        sys.exit(1)

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

# ─── _youtube.md ──────────────────────────────────────────────────────────────

def ler_youtube_md(pasta_videos):
    """Lê _youtube.md → dict { 'DD-MM': 'VIDEO_ID' }."""
    arquivo = pasta_videos / '_youtube.md'
    if not arquivo.exists():
        return {}
    ids = {}
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if ':' not in linha or linha.startswith('#'):
                continue
            chave, url = linha.split(':', 1)
            chave = chave.strip().lower()
            url   = url.strip()
            m = re.search(r'(?:youtu\.be/|[?&]v=)([a-zA-Z0-9_\-]{11})', url)
            if m:
                ids[chave] = m.group(1)
    return ids

def salvar_youtube_md(pasta_videos, ids_dict):
    """Grava/atualiza _youtube.md."""
    arquivo = pasta_videos / '_youtube.md'
    linhas  = ['# YouTube IDs dos Reels — gerado automaticamente\n']
    for chave in sorted(ids_dict.keys()):
        linhas.append(f"{chave}: https://youtu.be/{ids_dict[chave]}\n")
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.writelines(linhas)

# ─── UPLOAD ───────────────────────────────────────────────────────────────────

def fazer_upload(youtube, video_path, titulo, cliente):
    """Faz upload do vídeo como não-listado e retorna o video ID."""
    body = {
        'snippet': {
            'title': titulo,
            'description': f'Aprovação de conteúdo — {cliente} — Forster Filmes',
            'categoryId': '22',  # People & Blogs
        },
        'status': {
            'privacyStatus': 'unlisted',
            'selfDeclaredMadeForKids': False,
        }
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype='video/*',
        resumable=True,
        chunksize=4 * 1024 * 1024  # 4 MB por chunk
    )

    req      = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"      ⬆️  {int(status.progress() * 100)}%", end='\r')

    print(f"      ✅ Upload concluído                ")
    return response['id']

# ─── PROCESSAMENTO POR CLIENTE ────────────────────────────────────────────────

def processar_cliente(youtube, cliente, ano_mes, agencia_path):
    pasta_cliente = agencia_path / '_Clientes' / 'Clientes Recorrentes' / cliente
    if not pasta_cliente.exists():
        for entry in (agencia_path / '_Clientes' / 'Clientes Recorrentes').iterdir():
            if slugify(entry.name) == slugify(cliente):
                pasta_cliente = entry
                break
    if not pasta_cliente.exists():
        return

    pasta_entregas = pasta_cliente / '06_Entregas'
    if not pasta_entregas.exists():
        return

    # Encontra pasta do mês
    pasta_mes = None
    for entry in pasta_entregas.iterdir():
        if entry.is_dir() and entry.name.startswith(ano_mes):
            pasta_mes = entry
            break
    if not pasta_mes:
        return

    pasta_videos = pasta_mes / 'Videos'
    if not pasta_videos.exists():
        return

    extensoes = {'.mp4', '.mov', '.m4v'}
    videos = sorted([
        f for f in pasta_videos.iterdir()
        if f.suffix.lower() in extensoes and re.match(r'^\d{2}-\d{2}', f.name)
    ])
    if not videos:
        return

    print(f"\n🔷 {cliente}")
    ids = ler_youtube_md(pasta_videos)
    novos = False

    for video in videos:
        prefixo = video.stem[:5]  # DD-MM

        if prefixo in ids:
            print(f"  ✓ {video.name} — já enviado (youtu.be/{ids[prefixo]})")
            continue

        titulo = f"{cliente} — Reel {prefixo[0:2]}/{prefixo[3:5]}"
        print(f"  📤 Enviando {video.name} ...")

        try:
            video_id = fazer_upload(youtube, video, titulo, cliente)
            ids[prefixo] = video_id
            novos = True
            print(f"      🔗 https://youtu.be/{video_id}")
        except Exception as e:
            print(f"      ❌ Erro no upload: {e}")

    if novos:
        salvar_youtube_md(pasta_videos, ids)
        print(f"  💾 _youtube.md atualizado")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Sobe Reels para YouTube como não-listados.')
    parser.add_argument('--cliente', type=str, default=None, help='Nome parcial do cliente')
    parser.add_argument('--mes',     type=str, default=None, help='Mês no formato YYYY-MM')
    args = parser.parse_args()

    ano_mes      = args.mes or date.today().strftime('%Y-%m')
    agencia_path = encontrar_pasta_agencia()

    print(f"📁 Agência: {agencia_path}")
    print(f"📅 Mês: {ano_mes}\n")

    print("🔐 Autenticando com YouTube...")
    youtube = autenticar_youtube()
    print("✅ Autenticado")

    clientes = CLIENTES_RECORRENTES
    if args.cliente:
        clientes = [c for c in clientes if args.cliente.lower() in c.lower()]

    for cliente in clientes:
        processar_cliente(youtube, cliente, ano_mes, agencia_path)

    print("\n✅ Pronto. Rode agora o gerar_aprovacoes.py para gerar as páginas com os Reels embedados.")

if __name__ == '__main__':
    main()
