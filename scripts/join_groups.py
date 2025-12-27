#!/usr/bin/env python3
"""
Script para entrar em grupos do WhatsApp via Evolution API.

Uso:
    uv run python scripts/join_groups.py [--limit N] [--delay N]

Argumentos:
    --limit N   Máximo de grupos para processar nesta execução (default: 50)
    --delay N   Delay mínimo entre entradas em segundos (default: 30)

O script:
1. Lê os CSVs de múltiplos diretórios
2. Busca grupos que já participa
3. Entra apenas nos novos (respeitando limite diário)
4. Salva log de resultados

IMPORTANTE: Para evitar ban do WhatsApp, o script:
- Limita entradas por execução (default: 50)
- Usa delay aleatório entre 30-60s
- Rastreia quantos grupos entrou hoje
"""

import argparse
import asyncio
import csv
import json
import os
import random
import sys
from datetime import datetime, date
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Configurações
EVOLUTION_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
INSTANCE = os.getenv("EVOLUTION_INSTANCE", "julia")

# Limites de segurança (conta antiga > 1 ano)
DEFAULT_LIMIT_POR_EXECUCAO = 50  # Máximo por execução
LIMITE_DIARIO = 70  # Máximo por dia (conta antiga)
DEFAULT_DELAY_MIN = 10  # Segundos mínimo entre entradas
DELAY_MAX = 10  # Segundos máximo entre entradas

# Arquivo consolidado de grupos (único)
BASE_DIR = Path(__file__).parent.parent
CSV_FILE = BASE_DIR / "data" / "grupos_zap" / "grupos_consolidado.csv"
LOG_FILE = BASE_DIR / "data" / "grupos_zap" / "join_log.json"


class EvolutionGroupClient:
    """Cliente para operações de grupo na Evolution API."""

    def __init__(self):
        self.base_url = EVOLUTION_URL.rstrip("/")
        self.api_key = EVOLUTION_API_KEY
        self.instance = INSTANCE
        self.headers = {"apikey": self.api_key}

    async def listar_grupos(self) -> list[dict]:
        """Lista todos os grupos que a instância participa."""
        url = f"{self.base_url}/group/fetchAllGroups/{self.instance}?getParticipants=false"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=self.headers, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"Erro ao listar grupos: {e}")
                return []

    async def buscar_info_grupo(self, invite_code: str) -> dict | None:
        """Busca informações de um grupo pelo invite code."""
        url = f"{self.base_url}/group/inviteInfo/{self.instance}"
        params = {"inviteCode": invite_code}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=self.headers, params=params, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"Erro ao buscar info do grupo: {e}")
                return None

    async def entrar_grupo(self, invite_code: str) -> tuple[bool, str]:
        """
        Entra em um grupo via invite code.

        Returns:
            (sucesso, mensagem)
        """
        url = f"{self.base_url}/group/acceptInviteCode/{self.instance}"
        params = {"inviteCode": invite_code}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=self.headers, params=params, timeout=30)

                if resp.status_code == 200:
                    return True, "Solicitação enviada"
                elif resp.status_code == 404 and "already-exist" in resp.text:
                    return False, "Já solicitou entrada (aguardando aprovação)"
                elif resp.status_code == 409:
                    return False, "Já é membro do grupo"
                else:
                    return False, f"Erro {resp.status_code}: {resp.text[:100]}"

            except httpx.TimeoutException:
                return False, "Timeout na requisição"
            except Exception as e:
                return False, f"Erro: {str(e)}"


def carregar_grupos_csv() -> list[dict]:
    """Carrega grupos do CSV consolidado."""
    grupos = []

    if not CSV_FILE.exists():
        print(f"  ❌ Arquivo não encontrado: {CSV_FILE}")
        return grupos

    print(f"  Lendo {CSV_FILE.name}...")
    try:
        with open(CSV_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                invite_code = row.get("invite_code", "")
                if invite_code:
                    grupos.append({
                        "nome": row.get("name", "Sem nome"),
                        "invite_code": invite_code,
                        "url": row.get("url", ""),
                        "estado": row.get("state", ""),
                        "categoria": row.get("category", ""),
                    })
    except Exception as e:
        print(f"  Erro ao ler {CSV_FILE.name}: {e}")

    return grupos


def carregar_log_anterior() -> dict:
    """Carrega log de execuções anteriores."""
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return {"entradas": {}, "ultima_execucao": None, "entradas_hoje": {}}


def salvar_log(log: dict):
    """Salva log de execução."""
    log["ultima_execucao"] = datetime.now().isoformat()
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def contar_entradas_hoje(log: dict) -> int:
    """Conta quantas entradas com sucesso foram feitas hoje."""
    hoje = date.today().isoformat()

    # Inicializar se não existe
    if "entradas_por_dia" not in log:
        log["entradas_por_dia"] = {}

    return log["entradas_por_dia"].get(hoje, 0)


def registrar_entrada_hoje(log: dict):
    """Incrementa contador de entradas de hoje."""
    hoje = date.today().isoformat()

    if "entradas_por_dia" not in log:
        log["entradas_por_dia"] = {}

    log["entradas_por_dia"][hoje] = log["entradas_por_dia"].get(hoje, 0) + 1


async def main():
    """Executa o script."""
    # Parse argumentos
    parser = argparse.ArgumentParser(description="Entrar em grupos do WhatsApp")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT_POR_EXECUCAO,
                        help=f"Máximo de grupos por execução (default: {DEFAULT_LIMIT_POR_EXECUCAO})")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY_MIN,
                        help=f"Delay mínimo entre entradas em segundos (default: {DEFAULT_DELAY_MIN})")
    args = parser.parse_args()

    print("=" * 60)
    print("SCRIPT DE ENTRADA EM GRUPOS WHATSAPP")
    print("=" * 60)

    # Validar configuração
    if not EVOLUTION_API_KEY:
        print("ERRO: EVOLUTION_API_KEY não configurada no .env")
        sys.exit(1)

    print(f"\nEvolution URL: {EVOLUTION_URL}")
    print(f"Instância: {INSTANCE}")
    print(f"\nLimites de segurança:")
    print(f"  - Máximo esta execução: {args.limit}")
    print(f"  - Máximo diário: {LIMITE_DIARIO}")
    print(f"  - Delay entre entradas: {args.delay}-{DELAY_MAX}s (aleatório)")

    client = EvolutionGroupClient()

    # 1. Carregar log e verificar limite diário
    log = carregar_log_anterior()
    entradas_hoje = contar_entradas_hoje(log)

    print(f"\n[0/5] Verificando limite diário...")
    print(f"      Entradas hoje: {entradas_hoje}/{LIMITE_DIARIO}")

    if entradas_hoje >= LIMITE_DIARIO:
        print(f"\n⚠️  LIMITE DIÁRIO ATINGIDO ({LIMITE_DIARIO} grupos)")
        print("    Aguarde até amanhã para continuar.")
        return

    grupos_restantes_hoje = LIMITE_DIARIO - entradas_hoje
    limite_efetivo = min(args.limit, grupos_restantes_hoje)
    print(f"      Podem entrar hoje: {grupos_restantes_hoje}")

    # 2. Carregar grupos dos CSVs
    print("\n[1/5] Carregando grupos dos CSVs...")
    grupos_csv = carregar_grupos_csv()
    print(f"      Total único: {len(grupos_csv)} grupos")

    if not grupos_csv:
        print("Nenhum grupo encontrado nos CSVs.")
        return

    # 3. Buscar grupos que já participa
    print("\n[2/5] Buscando grupos que já participa...")
    grupos_atuais = await client.listar_grupos()
    print(f"      Participa de: {len(grupos_atuais)} grupos")

    # 4. Filtrar grupos novos
    print("\n[3/5] Identificando grupos novos...")
    grupos_novos = []

    for grupo in grupos_csv:
        invite_code = grupo["invite_code"]

        # Pular se já tentou entrar antes (sucesso, aguardando, ou não retentar)
        if invite_code in log["entradas"]:
            entrada = log["entradas"][invite_code]
            if (entrada.get("sucesso") or
                entrada.get("nao_retentar") or
                "aguardando" in entrada.get("mensagem", "").lower()):
                continue

        grupos_novos.append(grupo)

    print(f"      Novos para entrar: {len(grupos_novos)} grupos")

    if not grupos_novos:
        print("\n✅ Nenhum grupo novo para entrar!")
        return

    # 5. Aplicar limite
    grupos_a_processar = grupos_novos[:limite_efetivo]
    grupos_restantes = len(grupos_novos) - len(grupos_a_processar)

    print(f"\n[4/5] Aplicando limites de segurança...")
    print(f"      Processando: {len(grupos_a_processar)} grupos")
    if grupos_restantes > 0:
        print(f"      Restantes (próxima execução): {grupos_restantes} grupos")

    # 6. Entrar nos grupos
    print("\n[5/5] Entrando nos grupos...")
    print("-" * 60)

    sucesso = 0
    ja_solicitado = 0
    falha = 0

    for i, grupo in enumerate(grupos_a_processar, 1):
        nome = grupo["nome"]
        invite_code = grupo["invite_code"]
        categoria = grupo["categoria"]

        print(f"\n[{i}/{len(grupos_a_processar)}] {nome[:50]}")
        if categoria:
            print(f"      Categoria: {categoria}")
        print(f"      Código: {invite_code[:15]}...")

        ok, msg = await client.entrar_grupo(invite_code)

        # Registrar no log
        log["entradas"][invite_code] = {
            "nome": nome,
            "sucesso": ok,
            "mensagem": msg,
            "data": datetime.now().isoformat(),
        }

        if ok:
            print(f"      ✅ {msg}")
            sucesso += 1
            registrar_entrada_hoje(log)
        elif "aguardando" in msg.lower():
            print(f"      ⏳ {msg}")
            ja_solicitado += 1
        else:
            print(f"      ❌ {msg}")
            falha += 1

        # Salvar log após cada tentativa
        salvar_log(log)

        # Delay aleatório entre grupos (exceto no último)
        if i < len(grupos_a_processar):
            delay = random.randint(args.delay, DELAY_MAX)
            print(f"      ⏱️  Aguardando {delay}s...")
            await asyncio.sleep(delay)

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(f"Total processados: {len(grupos_a_processar)}")
    print(f"  ✅ Solicitação enviada: {sucesso}")
    print(f"  ⏳ Já havia solicitado: {ja_solicitado}")
    print(f"  ❌ Erro: {falha}")
    print(f"\nEntradas hoje: {contar_entradas_hoje(log)}/{LIMITE_DIARIO}")

    if grupos_restantes > 0:
        print(f"\n⚠️  Restam {grupos_restantes} grupos para próximas execuções.")
        print("   Execute novamente mais tarde ou amanhã.")

    print(f"\nLog salvo em: {LOG_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
