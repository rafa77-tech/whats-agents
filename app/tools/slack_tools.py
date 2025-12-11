"""
Tools para o agente Julia no Slack.

Estas tools permitem que a Julia execute acoes e busque informacoes
quando o gestor conversa com ela pelo Slack.
"""
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.services.supabase import supabase
from app.services.tipos_abordagem import (
    TipoAbordagem,
    inferir_tipo,
    descrever_tipo,
    extrair_hospital,
    extrair_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DEFINICAO DAS TOOLS (formato Claude)
# =============================================================================

TOOL_ENVIAR_MENSAGEM = {
    "name": "enviar_mensagem",
    "description": """Envia mensagem WhatsApp para um medico.

QUANDO USAR:
- Gestor pede para contatar/mandar msg/falar com um medico
- Gestor quer enviar uma mensagem especifica
- Gestor menciona telefone e quer enviar algo

EXEMPLOS:
- "manda msg pro 11999..."
- "contata o Dr Carlos"
- "fala com o 11988..."
- "envia uma mensagem oferecendo a vaga..."

ACAO CRITICA: Sempre mostre preview da mensagem e peca confirmacao antes de enviar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone": {
                "type": "string",
                "description": "Numero de telefone do medico com DDD (ex: 11999887766)"
            },
            "instrucao": {
                "type": "string",
                "description": "Instrucao sobre o que dizer na mensagem (ex: 'oferecer vaga do Sao Luiz')"
            },
            "tipo": {
                "type": "string",
                "enum": ["discovery", "oferta", "reativacao", "followup", "custom"],
                "description": "Tipo de abordagem. Use 'discovery' para primeiro contato, 'oferta' para vaga especifica."
            }
        },
        "required": ["telefone"]
    }
}

TOOL_BUSCAR_METRICAS = {
    "name": "buscar_metricas",
    "description": """Busca metricas de performance da Julia.

QUANDO USAR:
- Gestor pergunta como foi o dia/semana
- Gestor quer saber quantos responderam
- Gestor pergunta sobre taxa de resposta
- Gestor quer ver numeros/resultados

EXEMPLOS:
- "como foi hoje?"
- "quantos responderam?"
- "qual a taxa de resposta?"
- "como ta essa semana?"
- "me mostra os numeros"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "periodo": {
                "type": "string",
                "enum": ["hoje", "ontem", "semana", "mes"],
                "description": "Periodo para buscar metricas"
            },
            "tipo": {
                "type": "string",
                "enum": ["geral", "respostas", "envios", "conversoes"],
                "description": "Tipo de metrica. Use 'geral' para visao completa."
            }
        },
        "required": ["periodo"]
    }
}

TOOL_COMPARAR_PERIODOS = {
    "name": "comparar_periodos",
    "description": """Compara metricas entre dois periodos.

QUANDO USAR:
- Gestor pergunta comparacao entre periodos
- Gestor quer ver evolucao/tendencia
- Gestor menciona "vs", "comparado com", "em relacao a"

EXEMPLOS:
- "como ta essa semana comparado com a anterior?"
- "hoje foi melhor que ontem?"
- "evoluiu do mes passado pra ca?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "periodo1": {
                "type": "string",
                "enum": ["hoje", "ontem", "semana", "semana_passada", "mes", "mes_passado"],
                "description": "Primeiro periodo (mais recente)"
            },
            "periodo2": {
                "type": "string",
                "enum": ["hoje", "ontem", "semana", "semana_passada", "mes", "mes_passado"],
                "description": "Segundo periodo (para comparacao)"
            }
        },
        "required": ["periodo1", "periodo2"]
    }
}

TOOL_BUSCAR_MEDICO = {
    "name": "buscar_medico",
    "description": """Busca informacoes de um medico especifico.

QUANDO USAR:
- Gestor pergunta sobre um medico
- Gestor quer ver dados de alguem
- Gestor menciona nome/telefone e quer info

EXEMPLOS:
- "quem eh o Dr Carlos?"
- "me fala do 11999..."
- "busca o CRM 123456"
- "tem algum Carlos aqui?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "identificador": {
                "type": "string",
                "description": "Telefone, nome ou CRM do medico"
            }
        },
        "required": ["identificador"]
    }
}

TOOL_LISTAR_MEDICOS = {
    "name": "listar_medicos",
    "description": """Lista medicos com filtros.

QUANDO USAR:
- Gestor quer ver lista de medicos
- Gestor pergunta quem respondeu/nao respondeu
- Gestor quer ver interessados/positivos

EXEMPLOS:
- "quem respondeu hoje?"
- "lista os interessados"
- "quem ta sem resposta?"
- "mostra os medicos novos"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "filtro": {
                "type": "string",
                "enum": ["responderam_hoje", "positivos", "sem_resposta", "novos", "todos"],
                "description": "Tipo de filtro a aplicar"
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade maxima de medicos a retornar (padrao: 10)"
            }
        },
        "required": ["filtro"]
    }
}

TOOL_BLOQUEAR_MEDICO = {
    "name": "bloquear_medico",
    "description": """Bloqueia um medico (opt-out).

QUANDO USAR:
- Gestor pede para bloquear alguem
- Gestor diz que medico pediu para parar
- Gestor quer remover medico da lista

EXEMPLOS:
- "bloqueia o 11999..."
- "tira ele da lista"
- "nao manda mais pro Dr Carlos"

ACAO CRITICA: Peca confirmacao antes de bloquear.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone": {
                "type": "string",
                "description": "Telefone do medico"
            },
            "motivo": {
                "type": "string",
                "description": "Motivo do bloqueio (opcional)"
            }
        },
        "required": ["telefone"]
    }
}

TOOL_DESBLOQUEAR_MEDICO = {
    "name": "desbloquear_medico",
    "description": """Remove bloqueio de um medico.

QUANDO USAR:
- Gestor pede para desbloquear alguem
- Gestor quer reativar contato

EXEMPLOS:
- "desbloqueia o 11999..."
- "pode voltar a contatar o Dr Carlos"

ACAO CRITICA: Peca confirmacao antes de desbloquear.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone": {
                "type": "string",
                "description": "Telefone do medico"
            }
        },
        "required": ["telefone"]
    }
}

TOOL_BUSCAR_VAGAS = {
    "name": "buscar_vagas",
    "description": """Busca vagas disponiveis.

QUANDO USAR:
- Gestor pergunta sobre vagas abertas
- Gestor quer ver oportunidades disponiveis
- Gestor menciona hospital e quer ver vagas

EXEMPLOS:
- "quais vagas tem abertas?"
- "tem vaga no Sao Luiz?"
- "o que tem pra essa semana?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "hospital": {
                "type": "string",
                "description": "Nome do hospital (opcional)"
            },
            "especialidade": {
                "type": "string",
                "description": "Especialidade (opcional)"
            },
            "status": {
                "type": "string",
                "enum": ["aberta", "reservada", "fechada", "todas"],
                "description": "Status das vagas"
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade maxima de vagas"
            }
        },
        "required": []
    }
}

TOOL_RESERVAR_VAGA = {
    "name": "reservar_vaga",
    "description": """Reserva uma vaga para um medico.

QUANDO USAR:
- Gestor pede para fechar/reservar vaga para alguem
- Gestor confirma reserva

EXEMPLOS:
- "reserva a vaga do dia 15 pro Dr Carlos"
- "fecha essa vaga pro 11999..."

ACAO CRITICA: Peca confirmacao antes de reservar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone_medico": {
                "type": "string",
                "description": "Telefone do medico"
            },
            "data_vaga": {
                "type": "string",
                "description": "Data da vaga (YYYY-MM-DD)"
            },
            "hospital": {
                "type": "string",
                "description": "Nome do hospital (opcional, para confirmar)"
            }
        },
        "required": ["telefone_medico", "data_vaga"]
    }
}

TOOL_STATUS_SISTEMA = {
    "name": "status_sistema",
    "description": """Retorna status geral do sistema.

QUANDO USAR:
- Gestor pergunta como ta a Julia
- Gestor quer ver status geral
- Gestor pergunta se ta tudo funcionando

EXEMPLOS:
- "como ta a Julia?"
- "status"
- "ta tudo ok?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

TOOL_BUSCAR_HANDOFFS = {
    "name": "buscar_handoffs",
    "description": """Lista handoffs pendentes ou recentes.

QUANDO USAR:
- Gestor pergunta sobre handoffs
- Gestor quer ver conversas que precisam de atencao

EXEMPLOS:
- "tem handoff pendente?"
- "quem precisa de atencao?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["pendente", "resolvido", "todos"],
                "description": "Status do handoff"
            }
        },
        "required": []
    }
}

TOOL_BUSCAR_HISTORICO = {
    "name": "buscar_historico",
    "description": """Busca historico de conversa com um medico.

QUANDO USAR:
- Gestor quer ver conversa anterior
- Gestor pergunta o que foi falado com alguem

EXEMPLOS:
- "o que falamos com o Dr Carlos?"
- "mostra o historico do 11999..."

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone": {
                "type": "string",
                "description": "Telefone do medico"
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade de mensagens (padrao: 10)"
            }
        },
        "required": ["telefone"]
    }
}

TOOL_PAUSAR_JULIA = {
    "name": "pausar_julia",
    "description": """Pausa envios automaticos da Julia.

QUANDO USAR:
- Gestor pede para pausar
- Gestor quer parar os envios

EXEMPLOS:
- "pausa a Julia"
- "para de enviar"

ACAO CRITICA: Peca confirmacao antes de pausar.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

TOOL_RETOMAR_JULIA = {
    "name": "retomar_julia",
    "description": """Retoma envios automaticos da Julia.

QUANDO USAR:
- Gestor pede para retomar
- Gestor quer voltar os envios

EXEMPLOS:
- "retoma a Julia"
- "volta a enviar"

ACAO CRITICA: Peca confirmacao antes de retomar.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

# Lista de todas as tools
SLACK_TOOLS = [
    TOOL_ENVIAR_MENSAGEM,
    TOOL_BUSCAR_METRICAS,
    TOOL_COMPARAR_PERIODOS,
    TOOL_BUSCAR_MEDICO,
    TOOL_LISTAR_MEDICOS,
    TOOL_BLOQUEAR_MEDICO,
    TOOL_DESBLOQUEAR_MEDICO,
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_VAGA,
    TOOL_STATUS_SISTEMA,
    TOOL_BUSCAR_HANDOFFS,
    TOOL_BUSCAR_HISTORICO,
    TOOL_PAUSAR_JULIA,
    TOOL_RETOMAR_JULIA,
]

# Tools que requerem confirmacao
TOOLS_CRITICAS = {
    "enviar_mensagem",
    "bloquear_medico",
    "desbloquear_medico",
    "reservar_vaga",
    "pausar_julia",
    "retomar_julia",
}


# =============================================================================
# HANDLERS DAS TOOLS
# =============================================================================

async def executar_tool(nome: str, params: dict, user_id: str) -> dict[str, Any]:
    """
    Executa uma tool pelo nome.

    Args:
        nome: Nome da tool
        params: Parametros da tool
        user_id: ID do usuario Slack

    Returns:
        Resultado da execucao
    """
    handlers = {
        "enviar_mensagem": _handle_enviar_mensagem,
        "buscar_metricas": _handle_buscar_metricas,
        "comparar_periodos": _handle_comparar_periodos,
        "buscar_medico": _handle_buscar_medico,
        "listar_medicos": _handle_listar_medicos,
        "bloquear_medico": _handle_bloquear_medico,
        "desbloquear_medico": _handle_desbloquear_medico,
        "buscar_vagas": _handle_buscar_vagas,
        "reservar_vaga": _handle_reservar_vaga,
        "status_sistema": _handle_status_sistema,
        "buscar_handoffs": _handle_buscar_handoffs,
        "buscar_historico": _handle_buscar_historico,
        "pausar_julia": lambda p: _handle_pausar_julia(p, user_id),
        "retomar_julia": lambda p: _handle_retomar_julia(p, user_id),
    }

    handler = handlers.get(nome)
    if not handler:
        return {"success": False, "error": f"Tool '{nome}' nao encontrada"}

    try:
        return await handler(params)
    except Exception as e:
        logger.error(f"Erro ao executar tool {nome}: {e}")
        return {"success": False, "error": str(e)}


async def _handle_enviar_mensagem(params: dict) -> dict:
    """Envia mensagem WhatsApp para medico."""
    telefone = params.get("telefone", "").strip()
    instrucao = params.get("instrucao", "")
    tipo_param = params.get("tipo", "")

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    # Limpar telefone
    telefone_limpo = re.sub(r'\D', '', telefone)
    if len(telefone_limpo) < 8:
        return {"success": False, "error": "Telefone invalido"}

    # Buscar medico se existir
    medico = await _buscar_medico_por_identificador(telefone_limpo)

    # Verificar opt-out
    if medico and (medico.get("opt_out") or medico.get("opted_out")):
        return {
            "success": False,
            "error": f"Medico {medico.get('primeiro_nome')} esta bloqueado (opt-out)"
        }

    # Verificar se eh medico novo (nunca contatado)
    eh_novo = medico is None

    # Verificar se menciona vaga
    tem_vaga = False
    hospital = None
    data_vaga = None
    if instrucao:
        hospital = extrair_hospital(instrucao)
        data_vaga = extrair_data(instrucao)
        tem_vaga = hospital is not None or data_vaga is not None

    # Inferir tipo de abordagem se nao foi especificado
    if tipo_param and tipo_param in [t.value for t in TipoAbordagem]:
        tipo = tipo_param
    else:
        tipo_inferido = inferir_tipo(instrucao, tem_vaga=tem_vaga, eh_novo=eh_novo)
        tipo = tipo_inferido.value

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "telefone": telefone_limpo,
                "tipo": tipo,
                "instrucao": instrucao
            }

            # Adicionar dados de vaga se detectados
            if hospital:
                payload["hospital"] = hospital
            if data_vaga:
                payload["data_vaga"] = data_vaga

            response = await client.post(
                f"{settings.JULIA_API_URL}/jobs/primeira-mensagem",
                json=payload,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                nome = medico.get("primeiro_nome") if medico else "novo contato"
                return {
                    "success": True,
                    "telefone": telefone_limpo,
                    "nome": nome,
                    "tipo_abordagem": descrever_tipo(TipoAbordagem(tipo)),
                    "mensagem": data.get("mensagem_enviada", "Mensagem enviada")
                }
            else:
                return {"success": False, "error": f"Erro na API: {response.status_code}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _calcular_datas_periodo(periodo: str) -> tuple[datetime, datetime]:
    """Calcula data inicio e fim para um periodo."""
    agora = datetime.now(timezone.utc)

    if periodo == "hoje":
        data_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = agora
    elif periodo == "ontem":
        data_inicio = (agora - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semana":
        data_inicio = agora - timedelta(days=7)
        data_fim = agora
    elif periodo == "semana_passada":
        data_inicio = agora - timedelta(days=14)
        data_fim = agora - timedelta(days=7)
    elif periodo == "mes":
        data_inicio = agora - timedelta(days=30)
        data_fim = agora
    elif periodo == "mes_passado":
        data_inicio = agora - timedelta(days=60)
        data_fim = agora - timedelta(days=30)
    else:
        data_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = agora

    return data_inicio, data_fim


async def _buscar_metricas_periodo(data_inicio: datetime, data_fim: datetime) -> dict:
    """Busca metricas para um periodo especifico."""
    data_inicio_str = data_inicio.isoformat()
    data_fim_str = data_fim.isoformat()

    # Mensagens enviadas
    msgs_enviadas = supabase.table("fila_mensagens").select(
        "id", count="exact"
    ).eq("status", "enviada").gte("enviada_em", data_inicio_str).lte("enviada_em", data_fim_str).execute()

    # Respostas recebidas (interacoes de entrada)
    respostas = supabase.table("interacoes").select(
        "id", count="exact"
    ).eq("tipo", "entrada").gte("created_at", data_inicio_str).lte("created_at", data_fim_str).execute()

    # Conversas com sentimento positivo
    positivas = supabase.table("conversations").select(
        "id", count="exact"
    ).eq("sentimento", "positivo").gte("updated_at", data_inicio_str).lte("updated_at", data_fim_str).execute()

    # Conversas com sentimento negativo
    negativas = supabase.table("conversations").select(
        "id", count="exact"
    ).eq("sentimento", "negativo").gte("updated_at", data_inicio_str).lte("updated_at", data_fim_str).execute()

    # Opt-outs
    optouts = supabase.table("clientes").select(
        "id", count="exact"
    ).eq("opted_out", True).gte("opted_out_at", data_inicio_str).lte("opted_out_at", data_fim_str).execute()

    # Vagas reservadas
    vagas_reservadas = supabase.table("vagas").select(
        "id", count="exact"
    ).eq("status", "reservada").gte("updated_at", data_inicio_str).lte("updated_at", data_fim_str).execute()

    total_enviadas = msgs_enviadas.count or 0
    total_respostas = respostas.count or 0
    total_positivas = positivas.count or 0
    total_negativas = negativas.count or 0
    total_optouts = optouts.count or 0
    total_reservas = vagas_reservadas.count or 0

    taxa_resposta = round((total_respostas / total_enviadas * 100), 1) if total_enviadas > 0 else 0

    return {
        "enviadas": total_enviadas,
        "respostas": total_respostas,
        "taxa_resposta": taxa_resposta,
        "positivas": total_positivas,
        "negativas": total_negativas,
        "optouts": total_optouts,
        "vagas_reservadas": total_reservas
    }


async def _handle_buscar_metricas(params: dict) -> dict:
    """Busca metricas de performance."""
    periodo = params.get("periodo", "hoje")

    try:
        data_inicio, data_fim = _calcular_datas_periodo(periodo)
        metricas = await _buscar_metricas_periodo(data_inicio, data_fim)

        return {
            "success": True,
            "periodo": periodo,
            "metricas": metricas
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_comparar_periodos(params: dict) -> dict:
    """Compara metricas entre dois periodos."""
    periodo1 = params.get("periodo1", "semana")
    periodo2 = params.get("periodo2", "semana_passada")

    try:
        # Buscar metricas dos dois periodos
        data_inicio1, data_fim1 = _calcular_datas_periodo(periodo1)
        data_inicio2, data_fim2 = _calcular_datas_periodo(periodo2)

        metricas1 = await _buscar_metricas_periodo(data_inicio1, data_fim1)
        metricas2 = await _buscar_metricas_periodo(data_inicio2, data_fim2)

        # Calcular variacoes
        def calcular_variacao(v1, v2):
            if v2 == 0:
                return "+100%" if v1 > 0 else "0%"
            diff = ((v1 - v2) / v2) * 100
            sinal = "+" if diff > 0 else ""
            return f"{sinal}{round(diff, 1)}%"

        variacao_taxa = metricas1["taxa_resposta"] - metricas2["taxa_resposta"]
        tendencia = "melhora" if variacao_taxa > 0 else "piora" if variacao_taxa < 0 else "estavel"

        return {
            "success": True,
            "periodo1": {
                "nome": periodo1,
                "metricas": metricas1
            },
            "periodo2": {
                "nome": periodo2,
                "metricas": metricas2
            },
            "variacao": {
                "taxa_resposta": f"{'+' if variacao_taxa > 0 else ''}{round(variacao_taxa, 1)} pontos",
                "enviadas": calcular_variacao(metricas1["enviadas"], metricas2["enviadas"]),
                "respostas": calcular_variacao(metricas1["respostas"], metricas2["respostas"]),
                "tendencia": tendencia
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_buscar_medico(params: dict) -> dict:
    """Busca informacoes de um medico."""
    identificador = params.get("identificador", "").strip()

    if not identificador:
        return {"success": False, "error": "Identificador nao informado"}

    medico = await _buscar_medico_por_identificador(identificador)

    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {identificador}"}

    # Buscar ultima interacao
    ultima = supabase.table("interacoes").select(
        "created_at, conteudo"
    ).eq("cliente_id", medico["id"]).order(
        "created_at", desc=True
    ).limit(1).execute()

    ultima_interacao = None
    if ultima.data:
        ultima_interacao = ultima.data[0].get("created_at")

    return {
        "success": True,
        "medico": {
            "nome": medico.get("primeiro_nome"),
            "telefone": medico.get("telefone"),
            "crm": medico.get("crm"),
            "especialidade": medico.get("especialidade"),
            "cidade": medico.get("cidade"),
            "bloqueado": medico.get("opt_out") or medico.get("opted_out"),
            "ultima_interacao": ultima_interacao
        }
    }


async def _handle_listar_medicos(params: dict) -> dict:
    """Lista medicos com filtros."""
    filtro = params.get("filtro", "todos")
    limite = min(params.get("limite", 10), 20)

    agora = datetime.now(timezone.utc)
    hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    try:
        if filtro == "responderam_hoje":
            # Medicos que tiveram interacao de entrada hoje
            interacoes = supabase.table("interacoes").select(
                "cliente_id"
            ).eq("tipo", "entrada").gte("created_at", hoje).execute()

            cliente_ids = list(set([i["cliente_id"] for i in interacoes.data])) if interacoes.data else []

            if not cliente_ids:
                return {"success": True, "medicos": [], "total": 0}

            medicos = supabase.table("clientes").select(
                "primeiro_nome, telefone, especialidade"
            ).in_("id", cliente_ids[:limite]).execute()

        elif filtro == "positivos":
            # Conversas com sentimento positivo
            conversas = supabase.table("conversations").select(
                "cliente_id"
            ).eq("sentimento", "positivo").limit(limite).execute()

            cliente_ids = [c["cliente_id"] for c in conversas.data] if conversas.data else []

            if not cliente_ids:
                return {"success": True, "medicos": [], "total": 0}

            medicos = supabase.table("clientes").select(
                "primeiro_nome, telefone, especialidade"
            ).in_("id", cliente_ids).execute()

        elif filtro == "sem_resposta":
            # Medicos sem interacao de entrada
            medicos = supabase.table("clientes").select(
                "primeiro_nome, telefone, especialidade"
            ).eq("opted_out", False).order("created_at", desc=True).limit(limite).execute()

        elif filtro == "novos":
            # Medicos criados nos ultimos 7 dias
            semana_atras = (agora - timedelta(days=7)).isoformat()
            medicos = supabase.table("clientes").select(
                "primeiro_nome, telefone, especialidade"
            ).gte("created_at", semana_atras).limit(limite).execute()

        else:
            medicos = supabase.table("clientes").select(
                "primeiro_nome, telefone, especialidade"
            ).eq("opted_out", False).limit(limite).execute()

        lista = []
        for m in medicos.data or []:
            lista.append({
                "nome": m.get("primeiro_nome"),
                "telefone": m.get("telefone"),
                "especialidade": m.get("especialidade")
            })

        return {"success": True, "medicos": lista, "total": len(lista)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_bloquear_medico(params: dict) -> dict:
    """Bloqueia um medico."""
    telefone = params.get("telefone", "").strip()
    motivo = params.get("motivo", "Bloqueado via Slack")

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    medico = await _buscar_medico_por_identificador(telefone)

    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        supabase.table("clientes").update({
            "opt_out": True,
            "opted_out": True,
            "opted_out_at": datetime.now(timezone.utc).isoformat(),
            "opted_out_reason": motivo,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", medico["id"]).execute()

        return {
            "success": True,
            "nome": medico.get("primeiro_nome"),
            "telefone": medico.get("telefone")
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_desbloquear_medico(params: dict) -> dict:
    """Remove bloqueio de um medico."""
    telefone = params.get("telefone", "").strip()

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    medico = await _buscar_medico_por_identificador(telefone)

    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        supabase.table("clientes").update({
            "opt_out": False,
            "opted_out": False,
            "opted_out_at": None,
            "opted_out_reason": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", medico["id"]).execute()

        return {
            "success": True,
            "nome": medico.get("primeiro_nome"),
            "telefone": medico.get("telefone")
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_buscar_vagas(params: dict) -> dict:
    """Busca vagas disponiveis."""
    hospital = params.get("hospital")
    especialidade = params.get("especialidade")
    status = params.get("status", "aberta")
    limite = min(params.get("limite", 10), 20)

    try:
        query = supabase.table("vagas").select(
            "id, data, valor, status, hospitais(nome, cidade), periodos(nome), especialidades(nome)"
        )

        if status != "todas":
            query = query.eq("status", status)

        if hospital:
            # Buscar hospital primeiro
            hosp = supabase.table("hospitais").select("id").ilike("nome", f"%{hospital}%").limit(1).execute()
            if hosp.data:
                query = query.eq("hospital_id", hosp.data[0]["id"])

        if especialidade:
            esp = supabase.table("especialidades").select("id").ilike("nome", f"%{especialidade}%").limit(1).execute()
            if esp.data:
                query = query.eq("especialidade_id", esp.data[0]["id"])

        result = query.order("data").limit(limite).execute()

        vagas = []
        for v in result.data or []:
            vagas.append({
                "id": v.get("id"),
                "hospital": v.get("hospitais", {}).get("nome"),
                "cidade": v.get("hospitais", {}).get("cidade"),
                "data": v.get("data"),
                "periodo": v.get("periodos", {}).get("nome"),
                "valor": v.get("valor"),
                "especialidade": v.get("especialidades", {}).get("nome"),
                "status": v.get("status")
            })

        return {"success": True, "vagas": vagas, "total": len(vagas)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_reservar_vaga(params: dict) -> dict:
    """Reserva uma vaga para um medico."""
    telefone = params.get("telefone_medico", "").strip()
    data_vaga = params.get("data_vaga", "").strip()

    if not telefone or not data_vaga:
        return {"success": False, "error": "Telefone e data sao obrigatorios"}

    medico = await _buscar_medico_por_identificador(telefone)
    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        # Buscar vaga pela data
        vaga = supabase.table("vagas").select(
            "*, hospitais(nome), periodos(nome)"
        ).eq("data", data_vaga).eq("status", "aberta").limit(1).execute()

        if not vaga.data:
            return {"success": False, "error": f"Vaga nao encontrada para data {data_vaga}"}

        vaga_data = vaga.data[0]

        # Reservar
        supabase.table("vagas").update({
            "status": "reservada",
            "reservado_para_id": medico["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", vaga_data["id"]).execute()

        return {
            "success": True,
            "vaga": {
                "hospital": vaga_data.get("hospitais", {}).get("nome"),
                "data": vaga_data.get("data"),
                "periodo": vaga_data.get("periodos", {}).get("nome"),
                "valor": vaga_data.get("valor")
            },
            "medico": {
                "nome": medico.get("primeiro_nome"),
                "telefone": medico.get("telefone")
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_status_sistema(params: dict) -> dict:
    """Retorna status geral do sistema."""
    try:
        # Status Julia
        status_result = supabase.table("julia_status").select("status").order(
            "created_at", desc=True
        ).limit(1).execute()
        status = status_result.data[0].get("status") if status_result.data else "ativo"

        # Conversas ativas
        conversas = supabase.table("conversations").select(
            "id", count="exact"
        ).eq("status", "active").execute()

        # Handoffs pendentes
        handoffs = supabase.table("handoffs").select(
            "id", count="exact"
        ).eq("status", "pendente").execute()

        # Vagas abertas
        vagas = supabase.table("vagas").select(
            "id", count="exact"
        ).eq("status", "aberta").execute()

        # Mensagens hoje
        hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        msgs = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "enviada").gte("enviada_em", hoje).execute()

        return {
            "success": True,
            "status": status,
            "conversas_ativas": conversas.count or 0,
            "handoffs_pendentes": handoffs.count or 0,
            "vagas_abertas": vagas.count or 0,
            "mensagens_hoje": msgs.count or 0
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_buscar_handoffs(params: dict) -> dict:
    """Lista handoffs."""
    status = params.get("status", "pendente")

    try:
        query = supabase.table("handoffs").select(
            "*, conversations(clientes(primeiro_nome, telefone))"
        ).order("created_at", desc=True).limit(10)

        if status != "todos":
            query = query.eq("status", status)

        result = query.execute()

        handoffs = []
        for h in result.data or []:
            conv = h.get("conversations", {})
            cliente = conv.get("clientes", {}) if conv else {}
            handoffs.append({
                "id": h.get("id"),
                "medico": cliente.get("primeiro_nome"),
                "telefone": cliente.get("telefone"),
                "motivo": h.get("trigger_type"),
                "criado_em": h.get("created_at"),
                "status": h.get("status")
            })

        return {"success": True, "handoffs": handoffs, "total": len(handoffs)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_buscar_historico(params: dict) -> dict:
    """Busca historico de conversa."""
    telefone = params.get("telefone", "").strip()
    limite = min(params.get("limite", 10), 30)

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    medico = await _buscar_medico_por_identificador(telefone)
    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        interacoes = supabase.table("interacoes").select(
            "tipo, autor_tipo, conteudo, created_at"
        ).eq("cliente_id", medico["id"]).order(
            "created_at", desc=True
        ).limit(limite).execute()

        mensagens = []
        for i in interacoes.data or []:
            mensagens.append({
                "autor": "julia" if i.get("autor_tipo") == "julia" else "medico",
                "texto": i.get("conteudo"),
                "data": i.get("created_at")
            })

        return {
            "success": True,
            "medico": medico.get("primeiro_nome"),
            "mensagens": list(reversed(mensagens)),
            "total": len(mensagens)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_pausar_julia(params: dict, user_id: str) -> dict:
    """Pausa a Julia."""
    try:
        supabase.table("julia_status").insert({
            "status": "pausado",
            "motivo": "Pausado via Slack",
            "alterado_por": user_id,
            "alterado_via": "slack",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"success": True, "status": "pausado"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _handle_retomar_julia(params: dict, user_id: str) -> dict:
    """Retoma a Julia."""
    try:
        supabase.table("julia_status").insert({
            "status": "ativo",
            "motivo": "Retomado via Slack",
            "alterado_por": user_id,
            "alterado_via": "slack",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"success": True, "status": "ativo"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# HELPERS
# =============================================================================

async def _buscar_medico_por_identificador(identificador: str) -> dict | None:
    """Busca medico por telefone, nome ou CRM."""
    identificador = identificador.strip()
    telefone_limpo = re.sub(r'\D', '', identificador)

    # Por telefone
    if telefone_limpo and len(telefone_limpo) >= 8:
        result = supabase.table("clientes").select("*").or_(
            f"telefone.like.%{telefone_limpo[-8:]}"
        ).limit(1).execute()

        if result.data:
            return result.data[0]

    # Por CRM
    crm_limpo = re.sub(r'[^0-9]', '', identificador)
    if crm_limpo:
        result = supabase.table("clientes").select("*").or_(
            f"crm.eq.{crm_limpo},crm.ilike.%{crm_limpo}%"
        ).limit(1).execute()

        if result.data:
            return result.data[0]

    # Por nome
    if not telefone_limpo:
        result = supabase.table("clientes").select("*").ilike(
            "primeiro_nome", f"%{identificador}%"
        ).limit(1).execute()

        if result.data:
            return result.data[0]

    return None
