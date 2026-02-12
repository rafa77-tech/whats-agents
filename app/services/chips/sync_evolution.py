"""
Sincronização de Chips com Evolution API.

Responsável por manter a tabela chips atualizada com o estado real das instâncias
na Evolution API. Este serviço é executado periodicamente pelo scheduler.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def listar_instancias_evolution() -> list[dict]:
    """
    Lista todas as instâncias na Evolution API.

    Returns:
        Lista de instâncias com estado de conexão.
    """
    try:
        url = f"{settings.EVOLUTION_API_URL}/instance/fetchInstances"
        headers = {"apikey": settings.EVOLUTION_API_KEY}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                # Evolution retorna lista de instâncias
                if isinstance(data, list):
                    return data
                # Ou pode retornar em formato diferente
                return data.get("instances", data.get("data", []))
            else:
                logger.error(f"Erro ao listar instâncias Evolution: {response.status_code}")
                return []

    except httpx.TimeoutException:
        logger.error("Timeout ao listar instâncias Evolution")
        return []
    except Exception as e:
        logger.error(f"Erro ao listar instâncias Evolution: {e}")
        return []


async def buscar_estado_instancia(instance_name: str) -> Optional[dict]:
    """
    Busca o estado de conexão de uma instância específica.

    Args:
        instance_name: Nome da instância na Evolution API.

    Returns:
        Dict com estado da instância ou None se erro.
    """
    try:
        url = f"{settings.EVOLUTION_API_URL}/instance/connectionState/{instance_name}"
        headers = {"apikey": settings.EVOLUTION_API_KEY}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erro ao buscar estado de {instance_name}: {response.status_code}")
                return None

    except httpx.TimeoutException:
        logger.warning(f"Timeout ao buscar estado de {instance_name}")
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar estado de {instance_name}: {e}")
        return None


async def sincronizar_chips_com_evolution() -> dict:
    """
    Sincroniza a tabela chips com o estado atual da Evolution API.

    Este serviço:
    1. Lista todas as instâncias na Evolution API
    2. Para cada instância, verifica se existe na tabela chips
    3. Atualiza o status de conexão das instâncias existentes
    4. Opcionalmente cria novas entradas para instâncias desconhecidas

    Returns:
        Dict com estatísticas da sincronização.
    """
    stats = {
        "instancias_evolution": 0,
        "chips_atualizados": 0,
        "chips_criados": 0,
        "chips_desconectados": 0,
        "chips_conectados": 0,
        "erros": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Buscar instâncias na Evolution
    instancias = await listar_instancias_evolution()
    stats["instancias_evolution"] = len(instancias)

    if not instancias:
        logger.warning("Nenhuma instância encontrada na Evolution API")
        return stats

    # 2. Criar mapa de instâncias por nome
    instancias_map = {}
    for inst in instancias:
        # Evolution API v2 retorna formato diferente
        # Campos: name, connectionStatus (open/close), ownerJid
        name = (
            inst.get("name")
            or inst.get("instanceName")
            or inst.get("instance", {}).get("instanceName")
        )
        # connectionStatus pode ser "open" ou "close"
        state = (
            inst.get("connectionStatus")
            or inst.get("state")
            or inst.get("instance", {}).get("state", "unknown")
        )
        phone = (
            inst.get("ownerJid", "").split("@")[0] if inst.get("ownerJid") else inst.get("number")
        )

        if name:
            instancias_map[name] = {
                "name": name,
                "state": state,
                "phone": phone,
                "connected": state == "open",
            }

    # 3. Buscar chips existentes no banco (apenas provider evolution)
    try:
        response = (
            supabase.table("chips")
            .select("id, instance_name, status, evolution_connected, provider")
            .neq("provider", "z-api")
            .execute()
        )
        chips_existentes = {chip["instance_name"]: chip for chip in response.data}
    except Exception as e:
        logger.error(f"Erro ao buscar chips existentes: {e}")
        stats["erros"] += 1
        return stats

    # 4. Atualizar chips existentes
    for instance_name, inst_data in instancias_map.items():
        try:
            is_connected = inst_data["connected"]

            if instance_name in chips_existentes:
                # Chip existe, atualizar status
                chip = chips_existentes[instance_name]
                chip.get("evolution_connected", False)

                # Determinar novo status baseado na conexão
                new_status = chip["status"]
                if is_connected and chip["status"] == "pending":
                    # Chip conectou pela primeira vez
                    new_status = "warming"
                elif not is_connected and chip["status"] in ("active", "warming", "ready"):
                    # Chip desconectou
                    new_status = "pending"

                # Atualizar no banco
                update_data = {
                    "evolution_connected": is_connected,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                if new_status != chip["status"]:
                    update_data["status"] = new_status

                supabase.table("chips").update(update_data).eq("id", chip["id"]).execute()

                stats["chips_atualizados"] += 1
                if is_connected:
                    stats["chips_conectados"] += 1
                else:
                    stats["chips_desconectados"] += 1

            else:
                # Chip não existe, criar novo
                phone = inst_data.get("phone") or f"unknown_{instance_name}"
                new_chip = {
                    "telefone": phone,
                    "instance_name": instance_name,
                    "evolution_connected": is_connected,
                    "status": "warming" if is_connected else "pending",
                    "fase_warmup": "repouso",
                    "trust_score": 50,
                    "trust_level": "amarelo",
                }

                supabase.table("chips").insert(new_chip).execute()
                stats["chips_criados"] += 1
                logger.info(f"Novo chip criado: {instance_name}")

        except Exception as e:
            logger.error(f"Erro ao processar instância {instance_name}: {e}")
            stats["erros"] += 1

    # 5. Marcar chips sem instância como desconectados
    for instance_name, chip in chips_existentes.items():
        if instance_name not in instancias_map:
            try:
                if chip.get("evolution_connected", False):
                    supabase.table("chips").update(
                        {
                            "evolution_connected": False,
                            "status": "pending"
                            if chip["status"] in ("active", "warming", "ready")
                            else chip["status"],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("id", chip["id"]).execute()
                    stats["chips_desconectados"] += 1
                    logger.warning(
                        f"Chip {instance_name} não encontrado na Evolution, marcado como desconectado"
                    )
            except Exception as e:
                logger.error(f"Erro ao marcar chip {instance_name} como desconectado: {e}")
                stats["erros"] += 1

    logger.info(
        f"Sync concluído: {stats['chips_atualizados']} atualizados, "
        f"{stats['chips_criados']} criados, "
        f"{stats['chips_conectados']} conectados, "
        f"{stats['chips_desconectados']} desconectados"
    )

    return stats


async def atualizar_metricas_chip(chip_id: str, metricas: dict) -> bool:
    """
    Atualiza métricas de um chip específico.

    Args:
        chip_id: ID do chip.
        metricas: Dict com métricas a atualizar.

    Returns:
        True se atualizado com sucesso.
    """
    try:
        allowed_fields = {
            "msgs_enviadas_hoje",
            "msgs_recebidas_hoje",
            "msgs_enviadas_total",
            "msgs_recebidas_total",
            "erros_ultimas_24h",
            "taxa_resposta",
            "taxa_delivery",
            "taxa_block",
        }

        update_data = {k: v for k, v in metricas.items() if k in allowed_fields}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        supabase.table("chips").update(update_data).eq("id", chip_id).execute()
        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar métricas do chip {chip_id}: {e}")
        return False
