"""
Tools relacionadas a vagas e plantoes.

Sprint 31 - S31.E5: Refatorado para usar services
"""

import logging
from typing import Any

from app.core.timezone import agora_brasilia
from app.services.vagas import (
    buscar_vagas_compativeis,
    buscar_vagas_por_regiao,
    reservar_vaga,
    formatar_vaga_para_mensagem,
    formatar_vagas_contexto,
    verificar_conflito,
    # Sprint 31 - Novos componentes
    get_especialidade_service,
    aplicar_filtros,
    filtrar_por_conflitos,
)
from app.services.supabase import supabase
from app.tools.response_formatter import (
    get_vagas_formatter,
    get_reserva_formatter,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Compatibilidade - função wrapper para código legado
# =============================================================================


async def _buscar_especialidade_id_por_nome(nome: str) -> str | None:
    """
    Busca ID da especialidade pelo nome (com cache).

    DEPRECATED: Use get_especialidade_service().buscar_por_nome() diretamente.
    Mantido para compatibilidade com código legado.
    """
    service = get_especialidade_service()
    return await service.buscar_por_nome(nome)


# =============================================================================
# TOOL: BUSCAR VAGAS
# =============================================================================

TOOL_BUSCAR_VAGAS = {
    "name": "buscar_vagas",
    "description": """LISTA vagas de plantao disponiveis. Esta tool apenas MOSTRA opcoes, NAO reserva.

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
- "Tem vaga de cardiologia?" (especifica especialidade)

NAO USE ESTA TOOL PARA RESERVAR!
Se o medico quer RESERVAR uma vaga, use 'reservar_plantao' ao inves.

PARAMETROS OPCIONAIS:
- especialidade: Se medico pedir especialidade DIFERENTE da dele (ex: "vagas de cardiologia")
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
            "especialidade": {
                "type": "string",
                "description": "Especialidade solicitada pelo medico (ex: 'cardiologia', 'anestesiologia'). Se nao especificada, usa a especialidade cadastrada do medico.",
            },
            "regiao": {
                "type": "string",
                "description": "Regiao de preferencia do medico (ex: 'zona sul', 'ABC', 'centro'). Extrair da mensagem se mencionado.",
            },
            "periodo": {
                "type": "string",
                "enum": ["diurno", "noturno", "12h", "24h", "qualquer"],
                "description": "Tipo de plantao preferido. Use 'qualquer' se nao especificado.",
            },
            "valor_minimo": {
                "type": "number",
                "description": "Valor minimo do plantao em reais. Extrair se medico mencionar (ex: 'acima de 2000').",
            },
            "dias_semana": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dias preferidos (ex: ['segunda', 'terca']). Deixar vazio para qualquer dia.",
            },
            "limite": {
                "type": "integer",
                "default": 5,
                "description": "Maximo de vagas a retornar (padrao: 5, max: 10).",
            },
        },
        "required": [],
    },
}


async def handle_buscar_vagas(tool_input: dict, medico: dict, conversa: dict) -> dict[str, Any]:
    """
    Processa chamada da tool buscar_vagas.

    Sprint 31 - Refatorado para usar services.

    Fluxo:
    1. Parse e validação de input
    2. Resolução de especialidade via EspecialidadeService
    3. Busca de vagas via service existente
    4. Aplicação de filtros via módulo de filtros
    5. Formatação de resposta via VagasResponseFormatter

    Args:
        tool_input: Input da tool (especialidade, regiao, periodo, valor_minimo, etc)
        medico: Dados do medico (incluindo especialidade_id, preferencias)
        conversa: Dados da conversa atual

    Returns:
        Dict com vagas encontradas e contexto formatado
    """
    # Services
    especialidade_service = get_especialidade_service()
    formatter = get_vagas_formatter()

    # 1. Parse input
    especialidade_solicitada = _limpar_especialidade_input(tool_input.get("especialidade"))
    regiao = tool_input.get("regiao")
    periodo = tool_input.get("periodo", "qualquer")
    valor_minimo = tool_input.get("valor_minimo", 0)
    dias_semana = tool_input.get("dias_semana", [])
    limite = min(tool_input.get("limite", 5), 10)

    # 2. Resolver especialidade
    (
        especialidade_id,
        especialidade_nome,
        especialidade_diferente,
    ) = await especialidade_service.resolver_especialidade_medico(especialidade_solicitada, medico)

    # Validar especialidade
    if especialidade_solicitada and not especialidade_id:
        return {
            "success": False,
            "error": f"Especialidade '{especialidade_solicitada}' nao encontrada",
            "vagas": [],
            "mensagem_sugerida": formatter.mensagem_especialidade_nao_encontrada(
                especialidade_solicitada
            ),
        }

    if not especialidade_id:
        logger.warning(f"Medico {medico.get('id')} sem especialidade definida")
        return {
            "success": False,
            "error": "Especialidade nao identificada",
            "vagas": [],
            "mensagem_sugerida": formatter.mensagem_especialidade_nao_identificada(),
        }

    logger.info(
        f"Buscando vagas para medico {medico.get('id')}: "
        f"especialidade={especialidade_nome}, regiao={regiao}, periodo={periodo}"
    )

    # Atualizar medico dict
    medico["especialidade_id"] = especialidade_id
    medico_com_prefs = _preparar_medico_com_preferencias(medico, valor_minimo)

    try:
        # 3. Buscar vagas
        vagas = await _buscar_vagas_base(medico_com_prefs, regiao, limite)
        total_inicial = len(vagas)

        # 4. Aplicar filtros
        vagas, filtros_aplicados = aplicar_filtros(vagas, periodo, dias_semana)
        vagas = await filtrar_por_conflitos(vagas, medico["id"], verificar_conflito)
        vagas_final = vagas[:limite]

        # 5. Formatar resposta
        if not vagas_final:
            return _construir_resposta_sem_vagas(
                formatter,
                especialidade_nome,
                total_inicial,
                filtros_aplicados,
                especialidade_diferente,
                medico.get("especialidade"),
            )

        return _construir_resposta_com_vagas(
            formatter,
            vagas_final,
            especialidade_nome,
            especialidade_diferente,
            medico.get("especialidade"),
        )

    except Exception as e:
        logger.error(f"Erro ao buscar vagas: {e}")
        return {
            "success": False,
            "error": str(e),
            "vagas": [],
            "mensagem_sugerida": formatter.mensagem_erro_generico(),
        }


def _limpar_especialidade_input(especialidade: str | None) -> str | None:
    """Limpa input de especialidade (bug do LLM envia como array)."""
    if not especialidade:
        return None

    if especialidade.startswith("["):
        import json

        try:
            parsed = json.loads(especialidade)
            if isinstance(parsed, list) and parsed:
                return parsed[0]
        except json.JSONDecodeError:
            return especialidade.strip("[]\"'")

    return especialidade


def _preparar_medico_com_preferencias(medico: dict, valor_minimo: float) -> dict:
    """Prepara dict do médico com preferências para busca."""
    preferencias_extras = {}
    if valor_minimo > 0:
        preferencias_extras["valor_minimo"] = valor_minimo

    preferencias_medico = medico.get("preferencias_detectadas") or {}
    preferencias_combinadas = {**preferencias_medico, **preferencias_extras}

    return {**medico, "preferencias_detectadas": preferencias_combinadas}


async def _buscar_vagas_base(medico: dict, regiao: str | None, limite: int) -> list[dict]:
    """Busca vagas base (com ou sem priorização por região)."""
    if regiao:
        return await buscar_vagas_por_regiao(medico=medico, limite=limite * 2)
    return await buscar_vagas_compativeis(medico=medico, limite=limite * 2)


def _construir_resposta_sem_vagas(
    formatter,
    especialidade_nome: str,
    total_inicial: int,
    filtros_aplicados: list[str],
    especialidade_diferente: bool,
    especialidade_cadastrada: str | None,
) -> dict:
    """Constrói resposta quando não há vagas."""
    logger.info(f"Nenhuma vaga encontrada para especialidade {especialidade_nome}")

    mensagem = formatter.mensagem_sem_vagas(
        especialidade_nome=especialidade_nome,
        total_sem_filtros=total_inicial,
        filtros_aplicados=filtros_aplicados if filtros_aplicados else None,
        especialidade_diferente=especialidade_diferente,
        especialidade_cadastrada=especialidade_cadastrada,
    )

    result = {
        "success": True,
        "vagas": [],
        "total_encontradas": 0,
        "especialidade_buscada": especialidade_nome,
        "mensagem_sugerida": mensagem,
    }

    if filtros_aplicados:
        result["total_sem_filtros"] = total_inicial
        result["filtros_aplicados"] = filtros_aplicados

    if especialidade_diferente:
        result["especialidade_cadastrada"] = especialidade_cadastrada

    return result


def _construir_resposta_com_vagas(
    formatter,
    vagas: list[dict],
    especialidade_nome: str,
    especialidade_diferente: bool,
    especialidade_cadastrada: str | None,
) -> dict:
    """Constrói resposta com vagas encontradas."""
    logger.info(f"Encontradas {len(vagas)} vagas")

    # Formatar vagas
    vagas_resumo = formatter.formatar_vagas_resumo(vagas, especialidade_nome)
    contexto_formatado = formatar_vagas_contexto(vagas, especialidade_nome)

    # Construir instrução
    instrucao = formatter.construir_instrucao_vagas(
        especialidade_nome=especialidade_nome,
        especialidade_diferente=especialidade_diferente,
        especialidade_cadastrada=especialidade_cadastrada,
    )

    return {
        "success": True,
        "vagas": vagas_resumo,
        "total_encontradas": len(vagas),
        "especialidade_buscada": especialidade_nome,
        "especialidade_cadastrada": especialidade_cadastrada,
        "especialidade_diferente": especialidade_diferente,
        "contexto": contexto_formatado,
        "instrucao": instrucao,
    }


def _formatar_valor_display(vaga: dict) -> str:
    """
    Formata valor para exibição na resposta da tool.

    DEPRECATED: Use get_vagas_formatter().formatar_valor_display() diretamente.
    Mantido para compatibilidade com código legado.
    """
    formatter = get_vagas_formatter()
    return formatter.formatar_valor_display(vaga)


def _construir_instrucao_confirmacao(vaga: dict, hospital_data: dict) -> str:
    """
    Constrói instrução de confirmação baseada no tipo de valor.

    DEPRECATED: Use get_reserva_formatter().construir_instrucao_confirmacao() diretamente.
    Mantido para compatibilidade com código legado.
    """
    formatter = get_reserva_formatter()
    return formatter.construir_instrucao_confirmacao(vaga, hospital_data)


def _construir_instrucao_ponte_externa(
    vaga: dict,
    hospital_data: dict,
    ponte_externa: dict,
    medico: dict,
) -> str:
    """
    Constrói instrução de confirmação para vaga com ponte externa.

    DEPRECATED: Use get_reserva_formatter().construir_instrucao_ponte_externa() diretamente.
    Mantido para compatibilidade com código legado.
    """
    formatter = get_reserva_formatter()
    return formatter.construir_instrucao_ponte_externa(vaga, hospital_data, ponte_externa, medico)


def _filtrar_por_periodo(vagas: list[dict], periodo_desejado: str) -> list[dict]:
    """
    Filtra vagas por tipo de período.

    DEPRECATED: Use app.services.vagas.filtrar_por_periodo() diretamente.
    Mantido para compatibilidade com código legado.

    Note: Retorna lista vazia se não houver match (comportamento original).
    """
    from app.services.vagas.filtros import filtrar_por_periodo

    resultado, _ = filtrar_por_periodo(vagas, periodo_desejado)
    return resultado


def _filtrar_por_dias_semana(vagas: list[dict], dias_desejados: list[str]) -> list[dict]:
    """
    Filtra vagas por dias da semana.

    DEPRECATED: Use app.services.vagas.filtrar_por_dias_semana() diretamente.
    Mantido para compatibilidade com código legado.

    Note: Retorna lista vazia se não houver match (comportamento original).
    """
    from app.services.vagas.filtros import filtrar_por_dias_semana

    resultado, _ = filtrar_por_dias_semana(vagas, dias_desejados)
    return resultado


TOOL_RESERVAR_PLANTAO = {
    "name": "reservar_plantao",
    "description": """RESERVA um plantao/vaga para o medico. Use esta tool para CONFIRMAR uma reserva.

QUANDO USAR:
- Medico pede para RESERVAR uma vaga
- Medico ACEITA uma vaga oferecida
- Medico diz: "Pode reservar", "Quero essa", "Fechado", "Aceito", "Pode ser", "Vou querer"
- Medico pede: "Reserva pra mim", "Quero reservar", "Fecha essa vaga"
- Medico especifica: "Quero a vaga do dia X no hospital Y"

COMO USAR:
- Use o parametro 'data_plantao' com a data no formato YYYY-MM-DD (ex: 2025-12-09)
- A data e OBRIGATORIA e suficiente para identificar a vaga
- Extraia a data da conversa (se medico diz "hoje" use a data atual, se diz "dia 15" use essa data)
- NAO invente IDs - use apenas a data do plantao

IMPORTANTE: Se o medico quer VER vagas antes de reservar, use 'buscar_vagas' primeiro.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "data_plantao": {
                "type": "string",
                "description": "Data do plantao no formato YYYY-MM-DD (ex: 2025-12-12). OBRIGATORIO.",
            },
            "confirmacao": {
                "type": "string",
                "description": "Breve descricao da confirmacao do medico (ex: 'medico disse pode reservar')",
            },
        },
        "required": ["data_plantao", "confirmacao"],
    },
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
    logger.info(f"_buscar_vaga_por_data: data={data}, especialidade_id={especialidade_id}")

    try:
        response = (
            supabase.table("vagas")
            .select("*, hospitais(*), periodos(*), setores(*), source, source_id")
            .eq("data", data)
            .eq("especialidade_id", especialidade_id)
            .eq("status", "aberta")
            .limit(1)
            .execute()
        )

        logger.info(
            f"_buscar_vaga_por_data: encontradas {len(response.data) if response.data else 0} vagas"
        )

        if response.data:
            vaga = response.data[0]
            logger.info(
                f"_buscar_vaga_por_data: vaga encontrada id={vaga.get('id')}, "
                f"valor_tipo={vaga.get('valor_tipo')}"
            )
            return vaga

        logger.warning(
            f"_buscar_vaga_por_data: nenhuma vaga encontrada para data={data}, especialidade_id={especialidade_id}"
        )
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar vaga por data: {e}", exc_info=True)
        return None


async def handle_reservar_plantao(tool_input: dict, medico: dict, conversa: dict) -> dict[str, Any]:
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
    tool_input.get("confirmacao", "")

    logger.info(f"handle_reservar_plantao: tool_input={tool_input}, medico_id={medico.get('id')}")

    if not data_plantao:
        return {
            "success": False,
            "error": "Data do plantao nao informada",
            "mensagem_sugerida": "Qual a data do plantao que vc quer? Me fala no formato dia/mes",
        }

    # Normalizar data (aceitar formatos variados)
    import re

    data_normalizada = data_plantao

    # Se vier como DD/MM/YYYY, converter para YYYY-MM-DD
    if re.match(r"^\d{2}/\d{2}/\d{4}$", data_plantao):
        partes = data_plantao.split("/")
        data_normalizada = f"{partes[2]}-{partes[1]}-{partes[0]}"
    # Se vier como DD/MM, assumir ano atual
    elif re.match(r"^\d{2}/\d{2}$", data_plantao):
        partes = data_plantao.split("/")
        ano = agora_brasilia().year
        data_normalizada = f"{ano}-{partes[1]}-{partes[0]}"

    logger.info(f"handle_reservar_plantao: data_normalizada={data_normalizada}")

    # Verificar especialidade do médico
    especialidade_id = medico.get("especialidade_id")
    logger.info(f"handle_reservar_plantao: especialidade_id do medico={especialidade_id}")

    if not especialidade_id:
        especialidade_nome = medico.get("especialidade")
        logger.info(
            f"handle_reservar_plantao: especialidade_nome={especialidade_nome}, buscando ID..."
        )
        if especialidade_nome:
            especialidade_id = await _buscar_especialidade_id_por_nome(especialidade_nome)
            logger.info(f"handle_reservar_plantao: especialidade_id resolvido={especialidade_id}")

    if not especialidade_id:
        return {
            "success": False,
            "error": "Especialidade do medico nao identificada",
            "mensagem_sugerida": "Qual sua especialidade?",
        }

    # Buscar vaga pela data
    vaga = await _buscar_vaga_por_data(data_normalizada, especialidade_id)
    if not vaga:
        return {
            "success": False,
            "error": f"Nao encontrei vaga para a data {data_normalizada}",
            "mensagem_sugerida": "Nao achei vaga pra essa data. Quer que eu veja as vagas disponiveis?",
        }

    vaga_id = vaga["id"]
    logger.info(
        f"Vaga encontrada por data: {vaga_id} - {vaga.get('hospitais', {}).get('nome')} em {data_normalizada}"
    )

    try:
        # Reservar vaga
        vaga_atualizada = await reservar_vaga(
            vaga_id=vaga_id, cliente_id=medico["id"], medico=medico, notificar_gestor=True
        )

        # Formatar mensagem de confirmacao
        vaga_formatada = formatar_vaga_para_mensagem(vaga)

        logger.info(f"Plantao reservado: {vaga_id} para medico {medico['id']}")

        # Extrair dados completos do hospital
        hospital_data = vaga.get("hospitais", {})

        # Sprint 20: Verificar se vaga tem origem externa (grupo)
        ponte_externa = None
        if vaga.get("source") == "grupo" and vaga.get("source_id"):
            logger.info(f"Vaga {vaga_id} tem origem de grupo, iniciando ponte externa")

            from app.services.external_handoff.service import criar_ponte_externa

            try:
                ponte_externa = await criar_ponte_externa(
                    vaga_id=vaga_id,
                    cliente_id=medico["id"],
                    medico=medico,
                    vaga=vaga,
                )
            except Exception as e:
                logger.error(f"Erro ao criar ponte externa: {e}")
                ponte_externa = {"success": False, "error": str(e)}

        # Construir resposta
        resultado = {
            "success": True,
            "message": f"Plantao reservado com sucesso: {vaga_formatada}",
            "vaga": {
                "id": vaga_atualizada["id"],
                "hospital": hospital_data.get("nome"),
                "endereco": hospital_data.get("endereco_formatado"),
                "bairro": hospital_data.get("bairro"),
                "cidade": hospital_data.get("cidade"),
                "data": vaga_atualizada.get("data"),
                "periodo": (vaga.get("periodos") or {}).get("nome"),
                # Campos de valor expandidos (Sprint 19)
                "valor": vaga.get("valor"),
                "valor_minimo": vaga.get("valor_minimo"),
                "valor_maximo": vaga.get("valor_maximo"),
                "valor_tipo": vaga.get("valor_tipo", "fixo"),
                "valor_display": _formatar_valor_display(vaga),
                "status": vaga_atualizada.get("status"),
            },
        }

        # Sprint 20: Se teve ponte externa, adaptar instrucoes
        if ponte_externa and ponte_externa.get("success"):
            divulgador = ponte_externa.get("divulgador", {})
            resultado["ponte_externa"] = {
                "handoff_id": ponte_externa.get("handoff_id"),
                "divulgador_nome": divulgador.get("nome"),
                "divulgador_telefone": divulgador.get("telefone"),
                "divulgador_empresa": divulgador.get("empresa"),
                "msg_enviada": ponte_externa.get("msg_divulgador_enviada", False),
            }
            resultado["instrucao"] = _construir_instrucao_ponte_externa(
                vaga, hospital_data, ponte_externa, medico
            )
        else:
            resultado["instrucao"] = _construir_instrucao_confirmacao(vaga, hospital_data)

        return resultado

    except ValueError as e:
        logger.warning(f"Erro ao reservar plantao: {e}")
        return {"success": False, "error": str(e)}

    except Exception as e:
        logger.error(f"Erro inesperado ao reservar plantao: {e}")
        return {"success": False, "error": "Erro ao processar reserva. Tente novamente."}


# =============================================================================
# TOOL: BUSCAR INFO HOSPITAL
# =============================================================================

TOOL_BUSCAR_INFO_HOSPITAL = {
    "name": "buscar_info_hospital",
    "description": """Busca informacoes sobre um hospital (endereco, cidade, bairro).

QUANDO USAR:
- Medico pergunta endereco de um hospital
- Medico quer saber onde fica um hospital
- Medico pergunta: "Qual endereco?", "Onde fica?", "Como chego la?"
- Medico menciona nome de hospital e quer mais info

IMPORTANTE: Use esta tool para buscar informacoes do banco. NAO invente enderecos!

PARAMETROS:
- nome_hospital: Nome (ou parte do nome) do hospital a buscar""",
    "input_schema": {
        "type": "object",
        "properties": {
            "nome_hospital": {
                "type": "string",
                "description": "Nome do hospital (ou parte dele) para buscar. Ex: 'Salvalus', 'Santa Casa'",
            }
        },
        "required": ["nome_hospital"],
    },
}


async def handle_buscar_info_hospital(tool_input: dict, medico: dict, conversa: dict) -> dict:
    """
    Busca informacoes de um hospital pelo nome.

    Args:
        tool_input: Input da tool (nome_hospital)
        medico: Dados do medico (nao usado aqui)
        conversa: Dados da conversa (nao usado aqui)

    Returns:
        Dict com informacoes do hospital ou erro
    """
    nome_hospital = tool_input.get("nome_hospital", "").strip()

    if not nome_hospital:
        return {
            "success": False,
            "error": "Nome do hospital nao informado",
            "mensagem_sugerida": "Qual hospital voce quer saber o endereco?",
        }

    logger.info(f"Buscando info do hospital: {nome_hospital}")

    try:
        response = (
            supabase.table("hospitais")
            .select("*")
            .ilike("nome", f"%{nome_hospital}%")
            .limit(1)
            .execute()
        )

        if not response.data:
            logger.warning(f"Hospital '{nome_hospital}' nao encontrado")
            return {
                "success": False,
                "error": f"Hospital '{nome_hospital}' nao encontrado",
                "mensagem_sugerida": f"Nao encontrei o hospital '{nome_hospital}' no nosso sistema. Pode me dar o nome completo?",
            }

        hospital = response.data[0]
        logger.info(f"Hospital encontrado: {hospital.get('nome')}")

        return {
            "success": True,
            "hospital": {
                "nome": hospital.get("nome"),
                "endereco": hospital.get("endereco_formatado"),
                "logradouro": hospital.get("logradouro"),
                "numero": hospital.get("numero"),
                "bairro": hospital.get("bairro"),
                "cidade": hospital.get("cidade"),
                "estado": hospital.get("estado"),
                "cep": hospital.get("cep"),
            },
            "instrucao": f"Informe o endereco ao medico: {hospital.get('endereco_formatado') or 'endereco nao disponivel'}",
        }

    except Exception as e:
        logger.error(f"Erro ao buscar hospital: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "mensagem_sugerida": "Tive um probleminha pra buscar o endereco. Deixa eu verificar aqui e ja te mando",
        }


# Lista de todas as tools de vagas
TOOLS_VAGAS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
]
