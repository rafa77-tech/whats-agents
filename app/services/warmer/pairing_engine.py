"""
Pairing Engine - Pareamento de chips para warmup.

Responsável por criar pares de chips que conversam entre si
durante o processo de aquecimento, garantindo naturalidade
e distribuição equilibrada.
"""
import logging
import random
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class ChipInfo:
    """Informações de um chip para pareamento."""
    id: str
    telefone: str
    ddd: int
    fase_warmup: str
    trust_score: int
    msgs_enviadas_hoje: int
    msgs_recebidas_hoje: int
    ultimo_pareamento: Optional[datetime] = None
    pares_recentes: List[str] = None

    def __post_init__(self):
        if self.pares_recentes is None:
            self.pares_recentes = []


@dataclass
class ParInfo:
    """Informação de um par de chips."""
    chip_a: ChipInfo
    chip_b: ChipInfo
    score_compatibilidade: float
    motivo: str


# Mapeamento de DDDs por região para pareamento preferencial
REGIOES_DDD = {
    "sp_capital": [11],
    "sp_interior": [12, 13, 14, 15, 16, 17, 18, 19],
    "rj": [21, 22, 24],
    "mg": [31, 32, 33, 34, 35, 37, 38],
    "es": [27, 28],
    "sul": [41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55],
    "nordeste": [71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89],
    "norte": [63, 64, 65, 66, 67, 68, 69, 91, 92, 93, 94, 95, 96, 97],
    "centro_oeste": [61, 62],
}

# Fases que podem parear entre si
FASES_COMPATIVEIS = {
    "setup": ["setup", "primeiros_contatos"],
    "primeiros_contatos": ["setup", "primeiros_contatos", "expansao"],
    "expansao": ["primeiros_contatos", "expansao", "pre_operacao"],
    "pre_operacao": ["expansao", "pre_operacao", "teste_graduacao"],
    "teste_graduacao": ["pre_operacao", "teste_graduacao", "operacao"],
    "operacao": ["teste_graduacao", "operacao"],
}


class PairingEngine:
    """Engine de pareamento de chips."""

    # Pesos para score de compatibilidade
    PESO_MESMA_REGIAO = 30
    PESO_MESMO_DDD = 50
    PESO_FASE_COMPATIVEL = 40
    PESO_TRUST_SIMILAR = 20
    PESO_BALANCO_MSGS = 20
    PENALIDADE_PAR_RECENTE = -50
    PENALIDADE_MESMO_CHIP = -1000

    # Limites
    MAX_PARES_POR_DIA = 5  # Máximo de pares diferentes por chip por dia
    MIN_INTERVALO_MESMO_PAR = timedelta(hours=4)  # Mínimo entre conversas do mesmo par

    def __init__(self):
        self.cache_chips: List[ChipInfo] = []
        self.ultimo_refresh: Optional[datetime] = None

    async def _carregar_chips_disponiveis(self) -> List[ChipInfo]:
        """
        Carrega chips disponíveis para pareamento.

        Returns:
            Lista de ChipInfo
        """
        # Buscar chips ativos em fases de warmup
        fases_validas = list(FASES_COMPATIVEIS.keys())

        result = supabase.table("chips").select(
            "id, telefone, fase_warmup, trust_score, "
            "msgs_enviadas_hoje, msgs_recebidas_hoje, ultimo_pareamento"
        ).eq("status", "connected").in_("fase_warmup", fases_validas).execute()

        chips = []
        for row in result.data or []:
            telefone = row["telefone"]
            ddd = int(telefone[2:4]) if len(telefone) >= 4 else 11

            ultimo_pareamento = None
            if row.get("ultimo_pareamento"):
                ultimo_pareamento = datetime.fromisoformat(
                    row["ultimo_pareamento"].replace("Z", "+00:00")
                )

            chips.append(ChipInfo(
                id=row["id"],
                telefone=telefone,
                ddd=ddd,
                fase_warmup=row["fase_warmup"],
                trust_score=row.get("trust_score", 50),
                msgs_enviadas_hoje=row.get("msgs_enviadas_hoje", 0),
                msgs_recebidas_hoje=row.get("msgs_recebidas_hoje", 0),
                ultimo_pareamento=ultimo_pareamento,
            ))

        logger.info(f"[Pairing] {len(chips)} chips disponíveis para pareamento")

        return chips

    async def _carregar_pares_recentes(
        self,
        chip_id: str,
        horas: int = 24
    ) -> List[str]:
        """
        Carrega IDs de chips pareados recentemente.

        Args:
            chip_id: ID do chip
            horas: Janela de tempo em horas

        Returns:
            Lista de IDs de chips pareados
        """
        desde = datetime.now() - timedelta(hours=horas)

        result = supabase.table("chip_pairs").select(
            "chip_a_id, chip_b_id"
        ).or_(
            f"chip_a_id.eq.{chip_id},chip_b_id.eq.{chip_id}"
        ).gte("created_at", desde.isoformat()).execute()

        pares = set()
        for row in result.data or []:
            if row["chip_a_id"] == chip_id:
                pares.add(row["chip_b_id"])
            else:
                pares.add(row["chip_a_id"])

        return list(pares)

    def _obter_regiao_ddd(self, ddd: int) -> Optional[str]:
        """
        Obtém região de um DDD.

        Args:
            ddd: Código de área

        Returns:
            Nome da região ou None
        """
        for regiao, ddds in REGIOES_DDD.items():
            if ddd in ddds:
                return regiao
        return None

    def _calcular_score_compatibilidade(
        self,
        chip_a: ChipInfo,
        chip_b: ChipInfo,
    ) -> Tuple[float, str]:
        """
        Calcula score de compatibilidade entre dois chips.

        Args:
            chip_a: Primeiro chip
            chip_b: Segundo chip

        Returns:
            (score, motivo)
        """
        score = 50  # Base
        motivos = []

        # Mesmo chip = impossível
        if chip_a.id == chip_b.id:
            return -1000, "mesmo_chip"

        # Mesmo DDD = muito bom
        if chip_a.ddd == chip_b.ddd:
            score += self.PESO_MESMO_DDD
            motivos.append("mesmo_ddd")
        else:
            # Mesma região = bom
            regiao_a = self._obter_regiao_ddd(chip_a.ddd)
            regiao_b = self._obter_regiao_ddd(chip_b.ddd)
            if regiao_a and regiao_a == regiao_b:
                score += self.PESO_MESMA_REGIAO
                motivos.append("mesma_regiao")

        # Fase compatível = importante
        fases_ok = FASES_COMPATIVEIS.get(chip_a.fase_warmup, [])
        if chip_b.fase_warmup in fases_ok:
            score += self.PESO_FASE_COMPATIVEL
            motivos.append("fase_compativel")
        else:
            score -= 20
            motivos.append("fase_diferente")

        # Trust score similar = bom
        diff_trust = abs(chip_a.trust_score - chip_b.trust_score)
        if diff_trust <= 10:
            score += self.PESO_TRUST_SIMILAR
            motivos.append("trust_similar")
        elif diff_trust <= 20:
            score += self.PESO_TRUST_SIMILAR // 2

        # Balanceamento de mensagens
        ratio_a = chip_a.msgs_enviadas_hoje / max(1, chip_a.msgs_recebidas_hoje)
        ratio_b = chip_b.msgs_enviadas_hoje / max(1, chip_b.msgs_recebidas_hoje)

        # Parear quem envia muito com quem recebe muito
        if (ratio_a > 1.5 and ratio_b < 0.7) or (ratio_b > 1.5 and ratio_a < 0.7):
            score += self.PESO_BALANCO_MSGS
            motivos.append("balanceamento")

        # Penalidade se foram par recentemente
        if chip_b.id in chip_a.pares_recentes:
            score += self.PENALIDADE_PAR_RECENTE
            motivos.append("par_recente")

        return score, "+".join(motivos) if motivos else "base"

    async def encontrar_melhor_par(
        self,
        chip_id: str,
    ) -> Optional[ParInfo]:
        """
        Encontra melhor par para um chip.

        Args:
            chip_id: ID do chip buscando par

        Returns:
            ParInfo com melhor par ou None
        """
        # Carregar chips disponíveis
        chips = await self._carregar_chips_disponiveis()

        # Encontrar o chip alvo
        chip_alvo = None
        for c in chips:
            if c.id == chip_id:
                chip_alvo = c
                break

        if not chip_alvo:
            logger.warning(f"[Pairing] Chip {chip_id} não encontrado")
            return None

        # Carregar pares recentes
        chip_alvo.pares_recentes = await self._carregar_pares_recentes(chip_id)

        # Calcular scores para todos os outros chips
        candidatos = []
        for c in chips:
            if c.id == chip_id:
                continue

            score, motivo = self._calcular_score_compatibilidade(chip_alvo, c)

            if score > 0:  # Só considerar scores positivos
                candidatos.append((score, motivo, c))

        if not candidatos:
            logger.warning(f"[Pairing] Nenhum par compatível para {chip_id}")
            return None

        # Ordenar por score (melhor primeiro)
        candidatos.sort(key=lambda x: x[0], reverse=True)

        # Selecionar o melhor (com alguma aleatoriedade entre os top 3)
        top_n = min(3, len(candidatos))
        score, motivo, par = random.choice(candidatos[:top_n])

        logger.info(
            f"[Pairing] Par encontrado: {chip_id[:8]}... <-> {par.id[:8]}... "
            f"(score={score:.0f}, motivo={motivo})"
        )

        return ParInfo(
            chip_a=chip_alvo,
            chip_b=par,
            score_compatibilidade=score,
            motivo=motivo,
        )

    async def criar_pares_lote(
        self,
        quantidade: int = 10,
    ) -> List[ParInfo]:
        """
        Cria múltiplos pares de uma vez.

        Args:
            quantidade: Número de pares desejados

        Returns:
            Lista de ParInfo criados
        """
        chips = await self._carregar_chips_disponiveis()

        if len(chips) < 2:
            logger.warning("[Pairing] Chips insuficientes para pareamento")
            return []

        # Carregar pares recentes de todos
        for chip in chips:
            chip.pares_recentes = await self._carregar_pares_recentes(chip.id)

        # Criar matriz de compatibilidade
        pares_possiveis = []
        chips_usados = set()

        for i, chip_a in enumerate(chips):
            for chip_b in chips[i + 1:]:
                score, motivo = self._calcular_score_compatibilidade(chip_a, chip_b)
                if score > 0:
                    pares_possiveis.append((score, motivo, chip_a, chip_b))

        # Ordenar por score
        pares_possiveis.sort(key=lambda x: x[0], reverse=True)

        # Selecionar pares sem repetir chips
        pares_criados = []
        for score, motivo, chip_a, chip_b in pares_possiveis:
            if len(pares_criados) >= quantidade:
                break

            if chip_a.id in chips_usados or chip_b.id in chips_usados:
                continue

            chips_usados.add(chip_a.id)
            chips_usados.add(chip_b.id)

            pares_criados.append(ParInfo(
                chip_a=chip_a,
                chip_b=chip_b,
                score_compatibilidade=score,
                motivo=motivo,
            ))

        logger.info(f"[Pairing] {len(pares_criados)} pares criados em lote")

        return pares_criados

    async def registrar_pareamento(
        self,
        chip_a_id: str,
        chip_b_id: str,
        motivo: str = "warmup",
    ) -> str:
        """
        Registra um pareamento no banco.

        Args:
            chip_a_id: ID do primeiro chip
            chip_b_id: ID do segundo chip
            motivo: Motivo do pareamento

        Returns:
            ID do registro de pareamento
        """
        result = supabase.table("chip_pairs").insert({
            "chip_a_id": chip_a_id,
            "chip_b_id": chip_b_id,
            "tipo": motivo,
            "status": "ativo",
            "conversas_count": 0,
        }).execute()

        pair_id = result.data[0]["id"] if result.data else None

        # Atualizar último pareamento nos chips
        agora = datetime.now().isoformat()
        supabase.table("chips").update(
            {"ultimo_pareamento": agora}
        ).in_("id", [chip_a_id, chip_b_id]).execute()

        logger.info(f"[Pairing] Pareamento registrado: {pair_id}")

        return pair_id

    async def finalizar_pareamento(
        self,
        pair_id: str,
        sucesso: bool = True,
    ):
        """
        Finaliza um pareamento.

        Args:
            pair_id: ID do pareamento
            sucesso: Se o pareamento foi bem-sucedido
        """
        status = "concluido" if sucesso else "falhou"

        supabase.table("chip_pairs").update({
            "status": status,
            "ended_at": datetime.now().isoformat(),
        }).eq("id", pair_id).execute()

        logger.info(f"[Pairing] Pareamento {pair_id} finalizado: {status}")


# Instância global
pairing_engine = PairingEngine()


async def encontrar_par(chip_id: str) -> Optional[ParInfo]:
    """
    Função de conveniência para encontrar par.

    Args:
        chip_id: ID do chip

    Returns:
        ParInfo ou None
    """
    return await pairing_engine.encontrar_melhor_par(chip_id)


async def criar_pares(quantidade: int = 10) -> List[ParInfo]:
    """
    Função de conveniência para criar pares em lote.

    Args:
        quantidade: Número de pares

    Returns:
        Lista de ParInfo
    """
    return await pairing_engine.criar_pares_lote(quantidade)
