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

# ─── UTILITÁRIOS ─────────────────────────────────────────────────────────────

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

def validar_cliente(cliente, ano_mes, agencia_path):
    print(f"\n🔷 {cliente}")

    # Encontrar arquivo mensal
    md = encontrar_arquivo_mensal(cliente, ano_mes, agencia_path)
    if not md:
        print(f"  ⚠️  Arquivo de Conteúdo Mensal {ano_mes} não encontrado — pulando")
        return True  # não é erro crítico, cliente pode não ter conteúdo nesse mês

    print(f"  📄 {md.name}")
    posts = parse_planejamento(md)
    if not posts:
        print(f"  ⚠️  Nenhum post encontrado no arquivo")
        return True

    # Encontrar pasta de entrega
    pasta_cliente = md.parent.parent  # sobe de 04_Estratégia para o cliente
    pasta_fixos, pasta_videos = encontrar_pasta_entrega(ano_mes, pasta_cliente)

    erros  = []
    avisos = []
    ok     = []

    # ── Verificar artes (Posts_Fixos/) ───────────────────────────────────────
    posts_com_arte = [p for p in posts if p['formato'] in ('Card', 'Carrossel')]

    if posts_com_arte:
        if not pasta_fixos or not pasta_fixos.exists():
            erros.append("Pasta Posts_Fixos/ não encontrada em 06_Entregas/")
        else:
            # Arquivos de imagem presentes
            arquivos_presentes = {
                f.name.lower(): f
                for f in pasta_fixos.iterdir()
                if f.suffix.lower() in EXT_IMAGEM and '(capa)' not in f.name.lower()
            }

            for post in posts_com_arte:
                prefixo = post['data'].strftime('%d-%m')

                # Procura imagem única ou slides
                encontrados = [n for n in arquivos_presentes if n.startswith(prefixo)]

                if not encontrados:
                    erros.append(
                        f"Arte não encontrada para {post['data'].strftime('%d/%m')} "
                        f"({post['formato']}: {post['titulo'][:50]})\n"
                        f"          → esperado: {prefixo}.jpg ou {prefixo}_1.jpg, {prefixo}_2.jpg..."
                    )
                else:
                    ok.append(f"Arte {post['data'].strftime('%d/%m')}: {', '.join(sorted(encontrados))}")

            # Arquivos sem post correspondente
            datas_esperadas = {p['data'].strftime('%d-%m') for p in posts_com_arte}
            for nome in arquivos_presentes:
                prefixo_arquivo = re.match(r'(\d{2}-\d{2})', nome)
                if prefixo_arquivo and prefixo_arquivo.group(1) not in datas_esperadas:
                    avisos.append(
                        f"Arquivo sem post no planejamento: {nome}\n"
                        f"          → data {prefixo_arquivo.group(1)} não existe no .md deste mês"
                    )

    # ── Verificar Reels (Videos/) ─────────────────────────────────────────────
    posts_reel = [p for p in posts if p['formato'] in ('Reels', 'Video')]

    if posts_reel:
        if not pasta_videos or not pasta_videos.exists():
            if any(p['reel_nome'] for p in posts_reel):
                erros.append("Pasta Videos/ não encontrada em 06_Entregas/")
        else:
            arquivos_video = {
                f.stem.lower(): f
                for f in pasta_videos.iterdir()
                if f.suffix.lower() in EXT_VIDEO and '(capa)' not in f.name.lower()
            }
            nomes_video_lower = {k: v for k, v in arquivos_video.items()}

            for post in posts_reel:
                if not post['reel_nome']:
                    erros.append(
                        f"Campo **Vídeo:** ausente para {post['data'].strftime('%d/%m')} "
                        f"({post['titulo'][:50]})\n"
                        f"          → adicionar no .md: **Vídeo:** REEL NN – Nome"
                    )
                    continue

                reel_lower = post['reel_nome'].lower()
                if reel_lower in nomes_video_lower:
                    ok.append(f"Reel {post['data'].strftime('%d/%m')}: {post['reel_nome']}")
                else:
                    # Tentar match parcial (ignora traço vs hífen)
                    reel_norm = reel_lower.replace('–', '-').replace('—', '-')
                    match = next(
                        (k for k in nomes_video_lower if k.replace('–', '-').replace('—', '-') == reel_norm),
                        None
                    )
                    if match:
                        avisos.append(
                            f"Reel {post['data'].strftime('%d/%m')}: nome ligeiramente diferente\n"
                            f"          → .md diz:    {post['reel_nome']}\n"
                            f"          → arquivo é:  {nomes_video_lower[match].name}"
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
                p['reel_nome'].lower()
                for p in posts_reel
                if p['reel_nome']
            }
            for nome_stem, f in arquivos_video.items():
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
    args = parser.parse_args()

    ano_mes = args.mes or date.today().strftime('%Y-%m')

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
        ok = validar_cliente(cliente, ano_mes, agencia)
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
