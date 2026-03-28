#!/usr/bin/env python3
"""
Forster Filmes — Upload de Reels para YouTube
Lê vídeos de 06_Entregas/YYYY-MM*/Videos/ e faz upload como não-listados.
Sobe a capa (se existir) como thumbnail customizada.
Salva os IDs em _youtube.md na mesma pasta.

Nomenclatura esperada:
    Vídeo: REEL 01 – Nome do Vídeo.mov   (ou .mp4 / .m4v)
    Capa:  REEL 01 – Nome do Vídeo (capa).jpg

Entrada no .md da Silvana:
    **Vídeo:** REEL 01 – Nome do Vídeo

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
    print("    pip3 install --user google-api-python-client google-auth-oauthlib")
    sys.exit(1)

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',          # necessário para thumbnail
]

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
    home = Path.home()
    # Synology Drive — fonte de verdade ativa
    synology = home / 'Library/CloudStorage/SynologyDrive-Agencia'
    if synology.exists():
        return synology
    # Fallback: Google Drive (legado)
    gdrive = home / 'Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK'
    if gdrive.exists():
        for entry in gdrive.iterdir():
            if 'Ag' in entry.name:
                return entry
    raise FileNotFoundError("Pasta Agência não encontrada")

# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────

def autenticar_youtube():
    if not CREDENTIALS_FILE.exists():
        print(f"❌  Credenciais não encontradas: {CREDENTIALS_FILE}")
        sys.exit(1)

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Remove token antigo (pode ter escopos insuficientes)
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

# ─── _youtube.md ──────────────────────────────────────────────────────────────

def ler_youtube_md(pasta_videos):
    """Lê _youtube.md → dict { 'REEL 01 – Nome': 'VIDEO_ID' }."""
    arquivo = pasta_videos / '_youtube.md'
    if not arquivo.exists():
        return {}
    ids = {}
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#'):
                continue
            idx = linha.find(': http')
            if idx == -1:
                continue
            chave = linha[:idx].strip()
            url   = linha[idx+2:].strip()
            m = re.search(r'(?:youtu\.be/|[?&]v=)([a-zA-Z0-9_\-]{11})', url)
            if m:
                ids[chave] = m.group(1)
    return ids

def salvar_youtube_md(pasta_videos, ids_dict):
    arquivo = pasta_videos / '_youtube.md'
    linhas  = ['# YouTube IDs dos Reels — gerado automaticamente\n']
    for chave in sorted(ids_dict.keys()):
        linhas.append(f"{chave}: https://youtu.be/{ids_dict[chave]}\n")
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.writelines(linhas)

# ─── UPLOAD ───────────────────────────────────────────────────────────────────

def fazer_upload(youtube, video_path, reel_nome, cliente):
    """Faz upload do vídeo como não-listado. Retorna video ID."""
    body = {
        'snippet': {
            'title': f"{reel_nome} — {cliente}",
            'description': f'Aprovação de conteúdo — {cliente} — Forster Filmes',
            'categoryId': '22',
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
        chunksize=4 * 1024 * 1024
    )

    req = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"      ⬆️  {int(status.progress() * 100)}%", end='\r')

    print(f"      ✅ Upload concluído                ")
    return response['id']

def subir_thumbnail(youtube, video_id, capa_path):
    """Sobe a imagem de capa como thumbnail do vídeo."""
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(capa_path), mimetype='image/jpeg')
        ).execute()
        print(f"      🖼️  Capa enviada")
    except Exception as e:
        print(f"      ⚠️  Capa não enviada: {e}")

# ─── PROCESSAMENTO ────────────────────────────────────────────────────────────

def encontrar_pasta_cliente(cliente, agencia_path):
    """Busca a pasta do cliente em Recorrentes e depois em Pontuais."""
    for subfolder in ['Clientes Recorrentes', 'Clientes Pontuais']:
        pasta = agencia_path / '_Clientes' / subfolder / cliente
        if pasta.exists():
            return pasta
        base = agencia_path / '_Clientes' / subfolder
        if base.exists():
            for entry in base.iterdir():
                if slugify(entry.name) == slugify(cliente):
                    return entry
    return None

def _encontrar_pasta_videos(pasta_cliente, ano_mes):
    """Encontra a pasta com vídeos REEL. Suporta recorrentes e pontuais."""
    extensoes = {'.mov', '.mp4', '.m4v'}

    def _tem_reels(pasta):
        try:
            return any(
                f.suffix.lower() in extensoes
                and '(capa)' not in f.name.lower()
                and re.match(r'^REEL\s+\d+', f.name, re.IGNORECASE)
                for f in pasta.iterdir() if f.is_file()
            )
        except (PermissionError, OSError):
            return False

    # 1) Recorrentes: 06_Entregas/YYYY-MM*/Videos/
    pasta_entregas = pasta_cliente / '06_Entregas'
    if pasta_entregas.exists():
        for entry in sorted(pasta_entregas.iterdir()):
            if entry.is_dir() and entry.name.startswith(ano_mes):
                videos = entry / 'Videos'
                if videos.exists() and _tem_reels(videos):
                    return videos
                if _tem_reels(entry):
                    return entry

    # 2) Pontuais: YYYY-MM* na raiz do cliente, com subpastas flexíveis
    for entry in sorted(pasta_cliente.iterdir()):
        if entry.is_dir() and entry.name.startswith(ano_mes):
            for sub in ['Videos', '01 - Reels', 'Reels']:
                pasta = entry / sub
                if pasta.exists() and _tem_reels(pasta):
                    return pasta
            if _tem_reels(entry):
                return entry
            for sub in entry.iterdir():
                if sub.is_dir() and _tem_reels(sub):
                    return sub

    return None

def processar_cliente(youtube, cliente, ano_mes, agencia_path):
    pasta_cliente = encontrar_pasta_cliente(cliente, agencia_path)
    if not pasta_cliente:
        return

    pasta_videos = _encontrar_pasta_videos(pasta_cliente, ano_mes)
    if not pasta_videos:
        return

    # Encontra vídeos com padrão "REEL NN – Nome.mov"
    extensoes_video = {'.mov', '.mp4', '.m4v'}
    videos = sorted([
        f for f in pasta_videos.iterdir()
        if f.suffix.lower() in extensoes_video
        and '(capa)' not in f.name.lower()
        and re.match(r'^REEL\s+\d+', f.name, re.IGNORECASE)
    ])

    if not videos:
        return

    print(f"\n🔷 {cliente}")
    ids  = ler_youtube_md(pasta_videos)
    novos = False

    for video in videos:
        reel_nome = video.stem  # "REEL 01 – Nome do Vídeo"

        if reel_nome in ids:
            print(f"  ✓ {video.name} — já enviado (youtu.be/{ids[reel_nome]})")
            continue

        print(f"  📤 Enviando {video.name} ...")
        try:
            video_id = fazer_upload(youtube, video, reel_nome, cliente)
            ids[reel_nome] = video_id
            novos = True
            print(f"      🔗 https://youtu.be/{video_id}")

            # Sobe capa se existir: "REEL 01 – Nome do Vídeo (capa).jpg"
            capa = pasta_videos / f"{reel_nome} (capa).jpg"
            if not capa.exists():
                # tenta .png
                capa = pasta_videos / f"{reel_nome} (capa).png"
            if capa.exists():
                subir_thumbnail(youtube, video_id, capa)
            else:
                print(f"      ℹ️  Sem capa — YouTube vai gerar thumbnail automática")

        except Exception as e:
            print(f"      ❌ Erro: {e}")

    if novos:
        salvar_youtube_md(pasta_videos, ids)
        print(f"  💾 _youtube.md atualizado")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Sobe Reels para YouTube como não-listados.')
    parser.add_argument('--cliente', type=str, default=None)
    parser.add_argument('--mes',     type=str, default=None)
    parser.add_argument('--inicio',  type=str, default=None)
    parser.add_argument('--fim',     type=str, default=None)
    args = parser.parse_args()

    ano_mes      = args.mes or date.today().strftime('%Y-%m')
    agencia_path = encontrar_pasta_agencia()

    print(f"📁 Agência: {agencia_path}")
    print(f"📅 Mês: {ano_mes}\n")

    print("🔐 Autenticando com YouTube...")
    youtube = autenticar_youtube()
    print("✅ Autenticado\n")

    clientes = CLIENTES_RECORRENTES
    if args.cliente:
        filtrados = [c for c in clientes if args.cliente.lower() in c.lower()]
        if filtrados:
            clientes = filtrados
        else:
            # Cliente não está na lista de recorrentes — tenta como pontual
            clientes = [args.cliente]

    for cliente in clientes:
        processar_cliente(youtube, cliente, ano_mes, agencia_path)

    print("\n✅ Pronto. Rode agora o gerar_aprovacoes.py para gerar as páginas com os Reels embedados.")

if __name__ == '__main__':
    main()
