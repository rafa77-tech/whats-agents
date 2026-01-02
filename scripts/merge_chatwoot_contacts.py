#!/usr/bin/env python3
"""
Script para mesclar contatos duplicados no Chatwoot.

Quando mensagens chegam via LID (WhatsApp Linked ID), o Chatwoot pode
criar contatos duplicados - um com o LID e outro com o telefone real.

Este script:
1. Busca contatos que parecem duplicados
2. Identifica qual tem telefone real vs LID
3. Faz merge mantendo o contato com telefone real

Uso:
    python scripts/merge_chatwoot_contacts.py --dry-run    # Simular
    python scripts/merge_chatwoot_contacts.py              # Executar
"""
import argparse
import httpx
import asyncio
import re
import os
from typing import Optional


# Configuracao
CHATWOOT_URL = os.getenv("CHATWOOT_URL", "").rstrip("/")
CHATWOOT_API_KEY = os.getenv("CHATWOOT_API_KEY", "")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "1")


def is_lid_format(identifier: str) -> bool:
    """Verifica se o identificador parece ser um LID."""
    if not identifier:
        return False
    # LID tipicamente: numeros longos sem formato de telefone
    # Telefone BR: 55 + DDD(2) + numero(8-9) = 12-13 digitos
    # LID: geralmente 15+ digitos sem padrao de pais
    clean = re.sub(r'\D', '', identifier)

    # Se nao comeca com 55 (Brasil) e tem mais de 13 digitos, provavelmente LID
    if len(clean) > 13 and not clean.startswith('55'):
        return True

    # Se o identifier original tem @ (como @lid), e definitivamente LID
    if '@lid' in identifier.lower():
        return True

    return False


def is_valid_phone(phone: str) -> bool:
    """Verifica se e um telefone valido."""
    if not phone:
        return False
    clean = re.sub(r'\D', '', phone)
    # Telefone BR valido: 12-13 digitos comecando com 55
    return len(clean) >= 12 and len(clean) <= 13 and clean.startswith('55')


async def get_headers():
    return {
        "api_access_token": CHATWOOT_API_KEY,
        "Content-Type": "application/json"
    }


async def list_contacts(page: int = 1) -> list:
    """Lista contatos do Chatwoot."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts?page={page}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=await get_headers())
        response.raise_for_status()
        data = response.json()
        return data.get("payload", [])


async def search_contacts(query: str) -> list:
    """Busca contatos por telefone ou nome."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts/search"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params={"q": query}, headers=await get_headers())
        response.raise_for_status()
        data = response.json()
        return data.get("payload", [])


async def merge_contacts(base_contact_id: int, mergee_contact_id: int) -> bool:
    """
    Faz merge de dois contatos.

    O base_contact_id sobrevive e recebe tudo do mergee_contact_id.
    O mergee_contact_id e deletado apos o merge.
    """
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/actions/contact_merge"

    payload = {
        "base_contact_id": base_contact_id,
        "mergee_contact_id": mergee_contact_id
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=await get_headers())
        if response.status_code in [200, 201, 204]:
            return True
        else:
            print(f"  [ERRO] Status {response.status_code}: {response.text}")
            return False


async def find_duplicates() -> list:
    """
    Encontra pares de contatos duplicados.

    Retorna lista de tuplas: (contato_telefone_real, contato_lid)
    """
    duplicates = []

    print("Buscando contatos...")

    # Buscar todas as paginas de contatos
    all_contacts = []
    page = 1
    while True:
        contacts = await list_contacts(page)
        if not contacts:
            break
        all_contacts.extend(contacts)
        page += 1
        if page > 50:  # Limite de seguranca
            break

    print(f"Total de contatos: {len(all_contacts)}")

    # Agrupar por nome para encontrar duplicados
    by_name = {}
    for contact in all_contacts:
        name = contact.get("name", "").lower().strip()
        if name:
            if name not in by_name:
                by_name[name] = []
            by_name[name].append(contact)

    # Encontrar pares onde um tem telefone real e outro tem LID
    for name, contacts in by_name.items():
        if len(contacts) < 2:
            continue

        phones_real = []
        lids = []

        for c in contacts:
            phone = c.get("phone_number", "") or ""
            identifier = c.get("identifier", "") or ""

            # Verificar se e LID
            if is_lid_format(identifier) or is_lid_format(phone):
                lids.append(c)
            elif is_valid_phone(phone) or is_valid_phone(identifier):
                phones_real.append(c)

        # Se temos um com telefone real e um com LID, e candidato a merge
        if phones_real and lids:
            for real in phones_real:
                for lid in lids:
                    duplicates.append((real, lid))

    return duplicates


async def main(dry_run: bool = True):
    """Executa o merge de contatos duplicados."""

    if not CHATWOOT_URL or not CHATWOOT_API_KEY:
        print("ERRO: Configure CHATWOOT_URL e CHATWOOT_API_KEY")
        return

    print(f"Chatwoot URL: {CHATWOOT_URL}")
    print(f"Account ID: {CHATWOOT_ACCOUNT_ID}")
    print(f"Modo: {'DRY-RUN (simulacao)' if dry_run else 'EXECUCAO REAL'}")
    print("-" * 50)

    duplicates = await find_duplicates()

    if not duplicates:
        print("\nNenhum contato duplicado encontrado!")
        return

    print(f"\nEncontrados {len(duplicates)} pares de contatos duplicados:\n")

    for i, (real, lid) in enumerate(duplicates, 1):
        real_phone = real.get("phone_number", "") or real.get("identifier", "")
        lid_phone = lid.get("phone_number", "") or lid.get("identifier", "")

        print(f"{i}. {real.get('name', 'Sem nome')}")
        print(f"   BASE (manter):  ID={real['id']}, phone={real_phone}")
        print(f"   MERGEE (deletar): ID={lid['id']}, phone={lid_phone}")

        if not dry_run:
            success = await merge_contacts(real["id"], lid["id"])
            if success:
                print(f"   [OK] Merge realizado com sucesso!")
            else:
                print(f"   [FALHA] Erro ao fazer merge")
        print()

    if dry_run:
        print("\n[DRY-RUN] Nenhuma alteracao foi feita.")
        print("Para executar o merge, rode sem --dry-run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge de contatos duplicados no Chatwoot")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem fazer alteracoes")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run))
