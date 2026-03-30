#!/usr/bin/env python3
"""
Forster Filmes — Validador de Arquivos
Cruza o planejamento de postagens (.md) com os arquivos reais nas pastas
Posts_Fixos/ e Videos/ antes de subir ao YouTube e gerar aprovações.

Uso:
  python3 validar_arquivos.py                      # mês atual, todos os clientes
  python3 validar_arquivos.py --cliente "Prisma"   # só um cliente
  python3 validar_arquivos.py --mes 2026-04        # mês específico
"""

import os
import re
import sys
import unicodedata
import argparse
from datetime import date, timedelta
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

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

EXT_IMAGEM = {'.jpg', '.jpeg', '.png', '.webp'}
EXT_VIDEO  = {'.mov', '.mp4', '.m4v'}

# Padrão de nomes em Posts_Fixos/:
#   Imagem única:  DD-MM.jpg
#   Carrossel:     DD-MM_1.jpg, DD-MM_2.jpg, ...
#   Sem espaços, acentos, parênteses ou dia da semana.
#   Slides em subpastas são movidos para Posts_Fixos/ raiz.

# ─── UTILITÁRIOS ─────────────────────────────────────────────────────────────

def slugify(texto):
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().replace(' ', '-')

def normalizar_nome_arte(nome):
    """
    Converte nome de arte para o padrão limpo.
    '04-04 (Sáb).jpg'       → '04-04.jpg'
    '30-03 (Seg)  1.jpg'    → '30-03_1.jpg'
    '01-04 (Qua) .jpg'      → '01-04.jpg'
    '09-04 (qui)_2.png'     → '09-04_2.png'
    '27_04_1.jpg'            → '27-04_1.jpg'  (underscore entre dia-mês)
    Retorna None se não for um arquivo de arte válido.
    """
    # Normaliza NFD → NFC
    nome = unicodedata.normalize('NFC', nome)
    # Extrai prefixo DD-MM ou DD_MM e extensão
    m = re.match(r'^(\d{2})[-_](\d{2})\s*(?:\([^)]*\))?\s*[_\s]*(\d+)?\s*(\.\w+)$', nome)
    if not m:
        return None
    dia = m.group(1)
    mes = m.group(2)
    numero = m.group(3)
    ext = m.group(4).lower()
    prefixo = f'{dia}-{mes}'
    if numero:
        return f'{prefixo}_{numero}{ext}'
    return f'{prefixo}{ext}'


def normalizar_posts_fixos(pasta_pf):
    """
    Renomeia arquivos em Posts_Fixos/ para o padrão limpo.
    Move slides de subpastas para a raiz. Remove subpastas vazias.
    Retorna lista de renomeações feitas.
    """
    if not pasta_pf or not pasta_pf.exists():
        return []

    renomeacoes = []

    # 1. Mover arquivos de subpastas para a raiz
    for subdir in list(pasta_pf.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith('.'):
            continue
        for arquivo in list(subdir.iterdir()):
            if arquivo.is_file() and arquivo.suffix.lower() in EXT_IMAGEM:
                destino = pasta_pf / arquivo.name
                if not destino.exists():
                    arquivo.rename(destino)
                    renomeacoes.append((f'{subdir.name}/{arquivo.name}', arquivo.name))
        # Remove subpasta se ficou vazia
        remaining = [f for f in subdir.iterdir() if not f.name.startswith('.')]
        if not remaining:
            try:
                # Remove .DS_Store se existir
                ds = subdir / '.DS_Store'
                if ds.exists():
                    ds.unlink()
                subdir.rmdir()
            except OSError:
                pass

    # 2. Renomear arquivos na raiz para o padrão limpo
    for arquivo in list(pasta_pf.iterdir()):
        if not arquivo.is_file() or arquivo.suffix.lower() not in EXT_IMAGEM:
            continue
        if '(capa)' in arquivo.name.lower():
            continue

        nome_limpo = normalizar_nome_arte(arquivo.name)
        if nome_limpo and nome_limpo != arquivo.name:
            destino = pasta_pf / nome_limpo
            if not destino.exists():
                arquivo.rename(destino)
                renomeacoes.append((arquivo.name, nome_limpo))

    return renomeacoes


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

def encontrar_arquivo_mensal(cliente, ano_mes, agencia_path):
    pasta = agencia_path / '_Clientes' / 'Clientes Recorrentes' / cliente / '04_Estratégia'
    if not pasta.exists():
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

def encontrar_pasta_entrega(ano_mes, pasta_cliente):
    pasta_entregas = pasta_cliente / '06_Entregas'
    if not pasta_entregas.exists():
        return None, None
    for entry in pasta_entregas.iterdir():
        if entry.is_dir() and entry.name.startswith(ano_mes):
            return entry / 'Posts_Fixos', entry / 'Videos'
    return None, None

def encontrar_arte_em_qualquer_entrega(data, pasta_cliente):
    """Procura arte (DD-MM*.jpg) em todas as pastas de 06_Entregas/."""
    pasta_entregas = pasta_cliente / '06_Entregas'
    if not pasta_entregas.exists():
        return None
    prefixo = data.strftime('%d-%m')
    prefixo_mes = data.strftime('%Y-%m')
    # Prioriza pasta do mês do post
    for entry in sorted(pasta_entregas.iterdir(), key=lambda e: (not e.name.startswith(prefixo_mes), e.name)):
        if not entry.is_dir() or entry.name.startswith('.'):
            continue
        pf = entry / 'Posts_Fixos'
        if pf.exists():
            encontrados = [f.name.lower() for f in pf.rglob('*')
                          if f.is_file() and f.suffix.lower() in EXT_IMAGEM
                          and f.name.lower().startswith(prefixo)
                          and '(capa)' not in f.name.lower()]
            if encontrados:
                return pf, encontrados
    return None

def detectar_formato(texto):
    t = texto.lower()
    if 'carrossel' in t or 'carousel' in t: return 'Carrossel'
    if 'reel' in t or 'reels' in t:          return 'Reels'
    if 'vídeo' in t or 'video' in t:         return 'Video'
    return 'Card'

def parse_data(texto):
    m = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{4}))?', texto)
    if m:
        try:
            return date(int(m.group(3) or date.today().year), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None

# ─── PARSER DO .MD ───────────────────────────────────────────────────────────

def parse_planejamento(md_path):
    """
    Lê o .md e retorna lista de posts esperados:
    { data, formato, titulo, reel_nome }
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    linhas = conteudo.split('\n')

    # 1. Tabela do calendário
    posts = {}
    em_tabela = False
    cabecalho_ok = False

    for linha in linhas:
        linha = linha.strip()
        if not linha.startswith('|'):
            cabecalho_ok = False
            continue
        celulas = [c.strip() for c in linha.strip('|').split('|')]
        if len(celulas) < 2:
            continue
        if any(re.match(r'-+', c) for c in celulas):
            cabecalho_ok = True
            continue
        if not cabecalho_ok:
            continue
        data = parse_data(celulas[0])
        if data:
            titulo = re.sub(r'[★⚠️✓✗]', '', celulas[2] if len(celulas) > 2 else '').strip()
            titulo = re.sub(r'\s*\([^)]+\)\s*$', '', titulo).strip()
            posts[data] = {
                'data': data,
                'formato': detectar_formato(celulas[1] if len(celulas) > 1 else ''),
                'titulo': titulo,
                'reel_nome': None,
            }

    # 2. Seções de conteúdo — busca campo **Vídeo:**
    secao_data = None
    aguardando_reel = False

    for linha in linhas:
        m = re.match(r'^#{2,4}\s+(\d{1,2}/\d{1,2})', linha)
        if m:
            secao_data = parse_data(linha)
            aguardando_reel = False
            continue

        if secao_data is None:
            continue

        linha_lower = linha.lower().strip()

        if aguardando_reel:
            if linha.strip() and not linha.startswith('**'):
                if secao_data in posts:
                    posts[secao_data]['reel_nome'] = linha.strip()
                aguardando_reel = False
            continue

        if re.match(r'\*\*(vídeo|video|reel)\b', linha_lower):
            valor_m = re.search(r':\s*(.+)', linha)
            valor = valor_m.group(1).strip().strip('*').strip() if valor_m else ''
            if valor:
                if secao_data in posts:
                    posts[secao_data]['reel_nome'] = valor
            else:
                aguardando_reel = True

    return list(posts.values())

# ─── VALIDAÇÃO ───────────────────────────────────────────────────────────────

def validar_cliente(cliente, ano_mes, agencia_path, data_inicio=None, data_fim=None):
    print(f"\n🔷 {cliente}")

    # Encontrar arquivo mensal (com fallback para mês anterior)
    md = encontrar_arquivo_mensal(cliente, ano_mes, agencia_path)
    if not md and data_inicio:
        mes_anterior = (data_inicio.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        md = encontrar_arquivo_mensal(cliente, mes_anterior, agencia_path)
        if md:
            print(f"  ℹ️  Sem .md de {ano_mes} — usando {md.name}")
    if not md:
        print(f"  ⚠️  Arquivo de Conteúdo Mensal {ano_mes} não encontrado — pulando")
        return True  # não é erro crítico, cliente pode não ter conteúdo nesse mês

    print(f"  📄 {md.name}")
    posts = parse_planejamento(md)
    if not posts:
        print(f"  ⚠️  Nenhum post encontrado no arquivo")
        return True

    # Filtrar posts pelo período se definido
    if data_inicio and data_fim:
        posts = [p for p in posts if data_inicio <= p['data'] <= data_fim]
        if not posts:
            print(f"  ⚠️  Nenhum post no período {data_inicio} a {data_fim}")
            return True

    # Encontrar pasta de entrega
    pasta_cliente = md.parent.parent  # sobe de 04_Estratégia para o cliente

    # Normalizar nomes em Posts_Fixos/ (todas as pastas de entrega)
    pasta_entregas = pasta_cliente / '06_Entregas'
    if pasta_entregas.exists():
        for entry in pasta_entregas.iterdir():
            if entry.is_dir() and not entry.name.startswith('.'):
                pf = entry / 'Posts_Fixos'
                renomeacoes = normalizar_posts_fixos(pf)
                for antigo, novo in renomeacoes:
                    print(f"  🔄 Renomeado: {antigo} → {novo}")

    erros  = []
    avisos = []
    ok     = []

    # ── Verificar artes (Posts_Fixos/) ───────────────────────────────────────
    posts_com_arte = [p for p in posts if p['formato'] in ('Card', 'Carrossel')]

    if posts_com_arte:
        for post in posts_com_arte:
            prefixo = post['data'].strftime('%d-%m')
            resultado = encontrar_arte_em_qualquer_entrega(post['data'], pasta_cliente)
            if resultado:
                _, encontrados = resultado
                ok.append(f"Arte {post['data'].strftime('%d/%m')}: {', '.join(sorted(encontrados))}")
            else:
                erros.append(
                    f"Arte não encontrada para {post['data'].strftime('%d/%m')} "
                    f"({post['formato']}: {post['titulo'][:50]})\n"
                    f"          → esperado: {prefixo}.jpg ou {prefixo}_1.jpg, {prefixo}_2.jpg..."
                )

    # ── Verificar Reels (Videos/) ─────────────────────────────────────────────
    posts_reel = [p for p in posts if p['formato'] in ('Reels', 'Video')]

    # Coleta vídeos de todas as pastas de entrega relevantes
    all_videos = {}
    pasta_entregas = pasta_cliente / '06_Entregas'
    if pasta_entregas.exists():
        for entry in pasta_entregas.iterdir():
            if entry.is_dir() and not entry.name.startswith('.'):
                pv = entry / 'Videos'
                if pv.exists():
                    for f in pv.iterdir():
                        if f.suffix.lower() in EXT_VIDEO and '(capa)' not in f.name.lower():
                            # Normaliza NFC para evitar mismatch NFD/NFC do macOS
                            all_videos[unicodedata.normalize('NFC', f.stem.lower())] = f

    if posts_reel:
        if not all_videos:
            if any(p['reel_nome'] for p in posts_reel):
                erros.append("Pasta Videos/ não encontrada em 06_Entregas/")
        else:
            for post in posts_reel:
                if not post['reel_nome']:
                    erros.append(
                        f"Campo **Vídeo:** ausente para {post['data'].strftime('%d/%m')} "
                        f"({post['titulo'][:50]})\n"
                        f"          → adicionar no .md: **Vídeo:** REEL NN - Nome"
                    )
                    continue

                reel_lower = unicodedata.normalize('NFC', post['reel_nome'].lower())
                if reel_lower in all_videos:
                    ok.append(f"Reel {post['data'].strftime('%d/%m')}: {post['reel_nome']}")
                else:
                    # Tentar match parcial (ignora traço vs hífen)
                    reel_norm = reel_lower.replace('–', '-').replace('—', '-')
                    match = next(
                        (k for k in all_videos if k.replace('–', '-').replace('—', '-') == reel_norm),
                        None
                    )
                    if match:
                        avisos.append(
                            f"Reel {post['data'].strftime('%d/%m')}: nome ligeiramente diferente\n"
                            f"          → .md diz:    {post['reel_nome']}\n"
                            f"          → arquivo é:  {all_videos[match].name}"
                        )
                    else:
                        erros.append(
                            f"Arquivo de vídeo não encontrado para {post['data'].strftime('%d/%m')} "
                            f"({post['titulo'][:50]})\n"
                            f"          → .md diz: {post['reel_nome']}\n"
                            f"          → esperado: {post['reel_nome']}.mov"
                        )

            # Vídeos sem post correspondente
            nomes_referenciados = {
                unicodedata.normalize('NFC', p['reel_nome'].lower())
                for p in posts_reel
                if p['reel_nome']
            }
            for nome_stem, f in all_videos.items():
                if nome_stem not in nomes_referenciados:
                    avisos.append(
                        f"Vídeo sem referência no planejamento: {f.name}\n"
                        f"          → não aparece em nenhum campo **Vídeo:** do .md"
                    )

    # ── Resultado ─────────────────────────────────────────────────────────────
    tem_erro = bool(erros)

    for msg in ok:
        print(f"  ✅ {msg}")
    for msg in avisos:
        print(f"  ⚠️  {msg}")
    for msg in erros:
        print(f"  ❌ {msg}")

    if not erros and not avisos:
        print(f"  🎉 Tudo certo! {len(ok)} arquivo(s) verificado(s)")

    return not tem_erro

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Valida arquivos antes de gerar aprovações')
    parser.add_argument('--cliente', help='Nome do cliente (parcial aceito)')
    parser.add_argument('--mes', help='Mês no formato YYYY-MM (padrão: mês atual)')
    parser.add_argument('--inicio', help='Início do período personalizado (YYYY-MM-DD)')
    parser.add_argument('--fim', help='Fim do período personalizado (YYYY-MM-DD)')
    args = parser.parse_args()

    ano_mes = args.mes or date.today().strftime('%Y-%m')

    # Período personalizado
    data_inicio = None
    data_fim = None
    if args.inicio and args.fim:
        from datetime import datetime
        data_inicio = datetime.strptime(args.inicio, '%Y-%m-%d').date()
        data_fim = datetime.strptime(args.fim, '%Y-%m-%d').date()
        ano_mes = data_inicio.strftime('%Y-%m')

    print(f"\n📋 VALIDAÇÃO DE ARQUIVOS — {ano_mes}")
    print("=" * 54)

    agencia = encontrar_pasta_agencia()

    if args.cliente:
        clientes = [
            c for c in CLIENTES_RECORRENTES
            if args.cliente.lower() in c.lower()
        ]
        if not clientes:
            print(f"\n❌ Cliente '{args.cliente}' não encontrado.")
            sys.exit(1)
    else:
        clientes = CLIENTES_RECORRENTES

    todos_ok = True
    for cliente in clientes:
        ok = validar_cliente(cliente, ano_mes, agencia, data_inicio, data_fim)
        if not ok:
            todos_ok = False

    print("\n" + "=" * 54)
    if todos_ok:
        print("✅ Validação concluída sem erros críticos.")
        sys.exit(0)
    else:
        print("❌ Foram encontrados erros. Corrija antes de continuar.")
        sys.exit(1)

if __name__ == '__main__':
    main()
