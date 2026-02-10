"""
Indexador de documentação Julia.

Converte markdown em chunks com metadados para embedding.
"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkConhecimento:
    """Chunk de conhecimento extraído de documento."""

    arquivo: str
    secao: str
    subsecao: Optional[str]
    conteudo: str
    tipo: str  # 'perfil', 'objecao', 'erro', 'conversa', 'guardrail'
    subtipo: Optional[str]
    tags: list[str]


class ParserMarkdown:
    """Parser de markdown para chunks."""

    # Tamanho alvo dos chunks (em caracteres)
    CHUNK_SIZE_MIN = 300
    CHUNK_SIZE_MAX = 1200
    CHUNK_SIZE_TARGET = 700

    # Mapeamento arquivo -> tipo
    TIPO_POR_ARQUIVO = {
        "guia_adaptacao_perfis_medicos.md": "perfil",
        "julia_catalogo_objecoes_respostas.md": "objecao",
        "3_erros_criticos_medicos_senior.md": "erro",
        "CONVERSAS_REFERENCIA.md": "conversa",
        "julia_sistema_prompts_avancado.md": "guardrail",
        "julia_triggers_handoff_humano.md": "handoff",
        "julia_protocolo_escalacao_automatica.md": "escalacao",
        "julia_fundacao_cientifica.md": "fundacao",
        "julia_prompt_negociacao_detalhado.md": "negociacao",
        "PREFERENCIAS_MEDICO.md": "preferencias",
        "MENSAGENS_ABERTURA.md": "abertura",
    }

    # Padrões de seção
    PADRAO_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)
    PADRAO_H2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    PADRAO_H3 = re.compile(r"^###\s+(.+)$", re.MULTILINE)

    def parsear_arquivo(self, caminho: Path) -> list[ChunkConhecimento]:
        """
        Parseia arquivo markdown em chunks.

        Args:
            caminho: Path do arquivo .md

        Returns:
            Lista de chunks extraídos
        """
        nome_arquivo = caminho.name
        tipo = self.TIPO_POR_ARQUIVO.get(nome_arquivo, "geral")

        conteudo = caminho.read_text(encoding="utf-8")
        chunks = []

        # Dividir por seções H2
        secoes = self._dividir_por_secoes(conteudo)

        for secao_titulo, secao_conteudo in secoes:
            # Dividir seção em chunks menores se necessário
            sub_chunks = self._dividir_em_chunks(secao_conteudo)

            for i, chunk_texto in enumerate(sub_chunks):
                if len(chunk_texto.strip()) < self.CHUNK_SIZE_MIN:
                    continue

                # Detectar subtipo e tags
                subtipo = self._detectar_subtipo(secao_titulo, chunk_texto, tipo)
                tags = self._extrair_tags(secao_titulo, chunk_texto, tipo)

                chunk = ChunkConhecimento(
                    arquivo=nome_arquivo,
                    secao=secao_titulo,
                    subsecao=f"parte_{i + 1}" if len(sub_chunks) > 1 else None,
                    conteudo=chunk_texto.strip(),
                    tipo=tipo,
                    subtipo=subtipo,
                    tags=tags,
                )
                chunks.append(chunk)

        logger.info(f"Parseado {nome_arquivo}: {len(chunks)} chunks")
        return chunks

    def _dividir_por_secoes(self, conteudo: str) -> list[tuple[str, str]]:
        """Divide conteúdo por headers H2."""
        secoes = []
        partes = re.split(r"\n(?=##\s)", conteudo)

        for parte in partes:
            match = self.PADRAO_H2.match(parte)
            if match:
                titulo = match.group(1).strip()
                texto = parte[match.end() :].strip()
                secoes.append((titulo, texto))
            elif parte.strip():
                # Conteúdo antes do primeiro H2
                secoes.append(("Introdução", parte.strip()))

        return secoes

    def _dividir_em_chunks(self, texto: str) -> list[str]:
        """Divide texto em chunks de tamanho adequado."""
        if len(texto) <= self.CHUNK_SIZE_MAX:
            return [texto]

        chunks = []
        paragrafos = texto.split("\n\n")
        chunk_atual = ""

        for paragrafo in paragrafos:
            if len(chunk_atual) + len(paragrafo) <= self.CHUNK_SIZE_TARGET:
                chunk_atual += "\n\n" + paragrafo if chunk_atual else paragrafo
            else:
                if chunk_atual:
                    chunks.append(chunk_atual)
                chunk_atual = paragrafo

        if chunk_atual:
            chunks.append(chunk_atual)

        return chunks

    def _detectar_subtipo(self, secao: str, texto: str, tipo: str) -> Optional[str]:
        """Detecta subtipo baseado no conteúdo."""
        texto_lower = (secao + " " + texto).lower()

        if tipo == "perfil":
            if "recém-formado" in texto_lower or "0-2 anos" in texto_lower:
                return "recem_formado"
            elif "em desenvolvimento" in texto_lower or "2-7 anos" in texto_lower:
                return "em_desenvolvimento"
            elif "experiente" in texto_lower or "7-15 anos" in texto_lower:
                return "experiente"
            elif "sênior" in texto_lower or "15+ anos" in texto_lower:
                return "senior"
            elif "especialista" in texto_lower or "subespecialista" in texto_lower:
                return "especialista"
            elif "transição" in texto_lower:
                return "em_transicao"

        elif tipo == "objecao":
            if "preço" in texto_lower or "valor" in texto_lower or "pag" in texto_lower:
                return "preco"
            elif "tempo" in texto_lower or "agenda" in texto_lower or "ocupado" in texto_lower:
                return "tempo"
            elif "confia" in texto_lower or "conhec" in texto_lower:
                return "confianca"
            elif "processo" in texto_lower or "burocracia" in texto_lower:
                return "processo"
            elif "disponib" in texto_lower:
                return "disponibilidade"
            elif "qualidade" in texto_lower or "hospital" in texto_lower:
                return "qualidade"
            elif "lealdade" in texto_lower or "outra plataforma" in texto_lower:
                return "lealdade"

        elif tipo == "erro":
            if "apoio" in texto_lower or "parceria" in texto_lower:
                return "erro_tom"
            elif "pressão" in texto_lower or "urgência" in texto_lower:
                return "erro_pressao"
            elif "dinheiro" in texto_lower or "remuneração" in texto_lower:
                return "erro_dinheiro"

        return None

    def _extrair_tags(self, secao: str, texto: str, tipo: str) -> list[str]:
        """Extrai tags relevantes do conteúdo."""
        tags = [tipo]
        texto_lower = (secao + " " + texto).lower()

        # Tags de contexto
        if "negoci" in texto_lower:
            tags.append("negociacao")
        if "objeção" in texto_lower or "objecao" in texto_lower:
            tags.append("objecao")
        if "exemplo" in texto_lower:
            tags.append("exemplo")
        if "evitar" in texto_lower or "não faça" in texto_lower:
            tags.append("evitar")
        if "✅" in texto or "correto" in texto_lower:
            tags.append("bom_exemplo")
        if "❌" in texto or "errado" in texto_lower:
            tags.append("mau_exemplo")
        if "framework" in texto_lower or "laar" in texto_lower:
            tags.append("framework")
        if "senior" in texto_lower or "sênior" in texto_lower:
            tags.append("senior")

        return list(set(tags))


class IndexadorConhecimento:
    """Indexa documentação Julia no Supabase."""

    def __init__(self):
        self.parser = ParserMarkdown()
        self.docs_path = Path("docs/julia")

    async def indexar_todos(self, reindexar: bool = False) -> dict:
        """
        Indexa todos os documentos da pasta docs/julia/.

        Args:
            reindexar: Se True, remove dados antigos antes

        Returns:
            Estatísticas da indexação
        """
        from app.services.embedding import gerar_embedding
        from app.services.supabase import supabase

        stats = {"arquivos": 0, "chunks": 0, "embeddings": 0, "erros": 0}

        if reindexar:
            logger.info("Removendo dados antigos...")
            supabase.table("conhecimento_julia").delete().neq(
                "id", "00000000-0000-0000-0000-000000000000"
            ).execute()

        # Listar arquivos .md
        arquivos = list(self.docs_path.glob("*.md"))
        logger.info(f"Encontrados {len(arquivos)} arquivos para indexar")

        for arquivo in arquivos:
            try:
                chunks = self.parser.parsear_arquivo(arquivo)
                stats["arquivos"] += 1

                for chunk in chunks:
                    try:
                        # Gerar embedding
                        embedding = await gerar_embedding(chunk.conteudo)

                        # Salvar no banco
                        data = {
                            "arquivo": chunk.arquivo,
                            "secao": chunk.secao,
                            "subsecao": chunk.subsecao,
                            "conteudo": chunk.conteudo,
                            "tipo": chunk.tipo,
                            "subtipo": chunk.subtipo,
                            "tags": chunk.tags,
                            "embedding": embedding,
                        }

                        supabase.table("conhecimento_julia").insert(data).execute()
                        stats["chunks"] += 1
                        stats["embeddings"] += 1

                    except Exception as e:
                        logger.error(f"Erro ao indexar chunk: {e}")
                        stats["erros"] += 1

            except Exception as e:
                logger.error(f"Erro ao processar {arquivo}: {e}")
                stats["erros"] += 1

        logger.info(f"Indexação concluída: {stats}")
        return stats

    async def indexar_arquivo(self, nome_arquivo: str) -> int:
        """
        Indexa um arquivo específico.

        Args:
            nome_arquivo: Nome do arquivo em docs/julia/

        Returns:
            Número de chunks indexados
        """
        from app.services.embedding import gerar_embedding
        from app.services.supabase import supabase

        caminho = self.docs_path / nome_arquivo
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        # Remover chunks antigos deste arquivo
        supabase.table("conhecimento_julia").delete().eq("arquivo", nome_arquivo).execute()

        chunks = self.parser.parsear_arquivo(caminho)
        count = 0

        for chunk in chunks:
            embedding = await gerar_embedding(chunk.conteudo)

            data = {
                "arquivo": chunk.arquivo,
                "secao": chunk.secao,
                "subsecao": chunk.subsecao,
                "conteudo": chunk.conteudo,
                "tipo": chunk.tipo,
                "subtipo": chunk.subtipo,
                "tags": chunk.tags,
                "embedding": embedding,
            }

            supabase.table("conhecimento_julia").insert(data).execute()
            count += 1

        logger.info(f"Indexado {nome_arquivo}: {count} chunks")
        return count
