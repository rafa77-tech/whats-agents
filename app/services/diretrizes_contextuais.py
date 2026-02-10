"""
Serviço de Diretrizes Contextuais.

Sprint 32 E10 - Margens de negociação por vaga/médico com expiração automática.

Tipos de diretriz:
- margem_negociacao: Define valor/percentual máximo para negociação
- instrucao_especial: Instrução específica para vaga/médico

Escopos:
- vaga: Diretriz específica para uma vaga
- medico: Diretriz específica para um médico
- hospital: Diretriz para todas as vagas de um hospital
- especialidade: Diretriz para todas as vagas de uma especialidade
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================

# Tipos de diretriz
TIPO_MARGEM_NEGOCIACAO = "margem_negociacao"
TIPO_INSTRUCAO_ESPECIAL = "instrucao_especial"

# Escopos
ESCOPO_VAGA = "vaga"
ESCOPO_MEDICO = "medico"
ESCOPO_HOSPITAL = "hospital"
ESCOPO_ESPECIALIDADE = "especialidade"

# Status
STATUS_ATIVA = "ativa"
STATUS_EXPIRADA = "expirada"
STATUS_CANCELADA = "cancelada"

# Motivos de expiração
MOTIVO_VAGA_PREENCHIDA = "vaga_preenchida"
MOTIVO_MEDICO_SEM_INTERESSE = "medico_sem_interesse"
MOTIVO_CANCELADO_GESTOR = "cancelado_gestor"
MOTIVO_TIMEOUT = "timeout"


# =============================================================================
# FUNÇÕES DE CRIAÇÃO
# =============================================================================


async def criar_margem_vaga(
    vaga_id: str,
    valor_maximo: Optional[int] = None,
    percentual_maximo: Optional[float] = None,
    instrucao: Optional[str] = None,
    criado_por: str = "gestor",
    expira_em: Optional[datetime] = None,
) -> dict:
    """
    Cria margem de negociação para uma vaga específica.

    Args:
        vaga_id: ID da vaga
        valor_maximo: Valor máximo absoluto (R$)
        percentual_maximo: Percentual máximo acima do valor base
        instrucao: Instrução adicional
        criado_por: Quem criou a diretriz
        expira_em: Data de expiração (opcional)

    Returns:
        Dict com dados da diretriz criada
    """
    return await _criar_diretriz(
        tipo=TIPO_MARGEM_NEGOCIACAO,
        escopo=ESCOPO_VAGA,
        vaga_id=vaga_id,
        valor_maximo=valor_maximo,
        percentual_maximo=percentual_maximo,
        instrucao=instrucao,
        criado_por=criado_por,
        expira_em=expira_em,
    )


async def criar_margem_medico(
    cliente_id: str,
    valor_maximo: Optional[int] = None,
    percentual_maximo: Optional[float] = None,
    instrucao: Optional[str] = None,
    criado_por: str = "gestor",
    expira_em: Optional[datetime] = None,
) -> dict:
    """
    Cria margem de negociação para um médico específico.

    Args:
        cliente_id: ID do médico
        valor_maximo: Valor máximo absoluto (R$)
        percentual_maximo: Percentual máximo acima do valor base
        instrucao: Instrução adicional
        criado_por: Quem criou a diretriz
        expira_em: Data de expiração (opcional)

    Returns:
        Dict com dados da diretriz criada
    """
    return await _criar_diretriz(
        tipo=TIPO_MARGEM_NEGOCIACAO,
        escopo=ESCOPO_MEDICO,
        cliente_id=cliente_id,
        valor_maximo=valor_maximo,
        percentual_maximo=percentual_maximo,
        instrucao=instrucao,
        criado_por=criado_por,
        expira_em=expira_em,
    )


async def criar_margem_hospital(
    hospital_id: str,
    valor_maximo: Optional[int] = None,
    percentual_maximo: Optional[float] = None,
    instrucao: Optional[str] = None,
    criado_por: str = "gestor",
    expira_em: Optional[datetime] = None,
) -> dict:
    """
    Cria margem de negociação para todas as vagas de um hospital.

    Args:
        hospital_id: ID do hospital
        valor_maximo: Valor máximo absoluto (R$)
        percentual_maximo: Percentual máximo acima do valor base
        instrucao: Instrução adicional
        criado_por: Quem criou a diretriz
        expira_em: Data de expiração (opcional)

    Returns:
        Dict com dados da diretriz criada
    """
    return await _criar_diretriz(
        tipo=TIPO_MARGEM_NEGOCIACAO,
        escopo=ESCOPO_HOSPITAL,
        hospital_id=hospital_id,
        valor_maximo=valor_maximo,
        percentual_maximo=percentual_maximo,
        instrucao=instrucao,
        criado_por=criado_por,
        expira_em=expira_em,
    )


async def criar_margem_especialidade(
    especialidade_id: str,
    valor_maximo: Optional[int] = None,
    percentual_maximo: Optional[float] = None,
    instrucao: Optional[str] = None,
    criado_por: str = "gestor",
    expira_em: Optional[datetime] = None,
) -> dict:
    """
    Cria margem de negociação para todas as vagas de uma especialidade.

    Args:
        especialidade_id: ID da especialidade
        valor_maximo: Valor máximo absoluto (R$)
        percentual_maximo: Percentual máximo acima do valor base
        instrucao: Instrução adicional
        criado_por: Quem criou a diretriz
        expira_em: Data de expiração (opcional)

    Returns:
        Dict com dados da diretriz criada
    """
    return await _criar_diretriz(
        tipo=TIPO_MARGEM_NEGOCIACAO,
        escopo=ESCOPO_ESPECIALIDADE,
        especialidade_id=especialidade_id,
        valor_maximo=valor_maximo,
        percentual_maximo=percentual_maximo,
        instrucao=instrucao,
        criado_por=criado_por,
        expira_em=expira_em,
    )


async def criar_instrucao_especial(
    escopo: str,
    instrucao: str,
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    especialidade_id: Optional[str] = None,
    criado_por: str = "gestor",
    expira_em: Optional[datetime] = None,
) -> dict:
    """
    Cria instrução especial para um escopo.

    Args:
        escopo: Escopo da diretriz (vaga, medico, hospital, especialidade)
        instrucao: Texto da instrução
        vaga_id: ID da vaga (se escopo=vaga)
        cliente_id: ID do médico (se escopo=medico)
        hospital_id: ID do hospital (se escopo=hospital)
        especialidade_id: ID da especialidade (se escopo=especialidade)
        criado_por: Quem criou a diretriz
        expira_em: Data de expiração (opcional)

    Returns:
        Dict com dados da diretriz criada
    """
    return await _criar_diretriz(
        tipo=TIPO_INSTRUCAO_ESPECIAL,
        escopo=escopo,
        vaga_id=vaga_id,
        cliente_id=cliente_id,
        hospital_id=hospital_id,
        especialidade_id=especialidade_id,
        instrucao=instrucao,
        criado_por=criado_por,
        expira_em=expira_em,
    )


# =============================================================================
# FUNÇÕES DE BUSCA
# =============================================================================


async def buscar_margem_para_negociacao(
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    especialidade_id: Optional[str] = None,
) -> dict:
    """
    Busca margem de negociação aplicável.

    Ordem de precedência (mais específico primeiro):
    1. Margem específica para vaga
    2. Margem específica para médico
    3. Margem para hospital
    4. Margem para especialidade

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do médico
        hospital_id: ID do hospital
        especialidade_id: ID da especialidade

    Returns:
        Dict com margem aplicável ou padrão (sem margem)
    """
    try:
        # Buscar todas as diretrizes ativas relevantes
        diretrizes = []

        # 1. Por vaga
        if vaga_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_MARGEM_NEGOCIACAO,
                escopo=ESCOPO_VAGA,
                vaga_id=vaga_id,
            )
            diretrizes.extend(response)

        # 2. Por médico
        if cliente_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_MARGEM_NEGOCIACAO,
                escopo=ESCOPO_MEDICO,
                cliente_id=cliente_id,
            )
            diretrizes.extend(response)

        # 3. Por hospital
        if hospital_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_MARGEM_NEGOCIACAO,
                escopo=ESCOPO_HOSPITAL,
                hospital_id=hospital_id,
            )
            diretrizes.extend(response)

        # 4. Por especialidade
        if especialidade_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_MARGEM_NEGOCIACAO,
                escopo=ESCOPO_ESPECIALIDADE,
                especialidade_id=especialidade_id,
            )
            diretrizes.extend(response)

        if not diretrizes:
            return {
                "tem_margem": False,
                "valor_maximo": None,
                "percentual_maximo": None,
                "instrucao": None,
            }

        # Ordenar por precedência (vaga > medico > hospital > especialidade)
        precedencia = {
            ESCOPO_VAGA: 1,
            ESCOPO_MEDICO: 2,
            ESCOPO_HOSPITAL: 3,
            ESCOPO_ESPECIALIDADE: 4,
        }

        diretrizes_ordenadas = sorted(
            diretrizes, key=lambda d: precedencia.get(d.get("escopo"), 99)
        )

        # Retornar a mais específica
        diretriz = diretrizes_ordenadas[0]

        return {
            "tem_margem": True,
            "valor_maximo": diretriz.get("valor_maximo"),
            "percentual_maximo": float(diretriz.get("percentual_maximo") or 0),
            "instrucao": diretriz.get("instrucao"),
            "escopo": diretriz.get("escopo"),
            "diretriz_id": diretriz.get("id"),
        }

    except Exception as e:
        logger.error(f"Erro ao buscar margem: {e}")
        return {"tem_margem": False, "error": str(e)}


async def buscar_instrucoes_especiais(
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    especialidade_id: Optional[str] = None,
) -> list[str]:
    """
    Busca todas as instruções especiais aplicáveis.

    Diferente de margem, instruções podem ser combinadas.

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do médico
        hospital_id: ID do hospital
        especialidade_id: ID da especialidade

    Returns:
        Lista de instruções aplicáveis
    """
    try:
        instrucoes = []

        # Buscar por cada escopo
        if vaga_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_INSTRUCAO_ESPECIAL,
                escopo=ESCOPO_VAGA,
                vaga_id=vaga_id,
            )
            instrucoes.extend([d["instrucao"] for d in response if d.get("instrucao")])

        if cliente_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_INSTRUCAO_ESPECIAL,
                escopo=ESCOPO_MEDICO,
                cliente_id=cliente_id,
            )
            instrucoes.extend([d["instrucao"] for d in response if d.get("instrucao")])

        if hospital_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_INSTRUCAO_ESPECIAL,
                escopo=ESCOPO_HOSPITAL,
                hospital_id=hospital_id,
            )
            instrucoes.extend([d["instrucao"] for d in response if d.get("instrucao")])

        if especialidade_id:
            response = await _buscar_diretrizes_ativas(
                tipo=TIPO_INSTRUCAO_ESPECIAL,
                escopo=ESCOPO_ESPECIALIDADE,
                especialidade_id=especialidade_id,
            )
            instrucoes.extend([d["instrucao"] for d in response if d.get("instrucao")])

        return instrucoes

    except Exception as e:
        logger.error(f"Erro ao buscar instruções: {e}")
        return []


async def listar_diretrizes_ativas(
    tipo: Optional[str] = None,
    escopo: Optional[str] = None,
    limite: int = 50,
) -> list[dict]:
    """
    Lista todas as diretrizes ativas.

    Args:
        tipo: Filtrar por tipo
        escopo: Filtrar por escopo
        limite: Máximo de resultados

    Returns:
        Lista de diretrizes
    """
    try:
        query = supabase.table("diretrizes_contextuais").select("*").eq("status", STATUS_ATIVA)

        if tipo:
            query = query.eq("tipo", tipo)

        if escopo:
            query = query.eq("escopo", escopo)

        response = query.order("created_at", desc=True).limit(limite).execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar diretrizes: {e}")
        return []


# =============================================================================
# FUNÇÕES DE EXPIRAÇÃO
# =============================================================================


async def expirar_diretriz(
    diretriz_id: str,
    motivo: str,
) -> dict:
    """
    Expira uma diretriz.

    Args:
        diretriz_id: ID da diretriz
        motivo: Motivo da expiração

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("diretrizes_contextuais")
            .update(
                {
                    "status": STATUS_EXPIRADA,
                    "expirado_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_expiracao": motivo,
                }
            )
            .eq("id", diretriz_id)
            .eq("status", STATUS_ATIVA)
            .execute()
        )

        if response.data:
            logger.info(f"Diretriz {diretriz_id} expirada: {motivo}")
            return {"success": True, "diretriz_id": diretriz_id}

        return {"success": False, "error": "Diretriz não encontrada ou já expirada"}

    except Exception as e:
        logger.error(f"Erro ao expirar diretriz: {e}")
        return {"success": False, "error": str(e)}


async def expirar_diretrizes_vaga(vaga_id: str, motivo: str = MOTIVO_VAGA_PREENCHIDA) -> int:
    """
    Expira todas as diretrizes de uma vaga (quando preenchida).

    Args:
        vaga_id: ID da vaga
        motivo: Motivo da expiração

    Returns:
        Número de diretrizes expiradas
    """
    try:
        response = (
            supabase.table("diretrizes_contextuais")
            .update(
                {
                    "status": STATUS_EXPIRADA,
                    "expirado_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_expiracao": motivo,
                }
            )
            .eq("vaga_id", vaga_id)
            .eq("status", STATUS_ATIVA)
            .execute()
        )

        count = len(response.data or [])
        if count > 0:
            logger.info(f"{count} diretrizes expiradas para vaga {vaga_id}")

        return count

    except Exception as e:
        logger.error(f"Erro ao expirar diretrizes de vaga: {e}")
        return 0


async def expirar_diretrizes_medico(
    cliente_id: str, motivo: str = MOTIVO_MEDICO_SEM_INTERESSE
) -> int:
    """
    Expira todas as diretrizes de um médico (quando sem interesse).

    Args:
        cliente_id: ID do médico
        motivo: Motivo da expiração

    Returns:
        Número de diretrizes expiradas
    """
    try:
        response = (
            supabase.table("diretrizes_contextuais")
            .update(
                {
                    "status": STATUS_EXPIRADA,
                    "expirado_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_expiracao": motivo,
                }
            )
            .eq("cliente_id", cliente_id)
            .eq("status", STATUS_ATIVA)
            .execute()
        )

        count = len(response.data or [])
        if count > 0:
            logger.info(f"{count} diretrizes expiradas para médico {cliente_id}")

        return count

    except Exception as e:
        logger.error(f"Erro ao expirar diretrizes de médico: {e}")
        return 0


async def processar_expiracoes_por_tempo() -> dict:
    """
    Processa expiração de diretrizes por tempo (job).

    Returns:
        Dict com estatísticas
    """
    agora = datetime.now(timezone.utc)

    try:
        response = (
            supabase.table("diretrizes_contextuais")
            .update(
                {
                    "status": STATUS_EXPIRADA,
                    "expirado_em": agora.isoformat(),
                    "motivo_expiracao": MOTIVO_TIMEOUT,
                }
            )
            .eq("status", STATUS_ATIVA)
            .lt("expira_em", agora.isoformat())
            .execute()
        )

        count = len(response.data or [])
        if count > 0:
            logger.info(f"{count} diretrizes expiradas por tempo")

        return {"expiradas": count}

    except Exception as e:
        logger.error(f"Erro ao processar expiracoes: {e}")
        return {"error": str(e)}


async def cancelar_diretriz(diretriz_id: str, cancelado_por: str) -> dict:
    """
    Cancela uma diretriz manualmente.

    Args:
        diretriz_id: ID da diretriz
        cancelado_por: Quem cancelou

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("diretrizes_contextuais")
            .update(
                {
                    "status": STATUS_CANCELADA,
                    "cancelado_por": cancelado_por,
                    "expirado_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_expiracao": MOTIVO_CANCELADO_GESTOR,
                }
            )
            .eq("id", diretriz_id)
            .eq("status", STATUS_ATIVA)
            .execute()
        )

        if response.data:
            logger.info(f"Diretriz {diretriz_id} cancelada por {cancelado_por}")
            return {"success": True, "diretriz_id": diretriz_id}

        return {"success": False, "error": "Diretriz não encontrada ou já inativa"}

    except Exception as e:
        logger.error(f"Erro ao cancelar diretriz: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# FUNÇÕES INTERNAS
# =============================================================================


async def _criar_diretriz(
    tipo: str,
    escopo: str,
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    especialidade_id: Optional[str] = None,
    valor_maximo: Optional[int] = None,
    percentual_maximo: Optional[float] = None,
    instrucao: Optional[str] = None,
    criado_por: str = "gestor",
    expira_em: Optional[datetime] = None,
) -> dict:
    """Cria uma diretriz no banco."""
    diretriz_id = str(uuid4())

    try:
        data = {
            "id": diretriz_id,
            "tipo": tipo,
            "escopo": escopo,
            "status": STATUS_ATIVA,
            "criado_por": criado_por,
        }

        if vaga_id:
            data["vaga_id"] = vaga_id
        if cliente_id:
            data["cliente_id"] = cliente_id
        if hospital_id:
            data["hospital_id"] = hospital_id
        if especialidade_id:
            data["especialidade_id"] = especialidade_id
        if valor_maximo is not None:
            data["valor_maximo"] = valor_maximo
        if percentual_maximo is not None:
            data["percentual_maximo"] = percentual_maximo
        if instrucao:
            data["instrucao"] = instrucao
        if expira_em:
            data["expira_em"] = expira_em.isoformat()

        response = supabase.table("diretrizes_contextuais").insert(data).execute()

        logger.info(f"Diretriz criada: {diretriz_id} ({tipo}/{escopo})")
        return response.data[0] if response.data else data

    except Exception as e:
        logger.error(f"Erro ao criar diretriz: {e}")
        raise


async def _buscar_diretrizes_ativas(
    tipo: str,
    escopo: str,
    vaga_id: Optional[str] = None,
    cliente_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    especialidade_id: Optional[str] = None,
) -> list[dict]:
    """Busca diretrizes ativas para um escopo específico."""
    try:
        query = (
            supabase.table("diretrizes_contextuais")
            .select("*")
            .eq("tipo", tipo)
            .eq("escopo", escopo)
            .eq("status", STATUS_ATIVA)
        )

        if vaga_id:
            query = query.eq("vaga_id", vaga_id)
        if cliente_id:
            query = query.eq("cliente_id", cliente_id)
        if hospital_id:
            query = query.eq("hospital_id", hospital_id)
        if especialidade_id:
            query = query.eq("especialidade_id", especialidade_id)

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar diretrizes: {e}")
        return []


# =============================================================================
# FUNÇÕES PARA INTEGRAÇÃO COM JULIA
# =============================================================================


async def obter_contexto_negociacao(
    vaga: dict,
    cliente_id: str,
) -> dict:
    """
    Obtém contexto completo de negociação para Julia.

    Uso no agente:
    ```python
    contexto = await obter_contexto_negociacao(vaga, medico_id)
    if contexto["pode_negociar"]:
        # Julia pode negociar até contexto["valor_maximo"]
    ```

    Args:
        vaga: Dados da vaga
        cliente_id: ID do médico

    Returns:
        Dict com contexto de negociação
    """
    margem = await buscar_margem_para_negociacao(
        vaga_id=vaga.get("id"),
        cliente_id=cliente_id,
        hospital_id=vaga.get("hospital_id"),
        especialidade_id=vaga.get("especialidade_id"),
    )

    instrucoes = await buscar_instrucoes_especiais(
        vaga_id=vaga.get("id"),
        cliente_id=cliente_id,
        hospital_id=vaga.get("hospital_id"),
        especialidade_id=vaga.get("especialidade_id"),
    )

    valor_base = vaga.get("valor") or 0

    # Calcular valor máximo
    valor_maximo = valor_base
    if margem.get("tem_margem"):
        if margem.get("valor_maximo"):
            valor_maximo = margem["valor_maximo"]
        elif margem.get("percentual_maximo"):
            valor_maximo = int(valor_base * (1 + margem["percentual_maximo"] / 100))

    return {
        "pode_negociar": margem.get("tem_margem", False),
        "valor_base": valor_base,
        "valor_maximo": valor_maximo,
        "percentual_maximo": margem.get("percentual_maximo"),
        "instrucoes_especiais": instrucoes,
        "escopo_margem": margem.get("escopo"),
    }
