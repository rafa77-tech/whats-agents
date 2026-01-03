"""
Normalização de entidades extraídas para IDs do banco.

Sprint 14 - E06 - Fuzzy Match de Entidades
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)


# =============================================================================
# S06.1 - Normalização de Texto
# =============================================================================

def normalizar_para_busca(texto: str) -> str:
    """
    Normaliza texto para busca.

    - Lowercase
    - Remove parênteses e seu conteúdo (ex: "(USG)" -> "")
    - Remove acentos
    - Remove caracteres especiais
    - Remove espaços extras
    """
    if not texto:
        return ""

    # Lowercase
    texto = texto.lower()

    # Remover parênteses e seu conteúdo ANTES de remover caracteres especiais
    # Ex: "ultrassonografista (usg)" -> "ultrassonografista"
    texto = re.sub(r'\s*\([^)]*\)', '', texto)

    # Remover acentos
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))

    # Remover caracteres especiais (manter apenas letras, números e espaços)
    texto = re.sub(r'[^\w\s]', '', texto)

    # Remover espaços extras
    texto = ' '.join(texto.split())

    return texto


def extrair_tokens(texto: str) -> set:
    """
    Extrai tokens significativos do texto.

    Remove stopwords comuns.
    """
    texto = normalizar_para_busca(texto)
    tokens = set(texto.split())

    # Stopwords em português
    stopwords = {
        'de', 'do', 'da', 'dos', 'das', 'e', 'ou', 'o', 'a', 'os', 'as',
        'um', 'uma', 'uns', 'umas', 'em', 'no', 'na', 'nos', 'nas',
        'para', 'pra', 'por', 'com', 'sem', 'que', 'se'
    }
    tokens = tokens - stopwords

    return tokens


# =============================================================================
# S06.2 - Busca em Alias (Hospital)
# =============================================================================

@dataclass
class ResultadoMatch:
    """Resultado de um match de entidade."""
    entidade_id: UUID
    nome: str
    score: float
    fonte: str  # "alias_exato", "alias_similar", "nome_similar"


async def buscar_hospital_por_alias(texto: str) -> Optional[ResultadoMatch]:
    """
    Busca hospital por alias exato.

    Returns:
        ResultadoMatch ou None
    """
    texto_norm = normalizar_para_busca(texto)

    if not texto_norm:
        return None

    try:
        result = supabase.table("hospitais_alias") \
            .select("hospital_id, hospitais(nome)") \
            .eq("alias_normalizado", texto_norm) \
            .limit(1) \
            .execute()

        if result.data and result.data[0].get("hospitais"):
            # Atualizar contador de uso (atômico via RPC)
            try:
                supabase.rpc("incrementar_vezes_usado", {
                    "p_tabela": "hospitais_alias",
                    "p_alias_normalizado": texto_norm
                }).execute()
            except Exception:
                pass  # Contador é apenas para analytics, não crítico

            return ResultadoMatch(
                entidade_id=UUID(result.data[0]["hospital_id"]),
                nome=result.data[0]["hospitais"]["nome"],
                score=1.0,
                fonte="alias_exato"
            )
    except Exception as e:
        logger.warning(f"Erro ao buscar hospital por alias: {e}")

    return None


# =============================================================================
# S06.3 - Similaridade com Trigrams
# =============================================================================

async def buscar_hospital_por_similaridade(
    texto: str,
    threshold: float = 0.3
) -> Optional[ResultadoMatch]:
    """
    Busca hospital por similaridade de texto usando pg_trgm.

    Args:
        texto: Texto para buscar
        threshold: Score mínimo de similaridade (0-1)

    Returns:
        ResultadoMatch ou None
    """
    texto_norm = normalizar_para_busca(texto)

    if not texto_norm:
        return None

    try:
        # Buscar primeiro em aliases
        result = supabase.rpc(
            "buscar_hospital_por_similaridade",
            {"p_texto": texto_norm, "p_threshold": threshold}
        ).execute()

        if result.data and len(result.data) > 0:
            match = result.data[0]
            if match.get("score", 0) >= threshold:
                return ResultadoMatch(
                    entidade_id=UUID(match["hospital_id"]),
                    nome=match["nome"],
                    score=match["score"],
                    fonte="alias_similar" if match.get("fonte") == "alias" else "nome_similar"
                )
    except Exception as e:
        logger.warning(f"Erro ao buscar hospital por similaridade: {e}")

        # Fallback: busca simples no nome
        try:
            result = supabase.table("hospitais") \
                .select("id, nome") \
                .ilike("nome", f"%{texto_norm}%") \
                .limit(1) \
                .execute()

            if result.data:
                return ResultadoMatch(
                    entidade_id=UUID(result.data[0]["id"]),
                    nome=result.data[0]["nome"],
                    score=0.5,  # Score médio para match parcial
                    fonte="nome_similar"
                )
        except Exception as e2:
            logger.warning(f"Erro no fallback de busca: {e2}")

    return None


async def normalizar_hospital(texto: str) -> Optional[ResultadoMatch]:
    """
    Normaliza nome de hospital para ID do banco.

    Estratégia:
    1. Busca alias exato
    2. Busca por similaridade

    Returns:
        ResultadoMatch ou None
    """
    # 1. Alias exato
    match = await buscar_hospital_por_alias(texto)
    if match:
        return match

    # 2. Similaridade
    match = await buscar_hospital_por_similaridade(texto)
    if match:
        return match

    return None


# =============================================================================
# S06.4 - Match de Especialidade
# =============================================================================

async def buscar_especialidade_por_alias(texto: str) -> Optional[ResultadoMatch]:
    """Busca especialidade por alias exato."""
    texto_norm = normalizar_para_busca(texto)

    if not texto_norm:
        return None

    try:
        result = supabase.table("especialidades_alias") \
            .select("especialidade_id, especialidades(nome)") \
            .eq("alias_normalizado", texto_norm) \
            .limit(1) \
            .execute()

        if result.data and result.data[0].get("especialidades"):
            return ResultadoMatch(
                entidade_id=UUID(result.data[0]["especialidade_id"]),
                nome=result.data[0]["especialidades"]["nome"],
                score=1.0,
                fonte="alias_exato"
            )
    except Exception as e:
        logger.warning(f"Erro ao buscar especialidade por alias: {e}")

    return None


async def buscar_especialidade_por_similaridade(
    texto: str,
    threshold: float = 0.3
) -> Optional[ResultadoMatch]:
    """Busca especialidade por similaridade."""
    texto_norm = normalizar_para_busca(texto)

    if not texto_norm:
        return None

    try:
        result = supabase.rpc(
            "buscar_especialidade_por_similaridade",
            {"p_texto": texto_norm, "p_threshold": threshold}
        ).execute()

        if result.data and len(result.data) > 0:
            match = result.data[0]
            if match.get("score", 0) >= threshold:
                return ResultadoMatch(
                    entidade_id=UUID(match["especialidade_id"]),
                    nome=match["nome"],
                    score=match["score"],
                    fonte="alias_similar" if match.get("fonte") == "alias" else "nome_similar"
                )
    except Exception as e:
        logger.warning(f"Erro ao buscar especialidade por similaridade: {e}")

        # Fallback
        try:
            result = supabase.table("especialidades") \
                .select("id, nome") \
                .ilike("nome", f"%{texto_norm}%") \
                .limit(1) \
                .execute()

            if result.data:
                return ResultadoMatch(
                    entidade_id=UUID(result.data[0]["id"]),
                    nome=result.data[0]["nome"],
                    score=0.5,
                    fonte="nome_similar"
                )
        except Exception as e2:
            logger.warning(f"Erro no fallback: {e2}")

    return None


async def normalizar_especialidade(texto: str) -> Optional[ResultadoMatch]:
    """
    Normaliza nome de especialidade para ID do banco.
    """
    # 1. Alias exato
    match = await buscar_especialidade_por_alias(texto)
    if match:
        return match

    # 2. Similaridade
    match = await buscar_especialidade_por_similaridade(texto)
    if match:
        return match

    return None


# =============================================================================
# S06.5 - Match de Período/Setor/Tipo
# =============================================================================

# Mapas de normalização
MAPA_PERIODOS = {
    # Termos diretos
    "noturno": "Noturno",
    "diurno": "Diurno",
    "vespertino": "Vespertino",
    "cinderela": "Cinderela",
    # Partes do dia
    "manha": "Diurno",
    "manhã": "Diurno",
    "tarde": "Vespertino",
    "noite": "Noturno",
    "dia": "Diurno",
    "madrugada": "Noturno",
    # Combinações comuns
    "plantao diurno": "Diurno",
    "plantao noturno": "Noturno",
    "turno diurno": "Diurno",
    "turno noturno": "Noturno",
    # Durações
    "12h": "Diurno",
    "12 horas": "Diurno",
    "24h": "Diurno",  # Plantão 24h geralmente começa de dia
    "24 horas": "Diurno",
    # Abreviações
    "sd": "Diurno",  # SD = Serviço Diurno
    "sn": "Noturno",  # SN = Serviço Noturno
}

MAPA_SETORES = {
    "ps": "Pronto atendimento",
    "pa": "Pronto atendimento",
    "pronto socorro": "Pronto atendimento",
    "pronto atendimento": "Pronto atendimento",
    "emergencia": "Pronto atendimento",
    "uti": "Hospital",
    "enfermaria": "Hospital",
    "internacao": "Hospital",
    "centro cirurgico": "C. Cirúrgico",
    "cc": "C. Cirúrgico",
    "bloco cirurgico": "C. Cirúrgico",
    "rpa": "RPA",
    "recuperacao": "RPA",
    "sadt": "SADT",
    "ambulatorio": "SADT",
}

MAPA_TIPOS_VAGA = {
    "cobertura": "Cobertura",
    "extra": "Cobertura",
    "avulso": "Cobertura",
    "fixo": "Fixo",
    "mensal": "Mensal",
    "plantao fixo": "Fixo",
    "escala fixa": "Fixo",
    "ambulatorial": "Ambulatorial",
}

MAPA_FORMAS_PAGAMENTO = {
    "pj": "Pessoa jurídica",
    "pessoa juridica": "Pessoa jurídica",
    "pf": "Pessoa fisica",
    "pessoa fisica": "Pessoa fisica",
    "clt": "CLT",
    "scp": "SCP",
    "rpa": "Pessoa fisica",  # RPA geralmente é PF
}


def inferir_periodo_por_horario(hora_inicio: str, hora_fim: str = None) -> Optional[str]:
    """
    Infere período baseado nos horários quando não extraído explicitamente.

    Args:
        hora_inicio: Horário de início (ex: "19:00", "07:00:00")
        hora_fim: Horário de fim (opcional)

    Returns:
        Nome do período inferido ou None
    """
    if not hora_inicio:
        return None

    try:
        # Extrair hora (suporta HH:MM e HH:MM:SS)
        hora_str = str(hora_inicio).split(":")[0]
        h_inicio = int(hora_str)

        # Regras de inferência baseadas no horário de início:
        # 19:00-06:00 = Noturno (começa de noite)
        if h_inicio >= 19 or h_inicio < 6:
            return "Noturno"
        # 06:00-13:00 = Diurno (começa de manhã)
        elif 6 <= h_inicio < 13:
            return "Diurno"
        # 13:00-19:00 = Vespertino (começa de tarde)
        else:
            return "Vespertino"

    except (ValueError, AttributeError, IndexError) as e:
        logger.debug(f"Não foi possível inferir período de hora_inicio={hora_inicio}: {e}")
        return None


async def normalizar_periodo(texto: str) -> Optional[UUID]:
    """Normaliza período para ID."""
    if not texto:
        return None

    texto_norm = normalizar_para_busca(texto)

    # Buscar no mapa
    nome_periodo = None
    for key, value in MAPA_PERIODOS.items():
        if key in texto_norm:
            nome_periodo = value
            break

    if not nome_periodo:
        return None

    try:
        result = supabase.table("periodos") \
            .select("id") \
            .eq("nome", nome_periodo) \
            .limit(1) \
            .execute()

        return UUID(result.data[0]["id"]) if result.data else None
    except Exception as e:
        logger.warning(f"Erro ao normalizar período: {e}")
        return None


async def normalizar_setor(texto: str) -> Optional[UUID]:
    """Normaliza setor para ID."""
    if not texto:
        return None

    texto_norm = normalizar_para_busca(texto)

    nome_setor = None
    for key, value in MAPA_SETORES.items():
        if key in texto_norm:
            nome_setor = value
            break

    if not nome_setor:
        return None

    try:
        result = supabase.table("setores") \
            .select("id") \
            .eq("nome", nome_setor) \
            .limit(1) \
            .execute()

        return UUID(result.data[0]["id"]) if result.data else None
    except Exception as e:
        logger.warning(f"Erro ao normalizar setor: {e}")
        return None


async def normalizar_tipo_vaga(texto: str) -> Optional[UUID]:
    """Normaliza tipo de vaga para ID."""
    if not texto:
        return None

    texto_norm = normalizar_para_busca(texto)

    nome_tipo = None
    for key, value in MAPA_TIPOS_VAGA.items():
        if key in texto_norm:
            nome_tipo = value
            break

    if not nome_tipo:
        return None

    try:
        result = supabase.table("tipos_vaga") \
            .select("id") \
            .eq("nome", nome_tipo) \
            .limit(1) \
            .execute()

        return UUID(result.data[0]["id"]) if result.data else None
    except Exception as e:
        logger.warning(f"Erro ao normalizar tipo de vaga: {e}")
        return None


async def normalizar_forma_pagamento(texto: str) -> Optional[UUID]:
    """Normaliza forma de pagamento para ID."""
    if not texto:
        return None

    texto_norm = normalizar_para_busca(texto)

    nome_forma = None
    for key, value in MAPA_FORMAS_PAGAMENTO.items():
        if key in texto_norm:
            nome_forma = value
            break

    if not nome_forma:
        return None

    try:
        result = supabase.table("formas_recebimento") \
            .select("id") \
            .eq("nome", nome_forma) \
            .limit(1) \
            .execute()

        return UUID(result.data[0]["id"]) if result.data else None
    except Exception as e:
        logger.warning(f"Erro ao normalizar forma de pagamento: {e}")
        return None


# =============================================================================
# S06.6 - Processador de Normalização
# =============================================================================

@dataclass
class ResultadoNormalizacao:
    """Resultado da normalização de uma vaga."""
    hospital_id: Optional[UUID] = None
    hospital_nome: Optional[str] = None
    hospital_score: float = 0.0

    especialidade_id: Optional[UUID] = None
    especialidade_nome: Optional[str] = None
    especialidade_score: float = 0.0

    periodo_id: Optional[UUID] = None
    setor_id: Optional[UUID] = None
    tipo_vaga_id: Optional[UUID] = None
    forma_pagamento_id: Optional[UUID] = None

    status: str = "pendente"  # "normalizada", "aguardando_revisao", "erro"
    motivo_status: Optional[str] = None


async def normalizar_vaga(vaga_id: UUID) -> ResultadoNormalizacao:
    """
    Normaliza uma vaga extraída.

    Atualiza vagas_grupo com IDs normalizados.
    """
    resultado = ResultadoNormalizacao()

    try:
        # Buscar vaga
        vaga = supabase.table("vagas_grupo") \
            .select("*") \
            .eq("id", str(vaga_id)) \
            .single() \
            .execute()

        if not vaga.data:
            resultado.status = "erro"
            resultado.motivo_status = "vaga_nao_encontrada"
            return resultado

        dados = vaga.data
        updates = {}

        # Normalizar hospital (com criação automática se não existir)
        if dados.get("hospital_raw"):
            from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

            # Tentar obter região do grupo
            regiao_grupo = ""
            if dados.get("grupo_origem_id"):
                try:
                    grupo = supabase.table("grupos_whatsapp") \
                        .select("regiao") \
                        .eq("id", dados["grupo_origem_id"]) \
                        .single() \
                        .execute()
                    regiao_grupo = grupo.data.get("regiao", "") if grupo.data else ""
                except Exception:
                    pass

            match = await normalizar_ou_criar_hospital(dados["hospital_raw"], regiao_grupo)
            if match:
                updates["hospital_id"] = str(match.hospital_id)
                updates["hospital_match_score"] = match.score
                updates["hospital_criado"] = match.foi_criado
                resultado.hospital_id = match.hospital_id
                resultado.hospital_nome = match.nome
                resultado.hospital_score = match.score

        # Normalizar especialidade
        if dados.get("especialidade_raw"):
            match = await normalizar_especialidade(dados["especialidade_raw"])
            if match:
                updates["especialidade_id"] = str(match.entidade_id)
                updates["especialidade_match_score"] = match.score
                resultado.especialidade_id = match.entidade_id
                resultado.especialidade_nome = match.nome
                resultado.especialidade_score = match.score

        # Normalizar período
        periodo_id = None
        if dados.get("periodo_raw"):
            periodo_id = await normalizar_periodo(dados["periodo_raw"])
            if periodo_id:
                updates["periodo_id"] = str(periodo_id)
                resultado.periodo_id = periodo_id

        # Se não tem periodo_raw mas tem horário, inferir período
        if not periodo_id and dados.get("hora_inicio"):
            periodo_inferido = inferir_periodo_por_horario(
                str(dados.get("hora_inicio")),
                str(dados.get("hora_fim")) if dados.get("hora_fim") else None
            )
            if periodo_inferido:
                periodo_id = await normalizar_periodo(periodo_inferido)
                if periodo_id:
                    updates["periodo_id"] = str(periodo_id)
                    resultado.periodo_id = periodo_id
                    logger.info(
                        f"Período inferido por horário: {periodo_inferido} "
                        f"(hora_inicio={dados.get('hora_inicio')})"
                    )

        # Normalizar setor
        if dados.get("setor_raw"):
            setor_id = await normalizar_setor(dados["setor_raw"])
            if setor_id:
                updates["setor_id"] = str(setor_id)
                resultado.setor_id = setor_id

        # Normalizar tipo de vaga
        if dados.get("tipo_vaga_raw"):
            tipo_id = await normalizar_tipo_vaga(dados["tipo_vaga_raw"])
            if tipo_id:
                updates["tipo_vaga_id"] = str(tipo_id)
                resultado.tipo_vaga_id = tipo_id

        # Normalizar forma de pagamento
        if dados.get("forma_pagamento_raw"):
            forma_id = await normalizar_forma_pagamento(dados["forma_pagamento_raw"])
            if forma_id:
                updates["forma_pagamento_id"] = str(forma_id)
                resultado.forma_pagamento_id = forma_id

        # Determinar status
        if resultado.hospital_id and resultado.especialidade_id:
            # Match completo
            if resultado.hospital_score >= 0.8 and resultado.especialidade_score >= 0.8:
                updates["status"] = "normalizada"
                resultado.status = "normalizada"
            else:
                updates["status"] = "aguardando_revisao"
                updates["motivo_status"] = "score_baixo"
                resultado.status = "aguardando_revisao"
                resultado.motivo_status = "score_baixo"
        else:
            updates["status"] = "aguardando_revisao"
            campos_faltando = []
            if not resultado.hospital_id:
                campos_faltando.append("hospital")
            if not resultado.especialidade_id:
                campos_faltando.append("especialidade")
            updates["motivo_status"] = f"match_incompleto:{','.join(campos_faltando)}"
            resultado.status = "aguardando_revisao"
            resultado.motivo_status = updates["motivo_status"]

        # Salvar atualizações
        if updates:
            supabase.table("vagas_grupo") \
                .update(updates) \
                .eq("id", str(vaga_id)) \
                .execute()

        return resultado

    except Exception as e:
        logger.error(f"Erro ao normalizar vaga {vaga_id}: {e}")
        resultado.status = "erro"
        resultado.motivo_status = str(e)
        return resultado


async def normalizar_batch(limite: int = 50) -> dict:
    """
    Processa batch de vagas para normalização.

    Returns:
        Estatísticas do processamento
    """
    stats = {
        "vagas_processadas": 0,
        "normalizadas": 0,
        "aguardando_revisao": 0,
        "erros": 0,
    }

    try:
        # Buscar vagas pendentes
        result = supabase.table("vagas_grupo") \
            .select("id") \
            .eq("status", "nova") \
            .limit(limite) \
            .execute()

        for vaga in result.data:
            resultado = await normalizar_vaga(UUID(vaga["id"]))
            stats["vagas_processadas"] += 1

            if resultado.status == "normalizada":
                stats["normalizadas"] += 1
            elif resultado.status == "aguardando_revisao":
                stats["aguardando_revisao"] += 1
            else:
                stats["erros"] += 1

        logger.info(
            f"Normalização processou {stats['vagas_processadas']} vagas: "
            f"{stats['normalizadas']} normalizadas, "
            f"{stats['aguardando_revisao']} aguardando revisão"
        )

    except Exception as e:
        logger.error(f"Erro no batch de normalização: {e}")

    return stats


# =============================================================================
# Funções auxiliares para criar alias
# =============================================================================

async def criar_alias_hospital(
    hospital_id: UUID,
    alias: str,
    origem: str = "extracao",
    criado_por: str = "sistema"
) -> bool:
    """Cria um novo alias para hospital."""
    alias_norm = normalizar_para_busca(alias)

    if not alias_norm:
        return False

    try:
        supabase.table("hospitais_alias").insert({
            "hospital_id": str(hospital_id),
            "alias": alias,
            "alias_normalizado": alias_norm,
            "origem": origem,
            "criado_por": criado_por,
            "confianca": 0.5,  # Confiança inicial média
            "confirmado": False,
        }).execute()
        return True
    except Exception as e:
        logger.warning(f"Erro ao criar alias de hospital: {e}")
        return False


async def criar_alias_especialidade(
    especialidade_id: UUID,
    alias: str,
    origem: str = "extracao",
    criado_por: str = "sistema"
) -> bool:
    """Cria um novo alias para especialidade."""
    alias_norm = normalizar_para_busca(alias)

    if not alias_norm:
        return False

    try:
        supabase.table("especialidades_alias").insert({
            "especialidade_id": str(especialidade_id),
            "alias": alias,
            "alias_normalizado": alias_norm,
            "origem": origem,
            "criado_por": criado_por,
            "confianca": 0.5,
            "confirmado": False,
        }).execute()
        return True
    except Exception as e:
        logger.warning(f"Erro ao criar alias de especialidade: {e}")
        return False
