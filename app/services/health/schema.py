"""
Verificacoes de schema e contrato de prompts.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
"""

import hashlib
import logging

from app.services.supabase import supabase
from app.services.health.constants import CRITICAL_TABLES, REQUIRED_PROMPTS

logger = logging.getLogger(__name__)


def gerar_schema_fingerprint() -> dict:
    """
    Gera fingerprint do schema para deteccao de drift.

    Contrato:
    - hash(sorted(table_names) + sorted(column_definitions))
    - Inclui apenas tabelas criticas
    - Mudanca no fingerprint indica possivel drift

    Returns:
        dict com fingerprint e detalhes
    """
    try:
        # Buscar estrutura das tabelas criticas
        result = supabase.rpc(
            "get_table_columns_for_fingerprint", {"table_names": CRITICAL_TABLES}
        ).execute()

        if not result.data:
            # Fallback: usar query direta
            columns_query = (
                supabase.table("information_schema.columns")
                .select("table_name, column_name, data_type, is_nullable")
                .in_("table_name", CRITICAL_TABLES)
                .execute()
            )

            if columns_query.data:
                columns = columns_query.data
            else:
                return {
                    "fingerprint": "error",
                    "error": "Could not fetch schema info",
                    "tables_checked": CRITICAL_TABLES,
                }
        else:
            columns = result.data

        # Ordenar por tabela e coluna para consistencia
        sorted_columns = sorted(
            columns, key=lambda c: (c.get("table_name", ""), c.get("column_name", ""))
        )

        # Criar string para hash
        fingerprint_str = ""
        for col in sorted_columns:
            fingerprint_str += f"{col.get('table_name', '')}:{col.get('column_name', '')}:{col.get('data_type', '')}:{col.get('is_nullable', '')}|"

        # Gerar hash SHA256 truncado (primeiros 16 chars)
        fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]

        return {
            "fingerprint": fingerprint,
            "tables_checked": CRITICAL_TABLES,
            "columns_count": len(sorted_columns),
        }

    except Exception as e:
        logger.warning(f"[health] Schema fingerprint generation failed: {e}")
        # Fallback simples: hash da lista de tabelas
        simple_fp = hashlib.sha256("|".join(sorted(CRITICAL_TABLES)).encode()).hexdigest()[:16]

        return {
            "fingerprint": f"fallback-{simple_fp}",
            "tables_checked": CRITICAL_TABLES,
            "error": str(e),
        }


async def verificar_contrato_prompts() -> dict:
    """
    Valida contrato de prompts.

    Retorna dict com:
    - status: ok | error | warning
    - missing: prompts que nao existem
    - inactive: prompts que existem mas nao estao ativos
    - too_short: prompts com tamanho abaixo do minimo
    - missing_sentinels: sentinelas obrigatorias ausentes
    - missing_warnings: sentinelas de warning ausentes
    - versions: versao de cada prompt
    """
    result = {
        "status": "pending",
        "missing": [],
        "inactive": [],
        "too_short": [],
        "missing_sentinels": [],
        "missing_warnings": [],
        "versions": {},
    }

    has_error = False
    has_warning = False

    try:
        # Buscar todos os prompts necessarios
        response = (
            supabase.table("prompts")
            .select("nome, versao, ativo, conteudo")
            .in_("nome", list(REQUIRED_PROMPTS.keys()))
            .execute()
        )

        found = {r["nome"]: r for r in (response.data or [])}

        for nome, req in REQUIRED_PROMPTS.items():
            prompt = found.get(nome)

            # Check existencia
            if not prompt:
                result["missing"].append(nome)
                has_error = True
                continue

            # Check ativo
            if not prompt.get("ativo"):
                result["inactive"].append(nome)
                has_error = True
                continue

            # Registrar versao
            result["versions"][nome] = prompt.get("versao")

            conteudo = prompt.get("conteudo") or ""

            # Check tamanho minimo
            if len(conteudo) < req["min_len"]:
                result["too_short"].append(
                    {"nome": nome, "len": len(conteudo), "min": req["min_len"]}
                )
                has_error = True

            # Check sentinelas obrigatorias (BLOQUEADOR)
            for sentinel in req.get("required_sentinels", []):
                if sentinel not in conteudo:
                    result["missing_sentinels"].append({"prompt": nome, "sentinel": sentinel})
                    has_error = True

            # Check sentinelas de warning
            for sentinel in req.get("warning_sentinels", []):
                if sentinel not in conteudo:
                    result["missing_warnings"].append({"prompt": nome, "sentinel": sentinel})
                    has_warning = True

        if has_error:
            result["status"] = "error"
        elif has_warning:
            result["status"] = "warning"
        else:
            result["status"] = "ok"

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
        logger.error(f"[health/deep] Prompt contract check failed: {e}")

    return result
