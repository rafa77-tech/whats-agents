"""
Tool de SQL dinâmico para Helena.

Sprint 47: Permite queries flexíveis com guardrails de segurança.
Apenas SELECT é permitido.
"""

import logging
import re

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Palavras bloqueadas (case insensitive)
PALAVRAS_BLOQUEADAS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "EXECUTE",
    "INTO OUTFILE",
    "LOAD_FILE",
]

# Tabelas bloqueadas
TABELAS_BLOQUEADAS = [
    "pg_shadow",
    "pg_authid",
    "pg_roles",
    "information_schema.columns",
    "pg_stat_statements",
]

TOOL_CONSULTA_SQL = {
    "name": "consulta_sql",
    "description": """Executa consulta SQL customizada no banco de dados.

USE APENAS QUANDO as tools específicas (metricas_periodo, etc) NÃO atendem.

REGRAS OBRIGATÓRIAS:
1. Apenas SELECT (nunca INSERT, UPDATE, DELETE, DROP)
2. SEMPRE usar LIMIT (máximo 100 rows)
3. Preferir agregações (COUNT, SUM, AVG) a listagens completas
4. Usar JOINs quando necessário relacionar tabelas

SCHEMA DISPONÍVEL:
- clientes: id, primeiro_nome, sobrenome, telefone, especialidade_id, crm, regiao, opted_out, created_at
- especialidades: id, nome, codigo
- conversations: id, cliente_id, status ('ativa','convertida','perdida','pausada'), controlled_by, created_at
- interacoes: id, conversation_id, cliente_id, tipo ('entrada','saida'), direcao ('inbound','outbound'), conteudo, autor_tipo, chip_id, created_at
- campanhas: id, nome_template, tipo_campanha, status, total_destinatarios, enviados, entregues, respondidos
- fila_mensagens: id, cliente_id, status, conteudo, metadata (jsonb), enviada_em, created_at
- vagas: id, hospital_id, especialidade_id, data, periodo, valor, status
- hospitais: id, nome, cidade, uf
- handoffs: id, conversation_id, reason, motivo, status, created_at, resolvido_em
- julia_chips: id, instance_name, status, trust_score, messages_sent_today

EXEMPLOS:
1. "Quantos médicos cardiologistas?"
   -> SELECT COUNT(*) FROM clientes c JOIN especialidades e ON e.id = c.especialidade_id WHERE e.nome ILIKE '%cardio%' LIMIT 1

2. "Top 5 hospitais com mais vagas"
   -> SELECT h.nome, COUNT(v.id) as vagas FROM hospitais h JOIN vagas v ON v.hospital_id = h.id GROUP BY h.id ORDER BY vagas DESC LIMIT 5

3. "Mensagens enviadas por campanha"
   -> SELECT metadata->>'campanha_id' as campanha, COUNT(*) FROM fila_mensagens WHERE metadata->>'campanha_id' IS NOT NULL GROUP BY 1 LIMIT 20
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Query SQL (apenas SELECT)",
            },
            "explicacao": {
                "type": "string",
                "description": "Breve explicação do que a query faz",
            },
        },
        "required": ["query", "explicacao"],
    },
}


def validar_query(query: str) -> tuple[bool, str]:
    """
    Valida query SQL antes de executar.

    Args:
        query: Query SQL

    Returns:
        (valido, mensagem_erro)
    """
    query_upper = query.upper().strip()

    # 1. Deve começar com SELECT
    if not query_upper.startswith("SELECT"):
        return False, "Apenas SELECT é permitido"

    # 2. Verificar palavras bloqueadas
    for palavra in PALAVRAS_BLOQUEADAS:
        # Usar word boundary para evitar falsos positivos
        pattern = rf"\b{palavra}\b"
        if re.search(pattern, query_upper):
            return False, f"Operação '{palavra}' não é permitida"

    # 3. Verificar tabelas bloqueadas
    for tabela in TABELAS_BLOQUEADAS:
        if tabela.upper() in query_upper:
            return False, f"Acesso à tabela '{tabela}' não é permitido"

    # 4. Verificar se tem LIMIT
    if "LIMIT" not in query_upper:
        return False, "Query deve incluir LIMIT (máximo 100)"

    # 5. Verificar valor do LIMIT
    limit_match = re.search(r"LIMIT\s+(\d+)", query_upper)
    if limit_match:
        limit_value = int(limit_match.group(1))
        if limit_value > 100:
            return False, f"LIMIT máximo é 100 (encontrado: {limit_value})"

    return True, ""


async def handle_consulta_sql(params: dict, user_id: str, channel_id: str) -> dict:
    """
    Handler para consulta_sql.

    Args:
        params: {query, explicacao}
        user_id: ID do usuário Slack
        channel_id: ID do canal Slack

    Returns:
        Resultado da query ou erro
    """
    query = params.get("query", "").strip()
    explicacao = params.get("explicacao", "")

    if not query:
        return {"success": False, "error": "Query não fornecida"}

    # Validar query
    valido, erro = validar_query(query)
    if not valido:
        logger.warning(f"Query Helena rejeitada: {erro} | Query: {query[:100]}")
        return {"success": False, "error": erro}

    try:
        # Executar via função segura
        result = supabase.rpc("execute_readonly_query", {"sql_query": query}).execute()

        data = result.data or []

        logger.info(f"Query Helena executada: {explicacao} | User: {user_id} | Rows: {len(data)}")

        return {
            "success": True,
            "explicacao": explicacao,
            "query_executada": query,
            "data": data,
            "row_count": len(data),
        }

    except Exception as e:
        error_msg = str(e)

        # Simplificar mensagens de erro comuns
        if "timeout" in error_msg.lower():
            error_msg = "Query excedeu o tempo limite de 10 segundos. Tente uma query mais simples."
        elif "syntax error" in error_msg.lower():
            error_msg = "Erro de sintaxe SQL. Verifique a query."
        elif "does not exist" in error_msg.lower():
            error_msg = "Tabela ou coluna não encontrada. Verifique o schema."

        logger.error(f"Erro em consulta_sql: {e} | Query: {query[:100]}")
        return {"success": False, "error": error_msg}
