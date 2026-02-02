"""
Early Warning System - Detecção precoce de problemas.

Monitora chips e detecta sinais de alerta antes que se tornem
problemas graves (ban, desconexão, qualidade baixa).
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class SeveridadeAlerta(str, Enum):
    """Níveis de severidade dos alertas."""
    INFO = "info"           # Informativo
    ATENCAO = "atencao"     # Merece atenção
    ALERTA = "alerta"       # Ação recomendada
    CRITICO = "critico"     # Ação urgente necessária


class TipoAlerta(str, Enum):
    """Tipos de alerta detectados."""
    TRUST_CAINDO = "trust_caindo"
    TAXA_BLOCK_ALTA = "taxa_block_alta"
    ERROS_FREQUENTES = "erros_frequentes"
    DELIVERY_BAIXO = "delivery_baixo"
    RESPOSTA_BAIXA = "resposta_baixa"
    DESCONEXAO = "desconexao"
    LIMITE_PROXIMO = "limite_proximo"
    FASE_ESTAGNADA = "fase_estagnada"
    QUALIDADE_META = "qualidade_meta"
    COMPORTAMENTO_ANOMALO = "comportamento_anomalo"


@dataclass
class Alerta:
    """Um alerta gerado pelo sistema."""
    chip_id: str
    tipo: TipoAlerta
    severidade: SeveridadeAlerta
    mensagem: str
    dados: Dict[str, Any]
    recomendacao: str
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = agora_brasilia()


# Thresholds para detecção
THRESHOLDS = {
    # Trust Score
    "trust_queda_rapida": 10,      # Queda de X pontos em 24h = alerta
    "trust_queda_critica": 20,     # Queda de X pontos em 24h = crítico
    "trust_baixo": 40,             # Trust abaixo de X = alerta
    "trust_critico": 20,           # Trust abaixo de X = crítico

    # Taxas
    "taxa_block_atencao": 0.05,    # 5% de bloqueios = atenção
    "taxa_block_alerta": 0.10,     # 10% de bloqueios = alerta
    "taxa_block_critico": 0.20,    # 20% de bloqueios = crítico

    "taxa_delivery_atencao": 0.90, # Abaixo de 90% = atenção
    "taxa_delivery_alerta": 0.80,  # Abaixo de 80% = alerta
    "taxa_delivery_critico": 0.60, # Abaixo de 60% = crítico

    "taxa_resposta_baixa": 0.20,   # Abaixo de 20% = alerta

    # Erros
    "erros_24h_atencao": 3,        # X erros em 24h = atenção
    "erros_24h_alerta": 5,         # X erros em 24h = alerta
    "erros_24h_critico": 10,       # X erros em 24h = crítico

    # Limites
    "limite_proximo_pct": 0.80,    # 80% do limite = alerta

    # Estagnação
    "dias_sem_transicao": 14,      # X dias na mesma fase = atenção
    "dias_sem_transicao_alerta": 21,  # X dias = alerta
}


class EarlyWarningSystem:
    """Sistema de alertas precoces."""

    async def analisar_chip(self, chip_id: str) -> List[Alerta]:
        """
        Analisa um chip e retorna alertas encontrados.

        Args:
            chip_id: ID do chip

        Returns:
            Lista de alertas
        """
        alertas = []

        # Buscar dados do chip
        result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

        if not result.data:
            return alertas

        chip = result.data

        # Executar todas as verificações
        alertas.extend(await self._verificar_trust_score(chip))
        alertas.extend(await self._verificar_taxas(chip))
        alertas.extend(await self._verificar_erros(chip))
        alertas.extend(await self._verificar_limites(chip))
        alertas.extend(await self._verificar_conexao(chip))
        alertas.extend(await self._verificar_estagnacao(chip))

        # Ordenar por severidade
        ordem_severidade = {
            SeveridadeAlerta.CRITICO: 0,
            SeveridadeAlerta.ALERTA: 1,
            SeveridadeAlerta.ATENCAO: 2,
            SeveridadeAlerta.INFO: 3,
        }
        alertas.sort(key=lambda a: ordem_severidade[a.severidade])

        return alertas

    async def _verificar_trust_score(self, chip: dict) -> List[Alerta]:
        """Verifica problemas com trust score."""
        alertas = []
        chip_id = chip["id"]
        trust_atual = chip.get("trust_score", 50)

        # Trust muito baixo
        if trust_atual < THRESHOLDS["trust_critico"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.TRUST_CAINDO,
                severidade=SeveridadeAlerta.CRITICO,
                mensagem=f"Trust Score crítico: {trust_atual}",
                dados={"trust_atual": trust_atual},
                recomendacao="Pausar warmup imediatamente e investigar causa",
            ))
        elif trust_atual < THRESHOLDS["trust_baixo"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.TRUST_CAINDO,
                severidade=SeveridadeAlerta.ALERTA,
                mensagem=f"Trust Score baixo: {trust_atual}",
                dados={"trust_atual": trust_atual},
                recomendacao="Reduzir volume de mensagens e monitorar",
            ))

        # Verificar queda rápida (últimas 24h)
        historico = supabase.table("chip_trust_history").select(
            "score, created_at"
        ).eq("chip_id", chip_id).order(
            "created_at", desc=True
        ).limit(10).execute()

        if historico.data and len(historico.data) >= 2:
            score_anterior = historico.data[-1]["score"]
            queda = score_anterior - trust_atual

            if queda >= THRESHOLDS["trust_queda_critica"]:
                alertas.append(Alerta(
                    chip_id=chip_id,
                    tipo=TipoAlerta.TRUST_CAINDO,
                    severidade=SeveridadeAlerta.CRITICO,
                    mensagem=f"Trust caiu {queda} pontos rapidamente",
                    dados={"queda": queda, "anterior": score_anterior, "atual": trust_atual},
                    recomendacao="Investigar urgente - possível bloqueios ou denúncias",
                ))
            elif queda >= THRESHOLDS["trust_queda_rapida"]:
                alertas.append(Alerta(
                    chip_id=chip_id,
                    tipo=TipoAlerta.TRUST_CAINDO,
                    severidade=SeveridadeAlerta.ALERTA,
                    mensagem=f"Trust caiu {queda} pontos nas últimas horas",
                    dados={"queda": queda, "anterior": score_anterior, "atual": trust_atual},
                    recomendacao="Revisar atividades recentes e reduzir volume",
                ))

        return alertas

    async def _verificar_taxas(self, chip: dict) -> List[Alerta]:
        """Verifica taxas de block, delivery e resposta."""
        alertas = []
        chip_id = chip["id"]

        # Taxa de bloqueio
        taxa_block = chip.get("taxa_block", 0)

        if taxa_block >= THRESHOLDS["taxa_block_critico"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.TAXA_BLOCK_ALTA,
                severidade=SeveridadeAlerta.CRITICO,
                mensagem=f"Taxa de bloqueio crítica: {taxa_block*100:.1f}%",
                dados={"taxa_block": taxa_block},
                recomendacao="PARAR envios imediatamente - risco de ban",
            ))
        elif taxa_block >= THRESHOLDS["taxa_block_alerta"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.TAXA_BLOCK_ALTA,
                severidade=SeveridadeAlerta.ALERTA,
                mensagem=f"Taxa de bloqueio alta: {taxa_block*100:.1f}%",
                dados={"taxa_block": taxa_block},
                recomendacao="Pausar prospecção e revisar abordagem",
            ))
        elif taxa_block >= THRESHOLDS["taxa_block_atencao"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.TAXA_BLOCK_ALTA,
                severidade=SeveridadeAlerta.ATENCAO,
                mensagem=f"Taxa de bloqueio elevada: {taxa_block*100:.1f}%",
                dados={"taxa_block": taxa_block},
                recomendacao="Monitorar e ajustar mensagens se necessário",
            ))

        # Taxa de delivery
        taxa_delivery = chip.get("taxa_delivery", 1.0)

        if taxa_delivery < THRESHOLDS["taxa_delivery_critico"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.DELIVERY_BAIXO,
                severidade=SeveridadeAlerta.CRITICO,
                mensagem=f"Taxa de entrega muito baixa: {taxa_delivery*100:.1f}%",
                dados={"taxa_delivery": taxa_delivery},
                recomendacao="Verificar conexão e status do WhatsApp",
            ))
        elif taxa_delivery < THRESHOLDS["taxa_delivery_alerta"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.DELIVERY_BAIXO,
                severidade=SeveridadeAlerta.ALERTA,
                mensagem=f"Taxa de entrega baixa: {taxa_delivery*100:.1f}%",
                dados={"taxa_delivery": taxa_delivery},
                recomendacao="Investigar problemas de rede ou número bloqueado",
            ))
        elif taxa_delivery < THRESHOLDS["taxa_delivery_atencao"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.DELIVERY_BAIXO,
                severidade=SeveridadeAlerta.ATENCAO,
                mensagem=f"Taxa de entrega abaixo do ideal: {taxa_delivery*100:.1f}%",
                dados={"taxa_delivery": taxa_delivery},
                recomendacao="Monitorar entregas nas próximas horas",
            ))

        # Taxa de resposta
        taxa_resposta = chip.get("taxa_resposta", 0)

        if taxa_resposta < THRESHOLDS["taxa_resposta_baixa"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.RESPOSTA_BAIXA,
                severidade=SeveridadeAlerta.ATENCAO,
                mensagem=f"Taxa de resposta baixa: {taxa_resposta*100:.1f}%",
                dados={"taxa_resposta": taxa_resposta},
                recomendacao="Revisar qualidade das mensagens enviadas",
            ))

        return alertas

    async def _verificar_erros(self, chip: dict) -> List[Alerta]:
        """Verifica erros recentes."""
        alertas = []
        chip_id = chip["id"]
        erros_24h = chip.get("erros_ultimas_24h", 0)

        if erros_24h >= THRESHOLDS["erros_24h_critico"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.ERROS_FREQUENTES,
                severidade=SeveridadeAlerta.CRITICO,
                mensagem=f"{erros_24h} erros nas últimas 24h",
                dados={"erros_24h": erros_24h},
                recomendacao="Pausar operação e investigar logs",
            ))
        elif erros_24h >= THRESHOLDS["erros_24h_alerta"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.ERROS_FREQUENTES,
                severidade=SeveridadeAlerta.ALERTA,
                mensagem=f"{erros_24h} erros nas últimas 24h",
                dados={"erros_24h": erros_24h},
                recomendacao="Reduzir atividade e verificar logs",
            ))
        elif erros_24h >= THRESHOLDS["erros_24h_atencao"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.ERROS_FREQUENTES,
                severidade=SeveridadeAlerta.ATENCAO,
                mensagem=f"{erros_24h} erros nas últimas 24h",
                dados={"erros_24h": erros_24h},
                recomendacao="Monitorar ocorrência de erros",
            ))

        return alertas

    async def _verificar_limites(self, chip: dict) -> List[Alerta]:
        """Verifica proximidade de limites."""
        alertas = []
        chip_id = chip["id"]

        msgs_hoje = chip.get("msgs_enviadas_hoje", 0)
        limite_dia = chip.get("limite_dia", 100)

        if limite_dia > 0:
            uso_pct = msgs_hoje / limite_dia

            if uso_pct >= THRESHOLDS["limite_proximo_pct"]:
                alertas.append(Alerta(
                    chip_id=chip_id,
                    tipo=TipoAlerta.LIMITE_PROXIMO,
                    severidade=SeveridadeAlerta.ATENCAO,
                    mensagem=f"Uso próximo do limite: {uso_pct*100:.0f}% ({msgs_hoje}/{limite_dia})",
                    dados={"msgs_hoje": msgs_hoje, "limite_dia": limite_dia, "uso_pct": uso_pct},
                    recomendacao="Priorizar mensagens essenciais pelo resto do dia",
                ))

        return alertas

    async def _verificar_conexao(self, chip: dict) -> List[Alerta]:
        """Verifica status de conexão."""
        alertas = []
        chip_id = chip["id"]
        status = chip.get("status", "unknown")

        if status == "disconnected":
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.DESCONEXAO,
                severidade=SeveridadeAlerta.CRITICO,
                mensagem="Chip desconectado",
                dados={"status": status},
                recomendacao="Reconectar chip na Evolution API",
            ))
        elif status == "connecting":
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.DESCONEXAO,
                severidade=SeveridadeAlerta.ATENCAO,
                mensagem="Chip reconectando",
                dados={"status": status},
                recomendacao="Aguardar conexão estabilizar",
            ))

        return alertas

    async def _verificar_estagnacao(self, chip: dict) -> List[Alerta]:
        """Verifica estagnação na fase de warmup."""
        alertas = []
        chip_id = chip["id"]
        fase = chip.get("fase_warmup", "repouso")

        # Não verificar para repouso ou operação
        if fase in ["repouso", "operacao"]:
            return alertas

        ultima_transicao = chip.get("ultima_transicao")
        if not ultima_transicao:
            return alertas

        dt_transicao = datetime.fromisoformat(ultima_transicao.replace("Z", "+00:00"))
        dias_na_fase = (datetime.now(dt_transicao.tzinfo) - dt_transicao).days

        if dias_na_fase >= THRESHOLDS["dias_sem_transicao_alerta"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.FASE_ESTAGNADA,
                severidade=SeveridadeAlerta.ALERTA,
                mensagem=f"Chip estagnado na fase '{fase}' há {dias_na_fase} dias",
                dados={"fase": fase, "dias_na_fase": dias_na_fase},
                recomendacao="Revisar métricas e verificar bloqueios para transição",
            ))
        elif dias_na_fase >= THRESHOLDS["dias_sem_transicao"]:
            alertas.append(Alerta(
                chip_id=chip_id,
                tipo=TipoAlerta.FASE_ESTAGNADA,
                severidade=SeveridadeAlerta.ATENCAO,
                mensagem=f"Chip na fase '{fase}' há {dias_na_fase} dias",
                dados={"fase": fase, "dias_na_fase": dias_na_fase},
                recomendacao="Verificar critérios de transição faltantes",
            ))

        return alertas

    async def salvar_alertas(self, alertas: List[Alerta]) -> int:
        """
        Salva alertas no banco.

        Args:
            alertas: Lista de alertas

        Returns:
            Número de alertas salvos
        """
        if not alertas:
            return 0

        registros = []
        for alerta in alertas:
            registros.append({
                "chip_id": alerta.chip_id,
                "tipo": alerta.tipo.value,
                "severidade": alerta.severidade.value,
                "mensagem": alerta.mensagem,
                "dados": alerta.dados,
                "recomendacao": alerta.recomendacao,
                "status": "ativo",
            })

        result = supabase.table("chip_alerts").insert(registros).execute()

        count = len(result.data) if result.data else 0
        logger.info(f"[EarlyWarning] {count} alertas salvos")

        return count

    async def obter_alertas_ativos(
        self,
        chip_id: Optional[str] = None,
        severidade_min: Optional[SeveridadeAlerta] = None,
    ) -> List[Alerta]:
        """
        Obtém alertas ativos.

        Args:
            chip_id: Filtrar por chip
            severidade_min: Severidade mínima

        Returns:
            Lista de alertas
        """
        query = supabase.table("chip_alerts").select("*").eq("status", "ativo")

        if chip_id:
            query = query.eq("chip_id", chip_id)

        result = query.order("created_at", desc=True).limit(100).execute()

        alertas = []
        for row in result.data or []:
            alerta = Alerta(
                chip_id=row["chip_id"],
                tipo=TipoAlerta(row["tipo"]),
                severidade=SeveridadeAlerta(row["severidade"]),
                mensagem=row["mensagem"],
                dados=row.get("dados", {}),
                recomendacao=row["recomendacao"],
                created_at=datetime.fromisoformat(
                    row["created_at"].replace("Z", "+00:00")
                ),
            )

            # Filtrar por severidade se especificado
            if severidade_min:
                ordem = [SeveridadeAlerta.CRITICO, SeveridadeAlerta.ALERTA,
                        SeveridadeAlerta.ATENCAO, SeveridadeAlerta.INFO]
                if ordem.index(alerta.severidade) <= ordem.index(severidade_min):
                    alertas.append(alerta)
            else:
                alertas.append(alerta)

        return alertas

    async def resolver_alerta(
        self,
        alerta_id: str,
        resolucao: str = "resolvido_manual",
    ):
        """
        Marca alerta como resolvido.

        Args:
            alerta_id: ID do alerta
            resolucao: Descrição da resolução
        """
        supabase.table("chip_alerts").update({
            "status": "resolvido",
            "resolucao": resolucao,
            "resolved_at": agora_brasilia().isoformat(),
        }).eq("id", alerta_id).execute()

        logger.info(f"[EarlyWarning] Alerta {alerta_id} resolvido: {resolucao}")

    async def monitorar_pool(self) -> Dict[str, List[Alerta]]:
        """
        Monitora todo o pool de chips.

        Returns:
            Dict com alertas por chip_id
        """
        # Buscar todos os chips ativos
        result = supabase.table("chips").select("id").neq(
            "fase_warmup", "repouso"
        ).eq("status", "connected").execute()

        alertas_por_chip = {}

        for chip in result.data or []:
            chip_id = chip["id"]
            alertas = await self.analisar_chip(chip_id)

            if alertas:
                alertas_por_chip[chip_id] = alertas

                # Salvar alertas novos
                await self.salvar_alertas(alertas)

        # Resumo
        total_alertas = sum(len(a) for a in alertas_por_chip.values())
        criticos = sum(
            1 for alerts in alertas_por_chip.values()
            for a in alerts if a.severidade == SeveridadeAlerta.CRITICO
        )

        logger.info(
            f"[EarlyWarning] Monitoramento: {len(alertas_por_chip)} chips com alertas, "
            f"{total_alertas} alertas total, {criticos} críticos"
        )

        return alertas_por_chip


# Instância global
early_warning = EarlyWarningSystem()


async def analisar_chip(chip_id: str) -> List[Alerta]:
    """Função de conveniência para analisar chip."""
    return await early_warning.analisar_chip(chip_id)


async def monitorar_pool() -> Dict[str, List[Alerta]]:
    """Função de conveniência para monitorar pool."""
    return await early_warning.monitorar_pool()


async def obter_alertas(chip_id: Optional[str] = None) -> List[Alerta]:
    """Função de conveniência para obter alertas."""
    return await early_warning.obter_alertas_ativos(chip_id)
