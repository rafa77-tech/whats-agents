"""
Warming Scheduler - Agendamento de atividades de aquecimento.

Distribui atividades de warmup ao longo do dia respeitando:
- Horário comercial (8h-20h)
- Limites de taxa por fase
- Intervalos humanos entre ações
- Balanceamento entre chips
"""
import logging
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from enum import Enum

from app.services.supabase import supabase
from app.services.warmer.trust_score import TrustScoreEngine

logger = logging.getLogger(__name__)


class TipoAtividade(str, Enum):
    """Tipos de atividade de warmup."""
    CONVERSA_PAR = "conversa_par"           # Conversa com outro chip
    ENTRAR_GRUPO = "entrar_grupo"           # Entrar em grupo
    MENSAGEM_GRUPO = "mensagem_grupo"       # Enviar no grupo
    ATUALIZAR_PERFIL = "atualizar_perfil"   # Mudar foto/status
    ENVIAR_MIDIA = "enviar_midia"           # Enviar áudio/imagem
    MARCAR_LIDO = "marcar_lido"             # Marcar msgs como lidas


@dataclass
class AtividadeAgendada:
    """Uma atividade agendada."""
    id: Optional[str] = None
    chip_id: str = ""
    tipo: TipoAtividade = TipoAtividade.CONVERSA_PAR
    horario: datetime = None
    dados: Dict[str, Any] = None
    prioridade: int = 5  # 1-10, maior = mais prioritário
    status: str = "agendada"

    def __post_init__(self):
        if self.dados is None:
            self.dados = {}
        if self.horario is None:
            self.horario = datetime.now()


# Configuração de atividades por fase
ATIVIDADES_POR_FASE = {
    "setup": {
        "atividades": [TipoAtividade.CONVERSA_PAR],
        "por_dia": (2, 5),
        "intervalo_min_minutos": 60,
    },
    "primeiros_contatos": {
        "atividades": [
            TipoAtividade.CONVERSA_PAR,
            TipoAtividade.MARCAR_LIDO,
        ],
        "por_dia": (5, 10),
        "intervalo_min_minutos": 45,
    },
    "expansao": {
        "atividades": [
            TipoAtividade.CONVERSA_PAR,
            TipoAtividade.ENTRAR_GRUPO,
            TipoAtividade.MARCAR_LIDO,
            TipoAtividade.ENVIAR_MIDIA,
        ],
        "por_dia": (10, 20),
        "intervalo_min_minutos": 30,
    },
    "pre_operacao": {
        "atividades": [
            TipoAtividade.CONVERSA_PAR,
            TipoAtividade.MENSAGEM_GRUPO,
            TipoAtividade.ENVIAR_MIDIA,
            TipoAtividade.ATUALIZAR_PERFIL,
        ],
        "por_dia": (15, 30),
        "intervalo_min_minutos": 20,
    },
    "teste_graduacao": {
        "atividades": [
            TipoAtividade.CONVERSA_PAR,
            TipoAtividade.MENSAGEM_GRUPO,
            TipoAtividade.ENVIAR_MIDIA,
        ],
        "por_dia": (20, 40),
        "intervalo_min_minutos": 15,
    },
    "operacao": {
        "atividades": [
            TipoAtividade.CONVERSA_PAR,
            TipoAtividade.MENSAGEM_GRUPO,
        ],
        "por_dia": (5, 15),  # Manutenção apenas
        "intervalo_min_minutos": 60,
    },
}

# Distribuição de horários (mais atividade no meio do dia)
DISTRIBUICAO_HORARIA = {
    8: 0.5,   # 8h - pouca atividade
    9: 0.8,   # 9h - aumentando
    10: 1.0,  # 10h - normal
    11: 1.2,  # 11h - pico
    12: 0.7,  # 12h - almoço
    13: 0.6,  # 13h - pós-almoço
    14: 1.0,  # 14h - retomando
    15: 1.2,  # 15h - pico
    16: 1.0,  # 16h - normal
    17: 0.8,  # 17h - diminuindo
    18: 0.6,  # 18h - fim do dia
    19: 0.4,  # 19h - pouca atividade
}


class WarmingScheduler:
    """Agendador de atividades de aquecimento."""

    # Horário de operação
    HORA_INICIO = 8
    HORA_FIM = 20

    def __init__(self):
        self.trust_engine = TrustScoreEngine()

    def _esta_em_horario_comercial(self, dt: datetime) -> bool:
        """Verifica se datetime está em horário comercial."""
        if dt.weekday() >= 5:  # Fim de semana
            return False
        return self.HORA_INICIO <= dt.hour < self.HORA_FIM

    def _proximo_horario_valido(self, base: datetime) -> datetime:
        """
        Calcula próximo horário válido para atividade.

        Args:
            base: Datetime de referência

        Returns:
            Próximo datetime válido
        """
        dt = base

        # Se já passou do horário, vai para amanhã
        if dt.hour >= self.HORA_FIM:
            dt = dt.replace(hour=self.HORA_INICIO, minute=0, second=0)
            dt += timedelta(days=1)

        # Se antes do horário, ajusta para início
        if dt.hour < self.HORA_INICIO:
            dt = dt.replace(hour=self.HORA_INICIO, minute=0, second=0)

        # Pula fim de semana
        while dt.weekday() >= 5:
            dt += timedelta(days=1)

        return dt

    def _gerar_horarios_distribuidos(
        self,
        data: datetime,
        quantidade: int,
        intervalo_min: int,
    ) -> List[datetime]:
        """
        Gera horários distribuídos ao longo do dia.

        Args:
            data: Data base
            quantidade: Número de horários
            intervalo_min: Intervalo mínimo em minutos

        Returns:
            Lista de datetimes
        """
        horarios = []

        # Calcular janela disponível
        inicio = data.replace(hour=self.HORA_INICIO, minute=0, second=0)
        fim = data.replace(hour=self.HORA_FIM, minute=0, second=0)
        duracao_total = (fim - inicio).total_seconds() / 60  # Em minutos

        # Distribuir baseado nos pesos horários
        slots = []
        for hora in range(self.HORA_INICIO, self.HORA_FIM):
            peso = DISTRIBUICAO_HORARIA.get(hora, 1.0)
            # Criar slots de 15 minutos
            for minuto in [0, 15, 30, 45]:
                slots.append((hora, minuto, peso))

        # Selecionar slots baseado nos pesos
        peso_total = sum(s[2] for s in slots)
        slots_normalizados = [(h, m, p / peso_total) for h, m, p in slots]

        # Amostrar slots
        selecionados = []
        for _ in range(quantidade * 2):  # Pegar mais para filtrar
            r = random.random()
            acumulado = 0
            for hora, minuto, peso in slots_normalizados:
                acumulado += peso
                if r <= acumulado:
                    dt = data.replace(hour=hora, minute=minuto, second=0, microsecond=0)
                    # Adicionar variação de 0-14 minutos
                    dt += timedelta(minutes=random.randint(0, 14))
                    selecionados.append(dt)
                    break

        # Ordenar e filtrar por intervalo mínimo
        selecionados.sort()
        horarios = [selecionados[0]] if selecionados else []

        for dt in selecionados[1:]:
            if len(horarios) >= quantidade:
                break

            ultimo = horarios[-1]
            diff = (dt - ultimo).total_seconds() / 60

            if diff >= intervalo_min:
                horarios.append(dt)

        return horarios[:quantidade]

    async def planejar_dia(
        self,
        chip_id: str,
        data: Optional[datetime] = None,
    ) -> List[AtividadeAgendada]:
        """
        Planeja atividades de um chip para o dia.

        Args:
            chip_id: ID do chip
            data: Data a planejar (hoje se não especificado)

        Returns:
            Lista de atividades agendadas
        """
        if data is None:
            data = datetime.now()

        # Buscar dados do chip
        result = supabase.table("chips").select(
            "fase_warmup, trust_score, limite_dia, limite_hora"
        ).eq("id", chip_id).single().execute()

        if not result.data:
            logger.error(f"[Scheduler] Chip {chip_id} não encontrado")
            return []

        chip = result.data
        fase = chip.get("fase_warmup", "setup")

        # Configuração da fase
        config = ATIVIDADES_POR_FASE.get(fase, ATIVIDADES_POR_FASE["setup"])

        # Calcular quantidade de atividades
        min_atv, max_atv = config["por_dia"]

        # Ajustar baseado no trust score
        trust = chip.get("trust_score", 50)
        fator_trust = min(1.0, trust / 80)  # Trust < 80 reduz atividades

        quantidade = int(random.randint(min_atv, max_atv) * fator_trust)
        quantidade = min(quantidade, chip.get("limite_dia", 100))

        # Gerar horários
        horarios = self._gerar_horarios_distribuidos(
            data,
            quantidade,
            config["intervalo_min_minutos"]
        )

        # Criar atividades
        atividades = []
        tipos_disponiveis = config["atividades"]

        for i, horario in enumerate(horarios):
            # Variar tipos de atividade
            tipo = random.choice(tipos_disponiveis)

            # Prioridade diminui ao longo do dia
            prioridade = max(1, 10 - (i * 10 // len(horarios)))

            atividade = AtividadeAgendada(
                chip_id=chip_id,
                tipo=tipo,
                horario=horario,
                prioridade=prioridade,
            )
            atividades.append(atividade)

        logger.info(
            f"[Scheduler] Planejadas {len(atividades)} atividades "
            f"para chip {chip_id[:8]}... fase={fase}"
        )

        return atividades

    async def salvar_agenda(
        self,
        atividades: List[AtividadeAgendada],
    ) -> int:
        """
        Salva atividades no banco.

        Args:
            atividades: Lista de atividades

        Returns:
            Número de atividades salvas
        """
        if not atividades:
            return 0

        registros = []
        for atv in atividades:
            registros.append({
                "chip_id": atv.chip_id,
                "tipo": atv.tipo.value,
                "scheduled_for": atv.horario.isoformat(),
                "dados": atv.dados,
                "prioridade": atv.prioridade,
                "status": "agendada",
            })

        result = supabase.table("warmup_schedule").insert(registros).execute()

        count = len(result.data) if result.data else 0
        logger.info(f"[Scheduler] {count} atividades salvas no banco")

        return count

    async def obter_proximas_atividades(
        self,
        limite: int = 10,
        chip_id: Optional[str] = None,
    ) -> List[AtividadeAgendada]:
        """
        Obtém próximas atividades a executar.

        Args:
            limite: Máximo de atividades
            chip_id: Filtrar por chip (opcional)

        Returns:
            Lista de atividades ordenadas por horário
        """
        agora = datetime.now()

        query = supabase.table("warmup_schedule").select("*").eq(
            "status", "agendada"
        ).gte(
            "scheduled_for", (agora - timedelta(minutes=5)).isoformat()
        ).lte(
            "scheduled_for", (agora + timedelta(hours=1)).isoformat()
        ).order("scheduled_for").limit(limite)

        if chip_id:
            query = query.eq("chip_id", chip_id)

        result = query.execute()

        atividades = []
        for row in result.data or []:
            atividades.append(AtividadeAgendada(
                id=row["id"],
                chip_id=row["chip_id"],
                tipo=TipoAtividade(row["tipo"]),
                horario=datetime.fromisoformat(
                    row["scheduled_for"].replace("Z", "+00:00")
                ),
                dados=row.get("dados", {}),
                prioridade=row.get("prioridade", 5),
                status=row["status"],
            ))

        return atividades

    async def marcar_executada(
        self,
        atividade_id: str,
        sucesso: bool = True,
        resultado: Optional[dict] = None,
    ):
        """
        Marca atividade como executada.

        Args:
            atividade_id: ID da atividade
            sucesso: Se foi bem-sucedida
            resultado: Dados do resultado
        """
        status = "executada" if sucesso else "falhou"

        supabase.table("warmup_schedule").update({
            "status": status,
            "executed_at": datetime.now().isoformat(),
            "resultado": resultado or {},
        }).eq("id", atividade_id).execute()

        logger.debug(f"[Scheduler] Atividade {atividade_id} marcada como {status}")

    async def cancelar_atividades(
        self,
        chip_id: str,
        motivo: str = "cancelamento_manual",
    ) -> int:
        """
        Cancela todas as atividades pendentes de um chip.

        Args:
            chip_id: ID do chip
            motivo: Motivo do cancelamento

        Returns:
            Número de atividades canceladas
        """
        result = supabase.table("warmup_schedule").update({
            "status": "cancelada",
            "resultado": {"motivo": motivo},
        }).eq("chip_id", chip_id).eq("status", "agendada").execute()

        count = len(result.data) if result.data else 0
        logger.info(f"[Scheduler] {count} atividades canceladas para chip {chip_id[:8]}...")

        return count

    async def obter_estatisticas(
        self,
        chip_id: Optional[str] = None,
        data: Optional[datetime] = None,
    ) -> dict:
        """
        Obtém estatísticas de atividades.

        Args:
            chip_id: Filtrar por chip
            data: Filtrar por data

        Returns:
            Dict com estatísticas
        """
        if data is None:
            data = datetime.now()

        inicio_dia = data.replace(hour=0, minute=0, second=0)
        fim_dia = data.replace(hour=23, minute=59, second=59)

        query = supabase.table("warmup_schedule").select(
            "status, tipo"
        ).gte("scheduled_for", inicio_dia.isoformat()).lte(
            "scheduled_for", fim_dia.isoformat()
        )

        if chip_id:
            query = query.eq("chip_id", chip_id)

        result = query.execute()

        stats = {
            "total": 0,
            "agendadas": 0,
            "executadas": 0,
            "falharam": 0,
            "canceladas": 0,
            "por_tipo": {},
        }

        for row in result.data or []:
            stats["total"] += 1
            status = row["status"]
            tipo = row["tipo"]

            if status == "agendada":
                stats["agendadas"] += 1
            elif status == "executada":
                stats["executadas"] += 1
            elif status == "falhou":
                stats["falharam"] += 1
            elif status == "cancelada":
                stats["canceladas"] += 1

            stats["por_tipo"][tipo] = stats["por_tipo"].get(tipo, 0) + 1

        return stats


# Instância global
scheduler = WarmingScheduler()


async def planejar_dia_chip(chip_id: str) -> List[AtividadeAgendada]:
    """Função de conveniência para planejar dia."""
    return await scheduler.planejar_dia(chip_id)


async def obter_proximas(limite: int = 10) -> List[AtividadeAgendada]:
    """Função de conveniência para obter próximas atividades."""
    return await scheduler.obter_proximas_atividades(limite)
