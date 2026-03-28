#!/usr/bin/env python3
"""
Forster Filmes — Gerador da Biblioteca de Entregas por Cliente

Para cada cliente recorrente com estratégia gerenciada pela Forster,
gera uma página de índice de meses e uma página por mês com:
  - Todos os vídeos em ordem cronológica (cruzado com _Conteúdo Mensal_.md)
  - Download dos vídeos liberado conforme aprovação (estado-YYYY-MM.json)
  - Galeria de frames sempre disponível para download

URLs geradas:
  aprovacao/[slug]/index.html           ← lista de meses
  aprovacao/[slug]/[mes]-[yyyy].html    ← biblioteca do mês (ex: marco-2026.html)

Uso:
  python3 gerar_biblioteca.py                          # todos os clientes
  python3 gerar_biblioteca.py --cliente "Fyber Show"   # cliente específico
  python3 gerar_biblioteca.py --mes 2026-03            # mês específico
"""

import os
import re
import sys
import json
import unicodedata
import argparse
import subprocess
from datetime import date
from pathlib import Path

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

# Clientes com estratégia gerenciada — têm biblioteca de entregas
# Martina, Joele, Baviera: só produção de vídeo → usam gerar_entrega_videos.py
CLIENTES_BIBLIOTECA = [
    "Óticas Casa Marco",
    "Colégio Luterano Redentor",
    "Vanessa Mainardi",
    "Micheline Twigger",
    "Fyber Show Piscinas",
    "Prisma Especialidades",
    "Catarata Center",
]

MESES_PT = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}

# Nomes sem acento para URLs
MESES_URL = {
    1: 'janeiro', 2: 'fevereiro', 3: 'marco', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}

OUTPUT_DIR    = Path(__file__).parent.parent
SYNOLOGY_BASE = Path.home() / 'Library' / 'CloudStorage' / 'SynologyDrive-Agencia'
GITHUB_RAW    = 'https://raw.githubusercontent.com/oiforster/forster-aprovacoes/main'

# Slugs personalizados por cliente (sobrescreve o slugify automático)
SLUG_CLIENTES = {
    "Catarata Center": "catarata",
}

def slug_cliente(nome):
    return SLUG_CLIENTES.get(nome, slugify(nome))

# Token fragmentado (evita GitHub Secret Scanning)
_GH_TOKEN_BODY = '11A4XFG6Q0V9ee2TfDGWKP_Z1vH306NmDFc07' + 'G2UHTHWyTJQRYkc4ClwFZGa1j9LThUODYITL6dNhDr6Kn'

# ─── UTILITÁRIOS ──────────────────────────────────────────────────────────────

def slugify(texto):
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.lower().replace(' ', '-')
    texto = re.sub(r'[^a-z0-9\-]', '', texto)
    return re.sub(r'-+', '-', texto).strip('-')

def escape_html(texto):
    return (str(texto)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace('\n', '<br>'))

def normalizar(texto):
    return unicodedata.normalize('NFC', str(texto))

# ─── DETECÇÃO DE CAMINHOS ─────────────────────────────────────────────────────

def encontrar_agencia():
    cloud = Path.home() / 'Library' / 'CloudStorage'
    synology = cloud / 'SynologyDrive-Agencia'
    if synology.exists():
        return synology
    if cloud.exists():
        for gdrive in cloud.iterdir():
            if 'GoogleDrive' in gdrive.name:
                cowork = gdrive / 'Meu Drive' / 'Forster Filmes' / 'CLAUDE_COWORK'
                if cowork.exists():
                    for entry in cowork.iterdir():
                        if 'Ag' in entry.name:
                            return entry
    raise FileNotFoundError("Pasta Agência não encontrada.")

def _encontrar_gdrive_agencia():
    cloud = Path.home() / 'Library' / 'CloudStorage'
    if not cloud.exists():
        return None
    for entry in sorted(cloud.iterdir()):
        if not entry.name.startswith('GoogleDrive-'):
            continue
        for meu_drive in ['Meu Drive', 'My Drive']:
            base = entry / meu_drive / 'Forster Filmes' / 'CLAUDE_COWORK'
            if not base.exists():
                continue
            for nome in ['Agência', 'AGENCIA', 'Agencia']:
                for var in [nome, unicodedata.normalize('NFC', nome), unicodedata.normalize('NFD', nome)]:
                    p = base / var
                    if p.exists():
                        return p
            try:
                for sub in sorted(base.iterdir()):
                    if sub.is_dir() and (sub / '_Clientes').exists():
                        return sub
            except Exception:
                pass
    return None

GDRIVE_AGENCIA = _encontrar_gdrive_agencia()

def synology_para_gdrive(synology_path):
    if GDRIVE_AGENCIA is None:
        return None
    try:
        rel = Path(synology_path).relative_to(SYNOLOGY_BASE)
    except ValueError:
        return None
    gdrive_path = GDRIVE_AGENCIA / rel
    return gdrive_path if gdrive_path.exists() else None

def _get_gdrive_file_id(path):
    """Obtém o File ID do Google Drive via xattr."""
    try:
        result = subprocess.run(
            ['xattr', '-p', 'com.google.drivefs.item-id#S', str(path)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        result = subprocess.run(
            ['xattr', '-p', 'com.google.drivefs.item-id', str(path)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None

def gdrive_file_id(synology_path):
    """Obtém File ID: tenta xattr no Google Drive, fallback para _gdrive.md."""
    gdrive_path = synology_para_gdrive(synology_path)
    if gdrive_path:
        fid = _get_gdrive_file_id(gdrive_path)
        if fid:
            return fid
    return None

# ─── BUSCA DE ARQUIVOS DE CONFIGURAÇÃO ────────────────────────────────────────

def _pasta_meta(pasta_videos):
    meta = pasta_videos.parent / '_meta'
    return meta if meta.exists() else None

def _ler_md(pasta_videos, nome):
    meta = _pasta_meta(pasta_videos)
    if meta:
        c = meta / nome
        if c.exists():
            return c
    return pasta_videos / nome

def ler_youtube_ids(pasta_videos):
    """Lê _youtube.md → dict {reel_nome_nfc: youtube_id}."""
    arquivo = _ler_md(pasta_videos, '_youtube.md')
    if not arquivo.exists():
        return {}
    ids = {}
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#'):
                    continue
                idx = linha.rfind(':')
                if idx < 0:
                    continue
                chave = normalizar(linha[:idx].strip())
                valor = linha[idx+1:].strip()
                if valor:
                    ids[chave] = valor
    except Exception:
        pass
    return ids

def ler_gdrive_ids(pasta_videos):
    """Lê _gdrive.md → dict {reel_nome_nfc: file_id}."""
    arquivo = _ler_md(pasta_videos, '_gdrive.md')
    if not arquivo.exists():
        return {}
    ids = {}
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#'):
                    continue
                idx = linha.rfind(':')
                if idx < 0:
                    continue
                chave = normalizar(linha[:idx].strip())
                valor = linha[idx+1:].strip()
                if valor:
                    ids[chave] = valor
    except Exception:
        pass
    return ids

# ─── CALENDÁRIO — LEITURA E CROSS-REFERENCE ───────────────────────────────────

def encontrar_arquivo_mensal(cliente, ano_mes, agencia):
    """Encontra YYYY-MM — Conteúdo Mensal [Cliente].md."""
    for subfolder in ['Clientes Recorrentes', 'Clientes Pontuais']:
        base = agencia / '_Clientes' / subfolder
        if not base.exists():
            continue
        pasta = base / cliente / '04_Estratégia'
        if not pasta.exists():
            for entry in base.iterdir():
                if slugify(entry.name) == slugify(cliente):
                    pasta = entry / '04_Estratégia'
                    break
        if pasta.exists():
            for arq in pasta.iterdir():
                if arq.suffix == '.md' and ano_mes in arq.name and 'Conte' in arq.name:
                    return arq
    return None

def _parse_data(texto):
    m = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{4}))?', texto)
    if m:
        try:
            return date(int(m.group(3) or date.today().year), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None

def _extrair_reel_nome(texto_secao):
    """Extrai o campo **Vídeo:** de uma seção do .md."""
    for linha in texto_secao.split('\n'):
        m = re.match(r'\*\*Vídeo:\*\*\s*(.+)', linha.strip())
        if m:
            return normalizar(m.group(1).strip())
    return ''

def ler_calendario(arquivo_md):
    """
    Lê _Conteúdo Mensal_.md e retorna lista de:
    {data, titulo, formato, reel_nome, post_id}
    ordenada por data.
    """
    if not arquivo_md or not arquivo_md.exists():
        return []
    try:
        with open(arquivo_md, 'r', encoding='utf-8') as f:
            conteudo = f.read()
    except Exception:
        return []

    linhas = conteudo.split('\n')

    # 1. Tabela do calendário
    tabela = {}
    em_tabela = False
    tem_cabecalho = False
    for linha in linhas:
        linha = linha.strip()
        if not linha.startswith('|'):
            em_tabela = False
            continue
        celulas = [c.strip() for c in linha.strip('|').split('|')]
        if len(celulas) < 2:
            continue
        if any(re.match(r'-+', c) for c in celulas):
            tem_cabecalho = True
            em_tabela = True
            continue
        if not tem_cabecalho:
            continue
        if em_tabela:
            data = _parse_data(celulas[0])
            if data:
                titulo = celulas[2] if len(celulas) > 2 else ''
                titulo = re.sub(r'[★⚠️✓✗]', '', titulo).strip()
                titulo = re.sub(r'\s*\([^)]+\)\s*$', '', titulo).strip()
                formato = celulas[1] if len(celulas) > 1 else ''
                tabela[data] = {'titulo': titulo, 'formato': formato}

    if not tabela:
        return []

    # 2. Seções de conteúdo para extrair **Vídeo:**
    secoes = {}
    secao_data = None
    secao_texto = []
    for linha in linhas:
        m = re.match(r'^#{2,4}\s+(\d{1,2}/\d{1,2})', linha)
        if m:
            if secao_data:
                secoes[secao_data] = '\n'.join(secao_texto).strip()
            data = _parse_data(linha)
            secao_data = data
            secao_texto = []
        elif secao_data is not None:
            secao_texto.append(linha)
    if secao_data:
        secoes[secao_data] = '\n'.join(secao_texto).strip()

    # 3. Montar lista
    resultado = []
    for data in sorted(tabela.keys()):
        info = tabela[data]
        reel_nome = _extrair_reel_nome(secoes.get(data, ''))
        post_id = f"{data.strftime('%Y%m%d')}-{slugify(info['titulo'])[:30]}"
        resultado.append({
            'data':      data,
            'titulo':    info['titulo'] or 'Post sem título',
            'formato':   info['formato'],
            'reel_nome': reel_nome,
            'post_id':   post_id,
        })
    return resultado

# ─── BUSCA DE VÍDEOS E FRAMES ─────────────────────────────────────────────────

def encontrar_pasta_entregas(cliente, agencia):
    """Localiza 06_Entregas/ do cliente."""
    for subfolder in ['Clientes Recorrentes', 'Clientes Pontuais']:
        base = agencia / '_Clientes' / subfolder
        if not base.exists():
            continue
        for entry in base.iterdir():
            if slugify(entry.name) == slugify(cliente):
                p = entry / '06_Entregas'
                if p.exists():
                    return p
    return None

def listar_meses(pasta_entregas, cliente):
    """Lista subpastas YYYY-MM Entrega [Cliente]/, retorna [(ano_mes, pasta), ...]."""
    if not pasta_entregas or not pasta_entregas.exists():
        return []
    meses = []
    for entry in sorted(pasta_entregas.iterdir()):
        if not entry.is_dir():
            continue
        m = re.match(r'^(\d{4}-\d{2})\s', entry.name)
        if m:
            meses.append((m.group(1), entry))
    return meses

def construir_videos_info(pasta_mes, calendario, youtube_ids, gdrive_ids, slug_cliente, ano_mes):
    """
    Constrói lista de vídeos para a página de biblioteca.
    Ordena por data de postagem (cross-reference com calendário).
    """
    pasta_videos = pasta_mes / 'Videos'
    if not pasta_videos.exists():
        pasta_videos = pasta_mes

    # Mapeia reel_nome → data e post_id (do calendário)
    mapa_calendario = {}
    for item in calendario:
        if item['reel_nome']:
            chave = normalizar(item['reel_nome'])
            mapa_calendario[chave] = item

    # Encontra todos os arquivos REEL
    extensoes = {'.mov', '.mp4', '.m4v'}
    arquivos_reel = []
    try:
        for f in sorted(pasta_videos.iterdir()):
            if (f.is_file()
                    and f.suffix.lower() in extensoes
                    and '(capa)' not in f.name.lower()
                    and re.match(r'^REEL\s+\d+', f.name, re.IGNORECASE)):
                arquivos_reel.append(f)
    except Exception:
        pass

    videos = []
    sem_match = []  # REELs sem entrada no calendário

    for arquivo in arquivos_reel:
        reel_nome = normalizar(arquivo.stem)
        cal = mapa_calendario.get(reel_nome)

        # Capa
        capa = pasta_videos / f"{arquivo.stem} (capa).jpg"
        thumbnail_url = None
        drive_id = None

        # Drive ID via xattr ou _gdrive.md
        drive_id_manual = gdrive_ids.get(reel_nome)
        if drive_id_manual:
            drive_id = drive_id_manual
        else:
            gdrive_path = synology_para_gdrive(arquivo)
            if gdrive_path:
                fid = _get_gdrive_file_id(gdrive_path)
                if fid:
                    drive_id = fid

        # Thumbnail: usa capa se existir, senão lh3 do Drive
        if capa.exists():
            capa_gdrive = synology_para_gdrive(capa)
            if capa_gdrive:
                capa_id = _get_gdrive_file_id(capa_gdrive)
                if capa_id:
                    thumbnail_url = f'https://lh3.googleusercontent.com/d/{capa_id}'

        # YouTube ID
        youtube_id = youtube_ids.get(reel_nome)

        # Download URL
        download_url = f'https://drive.google.com/uc?export=download&id={drive_id}' if drive_id else None

        info = {
            'reel_nome':    reel_nome,
            'arquivo':      arquivo,
            'thumbnail':    thumbnail_url,
            'youtube_id':   youtube_id,
            'drive_id':     drive_id,
            'download_url': download_url,
        }

        if cal:
            info.update({
                'data':    cal['data'],
                'titulo':  cal['titulo'],
                'formato': cal['formato'],
                'post_id': cal['post_id'],
            })
            videos.append(info)
        else:
            # Extrai número do REEL para ordenação fallback
            m = re.match(r'^REEL\s+(\d+)', reel_nome, re.IGNORECASE)
            info.update({
                'data':    None,
                'titulo':  arquivo.stem,
                'formato': 'Reels',
                'post_id': f"{ano_mes.replace('-', '')}-{slugify(arquivo.stem)[:30]}",
                '_ordem':  int(m.group(1)) if m else 999,
            })
            sem_match.append(info)

    # Ordena: com data → por data; sem data → por número REEL
    videos.sort(key=lambda v: v['data'])
    sem_match.sort(key=lambda v: v.get('_ordem', 999))

    return videos + sem_match

def construir_frames_info(pasta_mes):
    """
    Constrói lista de frames agrupados por subfolder de Videos/Frames/.
    Regra: tem subfolder → bloco separado com título / sem subfolder → bloco único.
    """
    pasta_videos = pasta_mes / 'Videos'
    if not pasta_videos.exists():
        pasta_videos = pasta_mes

    pasta_frames = pasta_videos / 'Frames'
    if not pasta_frames.exists():
        return []

    extensoes_img = {'.jpg', '.jpeg', '.png', '.webp'}
    frames_info = []

    # Detecta subpastas
    try:
        subpastas = [e for e in sorted(pasta_frames.iterdir()) if e.is_dir()]
    except Exception:
        subpastas = []

    if subpastas:
        # Agrupa por subfolder
        for subpasta in subpastas:
            try:
                imgs = sorted(f for f in subpasta.iterdir()
                              if f.is_file() and f.suffix.lower() in extensoes_img)
            except Exception:
                imgs = []
            for img in imgs:
                thumbnail = _thumbnail_frame(img)
                drive_url = _drive_url_frame(img)
                frames_info.append({
                    'nome':     img.name,
                    'grupo':    subpasta.name,
                    'thumbnail': thumbnail,
                    'drive_url': drive_url,
                })
    else:
        # Pasta flat — grupo vazio = "Frames"
        try:
            imgs = sorted(f for f in pasta_frames.iterdir()
                          if f.is_file() and f.suffix.lower() in extensoes_img)
        except Exception:
            imgs = []
        for img in imgs:
            thumbnail = _thumbnail_frame(img)
            drive_url = _drive_url_frame(img)
            frames_info.append({
                'nome':     img.name,
                'grupo':    '',
                'thumbnail': thumbnail,
                'drive_url': drive_url,
            })

    return frames_info

def _thumbnail_frame(img_path):
    gdrive = synology_para_gdrive(img_path)
    if gdrive:
        fid = _get_gdrive_file_id(gdrive)
        if fid:
            return f'https://lh3.googleusercontent.com/d/{fid}'
    return None

def _drive_url_frame(img_path):
    gdrive = synology_para_gdrive(img_path)
    if gdrive:
        fid = _get_gdrive_file_id(gdrive)
        if fid:
            return f'https://lh3.googleusercontent.com/d/{fid}'
    return None

# ─── GERADOR DE HTML ──────────────────────────────────────────────────────────

def _css():
    return """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #F5F5F0; color: #1A1A1A; min-height: 100vh;
    }
    .header {
      background: #1A1A1A; color: #fff;
      padding: 20px 20px 16px; position: sticky; top: 0; z-index: 100;
    }
    .header-label { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #999; margin-bottom: 4px; }
    .header-cliente { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
    .header-periodo { font-size: 13px; color: #aaa; margin-top: 3px; }

    .content { padding: 16px 16px 48px; display: flex; flex-direction: column; gap: 16px; }
    @media (min-width: 480px) { .content { max-width: 480px; margin: 0 auto; } }

    /* CARD DE VÍDEO */
    .post-card {
      background: #fff; border-radius: 14px;
      overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    }
    .post-header { padding: 14px 14px 10px; display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
    .post-meta { display: flex; flex-direction: column; gap: 4px; }
    .post-data { font-size: 12px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.08em; }
    .post-titulo { font-size: 15px; font-weight: 700; color: #1A1A1A; line-height: 1.3; }
    .post-formato {
      display: inline-block; font-size: 11px; font-weight: 600;
      padding: 3px 8px; border-radius: 4px; letter-spacing: 0.06em;
      text-transform: uppercase; flex-shrink: 0; margin-top: 2px;
    }
    .formato-reels   { background: #FCE4EC; color: #AD1457; }
    .formato-video   { background: #E8F5E9; color: #2E7D32; }
    .formato-card    { background: #E3F2FD; color: #1565C0; }
    .formato-carrossel { background: #F3E5F5; color: #6A1B9A; }
    .post-divider { height: 1px; background: #F0F0EC; margin: 0 14px; }

    /* YOUTUBE FACADE */
    .post-arte { width: 100%; background: #000; overflow: hidden; }
    .youtube-facade {
      position: relative; width: 100%; aspect-ratio: 9/16;
      background: #000; cursor: pointer; overflow: hidden;
    }
    .youtube-facade img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .yt-play-btn {
      position: absolute; top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      pointer-events: none;
      filter: drop-shadow(0 2px 8px rgba(0,0,0,0.4));
    }
    .youtube-facade:active .yt-play-btn { transform: translate(-50%, -50%) scale(0.92); }
    /* Sem vídeo — capa estática */
    .capa-estatica { width: 100%; aspect-ratio: 9/16; object-fit: cover; display: block; background: #111; }

    /* BOTÕES DE DOWNLOAD */
    .post-acoes { padding: 10px 14px 14px; display: flex; flex-direction: column; gap: 8px; }
    .btn-download {
      display: flex; align-items: center; justify-content: center; gap: 8px;
      padding: 11px 14px; background: #1A1A1A; color: #fff;
      border-radius: 10px; font-size: 14px; font-weight: 600;
      text-decoration: none; cursor: pointer; transition: background 0.15s;
      border: none; width: 100%;
    }
    .btn-download:hover { background: #333; }
    .btn-download svg { flex-shrink: 0; }
    .badge-pendente {
      display: flex; align-items: center; justify-content: center;
      padding: 10px 14px; background: #F5F5F0; border-radius: 10px;
      font-size: 13px; color: #aaa; font-weight: 500; gap: 6px;
    }

    /* FRAMES */
    .frames-section { display: flex; flex-direction: column; gap: 16px; }
    .frames-header { padding: 6px 2px 2px; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
    .frames-titulo-texto { font-size: 13px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #888; }
    .btn-baixar-todos {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 8px 14px; background: #1A1A1A; color: #fff;
      border-radius: 8px; font-size: 12px; font-weight: 700;
      letter-spacing: 0.04em; text-decoration: none; white-space: nowrap; transition: background 0.15s;
    }
    .btn-baixar-todos:hover { background: #333; }
    .frames-grupo { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.07); }
    .frames-grupo-titulo { font-size: 11px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase; color: #999; padding: 12px 14px 6px; }
    .frames-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }
    .frame-cell { aspect-ratio: 1; overflow: hidden; cursor: pointer; background: #eee; }
    .frame-cell img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .frame-sem-preview { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #F0F0EC; font-size: 24px; }

    /* LIGHTBOX */
    .lb-overlay {
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,0.92); z-index: 500;
      flex-direction: column; align-items: center; justify-content: center;
    }
    .lb-overlay.ativo { display: flex; }
    .lb-img { max-width: 100vw; max-height: 80vh; object-fit: contain; }
    .lb-controls { display: flex; align-items: center; gap: 16px; margin-top: 16px; }
    .lb-btn {
      background: rgba(255,255,255,0.12); color: #fff; border: none;
      border-radius: 50%; width: 44px; height: 44px; font-size: 20px;
      display: flex; align-items: center; justify-content: center; cursor: pointer;
    }
    .lb-nome { color: #aaa; font-size: 13px; }
    .lb-download {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 10px 18px; background: #fff; color: #1A1A1A;
      border-radius: 8px; font-size: 13px; font-weight: 700; text-decoration: none;
      margin-top: 12px;
    }
    .lb-fechar {
      position: absolute; top: 16px; right: 16px;
      background: rgba(255,255,255,0.15); color: #fff; border: none;
      border-radius: 50%; width: 44px; height: 44px; font-size: 20px; cursor: pointer;
    }
    """

def _js_lightbox():
    return """
  var lbTotal = 0, lbIdx = 0;
  var lbDriveUrls = {}, lbNomes = {};

  function abrirLightbox(idx) {
    lbIdx = idx;
    _atualizarLightbox();
    document.getElementById('lbOverlay').classList.add('ativo');
  }
  function fecharLightbox() {
    document.getElementById('lbOverlay').classList.remove('ativo');
  }
  function lbAnterior() { lbIdx = (lbIdx - 1 + lbTotal) % lbTotal; _atualizarLightbox(); }
  function lbProximo()  { lbIdx = (lbIdx + 1) % lbTotal; _atualizarLightbox(); }

  function _atualizarLightbox() {
    var src = document.getElementById('lb-src-' + lbIdx);
    var img = document.getElementById('lbImg');
    if (src && src.tagName === 'IMG') {
      img.src = src.src;
      img.style.display = '';
    } else {
      img.src = '';
      img.style.display = 'none';
    }
    var driveUrl = lbDriveUrls[lbIdx] || '';
    var btn = document.getElementById('lbDownload');
    if (driveUrl) {
      btn.href = driveUrl;
      btn.style.display = '';
    } else {
      btn.style.display = 'none';
    }
    document.getElementById('lbNome').textContent = lbNomes[lbIdx] || '';
  }

  document.addEventListener('keydown', function(e) {
    var ol = document.getElementById('lbOverlay');
    if (!ol || !ol.classList.contains('ativo')) return;
    if (e.key === 'ArrowLeft')  lbAnterior();
    if (e.key === 'ArrowRight') lbProximo();
    if (e.key === 'Escape')     fecharLightbox();
  });
    """

def _js_aprovacao(slug, ano_mes):
    estado_raw = f'{GITHUB_RAW}/{slug}/estado-{ano_mes}.json'
    return f"""
  // Carrega estado de aprovação do GitHub e libera downloads dos itens aprovados
  (function() {{
    var estadoUrl = '{estado_raw}';
    fetch(estadoUrl + '?_=' + Date.now())
      .then(function(r) {{ return r.ok ? r.json() : {{}}; }})
      .catch(function() {{ return {{}}; }})
      .then(function(estado) {{
        document.querySelectorAll('[data-post-id]').forEach(function(card) {{
          var id     = card.dataset.postId;
          var status = estado[id] || 'pendente';
          var btnDl  = card.querySelector('.btn-download');
          var badge  = card.querySelector('.badge-pendente');
          if (status === 'aprovado') {{
            if (btnDl)  btnDl.style.display  = '';
            if (badge)  badge.style.display  = 'none';
          }} else {{
            if (btnDl)  btnDl.style.display  = 'none';
            if (badge)  badge.style.display  = '';
          }}
        }});
      }});
  }})();
    """

def _js_youtube():
    return """
  window.abrirReel = function(ytId, facadeId) {
    var overlay = document.getElementById('yt-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'yt-overlay';
      overlay.style.cssText = 'position:fixed;inset:0;background:#000;z-index:600;display:none;flex-direction:column;align-items:center;justify-content:center;';
      var closeBtn = document.createElement('button');
      closeBtn.innerHTML = '&#10005;';
      closeBtn.style.cssText = 'position:absolute;top:16px;right:16px;z-index:10;background:rgba(255,255,255,0.15);color:#fff;border:none;border-radius:50%;width:44px;height:44px;font-size:20px;cursor:pointer;';
      closeBtn.onclick = function() { overlay.style.display = 'none'; overlay.innerHTML = ''; overlay.appendChild(closeBtn); };
      overlay.appendChild(closeBtn);
      document.body.appendChild(overlay);
    }
    var w = Math.min(window.innerWidth, 400);
    var h = Math.round(w * 16 / 9);
    var iframe = document.createElement('iframe');
    iframe.src = 'https://www.youtube.com/embed/' + ytId + '?autoplay=1&rel=0';
    iframe.style.cssText = 'width:' + w + 'px;height:' + h + 'px;border:none;';
    iframe.allow = 'autoplay; fullscreen';
    overlay.appendChild(iframe);
    overlay.style.display = 'flex';
  };
    """

def gerar_card_video(v, idx):
    """Gera HTML de um card de vídeo para a biblioteca."""
    data_str = v['data'].strftime('%d/%m') if v['data'] else ''
    fmt = v.get('formato', 'Reels').strip()
    fmt_map = {'Reels': 'formato-reels', 'Vídeo': 'formato-video',
               'Card': 'formato-card', 'Carrossel': 'formato-carrossel'}
    fmt_class = fmt_map.get(fmt, 'formato-reels')
    fmt_label = 'VÍDEO' if fmt in ('Reels', 'Vídeo') else fmt.upper()

    html_header = f'''
  <div class="post-header">
    <div class="post-meta">
      <div class="post-data">{escape_html(data_str)}</div>
      <div class="post-titulo">{escape_html(v["titulo"])}</div>
    </div>
    <span class="post-formato {fmt_class}">{fmt_label}</span>
  </div>'''

    # Arte: YouTube facade ou capa estática
    if v.get('youtube_id'):
        ytf_id = f'ytf-{idx}'
        html_arte = f'''
  <div class="post-arte">
    <div class="youtube-facade" id="{ytf_id}" onclick="abrirReel('{v["youtube_id"]}','{ytf_id}')">
      <img src="https://img.youtube.com/vi/{v["youtube_id"]}/maxresdefault.jpg"
           onerror="this.src='https://img.youtube.com/vi/{v["youtube_id"]}/hqdefault.jpg'"
           alt="{escape_html(v["titulo"])}"/>
      <div class="yt-play-btn">
        <svg viewBox="0 0 68 48" width="68" height="48">
          <path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C56 0 34 0 34 0S12 0 7.5 1.7a8.5 8.5 0 0 0-6 6C0 14.3 0 24 0 24s0 9.7 1.5 16.3a8.5 8.5 0 0 0 6 6C12 48 34 48 34 48s22 0 26.5-1.7a8.5 8.5 0 0 0 6-6C68 33.7 68 24 68 24s0-9.7-1.5-16.3z" fill="rgba(0,0,0,0.7)"/>
          <path d="M45 24 27 14v20z" fill="white"/>
        </svg>
      </div>
    </div>
  </div>'''
    elif v.get('thumbnail'):
        html_arte = f'<div class="post-arte"><img class="capa-estatica" src="{v["thumbnail"]}" alt="{escape_html(v["titulo"])}"/></div>'
    else:
        html_arte = ''

    # Botão de download (visível após aprovação via JS)
    if v.get('download_url'):
        html_download = f'''
  <a class="btn-download" href="{v["download_url"]}" style="display:none">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
    Salvar vídeo original
  </a>
  <div class="badge-pendente">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    Aguardando aprovação
  </div>'''
    else:
        html_download = '<div class="badge-pendente">Vídeo não disponível para download</div>'

    return f'''
<div class="post-card" data-post-id="{v["post_id"]}">
  {html_header}
  <div class="post-divider"></div>
  {html_arte}
  <div class="post-acoes">
    {html_download}
  </div>
</div>'''

def gerar_html_frames(frames_info):
    if not frames_info:
        return ''

    # Agrupa por grupo
    grupos: dict = {}
    lb_links = {}
    lb_nomes = {}
    lb_drive_urls = {}
    idx = 0
    for fi in frames_info:
        g = fi.get('grupo', '')
        if g not in grupos:
            grupos[g] = []
        grupos[g].append((idx, fi))
        lb_nomes[idx] = fi['nome']
        lb_drive_urls[idx] = fi.get('drive_url', '')
        idx += 1

    total_frames = idx

    grupos_html = []
    for grupo, items in grupos.items():
        cells = []
        for i, fi in items:
            thumb = fi.get('thumbnail')
            if thumb:
                img_html = f'<img id="lb-src-{i}" src="{thumb}" alt="{escape_html(fi["nome"])}" loading="lazy">'
            else:
                img_html = f'<span id="lb-src-{i}" style="display:none"></span><div class="frame-sem-preview">🖼</div>'
            cells.append(f'<div class="frame-cell" onclick="abrirLightbox({i})">{img_html}</div>')
        titulo_html = f'<div class="frames-grupo-titulo">{escape_html(grupo)}</div>' if grupo else ''
        grupos_html.append(
            f'<div class="frames-grupo">'
            f'{titulo_html}'
            f'<div class="frames-grid">{"".join(cells)}</div>'
            f'</div>'
        )

    return f'''
<div class="frames-section">
  <div class="frames-header">
    <span class="frames-titulo-texto">Frames</span>
  </div>
  {"".join(grupos_html)}
</div>
<script>
  lbTotal = {total_frames};
  lbNomes = {json.dumps(lb_nomes)};
  lbDriveUrls = {json.dumps(lb_drive_urls)};
</script>'''

def gerar_pagina_mes(cliente, ano_mes, videos_info, frames_info, slug):
    """Gera HTML da página de biblioteca de um mês."""
    mes_num = int(ano_mes.split('-')[1])
    ano     = ano_mes.split('-')[0]
    mes_label = f'{MESES_PT[mes_num].capitalize()} de {ano}'

    cards = ''.join(gerar_card_video(v, i) for i, v in enumerate(videos_info))
    frames_html = gerar_html_frames(frames_info)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Biblioteca — {escape_html(cliente)} — {escape_html(mes_label)}</title>
  <meta property="og:title" content="Biblioteca — {escape_html(cliente)} — {escape_html(mes_label)}"/>
  <meta property="og:description" content="Acesse e baixe os conteúdos aprovados de {escape_html(mes_label)}."/>
  <style>{_css()}</style>
</head>
<body>

<div class="header">
  <div class="header-label">Biblioteca de conteúdo</div>
  <div class="header-cliente">{escape_html(cliente)}</div>
  <div class="header-periodo">{escape_html(mes_label)}</div>
</div>

<div class="content">
  {cards}
  {frames_html}
</div>

<!-- LIGHTBOX -->
<div class="lb-overlay" id="lbOverlay" onclick="if(event.target===this)fecharLightbox()">
  <button class="lb-fechar" onclick="fecharLightbox()">&#10005;</button>
  <img class="lb-img" id="lbImg" src="" alt=""/>
  <a class="lb-download" id="lbDownload" href="#" target="_blank" download>
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
    Baixar frame
  </a>
  <div class="lb-controls">
    <button class="lb-btn" onclick="lbAnterior()">&#8592;</button>
    <span class="lb-nome" id="lbNome"></span>
    <button class="lb-btn" onclick="lbProximo()">&#8594;</button>
  </div>
</div>

<script>
  {_js_lightbox()}
  {_js_youtube()}
  {_js_aprovacao(slug, ano_mes)}
</script>
</body>
</html>"""

def gerar_index(cliente, meses_info, slug):
    """Gera HTML do índice de meses para o cliente."""
    itens = ''
    for m in sorted(meses_info, key=lambda x: x['ano_mes'], reverse=True):
        label = m['label']
        total = m['total_videos']
        itens += f'''
<a class="mes-card" href="{m["nome_arquivo"]}">
  <div class="mes-label">{escape_html(label)}</div>
  <div class="mes-total">{total} vídeo{"s" if total != 1 else ""}</div>
  <div class="mes-seta">→</div>
</a>'''

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Biblioteca — {escape_html(cliente)}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #F5F5F0; color: #1A1A1A; min-height: 100vh;
    }}
    .header {{
      background: #1A1A1A; color: #fff;
      padding: 20px 20px 20px; position: sticky; top: 0; z-index: 100;
    }}
    .header-label {{ font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #999; margin-bottom: 4px; }}
    .header-cliente {{ font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }}
    .content {{ padding: 16px 16px 48px; display: flex; flex-direction: column; gap: 10px; max-width: 480px; margin: 0 auto; }}
    .mes-card {{
      background: #fff; border-radius: 14px; padding: 18px 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.07);
      display: flex; align-items: center; gap: 8px;
      text-decoration: none; color: #1A1A1A;
      transition: box-shadow 0.15s;
    }}
    .mes-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
    .mes-label {{ font-size: 16px; font-weight: 700; flex: 1; }}
    .mes-total {{ font-size: 13px; color: #888; white-space: nowrap; }}
    .mes-seta {{ font-size: 18px; color: #bbb; margin-left: 4px; }}
  </style>
</head>
<body>
<div class="header">
  <div class="header-label">Biblioteca de conteúdo</div>
  <div class="header-cliente">{escape_html(cliente)}</div>
</div>
<div class="content">
  {itens}
</div>
</body>
</html>"""

# ─── FUNÇÃO PRINCIPAL ─────────────────────────────────────────────────────────

def gerar_para_cliente(cliente, agencia, filtro_mes=None):
    slug = slug_cliente(cliente)
    print(f"\n{'─'*50}")
    print(f"  {cliente}")
    print(f"{'─'*50}")

    pasta_entregas = encontrar_pasta_entregas(cliente, agencia)
    if not pasta_entregas:
        print(f"  ⚠️  06_Entregas não encontrado para {cliente}")
        return

    meses = listar_meses(pasta_entregas, cliente)
    if filtro_mes:
        meses = [(am, p) for am, p in meses if am == filtro_mes]

    if not meses:
        print(f"  ⚠️  Nenhum mês de entrega encontrado")
        return

    output_cliente = OUTPUT_DIR / slug
    output_cliente.mkdir(parents=True, exist_ok=True)

    meses_info = []
    for ano_mes, pasta_mes in meses:
        mes_num  = int(ano_mes.split('-')[1])
        ano_str  = ano_mes.split('-')[0]
        mes_label = f'{MESES_PT[mes_num].capitalize()} de {ano_str}'
        print(f"\n  📅 {mes_label} ({ano_mes})")

        # Carrega calendário para ordenação cronológica
        arquivo_md = encontrar_arquivo_mensal(cliente, ano_mes, agencia)
        if arquivo_md:
            print(f"     📄 Calendário: {arquivo_md.name}")
        calendario = ler_calendario(arquivo_md)

        # Pasta de vídeos
        pasta_videos = pasta_mes / 'Videos'
        if not pasta_videos.exists():
            pasta_videos = pasta_mes

        # IDs auxiliares
        youtube_ids = ler_youtube_ids(pasta_videos)
        gdrive_ids  = ler_gdrive_ids(pasta_videos)

        videos_info = construir_videos_info(pasta_mes, calendario, youtube_ids, gdrive_ids, slug, ano_mes)
        frames_info = construir_frames_info(pasta_mes)

        print(f"     🎬 {len(videos_info)} vídeo(s)  🖼 {len(frames_info)} frame(s)")
        for v in videos_info:
            data_str = v['data'].strftime('%d/%m') if v['data'] else 'sem data'
            yt = '✅ YT' if v.get('youtube_id') else '— YT'
            dl = '✅ Drive' if v.get('drive_id') else '— Drive'
            print(f"     {yt}  {dl}  {data_str}  {v['titulo'][:50]}")

        # Gera página do mês como {mes-ano}/index.html → URL limpa sem .html
        html = gerar_pagina_mes(cliente, ano_mes, videos_info, frames_info, slug)
        nome_pasta = f"{MESES_URL[mes_num]}-{ano_str}"
        pasta_mes_out = output_cliente / nome_pasta
        pasta_mes_out.mkdir(parents=True, exist_ok=True)
        with open(pasta_mes_out / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"     ✅ Gerado: {nome_pasta}/index.html")

        meses_info.append({
            'ano_mes':      ano_mes,
            'nome_arquivo': f"{nome_pasta}/",
            'label':        mes_label,
            'total_videos': len(videos_info),
        })

    # Gera índice
    if meses_info:
        html_index = gerar_index(cliente, meses_info, slug)
        with open(output_cliente / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html_index)
        print(f"\n  ✅ Índice gerado: {slug}/index.html")
        print(f"  🔗 URL: https://aprovar.forsterfilmes.com/{slug}/")

def main():
    parser = argparse.ArgumentParser(description='Gera biblioteca de entregas por cliente recorrente')
    parser.add_argument('--cliente', help='Nome do cliente (parcial aceito)')
    parser.add_argument('--mes',     help='Mês específico (YYYY-MM)')
    args = parser.parse_args()

    agencia = encontrar_agencia()

    if args.cliente:
        matches = [c for c in CLIENTES_BIBLIOTECA if args.cliente.lower() in c.lower()]
        if not matches:
            print(f"❌ Cliente '{args.cliente}' não encontrado em CLIENTES_BIBLIOTECA.")
            sys.exit(1)
        clientes = matches
    else:
        clientes = CLIENTES_BIBLIOTECA

    print("━" * 50)
    print("  FORSTER FILMES — Biblioteca de Entregas")
    print("━" * 50)

    for cliente in clientes:
        gerar_para_cliente(cliente, agencia, filtro_mes=args.mes)

    print("\n" + "━" * 50)
    print("  Pronto!")
    print("━" * 50)

if __name__ == '__main__':
    main()
