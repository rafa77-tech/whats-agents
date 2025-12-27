"""
Pipeline de processamento de mensagens de grupos.

Sprint 14 - E11 - Worker e Orquestração

Orquestra os estágios de processamento:
1. Heurística - filtro rápido
2. Classificação LLM - confirmação
3. Extração - dados estruturados
4. Normalização - entidades do banco
5. Deduplicação - evitar duplicatas
6. Importação - criar vaga final
"""

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.heuristica import calcular_score_heuristica
from app.services.grupos.classificador_llm import classificar_com_llm
from app.services.grupos.extrator import extrair_dados_mensagem
from app.services.grupos.normalizador import normalizar_vaga
from app.services.grupos.deduplicador import processar_deduplicacao
from app.services.grupos.importador import processar_importacao

logger = get_logger(__name__)


# =============================================================================
# Constantes e Thresholds
# =============================================================================

THRESHOLD_HEURISTICA = 0.3  # Score mínimo para continuar
THRESHOLD_HEURISTICA_ALTO = 0.8  # Pular classificação LLM
THRESHOLD_LLM = 0.7  # Confiança mínima do LLM


@dataclass
class ResultadoPipeline:
    """Resultado de um estágio do pipeline."""
    acao: str  # proximo estágio ou ação
    mensagem_id: Optional[UUID] = None
    vaga_grupo_id: Optional[UUID] = None
    motivo: Optional[str] = None
    score: Optional[float] = None
    confianca: Optional[float] = None
    vagas_criadas: Optional[List[str]] = None
    detalhes: Optional[dict] = None


# =============================================================================
# S11.3 - Pipeline de Processamento
# =============================================================================

class PipelineGrupos:
    """Processador do pipeline de mensagens de grupos."""

    async def processar_pendente(self, item: dict) -> ResultadoPipeline:
        """
        Processa mensagem pendente (estágio inicial).

        Aplica heurística para decidir se continua.

        Args:
            item: Item da fila com mensagem_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        mensagem_id = item.get("mensagem_id")
        if isinstance(mensagem_id, str):
            mensagem_id = UUID(mensagem_id)

        # Buscar mensagem
        msg = supabase.table("mensagens_grupo") \
            .select("texto, nome_grupo, nome_contato, regiao") \
            .eq("id", str(mensagem_id)) \
            .single() \
            .execute()

        if not msg.data:
            return ResultadoPipeline(
                acao="descartar",
                mensagem_id=mensagem_id,
                motivo="mensagem_nao_encontrada"
            )

        texto = msg.data.get("texto", "")
        if not texto or len(texto) < 10:
            return ResultadoPipeline(
                acao="descartar",
                mensagem_id=mensagem_id,
                motivo="sem_texto"
            )

        # Aplicar heurística
        resultado = calcular_score_heuristica(texto)

        if resultado.score < THRESHOLD_HEURISTICA:
            logger.debug(f"Mensagem {mensagem_id} descartada por heurística: {resultado.score:.2f}")
            return ResultadoPipeline(
                acao="descartar",
                mensagem_id=mensagem_id,
                motivo="heuristica_baixa",
                score=resultado.score
            )

        if resultado.score >= THRESHOLD_HEURISTICA_ALTO:
            # Alta confiança - pula classificação LLM
            logger.debug(f"Mensagem {mensagem_id} aprovada direto: {resultado.score:.2f}")
            return ResultadoPipeline(
                acao="extrair",
                mensagem_id=mensagem_id,
                score=resultado.score
            )

        # Score intermediário - precisa classificação LLM
        return ResultadoPipeline(
            acao="classificar",
            mensagem_id=mensagem_id,
            score=resultado.score
        )

    async def processar_classificacao(self, item: dict) -> ResultadoPipeline:
        """
        Classifica mensagem com LLM.

        Args:
            item: Item da fila com mensagem_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        mensagem_id = item.get("mensagem_id")
        if isinstance(mensagem_id, str):
            mensagem_id = UUID(mensagem_id)

        # Buscar mensagem
        msg = supabase.table("mensagens_grupo") \
            .select("texto, nome_grupo, nome_contato") \
            .eq("id", str(mensagem_id)) \
            .single() \
            .execute()

        if not msg.data:
            return ResultadoPipeline(
                acao="descartar",
                mensagem_id=mensagem_id,
                motivo="mensagem_nao_encontrada"
            )

        # Classificar com LLM
        resultado = await classificar_com_llm(
            texto=msg.data.get("texto", ""),
            nome_grupo=msg.data.get("nome_grupo", ""),
            nome_contato=msg.data.get("nome_contato", "")
        )

        if resultado.eh_oferta and resultado.confianca >= THRESHOLD_LLM:
            logger.debug(f"Mensagem {mensagem_id} classificada como oferta: {resultado.confianca:.2f}")
            return ResultadoPipeline(
                acao="extrair",
                mensagem_id=mensagem_id,
                confianca=resultado.confianca
            )

        logger.debug(f"Mensagem {mensagem_id} descartada pelo LLM: {resultado.confianca:.2f}")
        return ResultadoPipeline(
            acao="descartar",
            mensagem_id=mensagem_id,
            motivo="nao_eh_oferta",
            confianca=resultado.confianca
        )

    async def processar_extracao(self, item: dict) -> ResultadoPipeline:
        """
        Extrai dados estruturados da mensagem.

        Args:
            item: Item da fila com mensagem_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        mensagem_id = item.get("mensagem_id")
        if isinstance(mensagem_id, str):
            mensagem_id = UUID(mensagem_id)

        # Buscar mensagem completa
        msg = supabase.table("mensagens_grupo") \
            .select("*") \
            .eq("id", str(mensagem_id)) \
            .single() \
            .execute()

        if not msg.data:
            return ResultadoPipeline(
                acao="descartar",
                mensagem_id=mensagem_id,
                motivo="mensagem_nao_encontrada"
            )

        # Extrair dados
        resultado = await extrair_dados_mensagem(
            texto=msg.data.get("texto", ""),
            nome_grupo=msg.data.get("nome_grupo", ""),
            regiao_grupo=msg.data.get("regiao", ""),
            nome_contato=msg.data.get("nome_contato", "")
        )

        if not resultado.vagas:
            return ResultadoPipeline(
                acao="descartar",
                mensagem_id=mensagem_id,
                motivo="extracao_falhou"
            )

        # Criar vagas_grupo para cada vaga extraída
        vagas_criadas = []
        for vaga in resultado.vagas:
            vaga_id = await self._criar_vaga_grupo(mensagem_id, vaga, msg.data)
            vagas_criadas.append(str(vaga_id))

        logger.info(f"Mensagem {mensagem_id}: {len(vagas_criadas)} vaga(s) extraída(s)")

        return ResultadoPipeline(
            acao="normalizar",
            mensagem_id=mensagem_id,
            vagas_criadas=vagas_criadas
        )

    async def _criar_vaga_grupo(
        self,
        mensagem_id: UUID,
        vaga,
        msg_data: dict
    ) -> UUID:
        """
        Cria registro de vaga_grupo a partir de extração.

        Args:
            mensagem_id: ID da mensagem original
            vaga: Dados extraídos da vaga
            msg_data: Dados completos da mensagem

        Returns:
            ID da vaga_grupo criada
        """
        dados = {
            "mensagem_id": str(mensagem_id),
            "grupo_id": msg_data.get("grupo_id"),
            "hospital_extraido": vaga.dados.hospital if vaga.dados else None,
            "especialidade_extraida": vaga.dados.especialidade if vaga.dados else None,
            "data_extraida": vaga.dados.data if vaga.dados else None,
            "hora_inicio_extraida": vaga.dados.hora_inicio if vaga.dados else None,
            "hora_fim_extraida": vaga.dados.hora_fim if vaga.dados else None,
            "valor_extraido": vaga.dados.valor if vaga.dados else None,
            "observacoes": vaga.dados.observacoes if vaga.dados else None,
            "confianca_extracao": vaga.confianca.media_ponderada() if vaga.confianca else None,
            "status": "extraido",
        }

        result = supabase.table("vagas_grupo") \
            .insert(dados) \
            .execute()

        return UUID(result.data[0]["id"])

    async def processar_normalizacao(self, item: dict) -> ResultadoPipeline:
        """
        Normaliza dados da vaga com entidades do banco.

        Args:
            item: Item da fila com vaga_grupo_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        vaga_grupo_id = item.get("vaga_grupo_id")
        if not vaga_grupo_id:
            return ResultadoPipeline(
                acao="erro",
                motivo="vaga_grupo_id_ausente"
            )

        if isinstance(vaga_grupo_id, str):
            vaga_grupo_id = UUID(vaga_grupo_id)

        resultado = await normalizar_vaga(vaga_grupo_id)

        if resultado.status == "erro":
            logger.warning(f"Normalização com erro para {vaga_grupo_id}")
            # Continua mesmo com erros de normalização - vai para revisão

        return ResultadoPipeline(
            acao="deduplicar",
            vaga_grupo_id=vaga_grupo_id,
            detalhes={
                "hospital_match": resultado.hospital_nome,
                "especialidade_match": resultado.especialidade_nome,
            }
        )

    async def processar_deduplicacao(self, item: dict) -> ResultadoPipeline:
        """
        Processa deduplicação da vaga.

        Args:
            item: Item da fila com vaga_grupo_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        vaga_grupo_id = item.get("vaga_grupo_id")
        if not vaga_grupo_id:
            return ResultadoPipeline(
                acao="erro",
                motivo="vaga_grupo_id_ausente"
            )

        if isinstance(vaga_grupo_id, str):
            vaga_grupo_id = UUID(vaga_grupo_id)

        resultado = await processar_deduplicacao(vaga_grupo_id)

        if resultado.duplicada:
            logger.debug(f"Vaga {vaga_grupo_id} é duplicata de {resultado.principal_id}")
            return ResultadoPipeline(
                acao="finalizar",
                vaga_grupo_id=vaga_grupo_id,
                motivo="duplicada",
                detalhes={"vaga_principal_id": str(resultado.principal_id) if resultado.principal_id else None}
            )

        return ResultadoPipeline(
            acao="importar",
            vaga_grupo_id=vaga_grupo_id
        )

    async def processar_importacao(self, item: dict) -> ResultadoPipeline:
        """
        Processa importação automática.

        Args:
            item: Item da fila com vaga_grupo_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        vaga_grupo_id = item.get("vaga_grupo_id")
        if not vaga_grupo_id:
            return ResultadoPipeline(
                acao="erro",
                motivo="vaga_grupo_id_ausente"
            )

        if isinstance(vaga_grupo_id, str):
            vaga_grupo_id = UUID(vaga_grupo_id)

        resultado = await processar_importacao(vaga_grupo_id)

        return ResultadoPipeline(
            acao="finalizar",
            vaga_grupo_id=vaga_grupo_id,
            detalhes={
                "acao": resultado.acao,
                "vaga_id": resultado.vaga_id,
                "confianca": resultado.score,
            }
        )


# =============================================================================
# Helper para mapeamento de ações para estágios
# =============================================================================

def mapear_acao_para_estagio(acao: str) -> str:
    """
    Mapeia ação do resultado para próximo estágio.

    Args:
        acao: Ação retornada pelo pipeline

    Returns:
        Nome do próximo estágio
    """
    mapeamento = {
        "descartar": "descartado",
        "classificar": "classificacao",
        "extrair": "extracao",
        "normalizar": "normalizacao",
        "deduplicar": "deduplicacao",
        "importar": "importacao",
        "finalizar": "finalizado",
        "erro": "erro",
    }
    return mapeamento.get(acao, "erro")
