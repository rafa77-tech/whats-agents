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
                "description": "Especialidade solicitada pelo medico (ex: 'cardiologia', 'anestesiologia'). Se nao especificada, usa a especialidade cadastrada do medico."
            },
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
    2. Determina especialidade (solicitada vs cadastrada)
    3. Busca vagas compativeis com especialidade
    4. Filtra por conflitos existentes
    5. Formata resultado para LLM (com alerta se especialidade diferente)

    Args:
        tool_input: Input da tool (especialidade, regiao, periodo, valor_minimo, etc)
        medico: Dados do medico (incluindo especialidade_id, preferencias)
        conversa: Dados da conversa atual

    Returns:
        Dict com vagas encontradas e contexto formatado
    """
    especialidade_solicitada = tool_input.get("especialidade")
    regiao = tool_input.get("regiao")
    periodo = tool_input.get("periodo", "qualquer")
    valor_minimo = tool_input.get("valor_minimo", 0)
    dias_semana = tool_input.get("dias_semana", [])
    limite = min(tool_input.get("limite", 5), 10)  # Max 10

    # Especialidade cadastrada do médico
    especialidade_medico = medico.get("especialidade")
    especialidade_id = None
    especialidade_nome = None
    especialidade_diferente = False

    # Se médico solicitou especialidade específica, usar ela
    if especialidade_solicitada:
        especialidade_id = await _buscar_especialidade_id_por_nome(especialidade_solicitada)
        if especialidade_id:
            especialidade_nome = especialidade_solicitada.title()
            # Verificar se é diferente da cadastrada
            if especialidade_medico and especialidade_medico.lower() != especialidade_solicitada.lower():
                especialidade_diferente = True
                logger.info(
                    f"Medico pediu {especialidade_solicitada} mas cadastro e {especialidade_medico}"
                )
        else:
            logger.warning(f"Especialidade '{especialidade_solicitada}' nao encontrada no banco")
            return {
                "success": False,
                "error": f"Especialidade '{especialidade_solicitada}' nao encontrada",
                "vagas": [],
                "mensagem_sugerida": f"Nao conheco a especialidade '{especialidade_solicitada}'. Pode confirmar o nome?"
            }
    else:
        # Usar especialidade cadastrada do médico
        especialidade_id = medico.get("especialidade_id")
        if not especialidade_id and especialidade_medico:
            especialidade_id = await _buscar_especialidade_id_por_nome(especialidade_medico)
        especialidade_nome = especialidade_medico

    logger.info(
        f"Buscando vagas para medico {medico.get('id')}: "
        f"especialidade={especialidade_nome}, regiao={regiao}, periodo={periodo}"
    )

    if not especialidade_id:
        logger.warning(f"Medico {medico.get('id')} sem especialidade definida")
        return {
            "success": False,
            "error": "Especialidade nao identificada",
            "vagas": [],
            "mensagem_sugerida": "Qual especialidade voce quer buscar? Me fala que eu procuro pra voce"
        }

    # Atualizar medico dict para usar nas próximas funções
    medico["especialidade_id"] = especialidade_id

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
            logger.info(f"Nenhuma vaga encontrada para especialidade {especialidade_nome}")

            # Se buscou especialidade diferente da cadastrada e não encontrou, sugerir a cadastrada
            if especialidade_diferente and especialidade_medico:
                return {
                    "success": True,
                    "vagas": [],
                    "total_encontradas": 0,
                    "especialidade_buscada": especialidade_nome,
                    "especialidade_cadastrada": especialidade_medico,
                    "mensagem_sugerida": (
                        f"Nao tenho vaga de {especialidade_nome} no momento. "
                        f"Mas vi que voce e de {especialidade_medico} - quer que eu veja as vagas dessa especialidade?"
                    )
                }

            return {
                "success": True,
                "vagas": [],
                "total_encontradas": 0,
                "especialidade_buscada": especialidade_nome,
                "mensagem_sugerida": f"Nao tem vaga de {especialidade_nome} no momento. Mas assim que surgir algo, te aviso!"
            }

        # Formatar para contexto do LLM
        # Prioridade: objeto relacionado > campo texto
        especialidade_nome = (
            medico.get("especialidades", {}).get("nome")
            or medico.get("especialidade")
        )
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
                # Campos de valor expandidos (Sprint 19)
                "valor": v.get("valor"),
                "valor_minimo": v.get("valor_minimo"),
                "valor_maximo": v.get("valor_maximo"),
                "valor_tipo": v.get("valor_tipo", "fixo"),
                "valor_display": _formatar_valor_display(v),
                "setor": v.get("setores", {}).get("nome"),
                "especialidade": v.get("especialidades", {}).get("nome") or especialidade_nome,
            })

        logger.info(f"Encontradas {len(vagas_final)} vagas para medico {medico.get('id')}")

        # Construir instrução baseada no contexto
        instrucao_base = (
            f"Estas vagas sao de {especialidade_nome}. "
            "Apresente as vagas de forma natural, uma por vez. "
            "SEMPRE mencione a DATA do plantao (dia/mes) pois sera usada para reservar. "
            "Quando o medico aceitar, use a tool reservar_plantao com a DATA no formato YYYY-MM-DD. "
            "IMPORTANTE: Para vagas 'a combinar', informe naturalmente que o valor sera negociado. "
            "Nao invente valores - use apenas o que esta nos dados da vaga."
        )

        # Alerta se especialidade diferente da cadastrada
        alerta_especialidade = None
        if especialidade_diferente:
            alerta_especialidade = (
                f"ALERTA: O medico pediu vagas de {especialidade_nome}, mas o cadastro dele e {especialidade_medico}. "
                f"Mencione naturalmente que encontrou vagas de {especialidade_nome} como ele pediu, "
                f"mas confirme se ele tambem atua nessa area ou se quer ver vagas de {especialidade_medico}."
            )
            instrucao_base = alerta_especialidade + " " + instrucao_base

        return {
            "success": True,
            "vagas": vagas_resumo,
            "total_encontradas": len(vagas_final),
            "especialidade_buscada": especialidade_nome,
            "especialidade_cadastrada": especialidade_medico,
            "especialidade_diferente": especialidade_diferente,
            "contexto": contexto_formatado,
            "instrucao": instrucao_base
        }

    except Exception as e:
        logger.error(f"Erro ao buscar vagas: {e}")
        return {
            "success": False,
            "error": str(e),
            "vagas": [],
            "mensagem_sugerida": "Tive um probleminha aqui, me da um minuto que ja te mostro as vagas"
        }


def _formatar_valor_display(vaga: dict) -> str:
    """
    Formata valor para exibicao na resposta da tool.

    Args:
        vaga: Dados da vaga

    Returns:
        String formatada para exibicao
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    elif valor_tipo == "faixa":
        if valor_minimo and valor_maximo:
            return f"R$ {valor_minimo:,.0f} a R$ {valor_maximo:,.0f}".replace(",", ".")
        elif valor_minimo:
            return f"a partir de R$ {valor_minimo:,.0f}".replace(",", ".")
        elif valor_maximo:
            return f"ate R$ {valor_maximo:,.0f}".replace(",", ".")

    elif valor_tipo == "a_combinar":
        return "a combinar"

    if valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    return "nao informado"


def _construir_instrucao_confirmacao(vaga: dict, hospital_data: dict) -> str:
    """
    Constroi instrucao de confirmacao baseada no tipo de valor.

    Args:
        vaga: Dados da vaga
        hospital_data: Dados do hospital

    Returns:
        Instrucao para o LLM
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    endereco = hospital_data.get("endereco_formatado") or "endereco nao disponivel"

    instrucao = "Confirme a reserva mencionando o hospital, data e periodo. "

    if valor_tipo == "fixo":
        valor = vaga.get("valor")
        if valor:
            instrucao += f"Mencione o valor de R$ {valor}. "
    elif valor_tipo == "faixa":
        instrucao += "Mencione que o valor sera dentro da faixa acordada. "
    elif valor_tipo == "a_combinar":
        instrucao += (
            "Informe que o valor sera combinado diretamente com o hospital/gestor. "
            "Pergunte se o medico tem alguma expectativa de valor para repassar. "
        )

    instrucao += f"Se o medico perguntar o endereco, use: {endereco}"

    return instrucao


def _construir_instrucao_ponte_externa(
    vaga: dict,
    hospital_data: dict,
    ponte_externa: dict,
    medico: dict,
) -> str:
    """
    Constroi instrucao de confirmacao para vaga com ponte externa.

    Sprint 20 - Marketplace assistido.

    Args:
        vaga: Dados da vaga
        hospital_data: Dados do hospital
        ponte_externa: Resultado da criacao da ponte
        medico: Dados do medico

    Returns:
        Instrucao para o LLM
    """
    divulgador = ponte_externa.get("divulgador", {})
    divulgador_nome = divulgador.get("nome", "o responsavel")
    divulgador_tel = divulgador.get("telefone", "")
    divulgador_empresa = divulgador.get("empresa", "")

    # Montar info do divulgador
    info_divulgador = divulgador_nome
    if divulgador_empresa:
        info_divulgador += f" ({divulgador_empresa})"

    instrucao = (
        f"IMPORTANTE: Esta vaga e de um divulgador externo ({info_divulgador}). "
        f"Voce JA ENTROU EM CONTATO com ele e passou os dados do medico.\n\n"
        f"Informe ao medico que:\n"
        f"1. Voce reservou a vaga\n"
        f"2. Ja contatou o responsavel ({divulgador_nome})"
    )

    if divulgador_tel:
        instrucao += f"\n3. Passe o contato: {divulgador_tel}"

    instrucao += (
        "\n\nPeca para o medico confirmar aqui quando fechar o plantao. "
        "Fale de forma natural, como se voce tivesse acabado de fazer a ponte entre eles."
    )

    # Adicionar info de valor se aplicavel
    valor_tipo = vaga.get("valor_tipo", "fixo")
    if valor_tipo == "a_combinar":
        instrucao += (
            "\n\nComo o valor e 'a combinar', mencione que o medico deve "
            "negociar diretamente com o divulgador."
        )

    return instrucao


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

        logger.info(f"_buscar_vaga_por_data: encontradas {len(response.data) if response.data else 0} vagas")

        if response.data:
            vaga = response.data[0]
            logger.info(
                f"_buscar_vaga_por_data: vaga encontrada id={vaga.get('id')}, "
                f"valor_tipo={vaga.get('valor_tipo')}"
            )
            return vaga

        logger.warning(f"_buscar_vaga_por_data: nenhuma vaga encontrada para data={data}, especialidade_id={especialidade_id}")
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar vaga por data: {e}", exc_info=True)
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

    logger.info(f"handle_reservar_plantao: tool_input={tool_input}, medico_id={medico.get('id')}")

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

    logger.info(f"handle_reservar_plantao: data_normalizada={data_normalizada}")

    # Verificar especialidade do médico
    especialidade_id = medico.get("especialidade_id")
    logger.info(f"handle_reservar_plantao: especialidade_id do medico={especialidade_id}")

    if not especialidade_id:
        especialidade_nome = medico.get("especialidade")
        logger.info(f"handle_reservar_plantao: especialidade_nome={especialidade_nome}, buscando ID...")
        if especialidade_nome:
            especialidade_id = await _buscar_especialidade_id_por_nome(especialidade_nome)
            logger.info(f"handle_reservar_plantao: especialidade_id resolvido={especialidade_id}")

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
                "periodo": vaga.get("periodos", {}).get("nome"),
                # Campos de valor expandidos (Sprint 19)
                "valor": vaga.get("valor"),
                "valor_minimo": vaga.get("valor_minimo"),
                "valor_maximo": vaga.get("valor_maximo"),
                "valor_tipo": vaga.get("valor_tipo", "fixo"),
                "valor_display": _formatar_valor_display(vaga),
                "status": vaga_atualizada.get("status")
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
                "description": "Nome do hospital (ou parte dele) para buscar. Ex: 'Salvalus', 'Santa Casa'"
            }
        },
        "required": ["nome_hospital"]
    }
}


async def handle_buscar_info_hospital(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict:
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
            "mensagem_sugerida": "Qual hospital voce quer saber o endereco?"
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
                "mensagem_sugerida": f"Nao encontrei o hospital '{nome_hospital}' no nosso sistema. Pode me dar o nome completo?"
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
            "instrucao": f"Informe o endereco ao medico: {hospital.get('endereco_formatado') or 'endereco nao disponivel'}"
        }

    except Exception as e:
        logger.error(f"Erro ao buscar hospital: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "mensagem_sugerida": "Tive um probleminha pra buscar o endereco. Deixa eu verificar aqui e ja te mando"
        }


# Lista de todas as tools de vagas
TOOLS_VAGAS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
]
