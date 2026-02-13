"""
Source Discovery - Descoberta ativa de novas fontes de grupos.

Sprint 26 - E12 - S12.6

Estratégias:
1. Google/Bing Search - Busca por termos relacionados
2. Link Follower - Segue links de sites conhecidos
3. Social Listening - Monitora menções em redes sociais
"""

import logging
import re
from typing import List, Optional, Dict
from datetime import datetime, timedelta, UTC
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.services.http_client import get_http_client
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class SourceDiscovery:
    """Descoberta de novas fontes de grupos."""

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Domínios a ignorar (já são fontes ou não relevantes)
        self.dominios_ignorados = {
            "chat.whatsapp.com",
            "wa.me",
            "t.me",
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "x.com",
            "youtube.com",
            "google.com",
            "bing.com",
        }

        # Indicadores de que é um site de grupos médicos
        self.indicadores_positivos = [
            "plantão",
            "plantao",
            "vagas médicas",
            "vagas medicas",
            "escala médica",
            "escala medica",
            "grupos médicos",
            "grupos medicos",
            "whatsapp médico",
            "whatsapp medico",
            "grupos whatsapp",
            "saúde",
            "saude",
            "hospital",
        ]

    async def buscar_google(self, query: str, num_results: int = 20) -> List[str]:
        """
        Busca no Google por sites relevantes.

        Usa scraping do Google (respeitar rate limits!).
        Alternativa: usar Google Custom Search API.
        """
        urls_encontradas = []

        # URL do Google
        search_url = "https://www.google.com/search"
        params = {
            "q": query,
            "num": num_results,
            "hl": "pt-BR",
            "gl": "BR",
        }

        try:
            client = await get_http_client()
            resp = await client.get(
                search_url,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=30,
            )

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extrai links dos resultados
            for link in soup.find_all("a", href=True):
                href = link["href"]

                # Google encapsula URLs em /url?q=...
                if href.startswith("/url?q="):
                    url = href.split("/url?q=")[1].split("&")[0]
                    urls_encontradas.append(url)
                elif href.startswith("http") and "google" not in href:
                    urls_encontradas.append(href)

        except Exception as e:
            logger.error(f"[Discovery] Erro no Google: {e}")

        return urls_encontradas

    async def buscar_bing(self, query: str, num_results: int = 20) -> List[str]:
        """Busca no Bing por sites relevantes."""
        urls_encontradas = []

        search_url = "https://www.bing.com/search"
        params = {
            "q": query,
            "count": num_results,
            "setlang": "pt-BR",
            "cc": "BR",
        }

        try:
            client = await get_http_client()
            resp = await client.get(
                search_url,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=30,
            )

            soup = BeautifulSoup(resp.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("http") and "bing" not in href and "microsoft" not in href:
                    urls_encontradas.append(href)

        except Exception as e:
            logger.error(f"[Discovery] Erro no Bing: {e}")

        return urls_encontradas

    def extrair_dominio(self, url: str) -> Optional[str]:
        """Extrai domínio de uma URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower().replace("www.", "")
        except Exception:
            return None

    def pontuar_url(self, url: str, html: str = "") -> int:
        """
        Pontua relevância de uma URL para grupos médicos.

        Returns:
            Score 0-100
        """
        score = 0
        url_lower = url.lower()
        html_lower = html.lower() if html else ""

        # Pontos por URL
        for indicador in self.indicadores_positivos:
            if indicador in url_lower:
                score += 15

        # Pontos por conteúdo
        for indicador in self.indicadores_positivos:
            if indicador in html_lower:
                score += 5

        # Pontos por ter links de WhatsApp
        whatsapp_count = html_lower.count("chat.whatsapp.com")
        score += min(whatsapp_count * 10, 30)  # Max 30 pontos

        # Penalidades
        if "login" in url_lower or "signin" in url_lower:
            score -= 20
        if "facebook.com" in url_lower or "instagram.com" in url_lower:
            score -= 50

        return max(0, min(100, score))

    async def analisar_url(self, url: str) -> Optional[Dict]:
        """
        Analisa uma URL candidata.

        Returns:
            Dict com info da fonte ou None se não relevante
        """
        dominio = self.extrair_dominio(url)

        if not dominio or dominio in self.dominios_ignorados:
            return None

        # Verificar se já existe
        result = supabase.table("group_sources").select("id").eq("dominio", dominio).execute()

        if result.data:
            return None  # Já conhecemos

        # Buscar conteúdo
        try:
            client = await get_http_client()
            resp = await client.get(
                url,
                headers={"User-Agent": self.user_agent},
                timeout=30,
            )
            html = resp.text
        except Exception as e:
            logger.debug(f"[Discovery] Erro ao acessar {url}: {e}")
            return None

        # Pontuar
        score = self.pontuar_url(url, html)

        if score < 30:
            return None  # Não relevante

        # Contar links de WhatsApp
        whatsapp_links = len(re.findall(r"chat\.whatsapp\.com/[A-Za-z0-9]+", html))

        if whatsapp_links == 0:
            return None  # Sem links de WhatsApp

        # Detectar método necessário
        metodo = "requests"
        if any(x in html.lower() for x in ["react", "vue", "angular", "__next"]):
            metodo = "playwright"

        return {
            "url": url,
            "dominio": dominio,
            "nome": dominio.split(".")[0].title(),
            "tipo": "agregador",
            "metodo_crawl": metodo,
            "score": score,
            "whatsapp_links": whatsapp_links,
        }

    async def executar_discovery(self) -> Dict:
        """
        Executa ciclo de descoberta de fontes.

        Returns:
            {
                "queries_executadas": N,
                "urls_analisadas": N,
                "fontes_novas": N,
                "fontes": [...]
            }
        """
        resultado = {
            "queries_executadas": 0,
            "urls_analisadas": 0,
            "fontes_novas": 0,
            "fontes": [],
        }

        # Buscar queries ativas
        queries_result = supabase.table("discovery_queries").select("*").eq("ativo", True).execute()

        # Filtrar queries que estão prontas para rodar
        agora = datetime.now(UTC)
        queries = [
            q
            for q in (queries_result.data or [])
            if q.get("proximo_run") is None or q["proximo_run"] <= agora.isoformat()
        ]

        for query_row in queries:
            query = query_row["query"]
            engine = query_row["engine"]

            logger.info(f"[Discovery] Executando: '{query}' via {engine}")

            # Buscar URLs
            if engine == "google":
                urls = await self.buscar_google(query)
            elif engine == "bing":
                urls = await self.buscar_bing(query)
            else:
                urls = []

            resultado["queries_executadas"] += 1
            resultado["urls_analisadas"] += len(urls)

            # Analisar cada URL
            for url in urls:
                fonte = await self.analisar_url(url)

                if fonte:
                    # Salvar nova fonte
                    try:
                        supabase.table("group_sources").insert(
                            {
                                "url": fonte["url"],
                                "dominio": fonte["dominio"],
                                "nome": fonte["nome"],
                                "tipo": fonte["tipo"],
                                "metodo_crawl": fonte["metodo_crawl"],
                                "descoberto_via": engine,
                                "proximo_crawl": datetime.now(UTC).isoformat(),
                            }
                        ).execute()

                        resultado["fontes_novas"] += 1
                        resultado["fontes"].append(fonte)

                        logger.info(
                            f"[Discovery] Nova fonte: {fonte['dominio']} "
                            f"({fonte['whatsapp_links']} links, score={fonte['score']})"
                        )

                    except Exception:
                        # Provavelmente duplicata
                        pass

            # Atualizar próximo run da query
            proximo = datetime.now(UTC) + timedelta(days=query_row["frequencia_dias"])
            supabase.table("discovery_queries").update(
                {
                    "ultimo_run": datetime.now(UTC).isoformat(),
                    "proximo_run": proximo.isoformat(),
                    "fontes_descobertas": (query_row.get("fontes_descobertas") or 0)
                    + resultado["fontes_novas"],
                }
            ).eq("id", query_row["id"]).execute()

        return resultado

    async def listar_fontes(self, status: Optional[str] = None) -> List[Dict]:
        """Lista fontes cadastradas."""
        query = supabase.table("group_sources").select("*")

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()
        return result.data or []

    async def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas de fontes e discovery."""
        # Contar fontes por status
        supabase.table("group_sources").select("status", count="exact").execute()

        stats = {
            "fontes": {"total": 0, "ativo": 0, "inativo": 0, "erro": 0},
            "queries": {"total": 0, "ativas": 0},
            "crawls_ultimos_7_dias": 0,
        }

        # Contagem por status
        for status in ["ativo", "inativo", "erro", "bloqueado"]:
            count_result = (
                supabase.table("group_sources")
                .select("id", count="exact")
                .eq("status", status)
                .execute()
            )
            stats["fontes"][status] = count_result.count or 0

        stats["fontes"]["total"] = sum(stats["fontes"].values())

        # Queries
        queries_result = (
            supabase.table("discovery_queries").select("id, ativo", count="exact").execute()
        )

        stats["queries"]["total"] = queries_result.count or 0
        stats["queries"]["ativas"] = len([q for q in (queries_result.data or []) if q.get("ativo")])

        # Crawls recentes
        uma_semana = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        crawls_result = (
            supabase.table("crawl_history")
            .select("id", count="exact")
            .gte("created_at", uma_semana)
            .execute()
        )

        stats["crawls_ultimos_7_dias"] = crawls_result.count or 0

        return stats


# Singleton
source_discovery = SourceDiscovery()
