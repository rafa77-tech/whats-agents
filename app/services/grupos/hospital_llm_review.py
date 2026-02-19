"""
Revisao de hospitais via LLM em batch.

Classifica hospitais pendentes e detecta duplicatas semanticas usando Claude Haiku.
Job one-shot para limpeza pos-Sprint 60.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.business_events.types import BusinessEvent, EventType, EventSource
from app.services.business_events.repository import emit_event
from app.services.grupos.hospital_cleanup import (
    deletar_hospital_seguro,
    mesclar_hospitais,
)

logger = get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS_CLASSIFICACAO = 4096
MAX_TOKENS_MERGE = 4096


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ClassificacaoHospital:
    """Resultado da classificacao LLM de um hospital."""

    id: str
    classificacao: str  # "hospital_real" | "generico_invalido" | "fragmento_lixo"
    nome_normalizado: Optional[str] = None
    cidade_inferida: Optional[str] = None
    confianca: float = 0.0
    erro: Optional[str] = None


@dataclass
class DecisaoMerge:
    """Decisao LLM sobre um par de hospitais candidatos a merge."""

    par_id: int
    id_a: str
    id_b: str
    eh_duplicata: bool = False
    hospital_principal: Optional[str] = None
    confianca: float = 0.0
    motivo: Optional[str] = None
    erro: Optional[str] = None


@dataclass
class ResultadoRevisaoLLM:
    """Resultado completo da revisao LLM."""

    # Fase 1
    hospitais_classificados: int = 0
    hospitais_reais: int = 0
    genericos_invalidos: int = 0
    fragmentos_lixo: int = 0
    deletados: int = 0
    flagged_revisao: int = 0
    nomes_atualizados: int = 0
    cidades_inferidas: int = 0

    # Fase 2
    pares_analisados: int = 0
    merges_auto: int = 0
    merges_revisao: int = 0
    merges_skip: int = 0

    # Tokens
    tokens_input: int = 0
    tokens_output: int = 0

    # Erros
    erros: list = field(default_factory=list)


# =============================================================================
# Prompts
# =============================================================================

PROMPT_CLASSIFICACAO_HOSPITAIS = """Voce e um especialista em dados de hospitais brasileiros.
Analise esta lista de hospitais e classifique cada um.

Classificacoes possiveis:
- "hospital_real": hospital, clinica, UPA, UBS, maternidade ou unidade de saude real
- "generico_invalido": nao e hospital (especialidade, fragmento, produto, data, horario)
- "fragmento_lixo": lixo de extracao (valor monetario, contato, texto truncado)

Para hospitais com cidade "Nao informada", infira a cidade se reconhecer o hospital.

Hospitais:
{lista_hospitais}

Responda com JSON em tags <json></json>:
<json>
[{{"id": "...", "classificacao": "hospital_real", "nome_normalizado": "Hospital Sao Luiz", "cidade_inferida": "Sao Paulo", "confianca": 0.95}}]
</json>

Regras:
- nome_normalizado: nome oficial se diferente do original, null se igual
- cidade_inferida: preencha se reconhecer o hospital e cidade esta "Nao informada", null caso contrario
- confianca: 0.0-1.0 refletindo certeza na classificacao"""

PROMPT_DETECCAO_DUPLICATAS = """Analise estes pares de hospitais e determine se sao o MESMO estabelecimento fisico.

{lista_pares}

Responda com JSON em tags <json></json>:
<json>
[{{"par_id": 1, "eh_duplicata": true, "hospital_principal": "uuid-principal", "confianca": 0.92, "motivo": "Mesmo hospital, nomes diferentes"}}]
</json>

Regras:
- eh_duplicata=true SOMENTE se e o mesmo local fisico
- Unidades diferentes de mesma rede NAO sao duplicatas (ex: Sao Luiz Morumbi vs Sao Luiz Analia Franco)
- hospital_principal: UUID do hospital com nome mais completo/oficial
- confianca: 0.0-1.0 refletindo certeza"""


# =============================================================================
# Helpers
# =============================================================================


def _extrair_json_lista(texto: str) -> list:
    """Extrai lista JSON da resposta LLM (entre tags <json> ou fallback regex)."""
    # Tentar entre tags <json>...</json>
    match = re.search(r"<json>\s*([\s\S]*?)\s*</json>", texto)
    if match:
        return json.loads(match.group(1))

    # Fallback: buscar array JSON
    match = re.search(r"\[[\s\S]+?\]", texto)
    if match:
        return json.loads(match.group())

    raise ValueError("Nenhum JSON encontrado na resposta LLM")


def _formatar_hospital_para_prompt(h: dict) -> str:
    """Formata hospital para inclusao no prompt."""
    return f"{h['id']} | {h['nome']} | {h.get('cidade', 'Nao informada')}, {h.get('estado', 'SP')}"


def _formatar_par_para_prompt(par_id: int, a: dict, b: dict, sim: float) -> str:
    """Formata par de hospitais para prompt de merge."""
    return (
        f"Par {par_id}:\n"
        f'  A: ID={a["id"]} | "{a["nome"]}" | {a.get("cidade", "?")}, {a.get("estado", "?")}\n'
        f'  B: ID={b["id"]} | "{b["nome"]}" | {b.get("cidade", "?")}, {b.get("estado", "?")}\n'
        f"  Similaridade: {sim:.0%}"
    )


# =============================================================================
# Fase 1: Classificacao
# =============================================================================


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
async def _chamar_llm_classificacao(
    client: anthropic.AsyncAnthropic, hospitais: list[dict]
) -> tuple[list[dict], int, int]:
    """Chama LLM para classificar um batch de hospitais."""
    lista_texto = "\n".join(_formatar_hospital_para_prompt(h) for h in hospitais)
    prompt = PROMPT_CLASSIFICACAO_HOSPITAIS.format(lista_hospitais=lista_texto)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_CLASSIFICACAO,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = response.content[0].text.strip()
    resultado = _extrair_json_lista(texto)

    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens

    return resultado, tokens_in, tokens_out


async def classificar_hospitais_llm(
    limite: int = 1000, tamanho_batch: int = 50
) -> tuple[list[ClassificacaoHospital], int, int]:
    """
    Classifica hospitais pendentes de revisao usando LLM.

    Args:
        limite: Maximo de hospitais a processar
        tamanho_batch: Hospitais por chamada LLM

    Returns:
        Tuple (classificacoes, tokens_input_total, tokens_output_total)
    """
    result = (
        supabase.table("hospitais")
        .select("id, nome, cidade, estado")
        .eq("precisa_revisao", True)
        .order("created_at")
        .limit(limite)
        .execute()
    )

    hospitais = result.data or []
    if not hospitais:
        logger.info("Nenhum hospital pendente de revisao")
        return [], 0, 0

    logger.info(
        "Iniciando classificacao LLM",
        extra={"total_hospitais": len(hospitais), "tamanho_batch": tamanho_batch},
    )

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    classificacoes: list[ClassificacaoHospital] = []
    tokens_in_total = 0
    tokens_out_total = 0

    # Processar em batches sequenciais
    for i in range(0, len(hospitais), tamanho_batch):
        batch = hospitais[i : i + tamanho_batch]
        batch_num = i // tamanho_batch + 1
        total_batches = (len(hospitais) + tamanho_batch - 1) // tamanho_batch

        logger.info(
            f"Classificacao batch {batch_num}/{total_batches}",
            extra={"batch_size": len(batch)},
        )

        ids_no_batch = {h["id"] for h in batch}

        try:
            resultados, tokens_in, tokens_out = await _chamar_llm_classificacao(client, batch)
            tokens_in_total += tokens_in
            tokens_out_total += tokens_out

            for item in resultados:
                item_id = item.get("id", "")
                if item_id not in ids_no_batch:
                    continue
                classificacoes.append(
                    ClassificacaoHospital(
                        id=item_id,
                        classificacao=item.get("classificacao", "hospital_real"),
                        nome_normalizado=item.get("nome_normalizado"),
                        cidade_inferida=item.get("cidade_inferida"),
                        confianca=item.get("confianca", 0.0),
                    )
                )
        except Exception as e:
            logger.error(
                f"Erro no batch {batch_num} de classificacao",
                extra={"erro": str(e), "batch_ids": [h["id"] for h in batch[:3]]},
            )
            for h in batch:
                classificacoes.append(
                    ClassificacaoHospital(
                        id=h["id"],
                        classificacao="hospital_real",
                        confianca=0.0,
                        erro=str(e),
                    )
                )

        # Rate limiting entre batches
        if i + tamanho_batch < len(hospitais):
            await asyncio.sleep(0.5)

    logger.info(
        "Classificacao LLM concluida",
        extra={
            "total": len(classificacoes),
            "tokens_in": tokens_in_total,
            "tokens_out": tokens_out_total,
        },
    )
    return classificacoes, tokens_in_total, tokens_out_total


async def aplicar_classificacoes(classificacoes: list[ClassificacaoHospital]) -> dict:
    """
    Aplica classificacoes LLM ao banco de dados.

    Returns:
        Dict com contadores: reais, invalidos, lixo, deletados, flagged, nomes_atualizados, cidades_inferidas
    """
    contadores = {
        "reais": 0,
        "invalidos": 0,
        "lixo": 0,
        "deletados": 0,
        "flagged": 0,
        "nomes_atualizados": 0,
        "cidades_inferidas": 0,
    }

    for c in classificacoes:
        if c.erro:
            continue

        try:
            if c.classificacao == "hospital_real":
                contadores["reais"] += 1
                update_data: dict = {
                    "precisa_revisao": False,
                    "revisado_em": datetime.now(UTC).isoformat(),
                    "revisado_por": "llm_haiku_batch",
                }

                if c.nome_normalizado:
                    update_data["nome"] = c.nome_normalizado
                    contadores["nomes_atualizados"] += 1

                if c.cidade_inferida:
                    # So atualizar cidade se estava "Nao informada"
                    current = (
                        supabase.table("hospitais")
                        .select("cidade")
                        .eq("id", c.id)
                        .single()
                        .execute()
                    )
                    if current.data and current.data.get("cidade") == "Não informada":
                        update_data["cidade"] = c.cidade_inferida
                        contadores["cidades_inferidas"] += 1

                supabase.table("hospitais").update(update_data).eq("id", c.id).execute()

            elif c.classificacao in ("generico_invalido", "fragmento_lixo"):
                if c.classificacao == "generico_invalido":
                    contadores["invalidos"] += 1
                else:
                    contadores["lixo"] += 1

                deletado = await deletar_hospital_seguro(c.id)
                if deletado:
                    contadores["deletados"] += 1
                    try:
                        await emit_event(
                            BusinessEvent(
                                event_type=EventType.HOSPITAL_CLEANED,
                                source=EventSource.SYSTEM,
                                hospital_id=c.id,
                                event_props={
                                    "classificacao": c.classificacao,
                                    "confianca": c.confianca,
                                    "revisado_por": "llm_haiku_batch",
                                },
                            )
                        )
                    except Exception:
                        pass
                else:
                    # Tem FKs, marcar para revisao humana
                    contadores["flagged"] += 1
                    supabase.table("hospitais").update(
                        {
                            "revisado_por": "llm_flagged",
                            "revisado_em": datetime.now(UTC).isoformat(),
                        }
                    ).eq("id", c.id).execute()

        except Exception as e:
            logger.warning(
                f"Erro ao aplicar classificacao para {c.id}: {e}",
                extra={"hospital_id": c.id, "classificacao": c.classificacao},
            )

    logger.info("Classificacoes aplicadas", extra=contadores)
    return contadores


# =============================================================================
# Fase 2: Deteccao de Duplicatas
# =============================================================================


async def _buscar_pares_candidatos(threshold: float = 0.5) -> list[dict]:
    """Busca pares de hospitais com similaridade >= threshold via pg_trgm."""
    query = f"""
    SELECT
        a.id as id_a, a.nome as nome_a, a.cidade as cidade_a, a.estado as estado_a,
        b.id as id_b, b.nome as nome_b, b.cidade as cidade_b, b.estado as estado_b,
        similarity(a.nome, b.nome) as sim
    FROM hospitais a
    JOIN hospitais b ON a.id < b.id
    WHERE similarity(a.nome, b.nome) >= {threshold}
    ORDER BY sim DESC
    """

    result = supabase.rpc("exec_sql", {"query": query}).execute()
    if result.data:
        return result.data
    return []


async def _buscar_pares_candidatos_supabase(threshold: float = 0.5) -> list[dict]:
    """Busca pares candidatos via SQL direto no Supabase."""
    from app.services.supabase import supabase as sb

    # Usar query direta via PostgREST nao suporta similarity, usar RPC
    # Fallback: buscar todos os hospitais e calcular localmente nao e viavel
    # Solucao: usar execute_sql via supabase client
    query = f"""
    SELECT
        a.id as id_a, a.nome as nome_a, a.cidade as cidade_a, a.estado as estado_a,
        b.id as id_b, b.nome as nome_b, b.cidade as cidade_b, b.estado as estado_b,
        similarity(a.nome, b.nome) as sim
    FROM hospitais a
    JOIN hospitais b ON a.id < b.id
    WHERE similarity(a.nome, b.nome) >= {threshold}
      AND a.precisa_revisao = false
      AND b.precisa_revisao = false
    ORDER BY sim DESC
    LIMIT 2000
    """

    # Usar rpc para executar SQL raw
    try:
        result = sb.rpc(
            "executar_sql_readonly",
            {"p_query": query},
        ).execute()
        if result.data:
            return result.data
    except Exception:
        pass

    return []


async def buscar_pares_candidatos_via_rpc(threshold: float = 0.5) -> list[dict]:
    """
    Busca pares candidatos a merge usando pg_trgm similarity.

    Cria RPC temporaria se necessario, ou usa query direta.
    Como fallback, busca hospitais e filtra localmente.
    """
    # Tentar usar a funcao SQL que ja existe ou executar direto
    # A forma mais confiavel e via postgrest rpc
    try:
        result = supabase.rpc(
            "buscar_pares_hospitais_similares",
            {"p_threshold": threshold},
        ).execute()
        if result.data:
            return result.data
    except Exception as e:
        logger.debug(f"RPC buscar_pares_hospitais_similares nao disponivel: {e}")

    # Fallback: buscar todos hospitais revisados e calcular similaridade localmente
    logger.info("Usando fallback local para busca de pares similares")
    return await _calcular_pares_localmente(threshold)


async def _calcular_pares_localmente(threshold: float = 0.5) -> list[dict]:
    """Calcula pares similares localmente usando SequenceMatcher."""
    from difflib import SequenceMatcher

    result = (
        supabase.table("hospitais")
        .select("id, nome, cidade, estado")
        .eq("precisa_revisao", False)
        .execute()
    )

    hospitais = result.data or []
    if len(hospitais) < 2:
        return []

    pares = []
    for i in range(len(hospitais)):
        for j in range(i + 1, len(hospitais)):
            a = hospitais[i]
            b = hospitais[j]
            sim = SequenceMatcher(None, a["nome"].lower(), b["nome"].lower()).ratio()
            if sim >= threshold:
                pares.append(
                    {
                        "id_a": a["id"],
                        "nome_a": a["nome"],
                        "cidade_a": a.get("cidade", ""),
                        "estado_a": a.get("estado", ""),
                        "id_b": b["id"],
                        "nome_b": b["nome"],
                        "cidade_b": b.get("cidade", ""),
                        "estado_b": b.get("estado", ""),
                        "sim": round(sim, 3),
                    }
                )

    pares.sort(key=lambda p: p["sim"], reverse=True)
    return pares[:2000]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
async def _chamar_llm_merge(
    client: anthropic.AsyncAnthropic, pares_texto: str
) -> tuple[list[dict], int, int]:
    """Chama LLM para analisar pares candidatos a merge."""
    prompt = PROMPT_DETECCAO_DUPLICATAS.format(lista_pares=pares_texto)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_MERGE,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = response.content[0].text.strip()
    resultado = _extrair_json_lista(texto)

    return resultado, response.usage.input_tokens, response.usage.output_tokens


async def detectar_duplicatas_llm(
    threshold: float = 0.5, tamanho_batch: int = 20
) -> tuple[list[DecisaoMerge], int, int]:
    """
    Detecta duplicatas semanticas usando LLM.

    Args:
        threshold: Similaridade minima pg_trgm para considerar par
        tamanho_batch: Pares por chamada LLM

    Returns:
        Tuple (decisoes, tokens_input_total, tokens_output_total)
    """
    pares = await buscar_pares_candidatos_via_rpc(threshold)

    if not pares:
        logger.info("Nenhum par candidato a merge encontrado")
        return [], 0, 0

    logger.info(
        "Iniciando deteccao de duplicatas LLM",
        extra={"total_pares": len(pares), "tamanho_batch": tamanho_batch},
    )

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    decisoes: list[DecisaoMerge] = []
    tokens_in_total = 0
    tokens_out_total = 0

    for i in range(0, len(pares), tamanho_batch):
        batch = pares[i : i + tamanho_batch]
        batch_num = i // tamanho_batch + 1
        total_batches = (len(pares) + tamanho_batch - 1) // tamanho_batch

        logger.info(
            f"Merge batch {batch_num}/{total_batches}",
            extra={"batch_size": len(batch)},
        )

        # Formatar pares para prompt
        pares_texto = "\n\n".join(
            _formatar_par_para_prompt(
                par_id=idx + 1,
                a={
                    "id": p["id_a"],
                    "nome": p["nome_a"],
                    "cidade": p.get("cidade_a", "?"),
                    "estado": p.get("estado_a", "?"),
                },
                b={
                    "id": p["id_b"],
                    "nome": p["nome_b"],
                    "cidade": p.get("cidade_b", "?"),
                    "estado": p.get("estado_b", "?"),
                },
                sim=p.get("sim", 0.5),
            )
            for idx, p in enumerate(batch)
        )

        try:
            resultados, tokens_in, tokens_out = await _chamar_llm_merge(client, pares_texto)
            tokens_in_total += tokens_in
            tokens_out_total += tokens_out

            for item in resultados:
                par_idx = item.get("par_id", 0) - 1
                if 0 <= par_idx < len(batch):
                    par = batch[par_idx]
                    decisoes.append(
                        DecisaoMerge(
                            par_id=item.get("par_id", 0),
                            id_a=par["id_a"],
                            id_b=par["id_b"],
                            eh_duplicata=item.get("eh_duplicata", False),
                            hospital_principal=item.get("hospital_principal"),
                            confianca=item.get("confianca", 0.0),
                            motivo=item.get("motivo"),
                        )
                    )
        except Exception as e:
            logger.error(
                f"Erro no batch {batch_num} de merge",
                extra={"erro": str(e)},
            )
            for idx, p in enumerate(batch):
                decisoes.append(
                    DecisaoMerge(
                        par_id=idx + 1,
                        id_a=p["id_a"],
                        id_b=p["id_b"],
                        erro=str(e),
                    )
                )

        if i + tamanho_batch < len(pares):
            await asyncio.sleep(0.5)

    logger.info(
        "Deteccao de duplicatas LLM concluida",
        extra={
            "total_decisoes": len(decisoes),
            "duplicatas": sum(1 for d in decisoes if d.eh_duplicata),
            "tokens_in": tokens_in_total,
            "tokens_out": tokens_out_total,
        },
    )
    return decisoes, tokens_in_total, tokens_out_total


async def executar_merges(decisoes: list[DecisaoMerge], limiar_auto: float = 0.85) -> dict:
    """
    Executa merges com base nas decisoes LLM.

    Args:
        decisoes: Lista de decisoes de merge
        limiar_auto: Confianca minima para auto-merge (>= 0.85)

    Returns:
        Dict com contadores: auto, revisao, skip, erros
    """
    contadores = {"auto": 0, "revisao": 0, "skip": 0, "erros": 0}

    for d in decisoes:
        if d.erro or not d.eh_duplicata:
            contadores["skip"] += 1
            continue

        if d.confianca < 0.60:
            contadores["skip"] += 1
            continue

        if d.confianca >= limiar_auto:
            # Auto-merge
            try:
                principal_id = d.hospital_principal or d.id_a
                duplicado_id = d.id_b if principal_id == d.id_a else d.id_a

                # Safety: verificar contagem de vagas para decidir direcao
                vagas_principal = (
                    supabase.table("vagas")
                    .select("id", count="exact")
                    .eq("hospital_id", principal_id)
                    .execute()
                )
                vagas_duplicado = (
                    supabase.table("vagas")
                    .select("id", count="exact")
                    .eq("hospital_id", duplicado_id)
                    .execute()
                )

                count_principal = vagas_principal.count or 0
                count_duplicado = vagas_duplicado.count or 0

                # Se duplicado tem mais vagas, inverter direcao
                if count_duplicado > count_principal:
                    logger.info(
                        "Invertendo direcao de merge (duplicado tem mais vagas)",
                        extra={
                            "principal_original": principal_id,
                            "duplicado_original": duplicado_id,
                            "vagas_principal": count_principal,
                            "vagas_duplicado": count_duplicado,
                        },
                    )
                    principal_id, duplicado_id = duplicado_id, principal_id

                resultado = await mesclar_hospitais(
                    principal_id=principal_id,
                    duplicado_id=duplicado_id,
                    executado_por="llm_batch",
                )

                if resultado is not None:
                    contadores["auto"] += 1
                    logger.info(
                        "Auto-merge executado",
                        extra={
                            "principal_id": principal_id,
                            "duplicado_id": duplicado_id,
                            "confianca": d.confianca,
                            "motivo": d.motivo,
                        },
                    )
                else:
                    contadores["erros"] += 1

                # Rate limiting entre merges
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(
                    f"Erro ao executar merge: {e}",
                    extra={"id_a": d.id_a, "id_b": d.id_b},
                )
                contadores["erros"] += 1
        else:
            # 0.60 <= confianca < 0.85: log para revisao humana
            contadores["revisao"] += 1
            logger.info(
                "Par flagged para revisao humana",
                extra={
                    "id_a": d.id_a,
                    "id_b": d.id_b,
                    "confianca": d.confianca,
                    "motivo": d.motivo,
                },
            )

    logger.info("Merges executados", extra=contadores)
    return contadores


# =============================================================================
# Orquestrador
# =============================================================================


async def executar_revisao_llm_completa() -> ResultadoRevisaoLLM:
    """
    Executa revisao LLM completa: classificacao + deteccao de duplicatas.

    Returns:
        ResultadoRevisaoLLM com todos os contadores
    """
    resultado = ResultadoRevisaoLLM()

    # === Fase 1: Classificacao ===
    logger.info("=== Fase 1: Classificacao de hospitais ===")

    try:
        classificacoes, tokens_in, tokens_out = await classificar_hospitais_llm()
        resultado.tokens_input += tokens_in
        resultado.tokens_output += tokens_out
        resultado.hospitais_classificados = len(classificacoes)

        contadores = await aplicar_classificacoes(classificacoes)
        resultado.hospitais_reais = contadores["reais"]
        resultado.genericos_invalidos = contadores["invalidos"]
        resultado.fragmentos_lixo = contadores["lixo"]
        resultado.deletados = contadores["deletados"]
        resultado.flagged_revisao = contadores["flagged"]
        resultado.nomes_atualizados = contadores["nomes_atualizados"]
        resultado.cidades_inferidas = contadores["cidades_inferidas"]
    except Exception as e:
        logger.error(f"Erro na fase 1 (classificacao): {e}")
        resultado.erros.append(f"fase1: {e}")

    # === Fase 2: Deteccao de duplicatas ===
    logger.info("=== Fase 2: Deteccao de duplicatas ===")

    try:
        decisoes, tokens_in, tokens_out = await detectar_duplicatas_llm()
        resultado.tokens_input += tokens_in
        resultado.tokens_output += tokens_out
        resultado.pares_analisados = len(decisoes)

        contadores_merge = await executar_merges(decisoes)
        resultado.merges_auto = contadores_merge["auto"]
        resultado.merges_revisao = contadores_merge["revisao"]
        resultado.merges_skip = contadores_merge["skip"]
    except Exception as e:
        logger.error(f"Erro na fase 2 (duplicatas): {e}")
        resultado.erros.append(f"fase2: {e}")

    logger.info(
        "Revisao LLM completa",
        extra={
            "classificados": resultado.hospitais_classificados,
            "reais": resultado.hospitais_reais,
            "deletados": resultado.deletados,
            "merges_auto": resultado.merges_auto,
            "merges_revisao": resultado.merges_revisao,
            "tokens_in": resultado.tokens_input,
            "tokens_out": resultado.tokens_output,
        },
    )

    return resultado
