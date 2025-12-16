"""
Servico de fluxo de aprovacao de briefings.

Sprint 11 - Epic 04: Fluxo de Aprovacao

Gerencia o ciclo de vida de um briefing:
1. Briefing processado -> aguardando aprovacao
2. Gestor responde -> detectar intencao
3. Aprovado/Ajuste/Duvida/Cancelado
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict

from app.services.supabase import supabase
from app.services.briefing_analyzer import (
    AnaliseResult,
    analisar_briefing,
    formatar_plano_para_documento,
    formatar_plano_para_slack,
)
from app.services.google_docs import (
    ler_documento,
    atualizar_secao_plano,
    adicionar_linha_historico,
)

logger = logging.getLogger(__name__)


# =============================================================================
# TIPOS
# =============================================================================

class StatusAprovacao(str, Enum):
    """Estados possiveis de um briefing."""
    AGUARDANDO = "aguardando"
    APROVADO = "aprovado"
    AJUSTE_SOLICITADO = "ajuste"
    DUVIDA = "duvida"
    CANCELADO = "cancelado"
    EXECUTANDO = "executando"
    CONCLUIDO = "concluido"


@dataclass
class BriefingPendente:
    """Briefing aguardando aprovacao."""
    id: str
    doc_id: str
    doc_nome: str
    doc_url: str
    channel_id: str
    user_id: str
    plano: AnaliseResult
    status: StatusAprovacao
    criado_em: datetime
    atualizado_em: datetime
    expira_em: datetime


# =============================================================================
# KEYWORDS PARA DETECCAO
# =============================================================================

KEYWORDS_APROVACAO = [
    "pode ir", "vai la", "manda ver", "manda bala",
    "sim", "aprovado", "ok", "blz", "beleza",
    "go", "show", "perfeito", "otimo", "otima",
    "pode executar", "pode rodar", "pode comecar",
    "aprovo", "aprovei", "ta bom", "fechado",
]

KEYWORDS_CANCELAR = [
    "cancela", "para", "esquece", "deixa pra la",
    "nao precisa", "mudou", "nao vai mais",
    "desiste", "para tudo", "aborta",
]

KEYWORDS_AJUSTE = [
    "ajusta", "muda", "altera", "remove", "adiciona",
    "na verdade", "mas", "esqueci", "faltou",
    "corrige", "troca", "inverte", "tira", "poe",
]


# =============================================================================
# SERVICO DE APROVACAO
# =============================================================================

class BriefingAprovacaoService:
    """Gerencia fluxo de aprovacao de briefings."""

    async def criar_pendente(
        self,
        doc_id: str,
        doc_nome: str,
        doc_url: str,
        channel_id: str,
        user_id: str,
        plano: AnaliseResult
    ) -> str:
        """
        Cria registro de briefing pendente de aprovacao.

        Args:
            doc_id: ID do documento
            doc_nome: Nome do documento
            doc_url: URL do documento
            channel_id: Canal Slack
            user_id: Usuario Slack que pediu
            plano: Resultado da analise

        Returns:
            ID do registro criado
        """
        agora = datetime.now()
        expira = agora + timedelta(hours=24)

        data = {
            "doc_id": doc_id,
            "doc_nome": doc_nome,
            "doc_url": doc_url,
            "channel_id": channel_id,
            "user_id": user_id,
            "plano": json.dumps(plano.to_dict()),
            "status": StatusAprovacao.AGUARDANDO.value,
            "criado_em": agora.isoformat(),
            "atualizado_em": agora.isoformat(),
            "expira_em": expira.isoformat(),
        }

        result = supabase.table("briefings_pendentes").insert(data).execute()

        if result.data:
            briefing_id = result.data[0]["id"]
            logger.info(f"Briefing pendente criado: {briefing_id} - {doc_nome}")
            return briefing_id

        raise Exception("Erro ao criar briefing pendente")

    async def buscar_pendente(self, channel_id: str) -> Optional[BriefingPendente]:
        """
        Busca briefing pendente no canal.

        Retorna o mais recente nao expirado.

        Args:
            channel_id: ID do canal Slack

        Returns:
            BriefingPendente ou None
        """
        agora = datetime.now().isoformat()

        result = supabase.table("briefings_pendentes")\
            .select("*")\
            .eq("channel_id", channel_id)\
            .eq("status", StatusAprovacao.AGUARDANDO.value)\
            .gt("expira_em", agora)\
            .order("criado_em", desc=True)\
            .limit(1)\
            .execute()

        if not result.data:
            return None

        row = result.data[0]

        # Parsear plano
        plano_dict = json.loads(row["plano"])
        plano = self._dict_para_analise(plano_dict)

        return BriefingPendente(
            id=row["id"],
            doc_id=row["doc_id"],
            doc_nome=row["doc_nome"],
            doc_url=row["doc_url"],
            channel_id=row["channel_id"],
            user_id=row["user_id"],
            plano=plano,
            status=StatusAprovacao(row["status"]),
            criado_em=datetime.fromisoformat(row["criado_em"]),
            atualizado_em=datetime.fromisoformat(row["atualizado_em"]),
            expira_em=datetime.fromisoformat(row["expira_em"]),
        )

    async def processar_resposta(
        self,
        briefing: BriefingPendente,
        resposta: str
    ) -> Tuple[StatusAprovacao, str]:
        """
        Processa resposta do gestor.

        Args:
            briefing: Briefing pendente
            resposta: Texto da resposta

        Returns:
            Tuple de (novo_status, mensagem_julia)
        """
        # Detectar intencao
        intencao = self._detectar_intencao(resposta)

        if intencao == StatusAprovacao.APROVADO:
            await self._marcar_status(briefing.id, StatusAprovacao.APROVADO)
            # Atualizar documento
            await atualizar_secao_plano(
                briefing.doc_id,
                formatar_plano_para_documento(briefing.plano).replace(
                    "Aguardando aprovacao",
                    f"Aprovado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
            )
            await adicionar_linha_historico(briefing.doc_id, "Plano aprovado", "-")
            return (
                StatusAprovacao.APROVADO,
                "Show! Vou comecar a executar o plano. Te aviso quando tiver novidades!"
            )

        elif intencao == StatusAprovacao.CANCELADO:
            await self._marcar_status(briefing.id, StatusAprovacao.CANCELADO)
            await adicionar_linha_historico(briefing.doc_id, "Plano cancelado", "Gestor cancelou")
            return (
                StatusAprovacao.CANCELADO,
                "Blz, cancelei o plano. Se precisar de novo eh soh pedir!"
            )

        elif intencao == StatusAprovacao.AJUSTE_SOLICITADO:
            # Manter aguardando, mas registrar que pediu ajuste
            await adicionar_linha_historico(briefing.doc_id, "Ajuste solicitado", resposta[:50])
            return (
                StatusAprovacao.AJUSTE_SOLICITADO,
                f"Entendi! Voce quer que eu ajuste: {resposta}\n\nMe fala mais detalhes do que precisa mudar?"
            )

        else:  # DUVIDA
            return (
                StatusAprovacao.DUVIDA,
                "Opa, pode perguntar! To aqui pra ajudar a entender o plano."
            )

    def _detectar_intencao(self, resposta: str) -> StatusAprovacao:
        """Detecta intencao na resposta do gestor."""
        resposta_lower = resposta.lower().strip()

        # Aprovacao
        for kw in KEYWORDS_APROVACAO:
            if kw in resposta_lower:
                return StatusAprovacao.APROVADO

        # Cancelamento
        for kw in KEYWORDS_CANCELAR:
            if kw in resposta_lower:
                return StatusAprovacao.CANCELADO

        # Ajuste
        for kw in KEYWORDS_AJUSTE:
            if kw in resposta_lower:
                return StatusAprovacao.AJUSTE_SOLICITADO

        # Se tem pergunta, eh duvida
        if "?" in resposta:
            return StatusAprovacao.DUVIDA

        # Default: duvida (melhor perguntar do que fazer errado)
        return StatusAprovacao.DUVIDA

    async def _marcar_status(self, briefing_id: str, status: StatusAprovacao) -> None:
        """Atualiza status de um briefing."""
        supabase.table("briefings_pendentes").update({
            "status": status.value,
            "atualizado_em": datetime.now().isoformat()
        }).eq("id", briefing_id).execute()

    def _dict_para_analise(self, data: dict) -> AnaliseResult:
        """Converte dict para AnaliseResult."""
        from app.services.briefing_analyzer import (
            AnaliseResult, TipoDemanda, PassoPlano, NecessidadeIdentificada
        )

        # Converter passos
        passos = []
        for p in data.get("passos", []):
            passos.append(PassoPlano(
                numero=p.get("numero", 0),
                descricao=p.get("descricao", ""),
                prazo=p.get("prazo"),
                requer_ajuda=p.get("requer_ajuda", False),
                tipo_ajuda=p.get("tipo_ajuda")
            ))

        # Converter necessidades
        necessidades = []
        for n in data.get("necessidades", []):
            necessidades.append(NecessidadeIdentificada(
                tipo=n.get("tipo", "dados"),
                descricao=n.get("descricao", ""),
                caso_uso=n.get("caso_uso", ""),
                alternativa_temporaria=n.get("alternativa_temporaria"),
                prioridade=n.get("prioridade", "media")
            ))

        # Tipo de demanda
        tipo_str = data.get("tipo_demanda", "operacional")
        try:
            tipo = TipoDemanda(tipo_str)
        except ValueError:
            tipo = TipoDemanda.OPERACIONAL

        return AnaliseResult(
            doc_id=data.get("doc_id", ""),
            doc_nome=data.get("doc_nome", ""),
            timestamp=data.get("timestamp", ""),
            resumo_demanda=data.get("resumo_demanda", ""),
            tipo_demanda=tipo,
            deadline=data.get("deadline"),
            urgencia=data.get("urgencia", "media"),
            dados_disponiveis=data.get("dados_disponiveis", []),
            dados_faltantes=data.get("dados_faltantes", []),
            ferramentas_necessarias=data.get("ferramentas_necessarias", []),
            ferramentas_faltantes=data.get("ferramentas_faltantes", []),
            perguntas_para_gestor=data.get("perguntas_para_gestor", []),
            passos=passos,
            metricas_sucesso=data.get("metricas_sucesso", []),
            riscos=data.get("riscos", []),
            necessidades=necessidades,
            viavel=data.get("viavel", True),
            ressalvas=data.get("ressalvas", []),
            avaliacao_honesta=data.get("avaliacao_honesta", "")
        )


# =============================================================================
# FLUXO COMPLETO DE BRIEFING
# =============================================================================

async def processar_briefing_completo(
    doc_id: str,
    doc_nome: str,
    conteudo: str,
    doc_url: str,
    channel_id: str,
    user_id: str
) -> Tuple[str, str]:
    """
    Processa briefing completo: analisa, escreve no doc, cria pendente.

    Args:
        doc_id: ID do documento
        doc_nome: Nome do documento
        conteudo: Conteudo do briefing
        doc_url: URL do documento
        channel_id: Canal Slack
        user_id: Usuario Slack

    Returns:
        Tuple de (briefing_id, mensagem_para_slack)
    """
    # 1. Analisar com Sonnet
    logger.info(f"Analisando briefing: {doc_nome}")
    analise = await analisar_briefing(doc_id, doc_nome, conteudo)

    # 2. Escrever plano no documento
    logger.info(f"Escrevendo plano no documento: {doc_nome}")
    plano_formatado = formatar_plano_para_documento(analise)
    await atualizar_secao_plano(doc_id, plano_formatado)

    # 3. Criar registro pendente
    service = BriefingAprovacaoService()
    briefing_id = await service.criar_pendente(
        doc_id=doc_id,
        doc_nome=doc_nome,
        doc_url=doc_url,
        channel_id=channel_id,
        user_id=user_id,
        plano=analise
    )

    # 4. Formatar mensagem para Slack
    mensagem = formatar_plano_para_slack(analise, doc_url)

    return briefing_id, mensagem


# =============================================================================
# INSTANCIA SINGLETON
# =============================================================================

_service: Optional[BriefingAprovacaoService] = None


def get_aprovacao_service() -> BriefingAprovacaoService:
    """Retorna instancia singleton do servico de aprovacao."""
    global _service
    if _service is None:
        _service = BriefingAprovacaoService()
    return _service
