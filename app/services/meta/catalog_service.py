"""
Meta Catalog/Commerce Service.

Sprint 68 — Epic 68.4: WhatsApp Catalog.
Sprint 72: v2 — push real via Graph API POST /{catalog_id}/items_batch.
Maps vagas (shifts) to WhatsApp catalog products.
"""

import logging
from typing import Optional, List

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Batch size for Graph API items_batch endpoint (max 20 per request)
_GRAPH_API_BATCH_SIZE = 20


class MetaCatalogService:
    """
    Serviço de catálogo WhatsApp para vagas médicas.

    Mapeia vagas como "produtos" no catálogo WhatsApp,
    permitindo envio de product messages e product lists.
    """

    def mapear_vaga_para_produto(
        self,
        vaga: dict,
        hospital: Optional[dict] = None,
        especialidade: Optional[dict] = None,
    ) -> dict:
        """
        Mapeia uma vaga para formato de produto do catálogo.

        Args:
            vaga: Dict com dados da vaga
            hospital: Dict com dados do hospital
            especialidade: Dict com dados da especialidade

        Returns:
            Dict no formato de produto Meta
        """
        vaga_id = str(vaga.get("id", ""))
        product_retailer_id = f"vaga_{vaga_id[:8]}"

        hospital_nome = "Hospital"
        if hospital:
            hospital_nome = hospital.get("nome", "Hospital")
        elif vaga.get("hospital_nome"):
            hospital_nome = vaga["hospital_nome"]

        esp_nome = ""
        if especialidade:
            esp_nome = especialidade.get("nome", "")
        elif vaga.get("especialidade_nome"):
            esp_nome = vaga["especialidade_nome"]

        name = f"Plantão {esp_nome} - {hospital_nome}".strip(" -")

        valor = vaga.get("valor", 0)
        price_milliunits = int(float(valor) * 1000) if valor else 0

        return {
            "product_retailer_id": product_retailer_id,
            "name": name[:150],  # Max 150 chars
            "description": self._construir_descricao_produto(vaga),
            "price_milliunits": price_milliunits,
            "currency": "BRL",
            "availability": "in stock" if vaga.get("status") == "aberta" else "out of stock",
            "vaga_id": vaga_id,
        }

    def _construir_descricao_produto(self, vaga: dict) -> str:
        """Constrói descrição do produto a partir da vaga."""
        partes = []

        if vaga.get("data"):
            partes.append(f"Data: {vaga['data']}")
        if vaga.get("horario"):
            partes.append(f"Horário: {vaga['horario']}")
        if vaga.get("periodo"):
            partes.append(f"Período: {vaga['periodo']}")
        if vaga.get("setor"):
            partes.append(f"Setor: {vaga['setor']}")

        return " | ".join(partes) if partes else "Plantão médico disponível"

    async def sincronizar_vagas_catalogo(
        self,
        waba_id: str,
        catalog_id: str,
    ) -> dict:
        """
        Sincroniza vagas abertas como produtos no catálogo.

        v2 (Sprint 72): Além de salvar localmente, faz push via Graph API
        POST /{catalog_id}/items_batch.

        Args:
            waba_id: WABA ID
            catalog_id: ID do catálogo Meta

        Returns:
            Dict com resultado da sincronização
        """
        if not settings.META_CATALOG_SYNC_ENABLED:
            return {"success": False, "error": "Sincronização de catálogo desabilitada"}

        try:
            # Buscar vagas abertas
            vagas_resp = (
                supabase.table("vagas")
                .select("*, hospitais(nome), especialidades(nome)")
                .eq("status", "aberta")
                .limit(100)
                .execute()
            )
            vagas = vagas_resp.data or []

            synced_local = 0
            produtos_para_push = []

            for vaga in vagas:
                hospital = vaga.get("hospitais")
                especialidade = vaga.get("especialidades")
                produto = self.mapear_vaga_para_produto(vaga, hospital, especialidade)

                try:
                    supabase.table("meta_catalog_products").upsert(
                        {
                            "vaga_id": vaga["id"],
                            "catalog_id": catalog_id,
                            "product_retailer_id": produto["product_retailer_id"],
                            "product_name": produto["name"],
                            "price_milliunits": produto["price_milliunits"],
                            "availability": produto["availability"],
                        },
                        on_conflict="vaga_id,catalog_id",
                    ).execute()
                    synced_local += 1
                    produtos_para_push.append(produto)
                except Exception as e:
                    logger.warning("[MetaCatalog] Erro ao sincronizar vaga %s: %s", vaga["id"], e)

            # Sprint 72: Push para Graph API
            pushed = await self._push_items_batch(catalog_id, produtos_para_push)

            logger.info(
                "[MetaCatalog] Sincronizadas %d/%d vagas (local=%d, meta=%d)",
                synced_local,
                len(vagas),
                synced_local,
                pushed,
            )
            return {
                "success": True,
                "total": len(vagas),
                "synced": synced_local,
                "pushed_to_meta": pushed,
            }

        except Exception as e:
            logger.error("[MetaCatalog] Erro ao sincronizar: %s", e)
            return {"success": False, "error": "Erro interno ao sincronizar catálogo"}

    async def _push_items_batch(
        self,
        catalog_id: str,
        produtos: List[dict],
    ) -> int:
        """
        Sprint 72: Envia produtos para Graph API via POST /{catalog_id}/items_batch.

        Args:
            catalog_id: ID do catálogo Meta
            produtos: Lista de produtos no formato interno

        Returns:
            Quantidade de produtos enviados com sucesso
        """
        if not produtos:
            return 0

        try:
            # Buscar access_token de um chip Meta ativo
            chip_result = (
                supabase.table("chips")
                .select("meta_access_token")
                .eq("provider", "meta")
                .eq("status", "active")
                .not_.is_("meta_access_token", "null")
                .limit(1)
                .execute()
            )

            if not chip_result.data:
                logger.warning("[MetaCatalog] Nenhum chip Meta para push de catálogo")
                return 0

            access_token = chip_result.data[0]["meta_access_token"]
            api_version = settings.META_GRAPH_API_VERSION or "v21.0"
            url = f"https://graph.facebook.com/{api_version}/{catalog_id}/items_batch"

            from app.services.http_client import get_http_client

            client = await get_http_client()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            pushed = 0
            # Processar em batches de _GRAPH_API_BATCH_SIZE
            for i in range(0, len(produtos), _GRAPH_API_BATCH_SIZE):
                batch = produtos[i : i + _GRAPH_API_BATCH_SIZE]
                items = [
                    {
                        "method": "UPDATE",
                        "retailer_id": p["product_retailer_id"],
                        "data": {
                            "name": p["name"],
                            "description": p.get("description", "Plantão médico"),
                            "price": p["price_milliunits"],
                            "currency": p.get("currency", "BRL"),
                            "availability": p.get("availability", "in stock"),
                        },
                    }
                    for p in batch
                ]

                try:
                    response = await client.post(
                        url,
                        headers=headers,
                        json={"item_type": "PRODUCT_ITEM", "requests": items},
                        timeout=30,
                    )
                    response.raise_for_status()
                    pushed += len(batch)
                except Exception as e:
                    logger.warning(
                        "[MetaCatalog] Erro no batch %d-%d: %s",
                        i,
                        i + len(batch),
                        e,
                    )

            return pushed

        except Exception as e:
            logger.warning("[MetaCatalog] Erro ao push para Graph API: %s", e)
            return 0

    async def listar_produtos(
        self,
        catalog_id: Optional[str] = None,
    ) -> List[dict]:
        """
        Lista produtos do catálogo local.

        Args:
            catalog_id: Filtrar por catálogo

        Returns:
            Lista de produtos
        """
        try:
            query = supabase.table("meta_catalog_products").select("*")
            if catalog_id:
                query = query.eq("catalog_id", catalog_id)

            result = query.order("created_at", desc=True).execute()
            return result.data or []

        except Exception as e:
            logger.error("[MetaCatalog] Erro ao listar produtos: %s", e)
            return []

    async def buscar_produto_por_vaga(self, vaga_id: str) -> Optional[dict]:
        """
        Busca produto pelo ID da vaga.

        Args:
            vaga_id: ID da vaga

        Returns:
            Produto ou None
        """
        try:
            result = (
                supabase.table("meta_catalog_products")
                .select("*")
                .eq("vaga_id", vaga_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None

        except Exception as e:
            logger.error("[MetaCatalog] Erro ao buscar produto: %s", e)
            return None


# Singleton
catalog_service = MetaCatalogService()
