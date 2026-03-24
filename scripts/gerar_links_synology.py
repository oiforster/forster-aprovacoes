#!/usr/bin/env python3
"""
Forster Filmes — Gerador de Links de Download Synology
Autentica na API do DSM, cria links de compartilhamento públicos para
vídeos (.mov) e frames (Frames/) e salva em _synology.md na pasta Videos/.

Uso:
  python3 gerar_links_synology.py --cliente "Empório Essenza" --mes 2026-03
  python3 gerar_links_synology.py --cliente "Joele Lerípio" --mes 2026-03 --pontual
"""

import os
import re
import sys
import json
import argparse
import unicodedata
import urllib.parse
import subprocess
from pathlib import Path
from datetime import date

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────
# Credenciais lidas de scripts/synology_config.json (gitignored).
# Se o arquivo não existir, o script cria um template e encerra.

CONFIG_FILE = Path(__file__).parent / 'synology_config.json'

CONFIG_TEMPLATE = {
    "host_local":    "https://192.168.2.25:5001",
    "host_external": "https://forsterfilmes.synology.me:5001",
    "username":      "guest",
    "password":      "COLOQUE_A_SENHA_AQUI",
    "nas_base_path": "/Claude Cowork/Agência",
    "local_sync_name": "SynologyDrive-Agencia",
}


def carregar_config() -> dict:
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CONFIG_TEMPLATE, f, ensure_ascii=False, indent=2)
        print(f"\n  ⚙️  Arquivo de configuração criado em:")
        print(f"     {CONFIG_FILE}")
        print(f"\n  Edite o arquivo e preencha os campos:")
        print(f"    • password     → senha do usuário Synology")
        print(f"    • host_local   → IP local do NAS (ex: https://192.168.2.25:5001)")
        print(f"    • nas_base_path → path da pasta Agência no NAS")
        sys.exit(0)
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    if cfg.get('password') == 'COLOQUE_A_SENHA_AQUI':
        print("  ❌ Configure a senha em scripts/synology_config.json antes de rodar.")
        sys.exit(1)
    return cfg


# Carrega configuração na inicialização do módulo
_cfg             = carregar_config()
NAS_HOST_LOCAL    = _cfg['host_local']
NAS_HOST_EXTERNAL = _cfg['host_external']
NAS_USER          = _cfg['username']
NAS_PASS          = _cfg['password']
NAS_BASE_PATH     = _cfg['nas_base_path']
LOCAL_SYNC_NAME   = _cfg['local_sync_name']

# ─── UTILITÁRIOS ─────────────────────────────────────────────────────────────

def slugify(texto):
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.lower().replace(' ', '-')
    texto = re.sub(r'[^a-z0-9\-]', '', texto)
    return re.sub(r'-+', '-', texto).strip('-')


def local_to_nas(local_path: Path, local_agencia: Path) -> str:
    """Converte path local (Synology Drive) para path interno da NAS.
    Normaliza para NFC: macOS armazena nomes em NFD (decomposed),
    mas a API do DSM espera NFC (composed)."""
    rel = local_path.relative_to(local_agencia)
    nas = NAS_BASE_PATH + '/' + rel.as_posix()
    return unicodedata.normalize('NFC', nas)

# ─── API SYNOLOGY ─────────────────────────────────────────────────────────────

def api_call(host: str, endpoint: str, params: dict) -> dict:
    """Chama a API via curl (suporta HTTP/2 e ignora cert auto-assinado)."""
    url = f"{host}/webapi/{endpoint}?" + urllib.parse.urlencode(params)
    result = subprocess.run(
        ['curl', '-k', '-s', '--max-time', '30', url],
        capture_output=True, text=True, timeout=35
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"curl retornou código {result.returncode}")
    if not result.stdout.strip():
        raise RuntimeError("curl não retornou dados — verifique host e porta")
    return json.loads(result.stdout)


def auth(host: str) -> str:
    """Autentica e retorna SID (session ID)."""
    resp = api_call(host, "entry.cgi", {
        "api":     "SYNO.API.Auth",
        "version": "3",
        "method":  "login",
        "account": NAS_USER,
        "passwd":  NAS_PASS,
        "session": "FileStation",
        "format":  "sid",
    })
    if not resp.get("success"):
        raise RuntimeError(f"Auth falhou: {resp.get('error', resp)}")
    return resp["data"]["sid"]


def logout(host: str, sid: str):
    try:
        api_call(host, "entry.cgi", {
            "api":     "SYNO.API.Auth",
            "version": "1",
            "method":  "logout",
            "session": "FileStation",
            "_sid":    sid,
        })
    except Exception:
        pass


def _gofile_to_direto(url: str) -> str:
    """Converte URL gofile.me → URL de download direto no NAS.
    Ex: http://gofile.me/7f88o/xX1071kdj → https://HOST:5001/fbdownload/xX1071kdj?bktype=sharing
    """
    if 'gofile.me' not in url:
        return url
    codigo = url.rstrip('/').split('/')[-1]
    host = NAS_HOST_EXTERNAL.rstrip('/')
    return f"{host}/fbdownload/{codigo}?bktype=sharing"


def criar_link(host: str, sid: str, nas_path: str) -> str:
    """Cria link de compartilhamento e retorna URL de download direto."""
    resp = api_call(host, "entry.cgi", {
        "api":            "SYNO.FileStation.Sharing",
        "version":        "3",
        "method":         "create",
        "path":           json.dumps([nas_path]),
        "is_writable":    "false",
        "date_expired":   "",
        "date_available": "",
        "_sid":           sid,
    })
    if not resp.get("success"):
        code = resp.get("error", {}).get("code", "?")
        raise RuntimeError(f"Erro ao criar link (código {code}) para: {nas_path}")
    url = resp["data"]["links"][0]["url"]
    return _gofile_to_direto(url)

# ─── _synology.md ─────────────────────────────────────────────────────────────

def ler_synology_md(pasta: Path) -> dict:
    """Lê _synology.md → dict { 'chave': 'https://...' }"""
    arquivo = pasta / '_synology.md'
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


def escrever_synology_md(pasta: Path, links: dict):
    """Escreve _synology.md preservando a ordem de inserção."""
    arquivo = pasta / '_synology.md'
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write('# Links de download — Synology — gerado automaticamente\n\n')

        # Vídeos primeiro
        for chave, url in links.items():
            if chave.upper().startswith('REEL'):
                f.write(f"{chave}: {url}\n")

        # Depois frames
        separador_escrito = False
        for chave, url in links.items():
            if chave.upper().startswith('FRAMES_FOLDER') or chave.upper().startswith('FRAME_'):
                if not separador_escrito:
                    f.write('\n')
                    separador_escrito = True
                f.write(f"{chave}: {url}\n")

# ─── BUSCA DE PASTAS ─────────────────────────────────────────────────────────

def encontrar_agencia() -> Path:
    cloud = Path.home() / 'Library' / 'CloudStorage'
    synology = cloud / LOCAL_SYNC_NAME
    if synology.exists():
        return synology
    raise FileNotFoundError(
        f"Pasta '{LOCAL_SYNC_NAME}' não encontrada em CloudStorage. "
        "Verifique se o Synology Drive está instalado e sincronizado."
    )


def encontrar_pasta_cliente(cliente: str, agencia: Path, pontual: bool = False):
    ordem = ['Clientes Pontuais', 'Clientes Recorrentes'] if pontual \
            else ['Clientes Recorrentes', 'Clientes Pontuais']
    for subfolder in ordem:
        base = agencia / '_Clientes' / subfolder
        if not base.exists():
            continue
        pasta = base / cliente
        if pasta.exists():
            return pasta
        for entry in base.iterdir():
            if entry.is_dir() and slugify(entry.name) == slugify(cliente):
                return entry
    return None


def _tem_reels(pasta: Path) -> bool:
    ext = {'.mov', '.mp4', '.m4v'}
    try:
        return any(
            f.suffix.lower() in ext
            and '(capa)' not in f.name.lower()
            and re.match(r'^REEL\s+\d+', f.name, re.IGNORECASE)
            for f in pasta.iterdir() if f.is_file()
        )
    except PermissionError:
        return False


def encontrar_pasta_videos(pasta_cliente: Path, ano_mes: str):
    entregas = pasta_cliente / '06_Entregas'
    if entregas.exists():
        for entry in sorted(entregas.iterdir()):
            if entry.is_dir() and entry.name.startswith(ano_mes):
                v = entry / 'Videos'
                if v.exists() and _tem_reels(v):
                    return v
    # Fallback: YYYY-MM* na raiz do cliente
    for entry in sorted(pasta_cliente.iterdir()):
        if entry.is_dir() and entry.name.startswith(ano_mes):
            for dirpath, _, _ in os.walk(entry):
                p = Path(dirpath)
                if _tem_reels(p):
                    return p
    return None


def listar_videos(pasta: Path) -> list:
    ext = {'.mov', '.mp4', '.m4v'}
    return sorted([
        f for f in pasta.iterdir()
        if f.suffix.lower() in ext
        and '(capa)' not in f.name.lower()
        and re.match(r'^REEL\s+\d+', f.name, re.IGNORECASE)
    ])


def _encontrar_pasta_frames(pasta_videos: Path):
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


def listar_frames(pasta_videos: Path) -> tuple:
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

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Gera links Synology para vídeos e frames de entrega.'
    )
    parser.add_argument('--cliente',  required=True,
                        help='Nome do cliente (ex: "Empório Essenza")')
    parser.add_argument('--mes',      default=None,
                        help='Mês no formato YYYY-MM (padrão: mês atual)')
    parser.add_argument('--pontual',  action='store_true', default=False,
                        help='Busca em Clientes Pontuais antes de Recorrentes')
    args = parser.parse_args()

    cliente = args.cliente
    ano_mes = args.mes or date.today().strftime('%Y-%m')

    print(f"\n🔗  Gerador de Links Synology — Forster Filmes")
    print(f"    Cliente : {cliente}")
    print(f"    Mês     : {ano_mes}\n")

    # 1. Encontrar estrutura de pastas
    try:
        agencia = encontrar_agencia()
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
        sys.exit(1)

    pasta_cliente = encontrar_pasta_cliente(cliente, agencia, args.pontual)
    if not pasta_cliente:
        print(f"  ❌ Cliente '{cliente}' não encontrado.")
        sys.exit(1)

    pasta_videos = encontrar_pasta_videos(pasta_cliente, ano_mes)
    if not pasta_videos:
        print(f"  ❌ Nenhuma pasta de vídeos encontrada para {cliente} / {ano_mes}")
        sys.exit(1)

    videos = listar_videos(pasta_videos)
    frames, pasta_frames = listar_frames(pasta_videos)

    if not videos:
        print(f"  ❌ Nenhum arquivo REEL encontrado em {pasta_videos}")
        sys.exit(1)

    print(f"  📂 Pasta : {pasta_videos}")
    print(f"  📹 Vídeos: {len(videos)}  |  🖼  Frames: {len(frames)}\n")

    # 2. Ler links já existentes e migrar gofile.me → download direto
    links = ler_synology_md(pasta_videos)
    migrados = sum(1 for url in links.values() if 'gofile.me' in url)
    if migrados > 0:
        links = {k: _gofile_to_direto(v) for k, v in links.items()}
        escrever_synology_md(pasta_videos, links)
        print(f"  🔄 {migrados} links gofile.me migrados para download direto\n")
    novos = 0

    # 3. Conectar ao Synology (local primeiro, DDNS como fallback)
    host = NAS_HOST_LOCAL
    sid  = None
    print("  🔌 Conectando ao Synology (rede local)...")
    try:
        sid = auth(host)
        print(f"  ✅ Conectado via rede local\n")
    except Exception as e_local:
        print(f"  ⚠️  Falhou ({e_local})")
        print("  🌐 Tentando via DDNS externo...")
        try:
            host = NAS_HOST_EXTERNAL
            sid  = auth(host)
            print(f"  ✅ Conectado via DDNS\n")
        except Exception as e_ext:
            print(f"  ❌ Não foi possível conectar: {e_ext}")
            print("\n  Verifique:")
            print("  • Synology está ligado e acessível")
            print(f"  • Usuário '{NAS_USER}' tem permissão de acesso no File Station")
            print("  • Porta 5001 está aberta no roteador (para DDNS)")
            sys.exit(1)

    try:
        # 4. Links de vídeos
        print("  📹 Criando links de vídeos:")
        for v in videos:
            chave = v.stem
            if chave in links:
                print(f"      ↩  {chave} (já existe)")
                continue
            try:
                nas_path = local_to_nas(v, agencia)
                url = criar_link(host, sid, nas_path)
                links[chave] = url
                novos += 1
                print(f"      ✅ {chave}")
            except RuntimeError as e:
                print(f"      ❌ {chave}: {e}")

        # 5. Links de frames individuais + pasta
        if frames:
            print(f"\n  🖼  Criando links de frames ({len(frames)}):")

            # Pasta Frames/ inteira (para "Baixar todos")
            if 'FRAMES_FOLDER' not in links:
                try:
                    nas_folder = local_to_nas(pasta_frames, agencia)
                    url_folder = criar_link(host, sid, nas_folder)
                    links['FRAMES_FOLDER'] = url_folder
                    novos += 1
                    print(f"      📁 Pasta completa: link criado")
                except RuntimeError as e:
                    print(f"      ❌ Pasta Frames: {e}")

            # Cada frame individualmente
            # Chave usa path relativo à pasta frames (suporta subpastas por REEL)
            for f in frames:
                rel = f.relative_to(pasta_frames).as_posix()
                chave = f'FRAME_{rel}'
                display = rel if '/' in rel else f.name
                if chave in links:
                    print(f"      ↩  {display} (já existe)")
                    continue
                try:
                    nas_path = local_to_nas(f, agencia)
                    url = criar_link(host, sid, nas_path)
                    links[chave] = url
                    novos += 1
                    print(f"      ✅ {display}")
                except RuntimeError as e:
                    print(f"      ❌ {display}: {e}")
        else:
            print(f"\n  ℹ️  Pasta Frames/ não encontrada (ou vazia) — pulando frames")

    finally:
        logout(host, sid)

    # 6. Salvar _synology.md
    if novos > 0:
        escrever_synology_md(pasta_videos, links)
        print(f"\n  💾 _synology.md atualizado com {novos} novo(s) link(s)")
        print(f"     {pasta_videos / '_synology.md'}")
    else:
        print(f"\n  ℹ️  Todos os links já existem. Nada a atualizar.")

    print()


if __name__ == '__main__':
    main()
