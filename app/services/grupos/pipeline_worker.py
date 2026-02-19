"""
Pipeline de processamento de mensagens de grupos.

Sprint 14 - E11 - Worker e Orquestração
Sprint 51 - Correções críticas de persistência
Sprint 63 - Refatoração: helpers compartilhados, feature flags como constantes

Orquestra os estágios de processamento:
1. Heurística - filtro rápido
2. Classificação LLM - confirmação
3. Extração - dados estruturados
4. Normalização - entidades do banco
5. Deduplicação - evitar duplicatas
6. Importação - criar vaga final
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from uuid import UUID

from app.core.config import GruposConfig
from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.heuristica import calcular_score_heuristica
from app.services.grupos.classificador_llm import classificar_com_llm
from app.services.grupos.classificador import (
    atualizar_resultado_heuristica,
    atualizar_resultado_classificacao_llm,
)
from app.services.grupos.normalizador import normalizar_vaga
from app.services.grupos.deduplicador import processar_deduplicacao
from app.services.grupos.importador import processar_importacao

# Sprint 40 - Extrator v2 (opcional, controlado por feature flag)
from app.services.grupos.extrator_v2 import extrair_vagas_v2

# Sprint 52 - Pipeline v3 (LLM unificado)
from app.services.grupos.extrator_v2 import extrair_vagas_v3

logger = get_logger(__name__)


# =============================================================================
# Constantes e Thresholds (centralizados em config)
# =============================================================================

THRESHOLD_HEURISTICA = GruposConfig.THRESHOLD_HEURISTICA
THRESHOLD_HEURISTICA_ALTO = GruposConfig.THRESHOLD_HEURISTICA_ALTO
THRESHOLD_LLM = GruposConfig.THRESHOLD_LLM
MAX_VAGAS_POR_MENSAGEM = GruposConfig.MAX_VAGAS_POR_MENSAGEM

# Feature flags (lidos uma vez na importação do módulo)
PIPELINE_V3_ENABLED = os.environ.get("PIPELINE_V3_ENABLED", "false").lower() == "true"


class AcaoPipeline(str, Enum):
    """Ações possíveis do resultado de cada estágio do pipeline."""

    CLASSIFICAR = "classificar"
    EXTRAIR = "extrair"
    NORMALIZAR = "normalizar"
    DEDUPLICAR = "deduplicar"
    IMPORTAR = "importar"
    FINALIZAR = "finalizar"
    DESCARTAR = "descartar"
    ERRO = "erro"


@dataclass
class ResultadoPipeline:
    """Resultado de um estágio do pipeline."""

    acao: str  # AcaoPipeline value (str Enum para backward compat)
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

    # -------------------------------------------------------------------------
    # Helpers compartilhados
    # -------------------------------------------------------------------------

    async def _fetch_mensagem(
        self, mensagem_id: UUID, campos: str = "*, grupos_whatsapp(nome, regiao)"
    ) -> Optional[dict]:
        """Busca dados da mensagem no banco.

        Args:
            mensagem_id: ID da mensagem
            campos: Select fields (default inclui join com grupo)

        Returns:
            Dados da mensagem ou None
        """
        result = (
            supabase.table("mensagens_grupo")
            .select(campos)
            .eq("id", str(mensagem_id))
            .single()
            .execute()
        )
        return result.data

    def _aplicar_fan_out_cap(self, vagas: list, mensagem_id: UUID, label: str = "") -> list:
        """Limita vagas ao MAX_VAGAS_POR_MENSAGEM.

        Args:
            vagas: Lista de vagas extraídas
            mensagem_id: ID da mensagem (para log)
            label: Prefixo opcional no log (ex: "[Pipeline v3] ")

        Returns:
            Lista truncada se necessário
        """
        if len(vagas) > MAX_VAGAS_POR_MENSAGEM:
            logger.warning(
                f"{label}Mensagem {mensagem_id} gerou {len(vagas)} vagas, "
                f"limitando a {MAX_VAGAS_POR_MENSAGEM}"
            )
            return vagas[:MAX_VAGAS_POR_MENSAGEM]
        return vagas

    async def _criar_vagas_em_lote(
        self, mensagem_id: UUID, vagas: list, msg_data: dict
    ) -> List[str]:
        """Cria vagas_grupo para cada vaga atômica.

        Args:
            mensagem_id: ID da mensagem original
            vagas: Lista de VagaAtomica
            msg_data: Dados completos da mensagem

        Returns:
            Lista de IDs de vagas criadas
        """
        vagas_criadas = []
        for vaga in vagas:
            vaga_id = await self._criar_vaga_grupo_v2(mensagem_id, vaga, msg_data)
            if vaga_id:
                vagas_criadas.append(str(vaga_id))
        return vagas_criadas

    # -------------------------------------------------------------------------
    # Estágios do pipeline
    # -------------------------------------------------------------------------

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

        # Buscar mensagem com dados do grupo
        msg = (
            supabase.table("mensagens_grupo")
            .select("texto, sender_nome, grupo_id, grupos_whatsapp(nome, regiao)")
            .eq("id", str(mensagem_id))
            .single()
            .execute()
        )

        if not msg.data:
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR,
                mensagem_id=mensagem_id,
                motivo="mensagem_nao_encontrada",
            )

        texto = msg.data.get("texto", "")
        msg.data.get("grupos_whatsapp") or {}
        if not texto or len(texto) < 10:
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR, mensagem_id=mensagem_id, motivo="sem_texto"
            )

        # Aplicar heurística
        resultado = calcular_score_heuristica(texto)

        # Sprint 51 - Fix: Salvar resultado da heurística no banco
        await atualizar_resultado_heuristica(mensagem_id=mensagem_id, resultado=resultado)

        if resultado.score < THRESHOLD_HEURISTICA:
            logger.debug(f"Mensagem {mensagem_id} descartada por heurística: {resultado.score:.2f}")
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR,
                mensagem_id=mensagem_id,
                motivo="heuristica_baixa",
                score=resultado.score,
            )

        if resultado.score >= THRESHOLD_HEURISTICA_ALTO:
            # Alta confiança - pula classificação LLM
            logger.debug(f"Mensagem {mensagem_id} aprovada direto: {resultado.score:.2f}")
            return ResultadoPipeline(
                acao=AcaoPipeline.EXTRAIR, mensagem_id=mensagem_id, score=resultado.score
            )

        # Score intermediário - precisa classificação LLM
        return ResultadoPipeline(
            acao=AcaoPipeline.CLASSIFICAR, mensagem_id=mensagem_id, score=resultado.score
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

        # Buscar mensagem com dados do grupo
        msg = (
            supabase.table("mensagens_grupo")
            .select("texto, sender_nome, grupos_whatsapp(nome)")
            .eq("id", str(mensagem_id))
            .single()
            .execute()
        )

        if not msg.data:
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR,
                mensagem_id=mensagem_id,
                motivo="mensagem_nao_encontrada",
            )

        grupo_info = msg.data.get("grupos_whatsapp") or {}

        # Classificar com LLM
        resultado = await classificar_com_llm(
            texto=msg.data.get("texto", ""),
            nome_grupo=grupo_info.get("nome", ""),
            nome_contato=msg.data.get("sender_nome", ""),
        )

        # Sprint 51 - Fix: Salvar resultado da classificação LLM no banco
        await atualizar_resultado_classificacao_llm(mensagem_id=mensagem_id, resultado=resultado)

        if resultado.eh_oferta and resultado.confianca >= THRESHOLD_LLM:
            logger.debug(
                f"Mensagem {mensagem_id} classificada como oferta: {resultado.confianca:.2f}"
            )
            return ResultadoPipeline(
                acao=AcaoPipeline.EXTRAIR, mensagem_id=mensagem_id, confianca=resultado.confianca
            )

        logger.debug(f"Mensagem {mensagem_id} descartada pelo LLM: {resultado.confianca:.2f}")
        return ResultadoPipeline(
            acao=AcaoPipeline.DESCARTAR,
            mensagem_id=mensagem_id,
            motivo="nao_eh_oferta",
            confianca=resultado.confianca,
        )

    async def processar_extracao(self, item: dict) -> ResultadoPipeline:
        """
        Extrai dados estruturados da mensagem.

        Pipeline versões:
        - v3 (Sprint 52): LLM unificado - classifica E extrai em uma chamada
        - v2 (Sprint 40): Regex para extração

        Args:
            item: Item da fila com mensagem_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        if PIPELINE_V3_ENABLED:
            return await self.processar_extracao_v3(item)

        return await self.processar_extracao_v2(item)

    async def processar_extracao_v2(self, item: dict) -> ResultadoPipeline:
        """
        Extrai dados estruturados usando o extrator v2 (Sprint 40).

        O extrator v2 resolve o problema de valores NULL gerando vagas
        atômicas com valor correto baseado no dia da semana.

        Args:
            item: Item da fila com mensagem_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        from datetime import date

        mensagem_id = item.get("mensagem_id")
        if isinstance(mensagem_id, str):
            mensagem_id = UUID(mensagem_id)

        msg_data = await self._fetch_mensagem(mensagem_id)
        if not msg_data:
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR,
                mensagem_id=mensagem_id,
                motivo="mensagem_nao_encontrada",
            )

        grupo_id = msg_data.get("grupo_id")
        if grupo_id:
            grupo_id = UUID(grupo_id) if isinstance(grupo_id, str) else grupo_id

        resultado = await extrair_vagas_v2(
            texto=msg_data.get("texto", ""),
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
            data_referencia=date.today(),
        )

        if not resultado.vagas:
            logger.warning(f"Extração v2 falhou para {mensagem_id}: {resultado.erro}")
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR,
                mensagem_id=mensagem_id,
                motivo=f"extracao_v2_falhou: {resultado.erro}",
            )

        vagas = self._aplicar_fan_out_cap(resultado.vagas, mensagem_id, "[v2] ")
        vagas_criadas = await self._criar_vagas_em_lote(mensagem_id, vagas, msg_data)

        logger.info(
            f"Mensagem {mensagem_id}: {len(vagas_criadas)} vaga(s) extraída(s) [v2] "
            f"(tempo: {resultado.tempo_processamento_ms}ms)"
        )

        return ResultadoPipeline(
            acao=AcaoPipeline.NORMALIZAR,
            mensagem_id=mensagem_id,
            vagas_criadas=vagas_criadas,
            detalhes={
                "extrator": "v2",
                "tempo_ms": resultado.tempo_processamento_ms,
                "warnings": resultado.warnings,
            },
        )

    async def processar_extracao_v3(self, item: dict) -> ResultadoPipeline:
        """
        Extrai dados estruturados usando LLM unificado (Sprint 52).

        O pipeline v3 usa LLM para classificar E extrair em uma única chamada,
        resolvendo problemas como:
        - Bug R$ 202 (regex capturava "202" de "2026")
        - Contexto semântico perdido
        - Normalização automática de especialidades

        Args:
            item: Item da fila com mensagem_id

        Returns:
            ResultadoPipeline com ação a tomar
        """
        from datetime import date
        import time

        mensagem_id = item.get("mensagem_id")
        if isinstance(mensagem_id, str):
            mensagem_id = UUID(mensagem_id)

        start_time = time.time()
        logger.info(f"[Pipeline v3] INICIO mensagem_id={mensagem_id} estagio=EXTRACAO_LLM")

        msg_data = await self._fetch_mensagem(mensagem_id)
        if not msg_data:
            tempo_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[Pipeline v3] DESCARTADA mensagem_id={mensagem_id} "
                f"estagio=EXTRACAO_LLM motivo=mensagem_nao_encontrada "
                f"tempo_ms={tempo_ms}"
            )
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR,
                mensagem_id=mensagem_id,
                motivo="mensagem_nao_encontrada",
            )

        grupo_id = msg_data.get("grupo_id")
        if grupo_id:
            grupo_id = UUID(grupo_id) if isinstance(grupo_id, str) else grupo_id

        grupo_info = msg_data.get("grupos_whatsapp") or {}

        resultado = await extrair_vagas_v3(
            texto=msg_data.get("texto", ""),
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
            nome_grupo=grupo_info.get("nome", ""),
            nome_contato=msg_data.get("sender_nome", ""),
            data_referencia=date.today(),
        )

        if not resultado.vagas:
            tempo_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[Pipeline v3] DESCARTADA mensagem_id={mensagem_id} "
                f"estagio=EXTRACAO_LLM motivo={resultado.erro} "
                f"tempo_ms={tempo_ms} tokens={resultado.tokens_usados}"
            )
            return ResultadoPipeline(
                acao=AcaoPipeline.DESCARTAR,
                mensagem_id=mensagem_id,
                motivo=f"extracao_v3_falhou: {resultado.erro}",
                detalhes={
                    "extrator": "v3",
                    "tokens_usados": resultado.tokens_usados,
                },
            )

        vagas = self._aplicar_fan_out_cap(resultado.vagas, mensagem_id, "[Pipeline v3] ")
        vagas_criadas = await self._criar_vagas_em_lote(mensagem_id, vagas, msg_data)

        tempo_total_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"[Pipeline v3] SUCESSO mensagem_id={mensagem_id} "
            f"estagio=EXTRACAO_LLM vagas_criadas={len(vagas_criadas)} "
            f"tempo_ms={tempo_total_ms} tokens={resultado.tokens_usados} "
            f"llm_ms={resultado.tempo_processamento_ms}"
        )

        return ResultadoPipeline(
            acao=AcaoPipeline.NORMALIZAR,
            mensagem_id=mensagem_id,
            vagas_criadas=vagas_criadas,
            detalhes={
                "extrator": "v3",
                "tempo_ms": resultado.tempo_processamento_ms,
                "tokens_usados": resultado.tokens_usados,
                "warnings": resultado.warnings,
            },
        )

    async def _criar_vaga_grupo_v2(
        self,
        mensagem_id: UUID,
        vaga,  # VagaAtomica
        msg_data: dict,
    ) -> Optional[UUID]:
        """
        Cria registro de vaga_grupo a partir de VagaAtomica (extrator v2).

        Args:
            mensagem_id: ID da mensagem original
            vaga: VagaAtomica do extrator v2
            msg_data: Dados completos da mensagem

        Returns:
            ID da vaga_grupo criada ou None se falhou
        """
        try:
            # Serializar data
            data_str = vaga.data.isoformat() if vaga.data else None

            # Serializar horários
            hora_inicio = vaga.hora_inicio.strftime("%H:%M") if vaga.hora_inicio else None
            hora_fim = vaga.hora_fim.strftime("%H:%M") if vaga.hora_fim else None

            # Determinar valor_tipo
            if vaga.valor and vaga.valor > 0:
                valor_tipo = "fixo"
            else:
                valor_tipo = "a_combinar"

            dados = {
                "mensagem_id": str(mensagem_id),
                "grupo_origem_id": msg_data.get("grupo_id"),
                # Campos do extrator v2
                "hospital_raw": vaga.hospital_raw,
                "setor_raw": vaga.setor_raw,
                "especialidade_raw": vaga.especialidade_raw,
                "data": data_str,
                "hora_inicio": hora_inicio,
                "hora_fim": hora_fim,
                "valor": vaga.valor if vaga.valor > 0 else None,
                "valor_tipo": valor_tipo,
                # Campos adicionais do v2
                "dia_semana": vaga.dia_semana.value if vaga.dia_semana else None,
                "periodo": vaga.periodo.value if vaga.periodo else None,
                "periodo_raw": vaga.periodo.value if vaga.periodo else None,
                "tipo_vaga_raw": vaga.tipo_vaga_raw,
                "endereco_raw": vaga.endereco_raw,
                "cidade": vaga.cidade,
                "estado": vaga.estado,
                "contato_nome": vaga.contato_nome,
                "contato_whatsapp": vaga.contato_whatsapp,
                # Metadados
                "confianca_geral": vaga.confianca_geral,
                "observacoes_raw": vaga.observacoes,
                "status": "extraido",
                # Flag para identificar origem v2
                "dados_minimos_ok": True,
                "data_valida": True,
                # Rastreabilidade: instância que captou
                "instance_name": msg_data.get("instance_name"),
            }

            result = supabase.table("vagas_grupo").insert(dados).execute()

            return UUID(result.data[0]["id"])

        except Exception as e:
            logger.error(f"Erro ao criar vaga_grupo v2: {e}")
            return None

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
            return ResultadoPipeline(acao=AcaoPipeline.ERRO, motivo="vaga_grupo_id_ausente")

        if isinstance(vaga_grupo_id, str):
            vaga_grupo_id = UUID(vaga_grupo_id)

        resultado = await normalizar_vaga(vaga_grupo_id)

        if resultado.status == "erro":
            logger.warning(f"Normalização com erro para {vaga_grupo_id}")
            # Continua mesmo com erros de normalização - vai para revisão

        return ResultadoPipeline(
            acao=AcaoPipeline.DEDUPLICAR,
            vaga_grupo_id=vaga_grupo_id,
            detalhes={
                "hospital_match": resultado.hospital_nome,
                "especialidade_match": resultado.especialidade_nome,
            },
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
            return ResultadoPipeline(acao=AcaoPipeline.ERRO, motivo="vaga_grupo_id_ausente")

        if isinstance(vaga_grupo_id, str):
            vaga_grupo_id = UUID(vaga_grupo_id)

        resultado = await processar_deduplicacao(vaga_grupo_id)

        if resultado.duplicada:
            logger.debug(f"Vaga {vaga_grupo_id} é duplicata de {resultado.principal_id}")
            return ResultadoPipeline(
                acao=AcaoPipeline.FINALIZAR,
                vaga_grupo_id=vaga_grupo_id,
                motivo="duplicada",
                detalhes={
                    "vaga_principal_id": str(resultado.principal_id)
                    if resultado.principal_id
                    else None
                },
            )

        return ResultadoPipeline(acao=AcaoPipeline.IMPORTAR, vaga_grupo_id=vaga_grupo_id)

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
            return ResultadoPipeline(acao=AcaoPipeline.ERRO, motivo="vaga_grupo_id_ausente")

        if isinstance(vaga_grupo_id, str):
            vaga_grupo_id = UUID(vaga_grupo_id)

        resultado = await processar_importacao(vaga_grupo_id)

        return ResultadoPipeline(
            acao=AcaoPipeline.FINALIZAR,
            vaga_grupo_id=vaga_grupo_id,
            detalhes={
                "acao": resultado.acao,
                "vaga_id": resultado.vaga_id,
                "confianca": resultado.score,
            },
        )


# =============================================================================
# Helper para mapeamento de ações para estágios
# =============================================================================


def mapear_acao_para_estagio(acao: str) -> str:
    """
    Mapeia ação do resultado para próximo estágio.

    Aceita tanto AcaoPipeline quanto strings (backward compat).

    Args:
        acao: Ação retornada pelo pipeline (AcaoPipeline ou str)

    Returns:
        Nome do próximo estágio
    """
    mapeamento = {
        AcaoPipeline.DESCARTAR: "descartado",
        AcaoPipeline.CLASSIFICAR: "classificacao",
        AcaoPipeline.EXTRAIR: "extracao",
        AcaoPipeline.NORMALIZAR: "normalizacao",
        AcaoPipeline.DEDUPLICAR: "deduplicacao",
        AcaoPipeline.IMPORTAR: "importacao",
        AcaoPipeline.FINALIZAR: "finalizado",
        AcaoPipeline.ERRO: "erro",
    }
    return mapeamento.get(acao, "erro")
