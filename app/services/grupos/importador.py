"""
Importação automática de vagas de grupos para tabela principal.

Sprint 14 - E09 - Importação Automática

Regras de confiança:
- >= 90%: Importa automaticamente
- 70-90%: Fila de revisão
- < 70%: Descarta
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Optional, List
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)


# Thresholds de decisão
# Sprint 29: Baixado de 0.90 para 0.85 - Julia intermedia ofertas,
# então vagas com confiança média-alta podem ser importadas
THRESHOLD_IMPORTAR = 0.85
THRESHOLD_REVISAR = 0.70


# =============================================================================
# S09.1 - Cálculo de Confiança
# =============================================================================


@dataclass
class ScoreConfianca:
    """Scores de confiança da vaga."""

    hospital: float = 0.0
    especialidade: float = 0.0
    data: float = 0.0
    periodo: float = 0.0
    valor: float = 0.0
    geral: float = 0.0
    detalhes: dict = field(default_factory=dict)


def calcular_confianca_geral(vaga: dict) -> ScoreConfianca:
    """
    Calcula score de confiança consolidado.

    Pesos:
    - Hospital: 30%
    - Especialidade: 30%
    - Data: 25%
    - Período: 10%
    - Valor: 5%

    Args:
        vaga: Dados da vaga do grupo

    Returns:
        ScoreConfianca com todos os scores calculados
    """
    scores = ScoreConfianca()

    # Hospital (30%)
    scores.hospital = vaga.get("hospital_match_score") or vaga.get("confianca_hospital") or 0.0
    scores.detalhes["hospital"] = scores.hospital

    # Especialidade (30%)
    scores.especialidade = (
        vaga.get("especialidade_match_score") or vaga.get("confianca_especialidade") or 0.0
    )
    scores.detalhes["especialidade"] = scores.especialidade

    # Data (25%)
    if vaga.get("data"):
        # Se tem data, usa confiança da extração ou assume alta
        scores.data = vaga.get("confianca_data") or 0.8
    else:
        scores.data = 0.0
    scores.detalhes["data"] = scores.data

    # Período (10%)
    if vaga.get("periodo_id"):
        scores.periodo = 1.0
    else:
        scores.periodo = 0.5  # Sem período não é crítico
    scores.detalhes["periodo"] = scores.periodo

    # Valor (5%) - Atualizado para considerar valor_tipo (Sprint 19)
    valor_tipo = vaga.get("valor_tipo", "a_combinar")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor and 100 <= valor <= 10000:
        scores.valor = 1.0  # Valor fixo válido
    elif valor_tipo == "faixa" and (valor_minimo or valor_maximo):
        scores.valor = 0.9  # Faixa definida
    elif valor_tipo == "a_combinar":
        scores.valor = 0.7  # A combinar é aceitável, não penalizar muito
    else:
        scores.valor = 0.3  # Inconsistente

    scores.detalhes["valor"] = scores.valor
    scores.detalhes["valor_tipo"] = valor_tipo

    # Cálculo ponderado
    scores.geral = (
        scores.hospital * 0.30
        + scores.especialidade * 0.30
        + scores.data * 0.25
        + scores.periodo * 0.10
        + scores.valor * 0.05
    )

    return scores


# =============================================================================
# S09.2 - Validação para Importação
# =============================================================================


@dataclass
class ResultadoValidacao:
    """Resultado da validação de vaga."""

    valido: bool
    erros: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)


def validar_para_importacao(vaga: dict) -> ResultadoValidacao:
    """
    Valida se vaga pode ser importada.

    Requisitos obrigatórios:
    - hospital_id
    - especialidade_id
    - data (futuro)

    Avisos (não bloqueiam):
    - Sem período
    - Sem valor
    - Data muito distante

    Args:
        vaga: Dados da vaga do grupo

    Returns:
        ResultadoValidacao com erros e avisos
    """
    erros = []
    avisos = []

    # Obrigatórios
    if not vaga.get("hospital_id"):
        erros.append("hospital_id ausente")

    if not vaga.get("especialidade_id"):
        erros.append("especialidade_id ausente")

    if not vaga.get("data"):
        erros.append("data ausente")
    else:
        # Validar data
        try:
            if isinstance(vaga["data"], str):
                data_vaga = datetime.strptime(vaga["data"], "%Y-%m-%d").date()
            else:
                data_vaga = vaga["data"]

            hoje = datetime.now(UTC).date()

            if data_vaga < hoje:
                erros.append("data no passado")
            elif data_vaga > hoje + timedelta(days=90):
                avisos.append("data muito distante (>90 dias)")

        except (ValueError, TypeError):
            erros.append("data em formato inválido")

    # Avisos (não bloqueiam)
    if not vaga.get("periodo_id"):
        avisos.append("período não identificado")

    # Avisos de valor (Sprint 19 - valor flexível)
    valor_tipo = vaga.get("valor_tipo", "a_combinar")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and not valor:
        avisos.append("valor_tipo=fixo mas valor ausente")
    elif valor_tipo == "faixa" and not valor_minimo and not valor_maximo:
        avisos.append("valor_tipo=faixa mas limites ausentes")
    # a_combinar não gera aviso - é um tipo válido

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros, avisos=avisos)


# =============================================================================
# S09.3 - Criar Vaga Principal
# =============================================================================


async def criar_vaga_principal(vaga_grupo: dict) -> UUID:
    """
    Cria vaga na tabela principal a partir de vaga do grupo.

    Args:
        vaga_grupo: Dados da vaga_grupo normalizada

    Returns:
        UUID da vaga criada
    """
    # Mapear campos
    dados_vaga = {
        "hospital_id": vaga_grupo["hospital_id"],
        "especialidade_id": vaga_grupo["especialidade_id"],
        "data": vaga_grupo["data"],
        "periodo_id": vaga_grupo.get("periodo_id"),
        "setor_id": vaga_grupo.get("setor_id"),
        "tipos_vaga_id": vaga_grupo.get("tipo_vaga_id"),
        # Campos de valor flexível (Sprint 19)
        "valor": vaga_grupo.get("valor"),
        "valor_minimo": vaga_grupo.get("valor_minimo"),
        "valor_maximo": vaga_grupo.get("valor_maximo"),
        "valor_tipo": vaga_grupo.get("valor_tipo", "a_combinar"),
        "hora_inicio": vaga_grupo.get("hora_inicio"),
        "hora_fim": vaga_grupo.get("hora_fim"),
        "status": "aberta",
        "origem": "grupo_whatsapp",
        "vaga_grupo_id": vaga_grupo["id"],
    }

    # Remover campos None
    dados_vaga = {k: v for k, v in dados_vaga.items() if v is not None}

    result = supabase.table("vagas").insert(dados_vaga).execute()
    vaga_id = UUID(result.data[0]["id"])

    logger.info(f"Vaga criada: {vaga_id} (origem: grupo {vaga_grupo['id']})")

    return vaga_id


async def atualizar_vaga_grupo_importada(vaga_grupo_id: UUID, vaga_id: UUID) -> None:
    """
    Marca vaga_grupo como importada.

    Args:
        vaga_grupo_id: ID da vaga de grupo
        vaga_id: ID da vaga criada
    """
    supabase.table("vagas_grupo").update(
        {
            "status": "importada",
            "vaga_importada_id": str(vaga_id),
            "importada_em": datetime.now(UTC).isoformat(),
        }
    ).eq("id", str(vaga_grupo_id)).execute()


# =============================================================================
# S09.4 - Regras de Decisão
# =============================================================================


class AcaoImportacao(Enum):
    """Ações possíveis para importação."""

    IMPORTAR = "importar"
    REVISAR = "revisar"
    DESCARTAR = "descartar"


def decidir_acao(score: ScoreConfianca, validacao: ResultadoValidacao) -> AcaoImportacao:
    """
    Decide ação baseado em confiança e validação.

    Regras:
    - Inválido: DESCARTAR
    - Confiança >= 90%: IMPORTAR
    - Confiança 70-90%: REVISAR
    - Confiança < 70%: DESCARTAR

    Args:
        score: Score de confiança calculado
        validacao: Resultado da validação

    Returns:
        AcaoImportacao a ser aplicada
    """
    if not validacao.valido:
        return AcaoImportacao.DESCARTAR

    if score.geral >= THRESHOLD_IMPORTAR:
        return AcaoImportacao.IMPORTAR

    if score.geral >= THRESHOLD_REVISAR:
        return AcaoImportacao.REVISAR

    return AcaoImportacao.DESCARTAR


async def aplicar_acao(
    vaga_grupo_id: UUID,
    vaga_grupo: dict,
    acao: AcaoImportacao,
    score: ScoreConfianca,
    validacao: ResultadoValidacao,
) -> dict:
    """
    Aplica a ação decidida na vaga.

    Args:
        vaga_grupo_id: ID da vaga de grupo
        vaga_grupo: Dados da vaga
        acao: Ação a aplicar
        score: Score de confiança
        validacao: Resultado da validação

    Returns:
        Resultado da aplicação
    """
    resultado = {
        "vaga_grupo_id": str(vaga_grupo_id),
        "acao": acao.value,
        "score": round(score.geral, 3),
    }

    if acao == AcaoImportacao.IMPORTAR:
        # Criar vaga na tabela principal
        vaga_id = await criar_vaga_principal(vaga_grupo)
        await atualizar_vaga_grupo_importada(vaga_grupo_id, vaga_id)

        resultado["vaga_id"] = str(vaga_id)
        resultado["status"] = "importada"

    elif acao == AcaoImportacao.REVISAR:
        # Mover para fila de revisão
        supabase.table("vagas_grupo").update(
            {
                "status": "aguardando_revisao",
                "confianca_geral": score.geral,
                "motivo_status": "confianca_media",
            }
        ).eq("id", str(vaga_grupo_id)).execute()

        resultado["status"] = "aguardando_revisao"

    else:  # DESCARTAR
        motivo = "baixa_confianca"
        if not validacao.valido:
            motivo = f"validacao_falhou: {', '.join(validacao.erros)}"

        supabase.table("vagas_grupo").update(
            {
                "status": "descartada",
                "confianca_geral": score.geral,
                "motivo_status": motivo,
            }
        ).eq("id", str(vaga_grupo_id)).execute()

        resultado["status"] = "descartada"
        resultado["motivo"] = motivo

    return resultado


# =============================================================================
# S09.5 - Processador de Importação
# =============================================================================


@dataclass
class ResultadoImportacao:
    """Resultado do processamento de importação."""

    vaga_grupo_id: str
    acao: str
    score: float
    status: str
    vaga_id: Optional[str] = None
    motivo: Optional[str] = None
    erro: Optional[str] = None


async def processar_importacao(vaga_grupo_id: UUID) -> ResultadoImportacao:
    """
    Processa importação de uma vaga do grupo.

    Fluxo:
    1. Buscar vaga
    2. Verificar status
    3. Calcular confiança
    4. Validar dados
    5. Decidir ação
    6. Aplicar ação

    Args:
        vaga_grupo_id: ID da vaga de grupo

    Returns:
        ResultadoImportacao com detalhes do processamento
    """
    # Buscar vaga
    vaga = supabase.table("vagas_grupo").select("*").eq("id", str(vaga_grupo_id)).single().execute()

    if not vaga.data:
        return ResultadoImportacao(
            vaga_grupo_id=str(vaga_grupo_id),
            acao="erro",
            score=0,
            status="erro",
            erro="vaga_nao_encontrada",
        )

    dados = vaga.data

    # Verificar se já foi processada
    if dados.get("status") in ["importada", "descartada"]:
        return ResultadoImportacao(
            vaga_grupo_id=str(vaga_grupo_id),
            acao="ignorada",
            score=dados.get("confianca_geral", 0),
            status=dados["status"],
            erro="vaga_ja_processada",
        )

    # Verificar se é duplicada
    if dados.get("eh_duplicada"):
        return ResultadoImportacao(
            vaga_grupo_id=str(vaga_grupo_id),
            acao="ignorada",
            score=0,
            status="duplicada",
            erro="vaga_duplicada",
        )

    # Calcular confiança
    score = calcular_confianca_geral(dados)

    # Validar
    validacao = validar_para_importacao(dados)

    # Decidir e aplicar
    acao = decidir_acao(score, validacao)
    resultado = await aplicar_acao(vaga_grupo_id, dados, acao, score, validacao)

    return ResultadoImportacao(
        vaga_grupo_id=resultado["vaga_grupo_id"],
        acao=resultado["acao"],
        score=resultado["score"],
        status=resultado["status"],
        vaga_id=resultado.get("vaga_id"),
        motivo=resultado.get("motivo"),
    )


async def processar_batch_importacao(limite: int = 50) -> dict:
    """
    Processa batch de vagas prontas para importação.

    Busca vagas com status 'pronta_importacao' (após deduplicação).

    Args:
        limite: Máximo de vagas a processar

    Returns:
        Estatísticas do processamento
    """
    # Buscar vagas prontas (não duplicadas, não importadas)
    vagas = (
        supabase.table("vagas_grupo")
        .select("id")
        .eq("status", "pronta_importacao")
        .eq("eh_duplicada", False)
        .is_("vaga_importada_id", "null")
        .order("created_at")
        .limit(limite)
        .execute()
    )

    stats = {
        "total": len(vagas.data),
        "importadas": 0,
        "revisao": 0,
        "descartadas": 0,
        "erros": 0,
    }

    for vaga in vagas.data:
        try:
            resultado = await processar_importacao(UUID(vaga["id"]))

            if resultado.status == "importada":
                stats["importadas"] += 1
            elif resultado.status == "aguardando_revisao":
                stats["revisao"] += 1
            elif resultado.status == "descartada":
                stats["descartadas"] += 1
            else:
                stats["erros"] += 1

        except Exception as e:
            logger.error(f"Erro ao importar vaga {vaga['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Importação: {stats['total']} processadas, "
        f"{stats['importadas']} importadas, "
        f"{stats['revisao']} para revisão, "
        f"{stats['descartadas']} descartadas"
    )

    return stats


# =============================================================================
# Funções de Consulta
# =============================================================================


async def listar_vagas_para_revisao(limite: int = 50) -> list:
    """
    Lista vagas aguardando revisão humana.

    Args:
        limite: Máximo de vagas a retornar

    Returns:
        Lista de vagas para revisão
    """
    result = (
        supabase.table("vagas_grupo")
        .select("*, hospitais(nome), especialidades(nome)")
        .eq("status", "aguardando_revisao")
        .order("confianca_geral", desc=True)
        .limit(limite)
        .execute()
    )

    return result.data


async def aprovar_vaga_revisao(vaga_grupo_id: UUID, aprovado_por: str = "gestor") -> dict:
    """
    Aprova vaga da fila de revisão para importação.

    Args:
        vaga_grupo_id: ID da vaga de grupo
        aprovado_por: Quem aprovou

    Returns:
        Resultado da importação
    """
    # Buscar vaga
    vaga = supabase.table("vagas_grupo").select("*").eq("id", str(vaga_grupo_id)).single().execute()

    if not vaga.data:
        return {"erro": "vaga_nao_encontrada"}

    if vaga.data.get("status") != "aguardando_revisao":
        return {"erro": "vaga_nao_esta_em_revisao"}

    # Criar vaga
    vaga_id = await criar_vaga_principal(vaga.data)
    await atualizar_vaga_grupo_importada(vaga_grupo_id, vaga_id)

    # Registrar aprovação
    supabase.table("vagas_grupo").update(
        {
            "aprovado_por": aprovado_por,
            "aprovado_em": datetime.now(UTC).isoformat(),
        }
    ).eq("id", str(vaga_grupo_id)).execute()

    return {
        "vaga_grupo_id": str(vaga_grupo_id),
        "vaga_id": str(vaga_id),
        "status": "importada",
        "aprovado_por": aprovado_por,
    }


async def rejeitar_vaga_revisao(
    vaga_grupo_id: UUID, motivo: str, rejeitado_por: str = "gestor"
) -> dict:
    """
    Rejeita vaga da fila de revisão.

    Args:
        vaga_grupo_id: ID da vaga de grupo
        motivo: Motivo da rejeição
        rejeitado_por: Quem rejeitou

    Returns:
        Resultado da rejeição
    """
    supabase.table("vagas_grupo").update(
        {
            "status": "rejeitada",
            "motivo_status": f"rejeitada: {motivo}",
            "rejeitado_por": rejeitado_por,
            "rejeitado_em": datetime.now(UTC).isoformat(),
        }
    ).eq("id", str(vaga_grupo_id)).execute()

    return {
        "vaga_grupo_id": str(vaga_grupo_id),
        "status": "rejeitada",
        "motivo": motivo,
    }


async def obter_estatisticas_importacao() -> dict:
    """
    Obtém estatísticas de importação.

    Returns:
        Estatísticas gerais
    """
    # Total de vagas de grupo
    total = supabase.table("vagas_grupo").select("id", count="exact").execute()

    # Importadas
    importadas = (
        supabase.table("vagas_grupo")
        .select("id", count="exact")
        .eq("status", "importada")
        .execute()
    )

    # Aguardando revisão
    revisao = (
        supabase.table("vagas_grupo")
        .select("id", count="exact")
        .eq("status", "aguardando_revisao")
        .execute()
    )

    # Descartadas
    descartadas = (
        supabase.table("vagas_grupo")
        .select("id", count="exact")
        .eq("status", "descartada")
        .execute()
    )

    # Prontas para importação
    prontas = (
        supabase.table("vagas_grupo")
        .select("id", count="exact")
        .eq("status", "pronta_importacao")
        .execute()
    )

    return {
        "total_vagas_grupo": total.count or 0,
        "importadas": importadas.count or 0,
        "aguardando_revisao": revisao.count or 0,
        "descartadas": descartadas.count or 0,
        "prontas_importacao": prontas.count or 0,
        "taxa_importacao": ((importadas.count or 0) / (total.count or 1) * 100),
    }
