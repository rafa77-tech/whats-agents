"""
Tools de grupos WhatsApp para o agente Slack.

Sprint 14 - E10 - Interface Slack para gestão de vagas capturadas de grupos.
"""
from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)


# =============================================================================
# DEFINICAO DAS TOOLS (formato Claude)
# =============================================================================

TOOL_LISTAR_VAGAS_REVISAO = {
    "name": "listar_vagas_revisao",
    "description": """Lista vagas de grupos WhatsApp aguardando revisão.

QUANDO USAR:
- Gestor quer ver vagas pendentes de aprovação
- Gestor menciona "vagas de grupo", "revisão", "pendentes"
- Gestor pergunta "o que tem pra revisar?"

EXEMPLOS:
- "quais vagas tem pra revisar?"
- "mostra as vagas pendentes dos grupos"
- "tem vaga de grupo pra aprovar?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "limite": {
                "type": "integer",
                "description": "Máximo de vagas a listar (default 10)"
            },
            "grupo": {
                "type": "string",
                "description": "Filtrar por nome do grupo (opcional)"
            }
        },
        "required": []
    }
}

TOOL_APROVAR_VAGA_GRUPO = {
    "name": "aprovar_vaga_grupo",
    "description": """Aprova uma vaga de grupo para importação para a tabela principal.

QUANDO USAR:
- Gestor quer aprovar/importar vaga de grupo
- Gestor diz "aprova", "importa", "pode subir"
- Após ver detalhes de uma vaga

EXEMPLOS:
- "aprova a vaga abc123"
- "pode importar essa vaga"
- "manda essa pro sistema"

ACAO CRITICA: Peca confirmacao antes de aprovar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "vaga_id": {
                "type": "string",
                "description": "ID da vaga (pode ser ID curto de 8 chars ou completo)"
            },
            "correcoes": {
                "type": "object",
                "description": "Correções opcionais (hospital_id, especialidade_id, data, valor)",
                "properties": {
                    "hospital_id": {"type": "string"},
                    "especialidade_id": {"type": "string"},
                    "data": {"type": "string"},
                    "valor": {"type": "integer"}
                }
            }
        },
        "required": ["vaga_id"]
    }
}

TOOL_REJEITAR_VAGA_GRUPO = {
    "name": "rejeitar_vaga_grupo",
    "description": """Rejeita uma vaga de grupo.

QUANDO USAR:
- Gestor quer rejeitar vaga incorreta
- Gestor diz "rejeita", "descarta", "não serve"

EXEMPLOS:
- "rejeita a vaga abc123"
- "descarta essa, tá errada"
- "pode ignorar essa vaga"

ACAO CRITICA: Peca confirmacao antes de rejeitar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "vaga_id": {
                "type": "string",
                "description": "ID da vaga"
            },
            "motivo": {
                "type": "string",
                "description": "Motivo da rejeição"
            }
        },
        "required": ["vaga_id"]
    }
}

TOOL_DETALHES_VAGA_GRUPO = {
    "name": "detalhes_vaga_grupo",
    "description": """Mostra detalhes completos de uma vaga de grupo.

QUANDO USAR:
- Gestor quer ver mais informações sobre uma vaga
- Gestor pergunta "mais detalhes", "mostra essa vaga"

EXEMPLOS:
- "mostra detalhes da vaga abc123"
- "me fala mais sobre essa vaga"
- "qual a origem dessa?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "vaga_id": {
                "type": "string",
                "description": "ID da vaga"
            }
        },
        "required": ["vaga_id"]
    }
}

TOOL_ESTATISTICAS_GRUPOS = {
    "name": "estatisticas_grupos",
    "description": """Mostra estatísticas de captura de vagas de grupos WhatsApp.

QUANDO USAR:
- Gestor quer ver métricas de grupos
- Gestor pergunta "como tá a captura?", "quantas vagas dos grupos?"
- Gestor quer relatório de performance

EXEMPLOS:
- "como tão as estatísticas dos grupos?"
- "quantas vagas capturamos hoje?"
- "qual o resumo da semana?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "periodo": {
                "type": "string",
                "enum": ["hoje", "semana", "mes"],
                "description": "Período para estatísticas (default: hoje)"
            }
        },
        "required": []
    }
}

TOOL_ADICIONAR_ALIAS_HOSPITAL = {
    "name": "adicionar_alias_hospital",
    "description": """Adiciona um alias (apelido) para um hospital.

QUANDO USAR:
- Gestor quer ensinar uma variação de nome de hospital
- Sistema não reconheceu abreviação
- Gestor diz "esse é o Hospital X"

EXEMPLOS:
- "adiciona HSL como alias do Hospital São Luiz"
- "quando falar HSPE é o Hospital do Servidor"
- "associa 'Luiz' ao São Luiz ABC"

ACAO CRITICA: Peca confirmacao antes de adicionar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "hospital_id": {
                "type": "string",
                "description": "ID do hospital"
            },
            "alias": {
                "type": "string",
                "description": "Novo alias a adicionar"
            }
        },
        "required": ["hospital_id", "alias"]
    }
}

TOOL_BUSCAR_HOSPITAL = {
    "name": "buscar_hospital_grupos",
    "description": """Busca hospital por nome ou alias para gestão de grupos.

QUANDO USAR:
- Gestor precisa encontrar ID de hospital
- Gestor quer associar alias a hospital
- Gestor pergunta "qual o ID do hospital X?"

EXEMPLOS:
- "busca o hospital são luiz"
- "qual o ID do Einstein?"
- "encontra hospitais com 'Santo'"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "termo": {
                "type": "string",
                "description": "Termo de busca (nome ou parte do nome)"
            }
        },
        "required": ["termo"]
    }
}


# =============================================================================
# HELPERS
# =============================================================================

async def resolver_id_vaga(vaga_id: str) -> Optional[str]:
    """Resolve ID curto para completo."""
    if len(vaga_id) >= 32:  # UUID completo ou quase
        return vaga_id

    # Buscar por prefixo
    result = supabase.table("vagas_grupo") \
        .select("id") \
        .ilike("id", f"{vaga_id}%") \
        .limit(1) \
        .execute()

    return result.data[0]["id"] if result.data else None


# =============================================================================
# HANDLERS
# =============================================================================

async def handle_listar_vagas_revisao(params: dict) -> dict:
    """Lista vagas de grupos aguardando revisão."""
    limite = min(params.get("limite", 10), 20)
    grupo = params.get("grupo")

    try:
        query = supabase.table("vagas_grupo") \
            .select("""
                id,
                hospital_raw,
                especialidade_raw,
                data,
                periodo_raw,
                valor,
                confianca_geral,
                created_at,
                grupos_whatsapp(nome),
                hospitais(nome),
                especialidades(nome)
            """) \
            .eq("status", "aguardando_revisao") \
            .order("confianca_geral", desc=True) \
            .limit(limite)

        if grupo:
            # Buscar grupo primeiro
            grupo_result = supabase.table("grupos_whatsapp") \
                .select("id") \
                .ilike("nome", f"%{grupo}%") \
                .limit(1) \
                .execute()

            if grupo_result.data:
                query = query.eq("grupo_origem_id", grupo_result.data[0]["id"])

        result = query.execute()

        vagas = []
        for v in result.data or []:
            vagas.append({
                "id": v["id"][:8],
                "id_completo": v["id"],
                "hospital": (v.get("hospitais") or {}).get("nome") or v.get("hospital_raw", "N/A"),
                "hospital_raw": v.get("hospital_raw"),
                "especialidade": (v.get("especialidades") or {}).get("nome") or v.get("especialidade_raw", "N/A"),
                "data": v.get("data"),
                "periodo": v.get("periodo_raw"),
                "valor": v.get("valor"),
                "confianca": f"{v.get('confianca_geral', 0)*100:.0f}%" if v.get("confianca_geral") else "N/A",
                "grupo": (v.get("grupos_whatsapp") or {}).get("nome", "N/A"),
                "criada": v.get("created_at", "")[:10] if v.get("created_at") else "N/A",
            })

        return {
            "success": True,
            "vagas": vagas,
            "total": len(vagas),
            "mensagem": f"Encontradas {len(vagas)} vagas aguardando revisão"
        }

    except Exception as e:
        logger.error(f"Erro ao listar vagas revisão: {e}")
        return {"success": False, "error": str(e)}


async def handle_aprovar_vaga_grupo(params: dict) -> dict:
    """Aprova vaga de grupo para importação."""
    from app.services.grupos.importador import criar_vaga_principal, atualizar_vaga_grupo_importada

    vaga_id = params.get("vaga_id", "").strip()
    correcoes = params.get("correcoes", {})

    if not vaga_id:
        return {"success": False, "error": "ID da vaga é obrigatório"}

    vaga_id_completo = await resolver_id_vaga(vaga_id)
    if not vaga_id_completo:
        return {"success": False, "error": f"Vaga não encontrada: {vaga_id}"}

    try:
        vaga = supabase.table("vagas_grupo") \
            .select("*") \
            .eq("id", vaga_id_completo) \
            .single() \
            .execute()

        if not vaga.data:
            return {"success": False, "error": "Vaga não encontrada"}

        dados = vaga.data

        # Verificar status
        if dados.get("status") != "aguardando_revisao":
            return {"success": False, "error": f"Vaga não está em revisão. Status: {dados.get('status')}"}

        # Aplicar correções
        if correcoes:
            campos_validos = ["hospital_id", "especialidade_id", "data", "valor", "periodo_id"]
            correcoes_filtradas = {k: v for k, v in correcoes.items() if k in campos_validos and v}

            if correcoes_filtradas:
                supabase.table("vagas_grupo") \
                    .update(correcoes_filtradas) \
                    .eq("id", vaga_id_completo) \
                    .execute()

                # Atualizar dados locais
                dados.update(correcoes_filtradas)

        # Validar dados mínimos
        if not dados.get("hospital_id") or not dados.get("especialidade_id"):
            faltando = []
            if not dados.get("hospital_id"):
                faltando.append("hospital_id")
            if not dados.get("especialidade_id"):
                faltando.append("especialidade_id")

            return {
                "success": False,
                "error": "Dados insuficientes para importar",
                "faltando": faltando
            }

        # Importar
        vaga_principal_id = await criar_vaga_principal(dados)
        await atualizar_vaga_grupo_importada(UUID(vaga_id_completo), vaga_principal_id)

        return {
            "success": True,
            "vaga_id": str(vaga_principal_id),
            "vaga_id_curto": str(vaga_principal_id)[:8],
            "mensagem": f"Vaga importada com sucesso! ID: {str(vaga_principal_id)[:8]}"
        }

    except Exception as e:
        logger.error(f"Erro ao aprovar vaga {vaga_id}: {e}")
        return {"success": False, "error": str(e)}


async def handle_rejeitar_vaga_grupo(params: dict) -> dict:
    """Rejeita vaga de grupo."""
    vaga_id = params.get("vaga_id", "").strip()
    motivo = params.get("motivo", "rejeitada_manualmente")

    if not vaga_id:
        return {"success": False, "error": "ID da vaga é obrigatório"}

    vaga_id_completo = await resolver_id_vaga(vaga_id)
    if not vaga_id_completo:
        return {"success": False, "error": f"Vaga não encontrada: {vaga_id}"}

    try:
        supabase.table("vagas_grupo") \
            .update({
                "status": "descartada",
                "motivo_status": motivo,
                "revisado_em": datetime.now(UTC).isoformat(),
            }) \
            .eq("id", vaga_id_completo) \
            .execute()

        return {
            "success": True,
            "mensagem": f"Vaga {vaga_id} rejeitada. Motivo: {motivo}"
        }

    except Exception as e:
        logger.error(f"Erro ao rejeitar vaga {vaga_id}: {e}")
        return {"success": False, "error": str(e)}


async def handle_detalhes_vaga_grupo(params: dict) -> dict:
    """Mostra detalhes completos de uma vaga de grupo."""
    vaga_id = params.get("vaga_id", "").strip()

    if not vaga_id:
        return {"success": False, "error": "ID da vaga é obrigatório"}

    vaga_id_completo = await resolver_id_vaga(vaga_id)
    if not vaga_id_completo:
        return {"success": False, "error": f"Vaga não encontrada: {vaga_id}"}

    try:
        vaga = supabase.table("vagas_grupo") \
            .select("""
                *,
                grupos_whatsapp(nome, regiao),
                contatos_grupo(nome, telefone),
                hospitais(nome, cidade),
                especialidades(nome),
                periodos(nome)
            """) \
            .eq("id", vaga_id_completo) \
            .single() \
            .execute()

        if not vaga.data:
            return {"success": False, "error": "Vaga não encontrada"}

        dados = vaga.data

        # Buscar fontes separadamente
        fontes = supabase.table("vagas_grupo_fontes") \
            .select("ordem, valor_informado, grupos_whatsapp(nome)") \
            .eq("vaga_grupo_id", vaga_id_completo) \
            .order("ordem") \
            .execute()

        return {
            "success": True,
            "id": dados["id"][:8],
            "id_completo": dados["id"],
            "status": dados.get("status"),
            "confianca": f"{dados.get('confianca_geral', 0)*100:.0f}%" if dados.get("confianca_geral") else "N/A",

            "dados_extraidos": {
                "hospital_raw": dados.get("hospital_raw"),
                "especialidade_raw": dados.get("especialidade_raw"),
                "data": dados.get("data"),
                "periodo_raw": dados.get("periodo_raw"),
                "valor": dados.get("valor"),
                "observacoes": dados.get("observacoes"),
            },

            "dados_normalizados": {
                "hospital": (dados.get("hospitais") or {}).get("nome"),
                "hospital_cidade": (dados.get("hospitais") or {}).get("cidade"),
                "hospital_score": f"{dados.get('hospital_match_score', 0)*100:.0f}%" if dados.get("hospital_match_score") else "N/A",
                "especialidade": (dados.get("especialidades") or {}).get("nome"),
                "especialidade_score": f"{dados.get('especialidade_match_score', 0)*100:.0f}%" if dados.get("especialidade_match_score") else "N/A",
                "periodo": (dados.get("periodos") or {}).get("nome"),
            },

            "origem": {
                "grupo": (dados.get("grupos_whatsapp") or {}).get("nome"),
                "regiao": (dados.get("grupos_whatsapp") or {}).get("regiao"),
                "contato": (dados.get("contatos_grupo") or {}).get("nome"),
                "telefone": (dados.get("contatos_grupo") or {}).get("telefone"),
            },

            "fontes": [
                {
                    "ordem": f["ordem"],
                    "grupo": (f.get("grupos_whatsapp") or {}).get("nome"),
                    "valor": f.get("valor_informado"),
                }
                for f in (fontes.data or [])
            ],

            "timestamps": {
                "criada": dados.get("created_at"),
            }
        }

    except Exception as e:
        logger.error(f"Erro ao buscar detalhes vaga {vaga_id}: {e}")
        return {"success": False, "error": str(e)}


async def handle_estatisticas_grupos(params: dict) -> dict:
    """Mostra estatísticas de captura de grupos."""
    periodo = params.get("periodo", "hoje")

    # Calcular data início
    hoje = datetime.now(UTC).date()
    if periodo == "hoje":
        data_inicio = hoje
    elif periodo == "semana":
        data_inicio = hoje - timedelta(days=7)
    elif periodo == "mes":
        data_inicio = hoje - timedelta(days=30)
    else:
        data_inicio = hoje

    data_inicio_str = data_inicio.isoformat()

    try:
        # Mensagens processadas
        msgs = supabase.table("mensagens_grupo") \
            .select("id", count="exact") \
            .gte("created_at", data_inicio_str) \
            .execute()

        # Vagas por status
        vagas_total = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .gte("created_at", data_inicio_str) \
            .execute()

        vagas_importadas = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .eq("status", "importada") \
            .gte("created_at", data_inicio_str) \
            .execute()

        vagas_revisao = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .eq("status", "aguardando_revisao") \
            .gte("created_at", data_inicio_str) \
            .execute()

        vagas_descartadas = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .eq("status", "descartada") \
            .gte("created_at", data_inicio_str) \
            .execute()

        vagas_duplicadas = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .eq("eh_duplicada", True) \
            .gte("created_at", data_inicio_str) \
            .execute()

        # Top grupos (usando query simples)
        top_grupos = supabase.table("vagas_grupo") \
            .select("grupo_origem_id, grupos_whatsapp(nome)") \
            .eq("status", "importada") \
            .gte("created_at", data_inicio_str) \
            .execute()

        # Contar manualmente por grupo
        grupos_count = {}
        for v in (top_grupos.data or []):
            gid = v.get("grupo_origem_id")
            nome = (v.get("grupos_whatsapp") or {}).get("nome", "N/A")
            if gid:
                if gid not in grupos_count:
                    grupos_count[gid] = {"nome": nome, "total": 0}
                grupos_count[gid]["total"] += 1

        top_5 = sorted(grupos_count.values(), key=lambda x: x["total"], reverse=True)[:5]

        total = vagas_total.count or 0
        importadas = vagas_importadas.count or 0

        taxa_conversao = (importadas / total * 100) if total > 0 else 0
        taxa_dup = ((vagas_duplicadas.count or 0) / total * 100) if total > 0 else 0

        return {
            "success": True,
            "periodo": periodo,
            "data_inicio": data_inicio_str,

            "mensagens": {
                "total": msgs.count or 0,
            },

            "vagas": {
                "total": total,
                "importadas": importadas,
                "aguardando_revisao": vagas_revisao.count or 0,
                "descartadas": vagas_descartadas.count or 0,
                "duplicadas": vagas_duplicadas.count or 0,
            },

            "taxas": {
                "conversao": f"{taxa_conversao:.1f}%",
                "duplicacao": f"{taxa_dup:.1f}%",
            },

            "top_grupos": top_5,

            "mensagem": f"Estatísticas de {periodo}: {importadas} vagas importadas de {total} capturadas"
        }

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        return {"success": False, "error": str(e)}


async def handle_adicionar_alias_hospital(params: dict) -> dict:
    """Adiciona alias para hospital."""
    from app.services.grupos.normalizador import normalizar_para_busca

    hospital_id = params.get("hospital_id", "").strip()
    alias = params.get("alias", "").strip()

    if not hospital_id or not alias:
        return {"success": False, "error": "hospital_id e alias são obrigatórios"}

    try:
        # Verificar hospital existe
        hospital = supabase.table("hospitais") \
            .select("id, nome") \
            .eq("id", hospital_id) \
            .single() \
            .execute()

        if not hospital.data:
            return {"success": False, "error": f"Hospital não encontrado: {hospital_id}"}

        # Normalizar alias
        alias_norm = normalizar_para_busca(alias)

        # Verificar se já existe
        existente = supabase.table("hospitais_alias") \
            .select("id") \
            .eq("alias_normalizado", alias_norm) \
            .limit(1) \
            .execute()

        if existente.data:
            return {"success": False, "error": f"Alias já existe: {alias}"}

        # Criar alias
        supabase.table("hospitais_alias").insert({
            "hospital_id": hospital_id,
            "alias": alias,
            "alias_normalizado": alias_norm,
            "origem": "gestor_manual",
            "confianca": 1.0,
        }).execute()

        return {
            "success": True,
            "mensagem": f"Alias '{alias}' adicionado ao hospital '{hospital.data['nome']}'"
        }

    except Exception as e:
        logger.error(f"Erro ao adicionar alias: {e}")
        return {"success": False, "error": str(e)}


async def handle_buscar_hospital_grupos(params: dict) -> dict:
    """Busca hospital por nome ou alias."""
    from app.services.grupos.normalizador import normalizar_para_busca

    termo = params.get("termo", "").strip()

    if not termo:
        return {"success": False, "error": "Termo de busca é obrigatório"}

    try:
        termo_norm = normalizar_para_busca(termo)

        # Buscar por alias primeiro
        alias_result = supabase.table("hospitais_alias") \
            .select("hospital_id, alias, hospitais(id, nome, cidade)") \
            .ilike("alias_normalizado", f"%{termo_norm}%") \
            .limit(5) \
            .execute()

        # Buscar direto pelo nome também
        nome_result = supabase.table("hospitais") \
            .select("id, nome, cidade") \
            .ilike("nome", f"%{termo}%") \
            .limit(5) \
            .execute()

        resultados = []
        ids_vistos = set()

        # Adicionar resultados de alias
        for a in (alias_result.data or []):
            hosp = a.get("hospitais") or {}
            if hosp.get("id") and hosp["id"] not in ids_vistos:
                ids_vistos.add(hosp["id"])
                resultados.append({
                    "id": hosp["id"],
                    "nome": hosp.get("nome"),
                    "cidade": hosp.get("cidade"),
                    "match_via": f"alias: {a.get('alias')}"
                })

        # Adicionar resultados diretos
        for h in (nome_result.data or []):
            if h["id"] not in ids_vistos:
                ids_vistos.add(h["id"])
                resultados.append({
                    "id": h["id"],
                    "nome": h.get("nome"),
                    "cidade": h.get("cidade"),
                    "match_via": "nome"
                })

        return {
            "success": True,
            "termo": termo,
            "resultados": resultados[:10],
            "total": len(resultados)
        }

    except Exception as e:
        logger.error(f"Erro ao buscar hospital: {e}")
        return {"success": False, "error": str(e)}
