"""
Crawler Manager - Gerencia crawling de fontes conhecidas.

Sprint 26 - E12 - S12.6

Características:
- Parser genérico para novos sites
- Parsers específicos para sites conhecidos
- Rate limiting por domínio
- Retry com backoff
"""

import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, UTC

import httpx
from bs4 import BeautifulSoup

from app.services.supabase import supabase
from app.services.group_entry.importer import extrair_invite_code

logger = logging.getLogger(__name__)


class CrawlerManager:
    """Gerenciador de crawling de fontes."""

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def crawl_fonte(self, source_id: str) -> Dict:
        """
        Executa crawl de uma fonte específica.

        Returns:
            {
                "status": "sucesso" | "parcial" | "erro",
                "links_encontrados": N,
                "links_novos": N,
                "erro": str (se houver)
            }
        """
        # Buscar fonte
        result = supabase.table("group_sources").select("*").eq("id", source_id).single().execute()

        if not result.data:
            return {"status": "erro", "erro": "Fonte não encontrada"}

        fonte = result.data
        inicio = datetime.now(UTC)

        logger.info(f"[Crawler] Iniciando: {fonte['dominio']}")

        try:
            # Executar crawl baseado no método
            if fonte["metodo_crawl"] == "requests":
                links = await self._crawl_requests(fonte)
            elif fonte["metodo_crawl"] == "playwright":
                links = await self._crawl_playwright(fonte)
            else:
                links = []

            # Processar links
            resultado = await self._processar_links(links, fonte)

            # Calcular duração
            duracao = int((datetime.now(UTC) - inicio).total_seconds())

            # Atualizar fonte
            supabase.table("group_sources").update(
                {
                    "ultimo_crawl": datetime.now(UTC).isoformat(),
                    "proximo_crawl": (
                        datetime.now(UTC) + timedelta(days=fonte["frequencia_dias"])
                    ).isoformat(),
                    "total_grupos_extraidos": (fonte.get("total_grupos_extraidos") or 0)
                    + resultado["links_novos"],
                    "falhas_consecutivas": 0,
                }
            ).eq("id", source_id).execute()

            # Registrar histórico
            supabase.table("crawl_history").insert(
                {
                    "source_id": source_id,
                    "status": "sucesso",
                    "duracao_segundos": duracao,
                    "links_encontrados": resultado["links_encontrados"],
                    "links_novos": resultado["links_novos"],
                    "links_duplicados": resultado["links_duplicados"],
                }
            ).execute()

            logger.info(
                f"[Crawler] {fonte['dominio']}: "
                f"{resultado['links_novos']} novos de {resultado['links_encontrados']}"
            )

            resultado["status"] = "sucesso"
            return resultado

        except Exception as e:
            logger.error(f"[Crawler] Erro em {fonte['dominio']}: {e}")

            # Atualizar falhas
            falhas = (fonte.get("falhas_consecutivas") or 0) + 1
            status = "erro" if falhas >= 3 else "ativo"

            supabase.table("group_sources").update(
                {
                    "falhas_consecutivas": falhas,
                    "status": status,
                    "proximo_crawl": (
                        datetime.now(UTC) + timedelta(days=1)  # Retry amanhã
                    ).isoformat(),
                }
            ).eq("id", source_id).execute()

            # Registrar histórico
            supabase.table("crawl_history").insert(
                {
                    "source_id": source_id,
                    "status": "erro",
                    "erro": str(e)[:500],
                }
            ).execute()

            return {"status": "erro", "erro": str(e)}

    async def _crawl_requests(self, fonte: Dict) -> List[Dict]:
        """Crawl usando requests (sites HTML simples)."""
        links = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                fonte["url"],
                headers={"User-Agent": self.user_agent},
                timeout=30,
                follow_redirects=True,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Buscar links de WhatsApp
            for a in soup.find_all("a", href=re.compile(r"chat\.whatsapp\.com")):
                href = a.get("href", "")
                invite_code = extrair_invite_code(href)

                if invite_code:
                    # Tentar extrair nome do contexto
                    nome = a.get_text(strip=True)
                    if not nome or len(nome) < 3:
                        parent = a.find_parent(["div", "li", "article"])
                        if parent:
                            title = parent.find(["h2", "h3", "h4", "strong"])
                            if title:
                                nome = title.get_text(strip=True)

                    links.append(
                        {
                            "invite_code": invite_code,
                            "invite_url": href,
                            "nome": nome[:100] if nome else None,
                        }
                    )

        return links

    async def _crawl_playwright(self, fonte: Dict) -> List[Dict]:
        """Crawl usando Playwright (sites JavaScript)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning(
                f"[Crawler] Playwright não instalado, usando requests para {fonte['dominio']}"
            )
            return await self._crawl_requests(fonte)

        links = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()

            try:
                await page.goto(fonte["url"], timeout=60000)
                await page.wait_for_timeout(5000)

                # Scroll para carregar lazy content
                for _ in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

                # Extrair links
                whatsapp_links = await page.query_selector_all('a[href*="chat.whatsapp.com"]')

                for link in whatsapp_links:
                    href = await link.get_attribute("href")
                    nome = await link.inner_text()

                    invite_code = extrair_invite_code(href or "")
                    if invite_code:
                        links.append(
                            {
                                "invite_code": invite_code,
                                "invite_url": href,
                                "nome": nome[:100] if nome else None,
                            }
                        )

            finally:
                await browser.close()

        return links

    async def _processar_links(self, links: List[Dict], fonte: Dict) -> Dict:
        """Processa links extraídos e salva novos."""
        resultado = {
            "links_encontrados": len(links),
            "links_novos": 0,
            "links_duplicados": 0,
            "links_invalidos": 0,
        }

        for link in links:
            invite_code = link["invite_code"]

            # Verificar se já existe
            exists = (
                supabase.table("group_links").select("id").eq("invite_code", invite_code).execute()
            )

            if exists.data:
                resultado["links_duplicados"] += 1
                continue

            # Inserir novo
            try:
                supabase.table("group_links").insert(
                    {
                        "invite_code": invite_code,
                        "invite_url": link.get("invite_url"),
                        "nome": link.get("nome"),
                        "fonte": fonte["dominio"],
                        "status": "pendente",
                    }
                ).execute()
                resultado["links_novos"] += 1
            except Exception:
                resultado["links_duplicados"] += 1

        return resultado

    async def executar_crawls_pendentes(self, limite: int = 5) -> Dict:
        """
        Executa crawls de fontes que estão prontas.

        Returns:
            {
                "fontes_processadas": N,
                "total_links_novos": N
            }
        """
        # Buscar fontes prontas
        result = (
            supabase.table("group_sources")
            .select("id, dominio")
            .eq("status", "ativo")
            .lte("proximo_crawl", datetime.now(UTC).isoformat())
            .limit(limite)
            .execute()
        )

        fontes = result.data or []

        total = {
            "fontes_processadas": 0,
            "total_links_novos": 0,
        }

        for fonte in fontes:
            resultado = await self.crawl_fonte(fonte["id"])
            total["fontes_processadas"] += 1
            total["total_links_novos"] += resultado.get("links_novos", 0)

        return total

    async def listar_crawls_recentes(
        self, source_id: Optional[str] = None, limite: int = 20
    ) -> List[Dict]:
        """Lista histórico de crawls."""
        query = supabase.table("crawl_history").select("*, group_sources!source_id(dominio, nome)")

        if source_id:
            query = query.eq("source_id", source_id)

        result = query.order("created_at", desc=True).limit(limite).execute()
        return result.data or []

    async def obter_metricas_crawl(self) -> Dict:
        """Retorna métricas de crawling."""
        # Últimos 7 dias
        uma_semana = (datetime.now(UTC) - timedelta(days=7)).isoformat()

        result = (
            supabase.table("crawl_history")
            .select("status, links_encontrados, links_novos, duracao_segundos")
            .gte("created_at", uma_semana)
            .execute()
        )

        crawls = result.data or []

        metricas = {
            "total_crawls": len(crawls),
            "sucesso": len([c for c in crawls if c["status"] == "sucesso"]),
            "erro": len([c for c in crawls if c["status"] == "erro"]),
            "links_encontrados": sum(c.get("links_encontrados") or 0 for c in crawls),
            "links_novos": sum(c.get("links_novos") or 0 for c in crawls),
            "duracao_media": 0,
        }

        duracoes = [c["duracao_segundos"] for c in crawls if c.get("duracao_segundos")]
        if duracoes:
            metricas["duracao_media"] = sum(duracoes) / len(duracoes)

        return metricas


# Singleton
crawler_manager = CrawlerManager()
