#!/usr/bin/env python3
"""
Forster Filmes — Gerador de Páginas de Aprovação
Lê arquivos .md de Conteúdo Mensal e gera páginas HTML para aprovação dos clientes.

Uso:
  python3 gerar_aprovacoes.py                      # gera páginas da semana seguinte para todos os clientes
  python3 gerar_aprovacoes.py --cliente "Prisma"   # gera só para um cliente
  python3 gerar_aprovacoes.py --semana 2026-04-07  # semana específica (segunda-feira)
  python3 gerar_aprovacoes.py --mes 2026-04        # gera o mês inteiro
"""

import os
import re
import sys
import json
import unicodedata
import argparse
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────

# Caminho base (detecta NFD automaticamente)
def encontrar_pasta_agencia():
    base = Path('/Users/samuelforster/Library/CloudStorage/GoogleDrive-oiforster@gmail.com/Meu Drive/Forster Filmes/CLAUDE_COWORK')
    if not base.exists():
        # Fallback para ambiente de desenvolvimento
        base = Path('/sessions/elegant-jolly-galileo/mnt')
    for entry in base.iterdir():
        if 'Ag' in entry.name:
            return entry
    raise FileNotFoundError(f"Pasta Agência não encontrada em {base}")

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

# Caminho de saída (pasta do repositório)
OUTPUT_DIR = Path(__file__).parent.parent / 'aprovacao'

# ─── MESES EM PORTUGUÊS ───────────────────────────────────────────────────────

MESES_PT = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}

DIAS_PT = {
    0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui',
    4: 'Sex', 5: 'Sáb', 6: 'Dom'
}

# ─── UTILITÁRIOS ─────────────────────────────────────────────────────────────

def slugify(texto):
    """Converte texto para slug URL-safe."""
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.lower().replace(' ', '-')
    texto = re.sub(r'[^a-z0-9\-]', '', texto)
    texto = re.sub(r'-+', '-', texto).strip('-')
    return texto

def proxima_segunda(referencia=None):
    """Retorna a segunda-feira da próxima semana."""
    hoje = referencia or date.today()
    # Dias até a próxima segunda (0 = segunda, 6 = domingo)
    dias_ate_segunda = (7 - hoje.weekday()) % 7
    if dias_ate_segunda == 0:
        dias_ate_segunda = 7  # Se hoje é segunda, vai para a próxima
    return hoje + timedelta(days=dias_ate_segunda)

def semana_para_datas(segunda):
    """Retorna lista de datas da semana (seg a dom) a partir de uma segunda-feira."""
    return [segunda + timedelta(days=i) for i in range(7)]

def formatar_data_display(d):
    """Formata data como '07 de abril (ter)'."""
    dia_semana = DIAS_PT[d.weekday()].lower()
    return f"{d.day:02d}/{d.month:02d} ({dia_semana})"

def formatar_periodo(datas):
    """Formata período como '07 a 13 de abril'."""
    inicio = datas[0]
    fim = datas[-1]
    if inicio.month == fim.month:
        return f"{inicio.day} a {fim.day} de {MESES_PT[inicio.month]}"
    else:
        return f"{inicio.day}/{inicio.month:02d} a {fim.day}/{fim.month:02d}"

# ─── BUSCA DE ARTES ──────────────────────────────────────────────────────────

def gdrive_id_para_url(filepath):
    """
    Lê o Google Drive File ID dos metadados macOS (xattr) e retorna URL de embed.
    Funciona com Google Drive for Desktop (modo streaming ou downloaded).
    """
    try:
        result = subprocess.run(
            ['xattr', '-p', 'com.google.drivefs.item-id', str(filepath)],
            capture_output=True, text=True, timeout=5
        )
        file_id = result.stdout.strip()
        if file_id:
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    except Exception:
        pass
    return None

def encontrar_arte(data, pasta_estrategia):
    """
    Procura arte para um post em 04_Estratégia/_Artes/YYYY-MM/
    Aceita arquivos nomeados como:
      - DD-MM.jpg / DD-MM.png
      - DD-MM-1.jpg (múltiplos posts no mesmo dia)
    Retorna URL de embed do Google Drive ou None.
    """
    pasta_artes = pasta_estrategia / '_Artes' / data.strftime('%Y-%m')

    if not pasta_artes.exists():
        return None

    prefixo = data.strftime('%d-%m')
    extensoes = {'.jpg', '.jpeg', '.png', '.webp'}

    # Tenta DD-MM.ext primeiro, depois DD-MM-1.ext
    candidatos = []
    for f in pasta_artes.iterdir():
        nome = f.name.lower()
        if f.suffix.lower() in extensoes:
            if nome.startswith(prefixo):
                candidatos.append(f)

    if not candidatos:
        return None

    # Ordena para pegar o primeiro (DD-MM.jpg antes de DD-MM-1.jpg)
    candidatos.sort(key=lambda x: x.name)
    arquivo = candidatos[0]

    return gdrive_id_para_url(arquivo)


# ─── PARSER DO .MD ──────────────────────────────────────────────────────────

def encontrar_arquivo_mensal(cliente, ano_mes, agencia_path):
    """Encontra o arquivo YYYY-MM — Conteúdo Mensal [Cliente].md"""
    pasta = agencia_path / '_Clientes' / 'Clientes Recorrentes' / cliente / '04_Estratégia'
    if not pasta.exists():
        # Tenta sem acento
        for entry in (agencia_path / '_Clientes' / 'Clientes Recorrentes').iterdir():
            if slugify(entry.name) == slugify(cliente):
                pasta = entry / '04_Estratégia'
                break

    if not pasta.exists():
        return None

    for arquivo in pasta.iterdir():
        if arquivo.suffix == '.md' and ano_mes in arquivo.name and 'Conte' in arquivo.name:
            return arquivo
    return None

def parse_data_linha(texto):
    """
    Extrai data de uma linha de tabela do calendário.
    Aceita formatos:
      - "25/03 Qua"
      - "25/03/2026 Qua"
      - "2026-03-25"
    Retorna objeto date ou None.
    """
    # Formato DD/MM
    m = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{4}))?', texto)
    if m:
        dia = int(m.group(1))
        mes = int(m.group(2))
        ano = int(m.group(3)) if m.group(3) else date.today().year
        try:
            return date(ano, mes, dia)
        except ValueError:
            pass
    # Formato YYYY-MM-DD
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None

def detectar_formato(texto):
    """Detecta o formato do post (Card, Carrossel, Reels, Vídeo)."""
    t = texto.lower()
    if 'carrossel' in t or 'carousel' in t:
        return 'Carrossel'
    if 'reel' in t or 'reels' in t:
        return 'Reels'
    if 'vídeo' in t or 'video' in t or 'yt' in t or 'youtube' in t:
        return 'Vídeo'
    if 'card' in t:
        return 'Card'
    return 'Post'

def parse_conteudo_mensal(arquivo_path, datas_semana=None, pasta_estrategia=None):
    """
    Lê um arquivo de Conteúdo Mensal e extrai os posts.
    Se datas_semana for fornecido, filtra só os posts dessas datas.

    Retorna lista de dicts:
    {
        id, data, data_display, titulo, formato,
        texto_card, legenda, slides, media_link, status
    }
    """
    try:
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
    except Exception as e:
        print(f"  ⚠️  Erro ao ler {arquivo_path}: {e}")
        return []

    posts = []

    # 1. Extrair tabela do calendário
    # Formato: | Data | Formato | Título | Status |
    tabela_posts = {}

    linhas = conteudo.split('\n')
    em_tabela = False
    cabecalho_tabela = False

    for linha in linhas:
        linha = linha.strip()
        if not linha.startswith('|'):
            em_tabela = False
            continue

        celulas = [c.strip() for c in linha.strip('|').split('|')]
        if len(celulas) < 2:
            continue

        # Detectar cabeçalho da tabela
        if any(re.match(r'-+', c) for c in celulas):
            cabecalho_tabela = True
            em_tabela = True
            continue

        if not cabecalho_tabela:
            # Pode ser linha de cabeçalho (Data, Formato, etc.)
            continue

        if em_tabela and cabecalho_tabela:
            data = parse_data_linha(celulas[0])
            if data:
                formato = detectar_formato(celulas[1] if len(celulas) > 1 else '')
                titulo = celulas[2] if len(celulas) > 2 else ''
                # Remove marcadores como ⚠️ ★
                titulo = re.sub(r'[★⚠️✓✗]', '', titulo).strip()
                # Remove texto entre parênteses que são notas
                titulo = re.sub(r'\s*\([^)]+\)\s*$', '', titulo).strip()
                status = celulas[3] if len(celulas) > 3 else ''

                tabela_posts[data] = {
                    'data': data,
                    'formato': formato,
                    'titulo': titulo,
                    'status': status,
                }

    # Reset para reler tabela mais cuidadosamente
    # Algumas tabelas têm a data na primeira coluna mas o formato pode variar
    if not tabela_posts:
        # Tenta extrair de listas simples: "25/03 Qua | Card | Título"
        for linha in linhas:
            data = parse_data_linha(linha)
            if data and '|' in linha:
                partes = [p.strip() for p in linha.split('|')]
                if len(partes) >= 3:
                    tabela_posts[data] = {
                        'data': data,
                        'formato': detectar_formato(partes[1] if len(partes) > 1 else ''),
                        'titulo': partes[2] if len(partes) > 2 else '',
                        'status': partes[3] if len(partes) > 3 else '',
                    }

    # 2. Extrair conteúdo detalhado de cada post
    # Seção: "#### DD/MM (Dia) — Formato — Título"
    secoes_conteudo = {}
    secao_atual_data = None
    secao_atual_texto = []

    for i, linha in enumerate(linhas):
        # Detecta início de seção de post
        m = re.match(r'^#{2,4}\s+(\d{1,2}/\d{1,2})', linha)
        if m:
            # Salva seção anterior
            if secao_atual_data:
                secoes_conteudo[secao_atual_data] = '\n'.join(secao_atual_texto).strip()

            data = parse_data_linha(linha)
            if data:
                secao_atual_data = data
                secao_atual_texto = []
            else:
                secao_atual_data = None
                secao_atual_texto = []
        elif secao_atual_data is not None:
            secao_atual_texto.append(linha)

    # Salva última seção
    if secao_atual_data:
        secoes_conteudo[secao_atual_data] = '\n'.join(secao_atual_texto).strip()

    # 3. Montar posts completos
    datas_para_processar = list(tabela_posts.keys())

    # Filtrar por semana se fornecido
    if datas_semana:
        datas_para_processar = [d for d in datas_para_processar if d in datas_semana]

    datas_para_processar.sort()

    for data in datas_para_processar:
        info = tabela_posts[data]
        texto_secao = secoes_conteudo.get(data, '')

        # Extrair texto do card, legenda e media_link da seção
        texto_card, legenda, slides, media_link = extrair_partes_post(texto_secao)

        post_id = f"{data.strftime('%Y%m%d')}-{slugify(info['titulo'])[:30]}"

        # Busca arte automaticamente na pasta _Artes/
        arte_url = None
        if pasta_estrategia:
            arte_url = encontrar_arte(data, pasta_estrategia)
            if arte_url:
                print(f"    🖼️  Arte encontrada para {data.strftime('%d/%m')}")

        posts.append({
            'id': post_id,
            'data': data,
            'data_display': formatar_data_display(data),
            'titulo': info['titulo'] or 'Post sem título',
            'formato': info['formato'],
            'status': info['status'],
            'texto_card': texto_card,
            'legenda': legenda,
            'slides': slides,
            'media_link': media_link,
            'arte_url': arte_url,
        })

    return posts

def extrair_partes_post(texto_secao):
    """
    Extrai do texto de uma seção:
    - texto_card: conteúdo do card/texto principal
    - legenda: legenda do post
    - slides: lista de slides (para carrosseis)
    - media_link: link para mídia (Drive, YouTube, etc.)
    """
    texto_card = ''
    legenda = ''
    slides = []
    media_link = ''

    if not texto_secao:
        return texto_card, legenda, slides, media_link

    linhas = texto_secao.split('\n')
    modo = None
    buffer = []
    slide_atual = None

    for linha in linhas:
        linha_lower = linha.lower().strip()

        # Detecta link de mídia
        if any(x in linha_lower for x in ['drive.google.com', 'youtu.be', 'youtube.com', 'frame.io']):
            m = re.search(r'https?://\S+', linha)
            if m:
                media_link = m.group(0).rstrip(')')

        # Detecta início de seção
        if re.match(r'\*\*texto do card', linha_lower) or re.match(r'\*\*texto:', linha_lower):
            if buffer and modo:
                _flush_buffer(modo, buffer, slides, lambda t: None, lambda l: None)
            modo = 'card'
            buffer = []
        elif re.match(r'\*\*legenda', linha_lower):
            if buffer and modo == 'card':
                texto_card = '\n'.join(buffer).strip()
            elif buffer and modo:
                _flush_buffer(modo, buffer, slides, lambda t: None, lambda l: None)
            modo = 'legenda'
            buffer = []
        elif re.match(r'\*\*slide\s*(\d+)', linha_lower):
            if buffer and modo == 'card':
                texto_card = '\n'.join(buffer).strip()
            elif buffer and modo == 'legenda':
                legenda = '\n'.join(buffer).strip()
            elif buffer and slide_atual is not None:
                slides.append({'titulo': slide_atual, 'texto': '\n'.join(buffer).strip()})
            m = re.match(r'\*\*slide\s*(\d+)\s*(?:\(([^)]+)\))?\*\*:?', linha, re.IGNORECASE)
            slide_atual = m.group(2) if m and m.group(2) else f"Slide {m.group(1) if m else len(slides)+1}"
            modo = 'slide'
            buffer = []
        elif linha.startswith('**') and '**' in linha[2:]:
            # Outro marcador de campo
            pass
        else:
            # Linha de conteúdo
            if linha.strip() and not linha.startswith('*Nota') and not linha.startswith('*⚠️'):
                buffer.append(linha)

    # Flush final
    if buffer:
        if modo == 'card':
            texto_card = '\n'.join(buffer).strip()
        elif modo == 'legenda':
            legenda = '\n'.join(buffer).strip()
        elif modo == 'slide' and slide_atual is not None:
            slides.append({'titulo': slide_atual, 'texto': '\n'.join(buffer).strip()})

    # Remove marcadores markdown do texto
    texto_card = limpar_markdown(texto_card)
    legenda = limpar_markdown(legenda)

    return texto_card, legenda, slides, media_link

def _flush_buffer(modo, buffer, slides, set_card, set_legenda):
    pass  # Helper interno

def limpar_markdown(texto):
    """Remove marcadores markdown básicos para exibição limpa."""
    if not texto:
        return texto
    # Remove **negrito**
    texto = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto)
    # Remove *itálico*
    texto = re.sub(r'\*([^*]+)\*', r'\1', texto)
    # Remove [texto](url)
    texto = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto)
    return texto.strip()

# ─── GERADOR DE HTML ─────────────────────────────────────────────────────────

FORMATO_CLASSES = {
    'Card': 'formato-card',
    'Carrossel': 'formato-carrossel',
    'Reels': 'formato-reels',
    'Vídeo': 'formato-video',
    'Post': 'formato-card',
}

def gerar_html_post(post):
    """Gera o HTML de um card de post."""
    fmt_class = FORMATO_CLASSES.get(post['formato'], 'formato-card')
    post_id = post['id']

    # Conteúdo principal
    html_conteudo = ''

    if post['texto_card']:
        html_conteudo += f'''
    <div class="post-conteudo">
      <div class="post-conteudo-label">Texto</div>
      <div class="post-texto">{escape_html(post["texto_card"])}</div>
    </div>'''

    if post['slides']:
        slides_html = ''
        for i, slide in enumerate(post['slides']):
            slides_html += f'<div class="post-conteudo-label" style="margin-top:{8 if i>0 else 0}px">Slide {i+1}{" — " + slide["titulo"] if slide["titulo"] != f"Slide {i+1}" else ""}</div>'
            slides_html += f'<div class="post-texto">{escape_html(slide["texto"])}</div>'
        html_conteudo += f'''
    <div class="post-conteudo">
      {slides_html}
    </div>'''

    if post['legenda']:
        html_conteudo += f'''
    <div class="post-conteudo" style="padding-top:0">
      <div class="post-conteudo-label">Legenda</div>
      <div class="post-texto">{escape_html(post["legenda"])}</div>
    </div>'''

    # Botão de mídia
    html_media = ''
    if post['media_link']:
        html_media = f'''
    <div class="post-media">
      <a class="btn-ver-midia" href="{post['media_link']}" target="_blank" rel="noopener">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        Ver vídeo / mídia
      </a>
    </div>'''

    # Se não tem conteúdo nenhum, mostra placeholder
    if not html_conteudo and not html_media:
        html_conteudo = f'''
    <div class="post-conteudo">
      <div class="post-texto" style="color:#aaa;font-style:italic">Conteúdo detalhado não disponível neste arquivo.</div>
    </div>'''

    # Arte inline (imagem do Drive)
    html_arte = ''
    if post.get('arte_url'):
        html_arte = f'''
    <div class="post-arte">
      <img
        src="{post['arte_url']}"
        alt="Arte — {escape_html(post['titulo'])}"
        loading="lazy"
        onerror="this.parentElement.style.display='none'"
      />
    </div>'''

    return f'''
  <div class="post-card" id="card-{post_id}" data-post-id="{post_id}">
    <div class="post-header">
      <div class="post-meta">
        <div class="post-data">{post['data_display']}</div>
        <div class="post-titulo">{escape_html(post['titulo'])}</div>
      </div>
      <span class="post-formato {fmt_class}">{post['formato']}</span>
    </div>
    {html_arte}
    <div class="post-divider"></div>
    {html_conteudo}
    {html_media}
    <div class="post-acoes">
      <button class="btn-aprovar" id="aprovar-{post_id}" onclick="marcarPost('{post_id}', 'aprovado')">
        ✓ Aprovar
      </button>
      <button class="btn-ajuste" id="ajuste-{post_id}" onclick="marcarPost('{post_id}', 'ajuste')">
        ✗ Pedir ajuste
      </button>
    </div>
    <div class="campo-ajuste" id="campo-{post_id}">
      <textarea
        placeholder="O que você gostaria de ajustar neste post?"
        oninput="atualizarComentario('{post_id}', this.value)"
        rows="3"
      ></textarea>
    </div>
  </div>'''

def escape_html(texto):
    """Escapa caracteres HTML."""
    if not texto:
        return ''
    return (texto
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace('\n', '<br>'))

def gerar_pagina_aprovacao(cliente, posts, periodo_label, semana_inicio, form_id):
    """Gera o HTML completo de uma página de aprovação."""
    template_path = Path(__file__).parent.parent / 'aprovacao' / 'template.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Organizar posts por semana
    semanas = {}
    for post in posts:
        # Semana = segunda-feira da semana do post
        segunda = post['data'] - timedelta(days=post['data'].weekday())
        semanas.setdefault(segunda, []).append(post)

    semanas_ordenadas = sorted(semanas.keys())

    # Gerar HTML dos posts e navegação de semanas
    posts_html = ''
    semanas_nav_html = ''

    if len(semanas_ordenadas) > 1:
        # Navegação de semanas
        semanas_nav_html = '<div class="semanas-nav">'
        for i, seg in enumerate(semanas_ordenadas):
            fim_sem = seg + timedelta(days=6)
            label = f"{seg.day}/{seg.month:02d} – {fim_sem.day}/{fim_sem.month:02d}"
            ativa = ' ativa' if i == 0 else ''
            semanas_nav_html += f'<button class="tab-semana{ativa}" id="tab-{seg}" onclick="mudarSemana(\'{seg}\')">{label}</button>'
        semanas_nav_html += '</div>'

        for i, seg in enumerate(semanas_ordenadas):
            ativa = ' ativa' if i == 0 else ''
            posts_html += f'<div class="semana-bloco{ativa}" id="semana-{seg}">'
            for post in semanas[seg]:
                posts_html += gerar_html_post(post)
            posts_html += '</div>'
    else:
        for post in posts:
            posts_html += gerar_html_post(post)

    # Substituir placeholders
    html = template
    html = html.replace('{{TITULO_PAGINA}}', f'Aprovação — {cliente}')
    html = html.replace('{{NOME_CLIENTE}}', cliente)
    html = html.replace('{{PERIODO}}', periodo_label)
    html = html.replace('{{TOTAL_POSTS}}', str(len(posts)))
    html = html.replace('{{POSTS_HTML}}', posts_html)
    html = html.replace('{{SEMANAS_NAV}}', semanas_nav_html)
    html = html.replace('{{FORM_ID}}', form_id)

    return html

# ─── GERADOR DE MENSAGEM WHATSAPP ───────────────────────────────────────────

def gerar_mensagem_whatsapp(cliente, periodo_label, url_aprovacao):
    """Gera a mensagem de WhatsApp pronta para copiar."""
    return f"""Olá! 😊

Aqui estão os posts da semana de *{periodo_label}* para aprovação.

👉 {url_aprovacao}

Você pode aprovar cada post ou pedir ajuste com um toque. Se preferir, tem um botão para aprovar tudo de uma vez.

Qualquer dúvida, é só chamar! 🙌"""

# ─── FUNÇÃO PRINCIPAL ────────────────────────────────────────────────────────

def gerar_para_cliente(cliente, datas_semana, agencia_path, base_url, output_dir, modo_mes=False):
    """Gera página de aprovação para um cliente."""

    # Determinar qual(is) arquivo(s) ler
    meses_necessarios = set()
    for d in datas_semana:
        meses_necessarios.add(d.strftime('%Y-%m'))

    todos_posts = []
    for ano_mes in sorted(meses_necessarios):
        arquivo = encontrar_arquivo_mensal(cliente, ano_mes, agencia_path)
        if not arquivo:
            continue
        print(f"  📄 Lendo: {arquivo.name}")

        pasta_estrategia = arquivo.parent

        if modo_mes:
            posts = parse_conteudo_mensal(arquivo, pasta_estrategia=pasta_estrategia)
        else:
            posts = parse_conteudo_mensal(arquivo, set(datas_semana), pasta_estrategia=pasta_estrategia)

        todos_posts.extend(posts)

    if not todos_posts:
        print(f"  ⚠️  Nenhum post encontrado para {cliente} no período.")
        return None, None

    print(f"  ✅ {len(todos_posts)} post(s) encontrado(s)")

    # Gerar identificadores
    slug_cliente = slugify(cliente)
    semana_str = datas_semana[0].strftime('%Y-%m-%d')
    form_id = f"{slug_cliente}-{semana_str}"

    # Período para exibição
    if modo_mes:
        d_inicio = min(p['data'] for p in todos_posts)
        d_fim = max(p['data'] for p in todos_posts)
        periodo_label = f"{MESES_PT[d_inicio.month].capitalize()} de {d_inicio.year}"
    else:
        periodo_label = formatar_periodo(datas_semana)

    # Gerar HTML
    html = gerar_pagina_aprovacao(cliente, todos_posts, periodo_label, datas_semana[0], form_id)

    # Salvar arquivo
    pasta_cliente = output_dir / slug_cliente
    pasta_cliente.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"{semana_str}.html"
    caminho_saida = pasta_cliente / nome_arquivo

    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(html)

    # Gerar também index.html na pasta do cliente (sempre a última semana)
    index_path = pasta_cliente / 'index.html'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)

    url = f"{base_url}/aprovacao/{slug_cliente}/{nome_arquivo}"
    url_index = f"{base_url}/aprovacao/{slug_cliente}/"

    mensagem = gerar_mensagem_whatsapp(cliente, periodo_label, url_index)

    return caminho_saida, mensagem

def main():
    parser = argparse.ArgumentParser(description='Gera páginas de aprovação para clientes Forster Filmes')
    parser.add_argument('--cliente', help='Nome do cliente (parcial aceito)')
    parser.add_argument('--semana', help='Segunda-feira da semana (YYYY-MM-DD)')
    parser.add_argument('--mes', help='Gerar mês completo (YYYY-MM)')
    parser.add_argument('--base-url', default='https://forster-filmes.netlify.app',
                        help='URL base do site Netlify')
    args = parser.parse_args()

    # Encontrar pasta da agência
    try:
        agencia_path = encontrar_pasta_agencia()
        print(f"📁 Agência: {agencia_path}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Determinar período
    modo_mes = False
    if args.mes:
        ano, mes = map(int, args.mes.split('-'))
        # Todas as datas do mês
        import calendar
        _, ultimo_dia = calendar.monthrange(ano, mes)
        datas_semana = [date(ano, mes, d) for d in range(1, ultimo_dia + 1)]
        modo_mes = True
        print(f"📅 Modo: mês completo {args.mes}")
    elif args.semana:
        segunda = datetime.strptime(args.semana, '%Y-%m-%d').date()
        datas_semana = semana_para_datas(segunda)
        print(f"📅 Semana: {args.semana} → {formatar_periodo(datas_semana)}")
    else:
        segunda = proxima_segunda()
        datas_semana = semana_para_datas(segunda)
        print(f"📅 Próxima semana: {formatar_periodo(datas_semana)}")

    # Determinar clientes
    if args.cliente:
        clientes = [c for c in CLIENTES_RECORRENTES if args.cliente.lower() in c.lower()]
        if not clientes:
            print(f"❌ Cliente '{args.cliente}' não encontrado.")
            print(f"   Clientes disponíveis: {', '.join(CLIENTES_RECORRENTES)}")
            sys.exit(1)
    else:
        clientes = CLIENTES_RECORRENTES

    print(f"\n👥 Processando {len(clientes)} cliente(s)...\n")

    resultados = []

    for cliente in clientes:
        print(f"🔷 {cliente}")
        caminho, mensagem = gerar_para_cliente(
            cliente, datas_semana, agencia_path,
            args.base_url, OUTPUT_DIR, modo_mes
        )
        if caminho:
            resultados.append({
                'cliente': cliente,
                'arquivo': str(caminho),
                'mensagem': mensagem,
            })
        print()

    # Resumo final
    print("=" * 60)
    print(f"✅ {len(resultados)} página(s) gerada(s) em: {OUTPUT_DIR}\n")

    for r in resultados:
        print(f"📱 {r['cliente']}")
        print(f"   Arquivo: {r['arquivo']}")
        print(f"\n   Mensagem WhatsApp:")
        print("   " + r['mensagem'].replace('\n', '\n   '))
        print()

    print("=" * 60)
    print("⬆️  Para publicar: git add . && git commit -m 'Aprovações' && git push")
    print("=" * 60)

if __name__ == '__main__':
    main()
