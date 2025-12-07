"""
Tools relacionadas a vagas e plantoes.
"""
import logging
from typing import Any

from app.services.vaga import (
    buscar_vaga_por_id,
    buscar_vagas_compativeis,
    buscar_vagas_por_regiao,
    reservar_vaga,
    formatar_vaga_para_mensagem,
    formatar_vagas_contexto,
    verificar_conflito,
)
from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

# Cache para especialidade nome -> id
CACHE_TTL_ESPECIALIDADE = 3600  # 1 hora


async def _buscar_especialidade_id_por_nome(nome: str) -> str | None:
    """
    Busca ID da especialidade pelo nome (com cache).

    Args:
        nome: Nome da especialidade (ex: "Anestesiologia")

    Returns:
        UUID da especialidade ou None se não encontrada
    """
    if not nome:
        return None

    # Normalizar nome para busca
    nome_normalizado = nome.strip().lower()
    cache_key = f"especialidade:nome:{nome_normalizado}"

    # Tentar cache
    cached = await cache_get_json(cache_key)
    if cached:
        return cached.get("id")

    # Buscar no banco (case insensitive)
    try:
        response = (
            supabase.table("especialidades")
            .select("id, nome")
            .ilike("nome", f"%{nome_normalizado}%")
            .limit(1)
            .execute()
        )

        if response.data:
            especialidade = response.data[0]
            # Salvar no cache
            await cache_set_json(cache_key, especialidade, CACHE_TTL_ESPECIALIDADE)
            return especialidade["id"]

        logger.warning(f"Especialidade '{nome}' não encontrada no banco")
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar especialidade por nome: {e}")
        return None


# =============================================================================
# TOOL: BUSCAR VAGAS
# =============================================================================

TOOL_BUSCAR_VAGAS = {
    "name": "buscar_vagas",
    "description": """Busca vagas de plantao compativeis com o perfil do medico.

QUANDO USAR:
- Medico pergunta por vagas/plantoes disponiveis
- Medico quer saber o que tem de vaga
- Medico menciona interesse em trabalhar
- Medico pergunta sobre oportunidades

EXEMPLOS DE GATILHO:
- "Tem alguma vaga?"
- "Quais plantoes tem?"
- "To procurando plantao"
- "O que voces tem de vaga?"
- "Tem algo pra essa semana?"
- "Quero ver as vagas"

PARAMETROS OPCIONAIS:
- regiao: Se medico mencionar regiao especifica (ex: "zona sul", "ABC")
- periodo: Se medico pedir turno especifico (diurno, noturno)
- valor_minimo: Se medico mencionar valor minimo aceitavel
- dias_semana: Se medico restringir a dias especificos

NAO use esta tool se:
- Medico ja recusou vagas recentemente
- Medico pediu para parar de mandar vagas
- Contexto indica opt-out""",
    "input_schema": {
        "type": "object",
        "properties": {
            "regiao": {
                "type": "string",
                "description": "Regiao de preferencia do medico (ex: 'zona sul', 'ABC', 'centro'). Extrair da mensagem se mencionado."
            },
            "periodo": {
                "type": "string",
                "enum": ["diurno", "noturno", "12h", "24h", "qualquer"],
                "description": "Tipo de plantao preferido. Use 'qualquer' se nao especificado."
            },
            "valor_minimo": {
                "type": "number",
                "description": "Valor minimo do plantao em reais. Extrair se medico mencionar (ex: 'acima de 2000')."
            },
            "dias_semana": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dias preferidos (ex: ['segunda', 'terca']). Deixar vazio para qualquer dia."
            },
            "limite": {
                "type": "integer",
                "default": 5,
                "description": "Maximo de vagas a retornar (padrao: 5, max: 10)."
            }
        },
        "required": []
    }
}


async def handle_buscar_vagas(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict[str, Any]:
    """
    Processa chamada da tool buscar_vagas.

    Fluxo:
    1. Extrai parametros da tool_input
    2. Aplica filtros de preferencias do medico
    3. Busca vagas compativeis com especialidade
    4. Filtra por conflitos existentes
    5. Formata resultado para LLM

    Args:
        tool_input: Input da tool (regiao, periodo, valor_minimo, etc)
        medico: Dados do medico (incluindo especialidade_id, preferencias)
        conversa: Dados da conversa atual

    Returns:
        Dict com vagas encontradas e contexto formatado
    """
    regiao = tool_input.get("regiao")
    periodo = tool_input.get("periodo", "qualquer")
    valor_minimo = tool_input.get("valor_minimo", 0)
    dias_semana = tool_input.get("dias_semana", [])
    limite = min(tool_input.get("limite", 5), 10)  # Max 10

    logger.info(
        f"Buscando vagas para medico {medico.get('id')}: "
        f"regiao={regiao}, periodo={periodo}, valor_min={valor_minimo}"
    )

    # Verificar se medico tem especialidade
    # Prioridade: especialidade_id > lookup por nome
    especialidade_id = medico.get("especialidade_id")

    if not especialidade_id:
        # Tentar obter especialidade_id pelo nome da especialidade
        especialidade_nome = medico.get("especialidade")
        if especialidade_nome:
            especialidade_id = await _buscar_especialidade_id_por_nome(especialidade_nome)
            if especialidade_id:
                logger.info(f"Especialidade '{especialidade_nome}' mapeada para ID {especialidade_id}")
                # Atualizar medico dict para usar nas próximas funções
                medico["especialidade_id"] = especialidade_id

    if not especialidade_id:
        logger.warning(f"Medico {medico.get('id')} sem especialidade definida")
        return {
            "success": False,
            "error": "Especialidade do medico nao identificada",
            "vagas": [],
            "mensagem_sugerida": "Qual sua especialidade? Preciso saber pra te mostrar as vagas certas"
        }

    # Aplicar preferencias extras do input da tool
    preferencias_extras = {}
    if valor_minimo > 0:
        preferencias_extras["valor_minimo"] = valor_minimo

    # Merge com preferencias existentes do medico
    preferencias_medico = medico.get("preferencias_detectadas") or {}
    preferencias_combinadas = {**preferencias_medico, **preferencias_extras}

    # Atualizar medico dict temporariamente para busca
    medico_com_prefs = {**medico, "preferencias_detectadas": preferencias_combinadas}

    try:
        # Buscar vagas (com priorização por região se disponível)
        if regiao:
            vagas = await buscar_vagas_por_regiao(
                medico=medico_com_prefs,
                limite=limite * 2  # Buscar mais para filtrar
            )
        else:
            vagas = await buscar_vagas_compativeis(
                medico=medico_com_prefs,
                limite=limite * 2
            )

        # Filtrar por período se especificado
        if periodo and periodo != "qualquer":
            vagas = _filtrar_por_periodo(vagas, periodo)

        # Filtrar por dias da semana se especificado
        if dias_semana:
            vagas = _filtrar_por_dias_semana(vagas, dias_semana)

        # Filtrar conflitos (vagas em dia/período que médico já tem plantão)
        vagas_sem_conflito = []
        for vaga in vagas:
            data = vaga.get("data")
            periodo_id = vaga.get("periodo_id")

            if data and periodo_id:
                tem_conflito = await verificar_conflito(
                    cliente_id=medico["id"],
                    data=data,
                    periodo_id=periodo_id
                )
                if not tem_conflito:
                    vagas_sem_conflito.append(vaga)
                else:
                    logger.debug(f"Vaga {vaga['id']} filtrada: conflito de horario")
            else:
                vagas_sem_conflito.append(vaga)

        # Limitar resultado final
        vagas_final = vagas_sem_conflito[:limite]

        if not vagas_final:
            logger.info(f"Nenhuma vaga encontrada para medico {medico.get('id')}")
            return {
                "success": True,
                "vagas": [],
                "total_encontradas": 0,
                "mensagem_sugerida": "Nao tem vaga disponivel no momento pra sua especialidade. Mas assim que surgir algo, te aviso!"
            }

        # Formatar para contexto do LLM
        especialidade_nome = medico.get("especialidades", {}).get("nome")
        contexto_formatado = formatar_vagas_contexto(vagas_final, especialidade_nome)

        # Preparar lista simplificada para resposta
        vagas_resumo = []
        for v in vagas_final:
            vagas_resumo.append({
                "id": v.get("id"),
                "hospital": v.get("hospitais", {}).get("nome"),
                "cidade": v.get("hospitais", {}).get("cidade"),
                "data": v.get("data"),
                "periodo": v.get("periodos", {}).get("nome"),
                "valor": v.get("valor"),
                "setor": v.get("setores", {}).get("nome"),
            })

        logger.info(f"Encontradas {len(vagas_final)} vagas para medico {medico.get('id')}")

        return {
            "success": True,
            "vagas": vagas_resumo,
            "total_encontradas": len(vagas_final),
            "contexto": contexto_formatado,
            "instrucao": (
                "Apresente as vagas de forma natural, uma por vez. "
                "SEMPRE mencione a DATA do plantao (dia/mes) pois sera usada para reservar. "
                "Quando o medico aceitar, use a tool reservar_plantao com a DATA no formato YYYY-MM-DD."
            )
        }

    except Exception as e:
        logger.error(f"Erro ao buscar vagas: {e}")
        return {
            "success": False,
            "error": str(e),
            "vagas": [],
            "mensagem_sugerida": "Tive um probleminha aqui, me da um minuto que ja te mostro as vagas"
        }


def _filtrar_por_periodo(vagas: list[dict], periodo_desejado: str) -> list[dict]:
    """
    Filtra vagas por tipo de período.

    Args:
        vagas: Lista de vagas
        periodo_desejado: 'diurno', 'noturno', '12h', '24h'

    Returns:
        Vagas filtradas
    """
    mapeamento = {
        "diurno": ["diurno", "dia", "manha", "tarde"],
        "noturno": ["noturno", "noite"],
        "12h": ["12h", "12 horas"],
        "24h": ["24h", "24 horas"],
    }

    termos = mapeamento.get(periodo_desejado.lower(), [periodo_desejado.lower()])

    resultado = []
    for v in vagas:
        periodo_nome = v.get("periodos", {}).get("nome", "").lower()
        if any(termo in periodo_nome for termo in termos):
            resultado.append(v)

    return resultado if resultado else vagas  # Retorna original se filtro não encontrar nada


def _filtrar_por_dias_semana(vagas: list[dict], dias_desejados: list[str]) -> list[dict]:
    """
    Filtra vagas por dias da semana.

    Args:
        vagas: Lista de vagas
        dias_desejados: Lista de dias (ex: ['segunda', 'terca'])

    Returns:
        Vagas filtradas
    """
    from datetime import datetime

    dias_map = {
        "segunda": 0, "seg": 0,
        "terca": 1, "ter": 1,
        "quarta": 2, "qua": 2,
        "quinta": 3, "qui": 3,
        "sexta": 4, "sex": 4,
        "sabado": 5, "sab": 5,
        "domingo": 6, "dom": 6,
    }

    dias_indices = set()
    for d in dias_desejados:
        d_lower = d.lower().replace("ç", "c").replace("-feira", "")
        if d_lower in dias_map:
            dias_indices.add(dias_map[d_lower])

    if not dias_indices:
        return vagas

    resultado = []
    for v in vagas:
        data_str = v.get("data")
        if data_str:
            try:
                data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                if data_obj.weekday() in dias_indices:
                    resultado.append(v)
            except ValueError:
                resultado.append(v)  # Incluir se data inválida
        else:
            resultado.append(v)

    return resultado if resultado else vagas


TOOL_RESERVAR_PLANTAO = {
    "name": "reservar_plantao",
    "description": """Reserva um plantao/vaga para o medico.

Use quando o medico aceitar uma vaga que voce ofereceu.
Exemplos de aceite:
- "Pode reservar"
- "Quero essa"
- "Fechado"
- "Aceito"
- "Pode ser"
- "Vou querer"

COMO USAR:
- Use o parametro 'data_plantao' com a data no formato YYYY-MM-DD (ex: 2025-12-12)
- A data e obrigatoria e suficiente para identificar a vaga
- NAO invente IDs - use apenas a data do plantao que o medico escolheu""",
    "input_schema": {
        "type": "object",
        "properties": {
            "data_plantao": {
                "type": "string",
                "description": "Data do plantao no formato YYYY-MM-DD (ex: 2025-12-12). OBRIGATORIO."
            },
            "confirmacao": {
                "type": "string",
                "description": "Breve descricao da confirmacao do medico (ex: 'medico disse pode reservar')"
            }
        },
        "required": ["data_plantao", "confirmacao"]
    }
}


async def _buscar_vaga_por_data(data: str, especialidade_id: str) -> dict | None:
    """
    Busca vaga pela data e especialidade.

    Args:
        data: Data no formato YYYY-MM-DD
        especialidade_id: ID da especialidade do médico

    Returns:
        Vaga encontrada ou None
    """
    try:
        response = (
            supabase.table("vagas")
            .select("*, hospitais(*), periodos(*), setores(*)")
            .eq("data", data)
            .eq("especialidade_id", especialidade_id)
            .eq("status", "aberta")
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar vaga por data: {e}")
        return None


async def handle_reservar_plantao(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict[str, Any]:
    """
    Processa chamada da tool reservar_plantao.

    Args:
        tool_input: Input da tool (data_plantao, confirmacao)
        medico: Dados do medico
        conversa: Dados da conversa

    Returns:
        Dict com resultado da operacao
    """
    data_plantao = tool_input.get("data_plantao")
    confirmacao = tool_input.get("confirmacao", "")

    if not data_plantao:
        return {
            "success": False,
            "error": "Data do plantao nao informada",
            "mensagem_sugerida": "Qual a data do plantao que vc quer? Me fala no formato dia/mes"
        }

    # Normalizar data (aceitar formatos variados)
    import re
    data_normalizada = data_plantao

    # Se vier como DD/MM/YYYY, converter para YYYY-MM-DD
    if re.match(r'^\d{2}/\d{2}/\d{4}$', data_plantao):
        partes = data_plantao.split('/')
        data_normalizada = f"{partes[2]}-{partes[1]}-{partes[0]}"
    # Se vier como DD/MM, assumir ano atual
    elif re.match(r'^\d{2}/\d{2}$', data_plantao):
        from datetime import datetime
        partes = data_plantao.split('/')
        ano = datetime.now().year
        data_normalizada = f"{ano}-{partes[1]}-{partes[0]}"

    logger.info(f"Buscando vaga para data: {data_normalizada}")

    # Verificar especialidade do médico
    especialidade_id = medico.get("especialidade_id")
    if not especialidade_id:
        especialidade_nome = medico.get("especialidade")
        if especialidade_nome:
            especialidade_id = await _buscar_especialidade_id_por_nome(especialidade_nome)

    if not especialidade_id:
        return {
            "success": False,
            "error": "Especialidade do medico nao identificada",
            "mensagem_sugerida": "Qual sua especialidade?"
        }

    # Buscar vaga pela data
    vaga = await _buscar_vaga_por_data(data_normalizada, especialidade_id)
    if not vaga:
        return {
            "success": False,
            "error": f"Nao encontrei vaga para a data {data_normalizada}",
            "mensagem_sugerida": "Nao achei vaga pra essa data. Quer que eu veja as vagas disponiveis?"
        }

    vaga_id = vaga["id"]
    logger.info(f"Vaga encontrada por data: {vaga_id} - {vaga.get('hospitais', {}).get('nome')} em {data_normalizada}")

    try:
        # Reservar vaga
        vaga_atualizada = await reservar_vaga(
            vaga_id=vaga_id,
            cliente_id=medico["id"],
            medico=medico,
            notificar_gestor=True
        )

        # Formatar mensagem de confirmacao
        vaga_formatada = formatar_vaga_para_mensagem(vaga)

        logger.info(f"Plantao reservado: {vaga_id} para medico {medico['id']}")

        return {
            "success": True,
            "message": f"Plantao reservado com sucesso: {vaga_formatada}",
            "vaga": {
                "id": vaga_atualizada["id"],
                "hospital": vaga.get("hospitais", {}).get("nome"),
                "data": vaga_atualizada.get("data"),
                "status": vaga_atualizada.get("status")
            }
        }

    except ValueError as e:
        logger.warning(f"Erro ao reservar plantao: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    except Exception as e:
        logger.error(f"Erro inesperado ao reservar plantao: {e}")
        return {
            "success": False,
            "error": "Erro ao processar reserva. Tente novamente."
        }


# Lista de todas as tools de vagas
TOOLS_VAGAS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
]
