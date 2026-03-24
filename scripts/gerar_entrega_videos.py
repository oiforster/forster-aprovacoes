#!/usr/bin/env python3
"""
Forster Filmes — Gerador de Páginas de Entrega de Vídeos
Lê vídeos de 06_Entregas/YYYY-MM*/Videos/ e gera página HTML para aprovação.
Não requer arquivo .md de Conteúdo Mensal.

_contexto.md (opcional, na pasta Videos/):
  REEL 01 – Nome do Vídeo: Descrição breve para o cliente ver na página
  REEL 02 – Outro Vídeo: Contexto adicional

Uso:
  python3 gerar_entrega_videos.py --cliente "Joele Lerípio" --mes 2026-03
  python3 gerar_entrega_videos.py --cliente "Empório Essenza" --mes 2026-03 --pontual
"""

import os
import re
import sys
import json
import base64
import tempfile
import unicodedata
import argparse
import subprocess
from datetime import date
from pathlib import Path

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────

MESES_PT = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}

# WhatsApp padrão para clientes pontuais — mesmo link da Silvana/Samuel
WHATSAPP_PADRAO_PONTUAL = "https://wa.me/message/O6NXY5T2OHTZO1"

# WhatsApp por cliente recorrente (sobrescreve o padrão quando configurado)
WHATSAPP_LINKS: dict = {
    "Joele Lerípio":      "https://wa.me/message/O6NXY5T2OHTZO1",
    "Baviera Tecnologia": "https://wa.me/message/O6NXY5T2OHTZO1",
}

OUTPUT_DIR = Path(__file__).parent.parent / 'aprovacao'

GITHUB_BASE = "https://oiforster.github.io/forster-aprovacoes/aprovacao"

# ─── UTILITÁRIOS ─────────────────────────────────────────────────────────────

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

# ─── BUSCA DE PASTAS ─────────────────────────────────────────────────────────

def encontrar_agencia():
    """Encontra a pasta Agência no Synology (prioritário) ou Google Drive."""
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

    raise FileNotFoundError(
        "Pasta Agência não encontrada. Verifique Synology Drive ou Google Drive."
    )

def encontrar_pasta_cliente(cliente, agencia, pontual=False):
    """Encontra a pasta do cliente em Recorrentes ou Pontuais."""
    subfolder = 'Clientes Pontuais' if pontual else 'Clientes Recorrentes'
    base = agencia / '_Clientes' / subfolder

    pasta = base / cliente
    if pasta.exists():
        return pasta

    if base.exists():
        for entry in base.iterdir():
            if slugify(entry.name) == slugify(cliente):
                return entry

    # Tenta no outro subfolder
    outro = 'Clientes Recorrentes' if pontual else 'Clientes Pontuais'
    base2 = agencia / '_Clientes' / outro
    pasta2 = base2 / cliente
    if pasta2.exists():
        return pasta2
    if base2.exists():
        for entry in base2.iterdir():
            if slugify(entry.name) == slugify(cliente):
                return entry

    return None

def _tem_reels(pasta):
    """Verifica se a pasta contém arquivos REEL NN – Nome.mov/mp4/m4v."""
    extensoes = {'.mov', '.mp4', '.m4v'}
    try:
        return any(
            f.suffix.lower() in extensoes
            and '(capa)' not in f.name.lower()
            and re.match(r'^REEL\s+\d+', f.name, re.IGNORECASE)
            for f in pasta.iterdir()
            if f.is_file()
        )
    except PermissionError:
        return False

def _encontrar_pasta_mes(raiz, ano_mes):
    """Procura a pasta do mês em qualquer nível da raiz do cliente."""
    # Primeiro tenta 06_Entregas/YYYY-MM* (clientes recorrentes)
    pasta_entregas = raiz / '06_Entregas'
    if pasta_entregas.exists():
        for entry in sorted(pasta_entregas.iterdir()):
            if entry.is_dir() and entry.name.startswith(ano_mes):
                return entry

    # Fallback: pasta YYYY-MM* direto na raiz do cliente (clientes pontuais)
    for entry in sorted(raiz.iterdir()):
        if entry.is_dir() and entry.name.startswith(ano_mes):
            return entry

    return None

def encontrar_pasta_videos(pasta_cliente, ano_mes):
    """Encontra a pasta com vídeos REEL dentro do mês.
    Suporta 06_Entregas/YYYY-MM* (recorrentes) e YYYY-MM* na raiz (pontuais).
    Dentro do mês, tenta Videos/ primeiro e depois varre recursivamente."""
    pasta_mes = _encontrar_pasta_mes(pasta_cliente, ano_mes)
    if not pasta_mes:
        return None

    # Tenta Videos/ primeiro (caminho padrão de recorrentes)
    pasta_videos = pasta_mes / 'Videos'
    if pasta_videos.exists() and _tem_reels(pasta_videos):
        return pasta_videos

    # Varre recursivamente procurando qualquer pasta com arquivos REEL
    for dirpath, dirnames, _ in os.walk(pasta_mes):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.'))
        path = Path(dirpath)
        if _tem_reels(path):
            return path

    return None

# ─── LEITURA DE ARQUIVOS ──────────────────────────────────────────────────────

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

def ler_contexto_md(pasta_videos):
    """
    Lê _contexto.md → dict { 'REEL 01 – Nome': 'descrição' }.
    Formato: REEL 01 – Nome do Vídeo: Descrição para o cliente ver
    """
    arquivo = pasta_videos / '_contexto.md'
    if not arquivo.exists():
        return {}
    contextos = {}
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#'):
                continue
            # Divide na primeira ocorrência de ': ' após o nome do reel
            m = re.match(r'^(REEL\s+\d+\s*[–\-]\s*.+?):\s*(.+)$', linha, re.IGNORECASE)
            if m:
                chave = m.group(1).strip()
                desc  = m.group(2).strip()
                contextos[chave] = desc
    return contextos

def ler_synology_md(pasta_videos):
    """Lê _synology.md → dict { 'REEL 01 – Nome': 'https://...' }"""
    arquivo = pasta_videos / '_synology.md'
    if not arquivo.exists():
        return {}
    links = {}
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#'):
                continue
            idx = linha.find(': http')
            if idx == -1:
                continue
            links[linha[:idx].strip()] = linha[idx + 2:].strip()
    return links


def _encontrar_pasta_frames(pasta_videos):
    """Localiza pasta de frames.
    Ordem: 1) subpasta 'Frames' dentro dos vídeos; 2) pasta irmã com 'frame' no nome."""
    candidato = pasta_videos / 'Frames'
    if candidato.exists():
        return candidato
    parent = pasta_videos.parent
    try:
        for entry in sorted(parent.iterdir()):
            if entry.is_dir() and 'frame' in entry.name.lower():
                return entry
    except PermissionError:
        pass
    return None


def listar_frames(pasta_videos):
    """Retorna (lista_de_frames, pasta_frames) ou ([], None) se não existir.
    Busca recursiva: suporta frames diretamente na pasta ou em subpastas por REEL."""
    pasta_frames = _encontrar_pasta_frames(pasta_videos)
    if not pasta_frames:
        return [], None
    ext = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
    frames = []
    for dirpath, dirnames, filenames in os.walk(pasta_frames):
        dirnames.sort()
        for fname in sorted(filenames):
            if not fname.startswith('.') and Path(fname).suffix.lower() in ext:
                frames.append(Path(dirpath) / fname)
    return frames, pasta_frames


def gerar_thumbnail_base64(frame_path, max_size=300):
    """Gera thumbnail JPEG via sips (macOS nativo) e retorna data URI base64."""
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
        result = subprocess.run(
            ['sips', '-Z', str(max_size), '-s', 'format', 'jpeg',
             str(frame_path), '--out', tmp_path],
            capture_output=True, timeout=15
        )
        if result.returncode != 0:
            return None
        with open(tmp_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        os.unlink(tmp_path)
        return f"data:image/jpeg;base64,{data}"
    except Exception:
        return None


def gerar_template_contexto(pasta_videos, videos):
    """Cria _contexto.md com template para Samuel preencher."""
    arquivo = pasta_videos / '_contexto.md'
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write('# Contexto por vídeo (opcional)\n')
        f.write('# Preencha uma descrição breve para o cliente ver na página de aprovação.\n')
        f.write('# Deixe em branco para não exibir contexto.\n\n')
        for v in videos:
            f.write(f"{v.stem}: \n")
    return arquivo

def listar_videos(pasta_videos):
    """Lista vídeos REEL NN – Nome.mov/.mp4/.m4v em ordem."""
    extensoes = {'.mov', '.mp4', '.m4v'}
    return sorted([
        f for f in pasta_videos.iterdir()
        if f.suffix.lower() in extensoes
        and '(capa)' not in f.name.lower()
        and re.match(r'^REEL\s+\d+', f.name, re.IGNORECASE)
    ])

# ─── GERAÇÃO DE HTML ─────────────────────────────────────────────────────────

CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }

    html { background: #E8E8E3; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #F5F5F0;
      color: #1A1A1A;
      min-height: 100vh;
      max-width: 480px;
      margin: 0 auto;
    }

    /* HEADER */
    .header {
      background: #1A1A1A;
      color: #fff;
      padding: 20px 20px 16px;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-label {
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #999;
      margin-bottom: 4px;
    }
    .header-cliente {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .header-periodo {
      font-size: 13px;
      color: #aaa;
      margin-top: 3px;
    }
    .header-progress {
      margin-top: 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .progress-bar-bg {
      flex: 1;
      height: 4px;
      background: #333;
      border-radius: 2px;
      overflow: hidden;
    }
    .progress-bar-fill {
      height: 100%;
      background: #4CAF50;
      border-radius: 2px;
      width: 0%;
      transition: width 0.3s ease;
    }
    .progress-text {
      font-size: 12px;
      color: #aaa;
      white-space: nowrap;
    }

    /* APROVAR TUDO */
    .aprovar-tudo-container {
      padding: 16px 16px 8px;
    }
    .btn-aprovar-tudo {
      width: 100%;
      padding: 14px;
      background: #1A1A1A;
      color: #fff;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: 600;
      letter-spacing: 0.01em;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-aprovar-tudo:hover { background: #333; }
    .btn-aprovar-tudo.ativo { background: #4CAF50; }

    /* LISTA DE VÍDEOS */
    .posts-lista {
      padding: 8px 16px 120px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    /* CARD DE VÍDEO */
    .post-card {
      background: #fff;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.07);
      transition: box-shadow 0.2s, opacity 0.2s;
    }
    .post-card.aprovado { box-shadow: 0 0 0 2px #4CAF50; }
    .post-card.ajuste   { box-shadow: 0 0 0 2px #FF5722; }

    .post-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 14px 10px;
    }
    .post-meta { flex: 1; min-width: 0; }

    .video-numero {
      display: inline-block;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: #888;
      margin-bottom: 4px;
    }

    .post-titulo {
      font-size: 15px;
      font-weight: 600;
      line-height: 1.35;
      word-break: break-word;
    }

    .video-contexto {
      margin: 0 14px 12px;
      font-size: 13px;
      color: #555;
      line-height: 1.5;
      padding: 10px 12px;
      background: #F8F8F5;
      border-radius: 8px;
      border-left: 3px solid #ddd;
    }

    .post-formato {
      flex-shrink: 0;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 4px 8px;
      border-radius: 6px;
    }
    .formato-reels { background: #FFF3E0; color: #E65100; }

    /* PLAYER YOUTUBE */
    .post-arte {
      width: 100%;
      aspect-ratio: 9/16;
      overflow: hidden;
      background: #000;
      position: relative;
    }
    .youtube-facade {
      width: 100%;
      height: 100%;
      position: relative;
      cursor: pointer;
    }
    .youtube-facade img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .yt-play-btn {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      pointer-events: none;
    }
    .sem-video {
      display: flex;
      align-items: center;
      justify-content: center;
      background: #F0F0EC;
    }
    .sem-video-label {
      font-size: 13px;
      color: #999;
      padding: 20px;
      text-align: center;
    }

    .post-divider {
      height: 1px;
      background: #F0F0EC;
      margin: 0 14px;
    }

    /* AÇÕES */
    .post-acoes {
      display: flex;
      gap: 10px;
      padding: 12px 14px;
    }
    .btn-aprovar, .btn-ajuste {
      flex: 1;
      padding: 11px 8px;
      border: 2px solid;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      background: transparent;
    }
    .btn-aprovar {
      border-color: #4CAF50;
      color: #4CAF50;
    }
    .btn-aprovar.ativo {
      background: #4CAF50;
      color: #fff;
    }
    .btn-ajuste {
      border-color: #FF5722;
      color: #FF5722;
    }
    .btn-ajuste.ativo {
      background: #FF5722;
      color: #fff;
    }

    .campo-ajuste {
      display: none;
      padding: 0 14px 14px;
      flex-direction: column;
      gap: 8px;
    }
    .campo-ajuste.visivel { display: flex; }
    .campo-ajuste textarea {
      width: 100%;
      padding: 10px 12px;
      border: 1.5px solid #E0E0E0;
      border-radius: 8px;
      font-size: 14px;
      font-family: inherit;
      resize: vertical;
      min-height: 80px;
    }
    .campo-ajuste textarea:focus {
      outline: none;
      border-color: #FF5722;
    }
    .btn-confirmar-obs {
      align-self: flex-end;
      padding: 8px 16px;
      background: #1A1A1A;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }

    /* FOOTER */
    .footer-enviar {
      position: fixed;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 100%;
      max-width: 480px;
      padding: 12px 16px 20px;
      background: #fff;
      box-shadow: 0 -1px 0 rgba(0,0,0,0.08);
    }
    .btn-enviar {
      width: 100%;
      padding: 15px;
      background: #25D366;
      color: #fff;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-enviar:hover { background: #1ebe5d; }
    .btn-enviar:disabled {
      background: #ccc;
      cursor: default;
    }
    .footer-pendente {
      font-size: 12px;
      color: #999;
      text-align: center;
      margin-top: 6px;
    }

    /* OVERLAY YOUTUBE */
    #yt-overlay {
      position: fixed;
      inset: 0;
      background: #000;
      z-index: 500;
      display: none;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    /* BOTÃO DOWNLOAD ORIGINAL */
    .btn-download-original {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      margin: 0 14px 14px;
      padding: 11px 14px;
      background: #F5F5F0;
      border: 1.5px solid #E0E0DA;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      color: #1A1A1A;
      text-decoration: none;
      transition: background 0.15s;
    }
    .btn-download-original:hover { background: #EAEAE5; }
    .btn-download-original svg { flex-shrink: 0; }

    /* SEÇÃO FRAMES */
    .frames-section {
      margin: 8px 16px 24px;
      background: #fff;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    }
    .frames-header {
      padding: 14px 14px 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .frames-titulo-texto {
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #888;
    }
    .btn-baixar-todos {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 8px 14px;
      background: #1A1A1A;
      color: #fff;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-decoration: none;
      white-space: nowrap;
      transition: background 0.15s;
    }
    .btn-baixar-todos:hover { background: #333; }
    .frames-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 2px;
      padding: 0 2px 2px;
    }
    .frame-cell {
      position: relative;
      aspect-ratio: 9/16;
      overflow: hidden;
      background: #E0E0DC;
      border-radius: 4px;
      cursor: pointer;
    }
    .frame-cell img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .frame-download-btn {
      position: absolute;
      bottom: 5px;
      right: 5px;
      width: 30px;
      height: 30px;
      background: rgba(0,0,0,0.60);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      color: #fff;
      font-size: 14px;
    }
    .frame-sem-preview {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      color: #bbb;
    }

    /* LIGHTBOX DE FRAMES */
    #frame-lightbox {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.96);
      z-index: 600;
      display: none;
      align-items: center;
      justify-content: center;
    }
    #lb-close {
      position: absolute;
      top: 16px;
      right: 16px;
      background: rgba(255,255,255,0.15);
      color: #fff;
      border: none;
      border-radius: 50%;
      width: 44px;
      height: 44px;
      font-size: 20px;
      cursor: pointer;
      z-index: 10;
    }
    #lb-prev, #lb-next {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      background: rgba(255,255,255,0.12);
      color: #fff;
      border: none;
      border-radius: 50%;
      width: 48px;
      height: 48px;
      font-size: 28px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10;
      transition: opacity 0.15s;
    }
    #lb-prev { left: 10px; }
    #lb-next { right: 10px; }
    #lb-img {
      width: min(88vw, 480px);
      height: auto;
      max-height: 80vh;
      object-fit: contain;
      border-radius: 4px;
      display: block;
    }
    #lb-footer {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 16px 16px 32px;
      background: linear-gradient(transparent, rgba(0,0,0,0.85));
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }
    #lb-counter {
      font-size: 12px;
      color: rgba(255,255,255,0.5);
    }
    #lb-download {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      padding: 14px 20px;
      background: rgba(255,255,255,0.18);
      color: #fff;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 600;
      text-decoration: none;
      letter-spacing: 0.01em;
    }
    #lb-download:hover { background: rgba(255,255,255,0.25); }
"""

JS_TEMPLATE = """
    var TOTAL = {total};
    var estados = {{}};
    var observacoes = {{}};

    function atualizar() {{
      var revisados = Object.keys(estados).length;
      var pct = TOTAL > 0 ? (revisados / TOTAL * 100) : 0;
      document.getElementById('progress-fill').style.width = pct + '%';
      document.getElementById('progress-text').textContent = revisados + ' / ' + TOTAL;

      var todos = revisados === TOTAL;
      var btnEnviar = document.getElementById('btn-enviar');
      var pendente  = document.getElementById('footer-pendente');
      btnEnviar.disabled = !todos;
      pendente.style.display = todos ? 'none' : 'block';

      var tudo = document.getElementById('btn-aprovar-tudo');
      var todosAprovados = Object.values(estados).every(function(e) {{ return e === 'aprovado'; }});
      tudo.classList.toggle('ativo', todos && todosAprovados);
    }}

    function marcarVideo(id, estado) {{
      var card    = document.getElementById('card-' + id);
      var btnApr  = document.getElementById('aprovar-' + id);
      var btnAjt  = document.getElementById('ajuste-' + id);
      var campo   = document.getElementById('campo-' + id);

      if (estados[id] === estado) {{
        delete estados[id];
        card.classList.remove('aprovado', 'ajuste');
        btnApr.classList.remove('ativo');
        btnAjt.classList.remove('ativo');
        campo.classList.remove('visivel');
      }} else {{
        estados[id] = estado;
        card.classList.remove('aprovado', 'ajuste');
        btnApr.classList.remove('ativo');
        btnAjt.classList.remove('ativo');
        card.classList.add(estado);
        if (estado === 'aprovado') btnApr.classList.add('ativo');
        if (estado === 'ajuste')   btnAjt.classList.add('ativo');
        campo.classList.toggle('visivel', estado === 'ajuste');
      }}
      atualizar();
    }}

    function atualizarObs(id, valor) {{
      observacoes[id] = valor;
    }}

    function confirmarObs(id) {{
      var txt = document.getElementById('obs-' + id).value.trim();
      if (!txt) {{ alert('Escreva uma observação antes de confirmar.'); return; }}
      observacoes[id] = txt;
      var btn = document.getElementById('btnobs-' + id);
      btn.textContent = '✓ Registrado';
      btn.style.background = '#4CAF50';
      setTimeout(function() {{
        btn.textContent = 'Registrar observação';
        btn.style.background = '';
      }}, 2000);
    }}

    function aprovarTudo() {{
      var ids = {ids_json};
      ids.forEach(function(id) {{
        if (estados[id] !== 'aprovado') marcarVideo(id, 'aprovado');
      }});
    }}

    function abrirVideo(ytId, facadeId) {{
      var overlay = document.getElementById('yt-overlay');
      var ifr = document.getElementById('yt-iframe');
      if (!ifr) {{
        var closeBtn = document.createElement('button');
        closeBtn.innerHTML = '&#10005;';
        closeBtn.style.cssText = 'position:absolute;top:16px;right:16px;z-index:10;background:rgba(255,255,255,0.15);color:#fff;border:none;border-radius:50%;width:44px;height:44px;font-size:20px;cursor:pointer;';
        closeBtn.onclick = function() {{
          overlay.style.display = 'none';
          document.getElementById('yt-iframe').src = '';
        }};
        ifr = document.createElement('iframe');
        ifr.id = 'yt-iframe';
        ifr.style.cssText = 'width:100%;height:100%;border:none;';
        ifr.setAttribute('allow','accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen');
        ifr.setAttribute('allowfullscreen','');
        overlay.appendChild(closeBtn);
        overlay.appendChild(ifr);
      }}
      ifr.src = 'https://www.youtube.com/embed/' + ytId + '?autoplay=1&rel=0&modestbranding=1&playsinline=1';
      overlay.style.display = 'flex';
    }}

    function enviarWhatsApp() {{
      var cliente = '{cliente_escaped}';
      var mes     = '{mes_display_escaped}';
      var url     = '{url_pagina}';

      var ids = {ids_json};
      var linhas = [
        '✅ *Aprovação de Vídeos — ' + cliente + ' — ' + mes + '*',
        ''
      ];

      ids.forEach(function(id) {{
        var card  = document.getElementById('card-' + id);
        var titulo = card.querySelector('.post-titulo').textContent;
        var estado = estados[id];
        var obs    = observacoes[id] || '';
        if (estado === 'aprovado') {{
          linhas.push('✓ ' + titulo + ' — *Aprovado*');
        }} else if (estado === 'ajuste') {{
          linhas.push('✗ ' + titulo + ' — *Ajuste solicitado*');
          if (obs) linhas.push('  → ' + obs);
        }}
      }});

      linhas.push('');
      linhas.push('🔗 ' + url);

      var msg = linhas.join('\\n');
      var link = '{whatsapp_link}';
      var sep = link.includes('?') ? '&' : '?';
      window.open(link + sep + 'text=' + encodeURIComponent(msg), '_blank');
    }}

    document.addEventListener('DOMContentLoaded', atualizar);

    // ── LIGHTBOX DE FRAMES ────────────────────────────────────────
    var lbIdx   = 0;
    var lbTotal = 0;
    var lbLinks = {{}};
    var lbNomes = {{}};

    function abrirLightbox(idx) {{
      lbIdx = idx;
      _lbAtualizar();
      document.getElementById('frame-lightbox').style.display = 'flex';
    }}

    function fecharLightbox() {{
      document.getElementById('frame-lightbox').style.display = 'none';
    }}

    function lightboxNavegar(dir) {{
      var novo = lbIdx + dir;
      if (novo >= 0 && novo < lbTotal) {{ lbIdx = novo; _lbAtualizar(); }}
    }}

    function _lbAtualizar() {{
      var srcEl = document.getElementById('lb-src-' + lbIdx);
      if (srcEl) document.getElementById('lb-img').src = srcEl.src;
      document.getElementById('lb-nome').textContent    = lbNomes[lbIdx] || '';
      document.getElementById('lb-counter').textContent = (lbIdx + 1) + ' / ' + lbTotal;
      var dl   = document.getElementById('lb-download');
      var link = lbLinks[lbIdx] || '';
      if (link) {{ dl.href = link; dl.style.display = 'inline-flex'; }}
      else {{ dl.style.display = 'none'; }}
      document.getElementById('lb-prev').style.opacity = lbIdx > 0 ? '1' : '0.25';
      document.getElementById('lb-next').style.opacity = lbIdx < lbTotal - 1 ? '1' : '0.25';
    }}

    document.addEventListener('keydown', function(e) {{
      var lb = document.getElementById('frame-lightbox');
      if (!lb || lb.style.display === 'none') return;
      if (e.key === 'ArrowLeft')  lightboxNavegar(-1);
      if (e.key === 'ArrowRight') lightboxNavegar(1);
      if (e.key === 'Escape')     fecharLightbox();
    }});
"""

def gerar_html_card(video_info):
    vid_id        = video_info['id']
    titulo        = video_info['titulo']
    contexto      = video_info.get('contexto', '')
    youtube_id    = video_info.get('youtube_id')
    numero        = video_info['numero']
    synology_link = video_info.get('synology_link', '')

    html_numero = f'<div class="video-numero">REEL {numero:02d}</div>'

    html_contexto = ''
    if contexto:
        html_contexto = f'  <div class="video-contexto">{escape_html(contexto)}</div>\n'

    if youtube_id:
        ytf_id = f"ytf-{vid_id}"
        html_player = f'''  <div class="post-arte">
    <div class="youtube-facade" id="{ytf_id}" onclick="abrirVideo('{youtube_id}','{ytf_id}')">
      <img
        src="https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg"
        onerror="this.src='https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg'"
        alt="{escape_html(titulo)}"
      />
      <div class="yt-play-btn">
        <svg viewBox="0 0 68 48" width="68" height="48">
          <path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C56 0 34 0 34 0S12 0 7.5 1.7a8.5 8.5 0 0 0-6 6C0 14.3 0 24 0 24s0 9.7 1.5 16.3a8.5 8.5 0 0 0 6 6C12 48 34 48 34 48s22 0 26.5-1.7a8.5 8.5 0 0 0 6-6C68 33.7 68 24 68 24s0-9.7-1.5-16.3z" fill="rgba(0,0,0,0.7)"/>
          <path d="M45 24 27 14v20z" fill="white"/>
        </svg>
      </div>
    </div>
  </div>'''
    else:
        html_player = '''  <div class="post-arte sem-video">
    <div class="sem-video-label">⏳ Vídeo ainda não enviado ao YouTube</div>
  </div>'''

    html_download = ''
    if synology_link:
        html_download = f'''  <a class="btn-download-original" href="{synology_link}" target="_blank">
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M7.5 1v9M4 7l3.5 3.5L11 7M2 13h11" stroke="#1A1A1A" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    Baixar vídeo original (.mov)
  </a>
'''

    return f'''
<div class="post-card" id="card-{vid_id}" data-video-id="{vid_id}">
  <div class="post-header">
    <div class="post-meta">
      {html_numero}
      <div class="post-titulo">{escape_html(titulo)}</div>
    </div>
    <span class="post-formato formato-reels">Vídeo</span>
  </div>
{html_contexto}{html_player}
{html_download}  <div class="post-divider"></div>
  <div class="post-acoes">
    <button class="btn-aprovar" id="aprovar-{vid_id}" onclick="marcarVideo('{vid_id}', 'aprovado')">✓ Aprovar</button>
    <button class="btn-ajuste"  id="ajuste-{vid_id}"  onclick="marcarVideo('{vid_id}', 'ajuste')">✗ Pedir ajuste</button>
  </div>
  <div class="campo-ajuste" id="campo-{vid_id}">
    <textarea id="obs-{vid_id}" placeholder="O que você gostaria de ajustar neste vídeo?"
      oninput="atualizarObs('{vid_id}', this.value)" rows="3"></textarea>
    <button class="btn-confirmar-obs" id="btnobs-{vid_id}" onclick="confirmarObs('{vid_id}')">
      Registrar observação
    </button>
  </div>
</div>'''

def gerar_html_frames_section(frames_info):
    """
    frames_info: lista de dicts com keys:
      nome       → nome do arquivo
      thumbnail  → data URI base64 ou None
      link       → URL Synology para download individual ou None
    O último item pode ter 'folder_link' para o botão "Baixar todos".
    """
    if not frames_info:
        return ''

    folder_link = ''
    cells       = []
    lb_links    = {}
    lb_nomes    = {}

    frame_items = [fi for fi in frames_info if not fi.get('folder_link')]
    for fi in frames_info:
        if fi.get('folder_link'):
            folder_link = fi['folder_link']

    for idx, fi in enumerate(frame_items):
        nome      = fi['nome']
        thumbnail = fi.get('thumbnail')
        link      = fi.get('link', '')

        lb_links[idx] = link
        lb_nomes[idx] = nome

        if thumbnail:
            img_html = f'<img id="lb-src-{idx}" src="{thumbnail}" alt="{escape_html(nome)}" loading="lazy">'
        else:
            img_html = f'<span id="lb-src-{idx}" style="display:none"></span><div class="frame-sem-preview">🖼</div>'

        download_html = ''
        if link:
            download_html = (
                f'<a class="frame-download-btn" href="{link}" target="_blank" '
                f'onclick="event.stopPropagation()" title="Baixar {escape_html(nome)}">'
                '⬇'
                '</a>'
            )

        cells.append(
            f'<div class="frame-cell" onclick="abrirLightbox({idx})">'
            f'{img_html}{download_html}</div>'
        )

    btn_todos = ''
    if folder_link:
        btn_todos = (
            f'<a class="btn-baixar-todos" href="{folder_link}" target="_blank">'
            '⬇ Baixar todos'
            '</a>'
        )

    grid_html    = '\n    '.join(cells)
    total_frames = len(frame_items)

    return f'''
  <div class="frames-section">
    <div class="frames-header">
      <span class="frames-titulo-texto">Frames</span>
      {btn_todos}
    </div>
    <div class="frames-grid">
    {grid_html}
    </div>
  </div>
  <script>
    lbTotal = {total_frames};
    lbLinks = {json.dumps(lb_links)};
    lbNomes = {json.dumps(lb_nomes)};
  </script>'''


def gerar_pagina_html(cliente, ano_mes, videos_info, whatsapp_link,
                      frames_info=None):
    ano, mes_num = ano_mes.split('-')
    mes_display = f"{MESES_PT[int(mes_num)]} de {ano}"
    slug = slugify(cliente)
    url_pagina = f"{GITHUB_BASE}/{slug}/{ano_mes}.html"

    total = len(videos_info)
    ids_json = '[' + ', '.join(f'"{v["id"]}"' for v in videos_info) + ']'

    cards_html = ''.join(gerar_html_card(v) for v in videos_info)
    frames_html = gerar_html_frames_section(frames_info or [])

    # Prepara link WhatsApp (grupo ou número direto)
    if not whatsapp_link:
        whatsapp_link = 'https://wa.me/5551980603512'

    js = JS_TEMPLATE.format(
        total=total,
        ids_json=ids_json,
        cliente_escaped=cliente.replace("'", "\\'"),
        mes_display_escaped=mes_display.replace("'", "\\'"),
        url_pagina=url_pagina,
        whatsapp_link=whatsapp_link,
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Aprovação de Vídeos — {escape_html(cliente)}</title>
  <style>{CSS}</style>
</head>
<body>

  <div class="header">
    <div class="header-label">Aprovação de Vídeos</div>
    <div class="header-cliente">{escape_html(cliente)}</div>
    <div class="header-periodo">{escape_html(mes_display)}</div>
    <div class="header-progress">
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progress-fill"></div>
      </div>
      <span class="progress-text" id="progress-text">0 / {total}</span>
    </div>
  </div>

  <div class="aprovar-tudo-container">
    <button class="btn-aprovar-tudo" id="btn-aprovar-tudo" onclick="aprovarTudo()">
      ✓ Aprovar todos os vídeos
    </button>
  </div>

  <div class="posts-lista">
    {cards_html}
  </div>

  <div id="yt-overlay"></div>

  <div id="frame-lightbox">
    <button id="lb-close" onclick="fecharLightbox()">✕</button>
    <button id="lb-prev"  onclick="lightboxNavegar(-1)">‹</button>
    <img id="lb-img" src="" alt="">
    <button id="lb-next"  onclick="lightboxNavegar(1)">›</button>
    <div id="lb-footer">
      <span id="lb-counter"></span>
      <a id="lb-download" href="" target="_blank">
        <svg width="16" height="16" viewBox="0 0 15 15" fill="none">
          <path d="M7.5 1v9M4 7l3.5 3.5L11 7M2 13h11" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Baixar este frame
      </a>
    </div>
  </div>

  <script>{js}</script>

{frames_html}

  <div class="footer-enviar">
    <button class="btn-enviar" id="btn-enviar" onclick="enviarWhatsApp()" disabled>
      Enviar resposta via WhatsApp
    </button>
    <div class="footer-pendente" id="footer-pendente">Revise todos os vídeos antes de enviar.</div>
  </div>

</body>
</html>"""

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Gera página de aprovação de vídeos sem arquivo .md de estratégia.'
    )
    parser.add_argument('--cliente', type=str, required=True,
                        help='Nome do cliente (ex: "Joele Lerípio")')
    parser.add_argument('--mes',     type=str, default=None,
                        help='Mês no formato YYYY-MM (padrão: mês atual)')
    parser.add_argument('--pontual', action='store_true', default=False,
                        help='Busca em Clientes Pontuais em vez de Recorrentes')
    parser.add_argument('--sem-contexto', action='store_true', default=False,
                        help='Pula criação de _contexto.md mesmo se não existir')
    args = parser.parse_args()

    cliente = args.cliente
    ano_mes = args.mes or date.today().strftime('%Y-%m')
    pontual = args.pontual

    print(f"\n🎬  Gerador de Entrega de Vídeos — Forster Filmes")
    print(f"    Cliente : {cliente}")
    print(f"    Mês     : {ano_mes}")
    print(f"    Tipo    : {'Pontual' if pontual else 'Recorrente'}\n")

    # 1. Achar a pasta Agência
    try:
        agencia = encontrar_agencia()
        print(f"  📁 Agência: {agencia}")
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
        sys.exit(1)

    # 2. Achar pasta do cliente
    pasta_cliente = encontrar_pasta_cliente(cliente, agencia, pontual)
    if not pasta_cliente:
        tipo = 'Pontuais' if pontual else 'Recorrentes'
        print(f"  ❌ Cliente '{cliente}' não encontrado em Clientes {tipo}.")
        sys.exit(1)
    print(f"  📂 Cliente: {pasta_cliente.name}")

    # 3. Achar pasta de vídeos
    pasta_videos = encontrar_pasta_videos(pasta_cliente, ano_mes)
    if not pasta_videos:
        print(f"  ❌ Nenhum arquivo REEL encontrado em 06_Entregas/{ano_mes}*")
        print(f"     Verifique se a pasta de entrega do mês existe e contém arquivos REEL NN – Nome.mov")
        sys.exit(1)
    print(f"  🎥 Vídeos : {pasta_videos}")

    # 4. Listar vídeos
    arquivos = listar_videos(pasta_videos)
    if not arquivos:
        print(f"  ❌ Nenhum vídeo REEL encontrado em {pasta_videos}")
        sys.exit(1)
    print(f"\n  📹 {len(arquivos)} vídeo(s) encontrado(s):")
    for f in arquivos:
        print(f"      {f.name}")

    # 5. _contexto.md
    if not args.sem_contexto:
        arquivo_contexto = pasta_videos / '_contexto.md'
        if not arquivo_contexto.exists():
            template = gerar_template_contexto(pasta_videos, arquivos)
            print(f"\n  📝 _contexto.md criado com template em:\n     {template}")
            print(f"\n  ℹ️  Preencha o contexto de cada vídeo (opcional) e rode novamente.")
            print(f"     Ou rode com --sem-contexto para gerar sem descrições.")
            sys.exit(0)
        else:
            print(f"\n  📝 _contexto.md encontrado — lendo descrições...")

    # 6. Ler YouTube IDs, contextos e links Synology
    youtube_ids   = ler_youtube_md(pasta_videos)
    contextos     = ler_contexto_md(pasta_videos)
    synology_links = ler_synology_md(pasta_videos)

    sem_yt = [f.stem for f in arquivos if f.stem not in youtube_ids]
    if sem_yt:
        print(f"\n  ⚠️  Sem YouTube ID (rode subir_reels.py primeiro):")
        for nome in sem_yt:
            print(f"      {nome}")

    sem_syn = [f.stem for f in arquivos if f.stem not in synology_links]
    if sem_syn:
        print(f"\n  ℹ️  Sem link Synology (rode gerar_links_synology.py para download direto):")
        for nome in sem_syn:
            print(f"      {nome}")

    # 7. Montar lista de vídeos
    videos_info = []
    for arquivo in arquivos:
        reel_nome = arquivo.stem
        m = re.match(r'^REEL\s+(\d+)\s*[–\-]\s*(.+)$', reel_nome, re.IGNORECASE)
        numero = int(m.group(1)) if m else 0
        titulo = m.group(2).strip() if m else reel_nome

        # Busca contexto com tolerância a variações no en-dash
        contexto = ''
        for chave, desc in contextos.items():
            if slugify(chave) == slugify(reel_nome):
                contexto = desc
                break

        # Busca link Synology com mesma tolerância
        synology_link = ''
        for chave, url in synology_links.items():
            if slugify(chave) == slugify(reel_nome):
                synology_link = url
                break

        videos_info.append({
            'id':            f"reel-{numero:02d}",
            'numero':        numero,
            'titulo':        titulo,
            'contexto':      contexto,
            'youtube_id':    youtube_ids.get(reel_nome),
            'synology_link': synology_link,
        })

    # 7b. Montar lista de frames (com thumbnails base64)
    frames_info = []
    frames, pasta_frames = listar_frames(pasta_videos)
    if frames:
        print(f"\n  🖼  Gerando thumbnails de {len(frames)} frame(s)...")
        folder_link = synology_links.get('FRAMES_FOLDER', '')
        for frame in frames:
            # Chave usa path relativo à pasta frames (mirrors gerar_links_synology.py)
            rel = frame.relative_to(pasta_frames).as_posix()
            chave_link = f'FRAME_{rel}'
            link       = synology_links.get(chave_link, '')
            thumbnail  = gerar_thumbnail_base64(frame, 600)
            if thumbnail:
                print(f"      ✅ {frame.name}")
            else:
                print(f"      ⚠️  {frame.name} (thumbnail não gerado)")
            frames_info.append({
                'nome':      frame.name,
                'thumbnail': thumbnail,
                'link':      link,
            })
        # Adiciona o folder link como item especial no fim
        if folder_link:
            frames_info.append({'folder_link': folder_link})

    # 8. Gerar HTML
    # Clientes recorrentes: usa o link configurado ou vazio
    # Clientes pontuais: usa o link padrão (mesmo da Silvana/Baviera)
    whatsapp_link = WHATSAPP_LINKS.get(cliente, WHATSAPP_PADRAO_PONTUAL if pontual else '')
    html = gerar_pagina_html(cliente, ano_mes, videos_info, whatsapp_link,
                             frames_info=frames_info)

    slug = slugify(cliente)
    pasta_saida = OUTPUT_DIR / slug
    pasta_saida.mkdir(parents=True, exist_ok=True)
    arquivo_saida = pasta_saida / f"{ano_mes}.html"

    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n  ✅ Página gerada: {arquivo_saida}")
    print(f"\n  🔗 URL (após publicar): {GITHUB_BASE}/{slug}/{ano_mes}.html")
    print(f"\n  📱 WhatsApp: {whatsapp_link or '(não configurado)'}")

if __name__ == '__main__':
    main()
