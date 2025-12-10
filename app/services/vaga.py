"""
Servico de gestao de vagas.
"""
from datetime import date, datetime, timezone
from typing import Optional
import logging

from app.services.supabase import supabase
from app.config.especialidades import obter_config_especialidade
from app.config.regioes import detectar_regiao_por_telefone
from app.services.redis import cache_get_json, cache_set_json, cache_delete

logger = logging.getLogger(__name__)

# TTL do cache em segundos
CACHE_TTL_VAGAS = 60  # 1 minuto (vagas mudam frequentemente)


async def buscar_vagas_compativeis(
    especialidade_id: str = None,
    cliente_id: str = None,
    medico: dict = None,
    limite: int = 5
) -> list[dict]:
    """
    Busca vagas compativeis com o medico.

    Filtros:
    - Especialidade do medico
    - Status = aberta
    - Data >= hoje
    - Nao oferece vaga ja reservada pelo mesmo medico
    - Preferencias do medico (se houver)

    Ordenacao:
    - Data mais proxima primeiro

    Args:
        especialidade_id: ID da especialidade do medico (opcional se medico fornecido)
        cliente_id: ID do medico (para excluir vagas dele)
        medico: Dados completos do medico (opcional, para aplicar preferencias)
        limite: Maximo de vagas a retornar

    Returns:
        Lista de vagas com dados de hospital, periodo e setor
    """
    # Se medico fornecido, usar especialidade_id dele
    if medico and not especialidade_id:
        especialidade_id = medico.get("especialidade_id")
    
    if not especialidade_id:
        logger.warning("Nenhuma especialidade fornecida para buscar vagas")
        return []
    
    # Tentar cache primeiro
    cache_key = f"vagas:especialidade:{especialidade_id}:limite:{limite}"
    cached = await cache_get_json(cache_key)
    if cached:
        logger.debug(f"Cache hit para vagas: especialidade {especialidade_id}")
        # Aplicar filtros de preferências mesmo no cache
        if medico:
            preferencias = medico.get("preferencias_detectadas") or {}
            cached = filtrar_por_preferencias(cached, preferencias)
        return cached[:limite]
    
    hoje = date.today().isoformat()

    query = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
        .eq("especialidade_id", especialidade_id)
        .eq("status", "aberta")
        .gte("data", hoje)
        .order("data")
        .limit(limite * 2)  # Buscar mais para filtrar
    )

    response = query.execute()
    vagas = response.data or []

    logger.info(f"Encontradas {len(vagas)} vagas para especialidade {especialidade_id}")

    # Aplicar filtros de preferências se médico fornecido
    if medico:
        preferencias = medico.get("preferencias_detectadas") or {}
        vagas = filtrar_por_preferencias(vagas, preferencias)

    vagas_finais = vagas[:limite]
    
    # Salvar no cache
    await cache_set_json(cache_key, vagas_finais, CACHE_TTL_VAGAS)
    
    return vagas_finais


def filtrar_por_preferencias(vagas: list[dict], preferencias: dict) -> list[dict]:
    """
    Remove vagas incompativeis com preferencias do medico.

    Args:
        vagas: Lista de vagas do banco
        preferencias: Dict com preferencias (hospitais_bloqueados, setores_bloqueados, valor_minimo)

    Returns:
        Lista filtrada de vagas
    """
    if not preferencias:
        return vagas

    resultado = []

    hospitais_bloqueados = preferencias.get("hospitais_bloqueados", [])
    setores_bloqueados = preferencias.get("setores_bloqueados", [])
    valor_minimo = preferencias.get("valor_minimo", 0)

    for v in vagas:
        # Pular hospital bloqueado
        if v.get("hospital_id") in hospitais_bloqueados:
            logger.debug(f"Vaga {v['id']} ignorada: hospital bloqueado")
            continue

        # Pular setor bloqueado
        if v.get("setor_id") in setores_bloqueados:
            logger.debug(f"Vaga {v['id']} ignorada: setor bloqueado")
            continue

        # Pular se valor abaixo do minimo
        valor = v.get("valor") or 0
        if valor < valor_minimo:
            logger.debug(f"Vaga {v['id']} ignorada: valor {valor} < {valor_minimo}")
            continue

        resultado.append(v)

    logger.info(f"Filtro de preferencias: {len(vagas)} -> {len(resultado)} vagas")

    return resultado


async def buscar_vaga_por_id(vaga_id: str) -> dict | None:
    """
    Busca vaga pelo ID com dados relacionados.

    Args:
        vaga_id: ID da vaga

    Returns:
        Dados da vaga ou None
    """
    response = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
        .eq("id", vaga_id)
        .execute()
    )
    return response.data[0] if response.data else None


async def verificar_conflito(
    cliente_id: str,
    data: str,
    periodo_id: str
) -> bool:
    """
    Verifica se medico ja tem plantao no mesmo dia/periodo.

    Args:
        cliente_id: ID do medico
        data: Data do plantao (YYYY-MM-DD)
        periodo_id: ID do periodo

    Returns:
        True se ha conflito, False se pode agendar
    """
    resultado = await verificar_conflito_vaga(cliente_id, data, periodo_id)
    return resultado["conflito"]


async def verificar_conflito_vaga(
    cliente_id: str,
    data: str,
    periodo_id: str
) -> dict:
    """
    Verifica se medico ja tem vaga reservada/confirmada no mesmo dia e periodo.

    Args:
        cliente_id: ID do medico
        data: Data do plantao (YYYY-MM-DD)
        periodo_id: ID do periodo

    Returns:
        dict com:
        - conflito: bool
        - vaga_conflitante: dict ou None (se houver conflito)
        - mensagem: str explicativa
    """
    response = (
        supabase.table("vagas")
        .select("id, hospital_id, data, periodo_id, status, hospitais(nome)")
        .eq("cliente_id", cliente_id)
        .eq("data", data)
        .eq("periodo_id", periodo_id)
        .in_("status", ["reservada", "confirmada"])
        .limit(1)
        .execute()
    )

    if response.data:
        vaga_conflitante = response.data[0]
        hospital_nome = vaga_conflitante.get("hospitais", {}).get("nome", "Hospital")
        logger.info(
            f"Conflito encontrado: medico {cliente_id} ja tem plantao em {data} "
            f"no {hospital_nome}"
        )
        return {
            "conflito": True,
            "vaga_conflitante": {
                "id": vaga_conflitante["id"],
                "hospital": hospital_nome,
                "data": vaga_conflitante["data"],
                "status": vaga_conflitante["status"]
            },
            "mensagem": f"Voce ja tem plantao em {data} no {hospital_nome}"
        }

    return {
        "conflito": False,
        "vaga_conflitante": None,
        "mensagem": None
    }


async def reservar_vaga(
    vaga_id: str,
    cliente_id: str,
    medico: dict = None,
    notificar_gestor: bool = True
) -> dict:
    """
    Reserva vaga para o medico.

    1. Verificar se vaga ainda esta aberta
    2. Verificar conflito de horario
    3. Atualizar status para 'reservada'
    4. Associar cliente_id
    5. Notificar gestor via Slack
    6. Retornar vaga atualizada

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do medico
        medico: Dados do medico (para notificacao)
        notificar_gestor: Se deve notificar gestor via Slack

    Returns:
        Dados da vaga atualizada

    Raises:
        ValueError: Se vaga nao disponivel ou ha conflito
    """
    # Buscar vaga
    vaga = await buscar_vaga_por_id(vaga_id)
    if not vaga:
        raise ValueError("Vaga nao encontrada")

    # Verificar disponibilidade
    if vaga["status"] != "aberta":
        raise ValueError(f"Vaga nao esta mais disponivel (status: {vaga['status']})")

    # Verificar conflito
    if vaga.get("periodo_id"):
        conflito = await verificar_conflito(
            cliente_id=cliente_id,
            data=vaga["data"],
            periodo_id=vaga["periodo_id"]
        )
        if conflito:
            raise ValueError("Voce ja tem um plantao neste dia e periodo")

    # Reservar
    response = (
        supabase.table("vagas")
        .update({
            "status": "reservada",
            "cliente_id": cliente_id,
            "fechada_em": datetime.now(timezone.utc).isoformat(),
            "fechada_por": "julia",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", vaga_id)
        .eq("status", "aberta")  # Optimistic locking
        .execute()
    )

    if not response.data:
        raise ValueError("Vaga foi reservada por outro medico")

    vaga_atualizada = response.data[0]
    logger.info(f"Vaga {vaga_id} reservada para medico {cliente_id}")

    # Invalidar cache de vagas
    if vaga.get("especialidade_id"):
        # Invalidar cache para esta especialidade
        await invalidar_cache_vagas(vaga["especialidade_id"])

    # Notificar gestor via Slack
    if notificar_gestor and medico:
        try:
            from app.services.slack import notificar_plantao_reservado
            await notificar_plantao_reservado(medico, vaga)
        except Exception as e:
            logger.error(f"Erro ao notificar Slack: {e}")

    return vaga_atualizada


async def cancelar_reserva(vaga_id: str, cliente_id: str) -> dict:
    """
    Cancela reserva de uma vaga.

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do medico (para verificar propriedade)

    Returns:
        Vaga atualizada

    Raises:
        ValueError: Se vaga nao pertence ao medico
    """
    vaga = await buscar_vaga_por_id(vaga_id)
    if not vaga:
        raise ValueError("Vaga nao encontrada")

    if vaga.get("cliente_id") != cliente_id:
        raise ValueError("Vaga nao pertence a este medico")

    if vaga["status"] not in ["reservada"]:
        raise ValueError(f"Vaga nao pode ser cancelada (status: {vaga['status']})")

    response = (
        supabase.table("vagas")
        .update({
            "status": "aberta",
            "cliente_id": None,
            "fechada_em": None,
            "fechada_por": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", vaga_id)
        .execute()
    )

    logger.info(f"Reserva da vaga {vaga_id} cancelada pelo medico {cliente_id}")

    return response.data[0] if response.data else None


def formatar_vaga_para_mensagem(vaga: dict) -> str:
    """
    Formata vaga para mensagem natural da Julia.

    Args:
        vaga: Dados da vaga com relacionamentos

    Returns:
        String formatada para mensagem
    """
    hospital = vaga.get("hospitais", {}).get("nome", "Hospital")
    data = vaga.get("data", "")
    periodo = vaga.get("periodos", {}).get("nome", "")
    valor = vaga.get("valor") or 0
    setor = vaga.get("setores", {}).get("nome", "")

    # Formatar data para PT-BR
    if data:
        try:
            data_obj = datetime.strptime(data, "%Y-%m-%d")
            dias_semana = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
            dia_semana = dias_semana[data_obj.weekday()]
            data = f"{dia_semana}, {data_obj.strftime('%d/%m')}"
        except ValueError:
            pass

    partes = [hospital]
    if data:
        partes.append(data)
    if periodo:
        partes.append(periodo.lower())
    if setor:
        partes.append(setor)
    if valor:
        partes.append(f"R$ {valor:,.0f}".replace(",", "."))

    return ", ".join(partes)


async def invalidar_cache_vagas(especialidade_id: Optional[str] = None):
    """
    Invalida cache de vagas após alteração.
    
    Args:
        especialidade_id: ID da especialidade (opcional, invalida todas se None)
    """
    try:
        from app.services.redis import redis_client
        
        if especialidade_id:
            # Invalidar padrão específico
            pattern = f"vagas:especialidade:{especialidade_id}:*"
        else:
            pattern = "vagas:*"
        
        # Buscar todas as chaves que correspondem ao padrão
        keys = await redis_client.keys(pattern)
        
        if keys:
            await redis_client.delete(*keys)
            logger.debug(f"Cache invalidado: {len(keys)} chave(s) removida(s)")
    except Exception as e:
        logger.warning(f"Erro ao invalidar cache de vagas: {e}")


def formatar_vagas_contexto(vagas: list[dict], especialidade: str = None) -> str:
    """
    Formata vagas para incluir no contexto do LLM.
    
    Args:
        vagas: Lista de vagas
        especialidade: Nome da especialidade (opcional)
    
    Returns:
        String formatada com vagas
    """
    if not vagas:
        return "Não há vagas disponíveis no momento para esta especialidade."
    
    config = obter_config_especialidade(especialidade) if especialidade else {}
    nome_display = config.get("nome_display", "médico") if config else "médico"
    
    texto = f"## Vagas Disponíveis para {nome_display}:\n\n"
    
    for i, v in enumerate(vagas[:5], 1):
        hospital = v.get("hospitais", {})
        periodo = v.get("periodos", {})
        setor = v.get("setores", {})
        
        texto += f"""**Vaga {i}:**
- Hospital: {hospital.get('nome', 'N/A')} ({hospital.get('cidade', 'N/A')})
- Data: {v.get('data', 'N/A')}
- Período: {periodo.get('nome', 'N/A')} ({periodo.get('hora_inicio', '')}-{periodo.get('hora_fim', '')})
- Setor: {setor.get('nome', 'N/A')}
- Valor: R$ {v.get('valor', 'N/A')}
- ID: {v.get('id', 'N/A')}
"""
    
    return texto


async def buscar_vagas_por_regiao(
    medico: dict,
    limite: int = 5
) -> list[dict]:
    """
    Busca vagas priorizando região do médico.
    
    Args:
        medico: Dados do médico
        limite: Máximo de vagas a retornar
    
    Returns:
        Lista de vagas ordenadas por prioridade de região
    """
    # Buscar vagas compatíveis
    vagas = await buscar_vagas_compativeis(
        medico=medico,
        limite=limite * 2
    )
    
    # Detectar região do médico
    telefone = medico.get("telefone", "")
    regiao_medico = detectar_regiao_por_telefone(telefone)
    
    if not regiao_medico:
        # Se não detectar região, retornar como está
        return vagas[:limite]
    
    # Ordenar: vagas da região primeiro
    def prioridade_regiao(vaga):
        hospital = vaga.get("hospitais", {})
        hospital_regiao = hospital.get("regiao")
        if hospital_regiao == regiao_medico:
            return 0  # Alta prioridade
        return 1
    
    vagas_ordenadas = sorted(vagas, key=prioridade_regiao)
    return vagas_ordenadas[:limite]
