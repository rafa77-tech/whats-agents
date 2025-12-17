"""
Orquestrador de detectores de situação.

Coordena os 3 detectores e busca conhecimento relevante.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from .detector_objecao import DetectorObjecao, TipoObjecao, ResultadoDeteccao
from .detector_perfil import DetectorPerfil, PerfilMedico, ResultadoPerfil
from .detector_objetivo import DetectorObjetivo, ObjetivoConversa, ResultadoObjetivo
from .buscador import BuscadorConhecimento, ResultadoBusca

logger = logging.getLogger(__name__)


@dataclass
class ContextoSituacao:
    """Contexto completo da situação detectada."""

    # Resultados dos detectores
    objecao: ResultadoDeteccao
    perfil: ResultadoPerfil
    objetivo: ResultadoObjetivo

    # Conhecimento relevante encontrado
    conhecimento: list[ResultadoBusca]

    # Resumo para injeção no prompt
    resumo: str


class OrquestradorConhecimento:
    """Orquestra detectores e busca de conhecimento."""

    def __init__(self):
        self.detector_objecao = DetectorObjecao()
        self.detector_perfil = DetectorPerfil()
        self.detector_objetivo = DetectorObjetivo()
        self.buscador = BuscadorConhecimento()

    async def analisar_situacao(
        self,
        mensagem: str,
        historico: list[str] = None,
        dados_cliente: Optional[dict] = None,
        stage: str = "novo",
        tem_vagas_oferecidas: bool = False,
        dias_inativo: int = 0,
    ) -> ContextoSituacao:
        """
        Analisa situação completa e busca conhecimento relevante.

        Args:
            mensagem: Última mensagem do médico
            historico: Mensagens anteriores
            dados_cliente: Dados do cliente do banco
            stage: Stage atual da jornada
            tem_vagas_oferecidas: Se já ofereceu vagas
            dias_inativo: Dias sem interação

        Returns:
            ContextoSituacao com análise e conhecimento
        """
        logger.info(f"Analisando situação: mensagem='{mensagem[:50]}...'")

        # 1. Detectar objeção
        resultado_objecao = self.detector_objecao.detectar(mensagem)
        logger.debug(f"Objeção: {resultado_objecao.tipo} ({resultado_objecao.confianca})")

        # 2. Detectar perfil
        if dados_cliente:
            resultado_perfil = self.detector_perfil.detectar_por_historico(
                historico=[{"conteudo": m, "tipo": "recebida"} for m in (historico or [])],
                dados_cliente=dados_cliente,
            )
        else:
            resultado_perfil = self.detector_perfil.detectar_por_mensagem(mensagem)
        logger.debug(f"Perfil: {resultado_perfil.perfil} ({resultado_perfil.confianca})")

        # 3. Detectar objetivo
        resultado_objetivo = await self.detector_objetivo.detectar_completo(
            mensagem=mensagem,
            stage=stage,
            historico=historico,
            tem_vagas_oferecidas=tem_vagas_oferecidas,
            tem_objecao=resultado_objecao.tem_objecao,
            dias_inativo=dias_inativo,
        )
        logger.debug(f"Objetivo: {resultado_objetivo.objetivo} ({resultado_objetivo.confianca})")

        # 4. Buscar conhecimento relevante
        conhecimento = await self._buscar_conhecimento(
            objecao=resultado_objecao,
            perfil=resultado_perfil,
            objetivo=resultado_objetivo,
            mensagem=mensagem,
        )
        logger.info(f"Conhecimento: {len(conhecimento)} chunks encontrados")

        # 5. Gerar resumo
        resumo = self._gerar_resumo(
            objecao=resultado_objecao,
            perfil=resultado_perfil,
            objetivo=resultado_objetivo,
            conhecimento=conhecimento,
        )

        return ContextoSituacao(
            objecao=resultado_objecao,
            perfil=resultado_perfil,
            objetivo=resultado_objetivo,
            conhecimento=conhecimento,
            resumo=resumo,
        )

    async def _buscar_conhecimento(
        self,
        objecao: ResultadoDeteccao,
        perfil: ResultadoPerfil,
        objetivo: ResultadoObjetivo,
        mensagem: str,
    ) -> list[ResultadoBusca]:
        """Busca conhecimento relevante baseado na situação."""
        conhecimento = []

        # 1. Se tem objeção com confiança, busca específico
        if objecao.tem_objecao and objecao.confianca >= 0.6:
            resultados = await self.buscador.buscar_para_objecao(mensagem)
            conhecimento.extend(resultados)
            logger.debug(f"Conhecimento objeção: {len(resultados)} chunks")

        # 2. Se perfil identificado com confiança, busca específico
        if perfil.perfil != PerfilMedico.DESCONHECIDO and perfil.confianca >= 0.6:
            resultados = await self.buscador.buscar_para_perfil(perfil.perfil.value)
            conhecimento.extend(resultados)
            logger.debug(f"Conhecimento perfil: {len(resultados)} chunks")

        # 3. Busca por objetivo (se não tem conhecimento específico)
        if len(conhecimento) < 2:
            query = f"Como {objetivo.objetivo.value} médico"
            resultados = await self.buscador.buscar(query=query, limite=2)
            conhecimento.extend(resultados)

        # 4. Limitar e ordenar por relevância
        conhecimento = sorted(conhecimento, key=lambda k: k.similaridade, reverse=True)
        return conhecimento[:5]  # Máximo 5 chunks

    def _gerar_resumo(
        self,
        objecao: ResultadoDeteccao,
        perfil: ResultadoPerfil,
        objetivo: ResultadoObjetivo,
        conhecimento: list[ResultadoBusca],
    ) -> str:
        """Gera resumo da situação para injeção no prompt."""
        partes = []

        # Situação
        partes.append("## SITUAÇÃO DETECTADA\n")

        # Objeção
        if objecao.tem_objecao:
            partes.append(f"**Objeção:** {objecao.tipo.value}")
            if objecao.subtipo:
                partes.append(f" ({objecao.subtipo})")
            partes.append("\n")

        # Perfil
        if perfil.perfil != PerfilMedico.DESCONHECIDO:
            partes.append(f"**Perfil:** {perfil.perfil.value}\n")
            if perfil.recomendacao_abordagem:
                partes.append(f"**Abordagem:** {perfil.recomendacao_abordagem}\n")

        # Objetivo
        partes.append(f"**Objetivo:** {objetivo.objetivo.value}\n")
        if objetivo.proxima_acao:
            partes.append(f"**Próxima ação:** {objetivo.proxima_acao}\n")

        # Conhecimento relevante
        if conhecimento:
            partes.append("\n## CONHECIMENTO RELEVANTE\n")
            for i, k in enumerate(conhecimento[:3], 1):
                partes.append(f"\n### {i}. {k.secao or k.arquivo}\n")
                # Truncar conteúdo longo
                conteudo = k.conteudo[:500] + "..." if len(k.conteudo) > 500 else k.conteudo
                partes.append(f"{conteudo}\n")

        return "".join(partes)

    async def analisar_rapido(self, mensagem: str) -> dict:
        """
        Análise rápida apenas com detecção (sem busca de conhecimento).

        Útil para decisões rápidas sem latência de embedding.

        Args:
            mensagem: Texto da mensagem

        Returns:
            Dict com resultados básicos
        """
        objecao = self.detector_objecao.detectar(mensagem)
        perfil = self.detector_perfil.detectar_por_mensagem(mensagem)
        objetivo = self.detector_objetivo.detectar_por_mensagem(mensagem)

        return {
            "tem_objecao": objecao.tem_objecao,
            "tipo_objecao": objecao.tipo.value if objecao.tem_objecao else None,
            "perfil": perfil.perfil.value,
            "objetivo": objetivo.objetivo.value,
            "confianca_media": (
                objecao.confianca + perfil.confianca + objetivo.confianca
            ) / 3,
        }
