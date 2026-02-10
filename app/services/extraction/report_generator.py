"""
Gerador de relatórios Julia para campanhas.

Sprint 54: Insights Dashboard & Relatório Julia.

Gera análise qualitativa usando LLM baseada nos insights extraídos.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.supabase import supabase
from app.services.redis import cache_get, cache_set

logger = logging.getLogger(__name__)

# Cache de 1 hora para relatórios
CACHE_TTL = 3600
CACHE_PREFIX = "report:campaign:"


@dataclass
class MedicoDestaque:
    """Médico em destaque no relatório."""

    cliente_id: str
    nome: str
    interesse: str
    interesse_score: float
    proximo_passo: str
    insight: Optional[str] = None
    especialidade: Optional[str] = None


@dataclass
class ObjecaoAgregada:
    """Objeção agregada."""

    tipo: str
    quantidade: int
    exemplo: Optional[str] = None


@dataclass
class CampaignReportMetrics:
    """Métricas agregadas da campanha."""

    total_respostas: int = 0
    interesse_positivo: int = 0
    interesse_negativo: int = 0
    interesse_neutro: int = 0
    interesse_incerto: int = 0
    taxa_interesse_pct: float = 0.0
    interesse_score_medio: float = 0.0
    total_objecoes: int = 0
    objecao_mais_comum: Optional[str] = None
    prontos_para_vagas: int = 0
    para_followup: int = 0
    para_escalar: int = 0


@dataclass
class CampaignReport:
    """Relatório completo da campanha."""

    campaign_id: int
    campaign_name: str
    generated_at: str
    metrics: CampaignReportMetrics
    medicos_destaque: List[MedicoDestaque] = field(default_factory=list)
    objecoes_encontradas: List[ObjecaoAgregada] = field(default_factory=list)
    preferencias_comuns: List[str] = field(default_factory=list)
    relatorio_julia: str = ""
    tokens_usados: int = 0
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "generated_at": self.generated_at,
            "metrics": {
                "total_respostas": self.metrics.total_respostas,
                "interesse_positivo": self.metrics.interesse_positivo,
                "interesse_negativo": self.metrics.interesse_negativo,
                "interesse_neutro": self.metrics.interesse_neutro,
                "interesse_incerto": self.metrics.interesse_incerto,
                "taxa_interesse_pct": self.metrics.taxa_interesse_pct,
                "interesse_score_medio": self.metrics.interesse_score_medio,
                "total_objecoes": self.metrics.total_objecoes,
                "objecao_mais_comum": self.metrics.objecao_mais_comum,
                "prontos_para_vagas": self.metrics.prontos_para_vagas,
                "para_followup": self.metrics.para_followup,
                "para_escalar": self.metrics.para_escalar,
            },
            "medicos_destaque": [
                {
                    "cliente_id": m.cliente_id,
                    "nome": m.nome,
                    "interesse": m.interesse,
                    "interesse_score": m.interesse_score,
                    "proximo_passo": m.proximo_passo,
                    "insight": m.insight,
                    "especialidade": m.especialidade,
                }
                for m in self.medicos_destaque
            ],
            "objecoes_encontradas": [
                {
                    "tipo": o.tipo,
                    "quantidade": o.quantidade,
                    "exemplo": o.exemplo,
                }
                for o in self.objecoes_encontradas
            ],
            "preferencias_comuns": self.preferencias_comuns,
            "relatorio_julia": self.relatorio_julia,
            "tokens_usados": self.tokens_usados,
            "cached": self.cached,
        }


REPORT_PROMPT = """Voce e Julia, escalista da Revoluna. Analise os dados desta campanha e gere um relatorio executivo.

DADOS DA CAMPANHA:
- Nome: {nome}
- Total de respostas: {total}
- Interesse positivo: {positivo} ({pct_positivo}%)
- Interesse negativo: {negativo}
- Interesse neutro: {neutro}
- Score medio de interesse: {score_medio}/10

MEDICOS COM INTERESSE POSITIVO:
{lista_interessados}

OBJECOES ENCONTRADAS:
{lista_objecoes}

PREFERENCIAS MENCIONADAS:
{preferencias}

MEDICOS PARA ACAO:
- Prontos para vagas: {prontos_vagas}
- Para follow-up: {para_followup}

Gere um relatorio em primeira pessoa, como se voce (Julia) estivesse apresentando para o gestor.

ESTRUTURA OBRIGATORIA (use exatamente estes titulos com emoji):

## ✅ O que funcionou
[Liste 2-4 pontos positivos da campanha]

## ⚠️ Pontos de atencao
[Liste 2-3 problemas ou objecoes identificadas]

## 🎯 Proximos passos sugeridos
[Liste 3-5 acoes concretas numeradas]

## 💡 Insight estrategico
[1-2 paragrafos com analise estrategica e oportunidade identificada]

REGRAS:
- Seja concisa mas informativa
- Use nomes reais dos medicos quando relevante
- Nao invente dados - use apenas o que foi fornecido
- Se nao houver dados suficientes em alguma secao, diga "Dados insuficientes para analise"
- Mantenha tom profissional mas acessivel"""


async def gerar_relatorio_campanha(
    campaign_id: int,
    force_refresh: bool = False,
) -> CampaignReport:
    """
    Gera relatório completo de uma campanha.

    Args:
        campaign_id: ID da campanha
        force_refresh: Se True, ignora cache

    Returns:
        CampaignReport com métricas e relatório Julia
    """
    # 1. Verificar cache
    if not force_refresh:
        cached = await _get_cached_report(campaign_id)
        if cached:
            cached.cached = True
            return cached

    # 2. Buscar dados da campanha
    campanha = await _buscar_campanha(campaign_id)
    if not campanha:
        raise ValueError(f"Campanha {campaign_id} não encontrada")

    # 3. Buscar insights da campanha
    insights = await _buscar_insights_campanha(campaign_id)

    if not insights:
        # Retornar relatório vazio
        return CampaignReport(
            campaign_id=campaign_id,
            campaign_name=campanha.get("nome_template", f"Campanha {campaign_id}"),
            generated_at=datetime.now(timezone.utc).isoformat(),
            metrics=CampaignReportMetrics(),
            relatorio_julia="Ainda não há dados suficientes para gerar um relatório. Aguarde mais respostas.",
        )

    # 4. Agregar métricas
    metrics = _agregar_metricas(insights)

    # 5. Identificar médicos em destaque
    medicos_destaque = await _identificar_medicos_destaque(insights)

    # 6. Agregar objeções
    objecoes = _agregar_objecoes(insights)

    # 7. Extrair preferências comuns
    preferencias = _extrair_preferencias_comuns(insights)

    # 8. Gerar relatório via LLM
    relatorio, tokens = await _gerar_relatorio_llm(
        nome=campanha.get("nome_template", f"Campanha {campaign_id}"),
        metrics=metrics,
        medicos=medicos_destaque,
        objecoes=objecoes,
        preferencias=preferencias,
    )

    # 9. Montar resultado
    report = CampaignReport(
        campaign_id=campaign_id,
        campaign_name=campanha.get("nome_template", f"Campanha {campaign_id}"),
        generated_at=datetime.now(timezone.utc).isoformat(),
        metrics=metrics,
        medicos_destaque=medicos_destaque,
        objecoes_encontradas=objecoes,
        preferencias_comuns=preferencias,
        relatorio_julia=relatorio,
        tokens_usados=tokens,
        cached=False,
    )

    # 10. Salvar no cache
    await _save_report_cache(campaign_id, report)

    logger.info(
        f"[Report] Relatório gerado para campanha {campaign_id}: "
        f"{metrics.total_respostas} respostas, {tokens} tokens"
    )

    return report


async def _get_cached_report(campaign_id: int) -> Optional[CampaignReport]:
    """Busca relatório do cache."""
    try:
        key = f"{CACHE_PREFIX}{campaign_id}"
        data = await cache_get(key)
        if data:
            parsed = json.loads(data)
            return _dict_to_report(parsed)
    except Exception as e:
        logger.warning(f"[Report] Erro ao ler cache: {e}")
    return None


async def _save_report_cache(campaign_id: int, report: CampaignReport) -> None:
    """Salva relatório no cache."""
    try:
        key = f"{CACHE_PREFIX}{campaign_id}"
        data = json.dumps(report.to_dict(), ensure_ascii=False)
        await cache_set(key, data, CACHE_TTL)
    except Exception as e:
        logger.warning(f"[Report] Erro ao salvar cache: {e}")


def _dict_to_report(data: Dict) -> CampaignReport:
    """Converte dicionário para CampaignReport."""
    metrics_data = data.get("metrics", {})
    metrics = CampaignReportMetrics(
        total_respostas=metrics_data.get("total_respostas", 0),
        interesse_positivo=metrics_data.get("interesse_positivo", 0),
        interesse_negativo=metrics_data.get("interesse_negativo", 0),
        interesse_neutro=metrics_data.get("interesse_neutro", 0),
        interesse_incerto=metrics_data.get("interesse_incerto", 0),
        taxa_interesse_pct=metrics_data.get("taxa_interesse_pct", 0.0),
        interesse_score_medio=metrics_data.get("interesse_score_medio", 0.0),
        total_objecoes=metrics_data.get("total_objecoes", 0),
        objecao_mais_comum=metrics_data.get("objecao_mais_comum"),
        prontos_para_vagas=metrics_data.get("prontos_para_vagas", 0),
        para_followup=metrics_data.get("para_followup", 0),
        para_escalar=metrics_data.get("para_escalar", 0),
    )

    medicos = [
        MedicoDestaque(
            cliente_id=m["cliente_id"],
            nome=m["nome"],
            interesse=m["interesse"],
            interesse_score=m["interesse_score"],
            proximo_passo=m["proximo_passo"],
            insight=m.get("insight"),
            especialidade=m.get("especialidade"),
        )
        for m in data.get("medicos_destaque", [])
    ]

    objecoes = [
        ObjecaoAgregada(
            tipo=o["tipo"],
            quantidade=o["quantidade"],
            exemplo=o.get("exemplo"),
        )
        for o in data.get("objecoes_encontradas", [])
    ]

    return CampaignReport(
        campaign_id=data["campaign_id"],
        campaign_name=data["campaign_name"],
        generated_at=data["generated_at"],
        metrics=metrics,
        medicos_destaque=medicos,
        objecoes_encontradas=objecoes,
        preferencias_comuns=data.get("preferencias_comuns", []),
        relatorio_julia=data.get("relatorio_julia", ""),
        tokens_usados=data.get("tokens_usados", 0),
        cached=True,
    )


async def _buscar_campanha(campaign_id: int) -> Optional[Dict]:
    """Busca dados da campanha."""
    try:
        result = (
            supabase.table("campanhas")
            .select("id, nome_template, tipo_campanha, status")
            .eq("id", campaign_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error(f"[Report] Erro ao buscar campanha: {e}")
        return None


async def _buscar_insights_campanha(campaign_id: int) -> List[Dict]:
    """Busca todos os insights de uma campanha."""
    try:
        result = (
            supabase.table("conversation_insights")
            .select(
                """
            id,
            cliente_id,
            interesse,
            interesse_score,
            proximo_passo,
            objecao_tipo,
            objecao_descricao,
            preferencias,
            restricoes,
            especialidade_mencionada,
            regiao_mencionada,
            disponibilidade_mencionada,
            confianca,
            created_at
            """
            )
            .eq("campaign_id", campaign_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"[Report] Erro ao buscar insights: {e}")
        return []


def _agregar_metricas(insights: List[Dict]) -> CampaignReportMetrics:
    """Agrega métricas dos insights."""
    total = len(insights)
    if total == 0:
        return CampaignReportMetrics()

    positivo = sum(1 for i in insights if i.get("interesse") == "positivo")
    negativo = sum(1 for i in insights if i.get("interesse") == "negativo")
    neutro = sum(1 for i in insights if i.get("interesse") == "neutro")
    incerto = sum(1 for i in insights if i.get("interesse") == "incerto")

    scores = [i.get("interesse_score", 0) or 0 for i in insights]
    score_medio = sum(scores) / len(scores) if scores else 0

    objecoes = [i for i in insights if i.get("objecao_tipo")]
    objecao_tipos = [o.get("objecao_tipo") for o in objecoes]
    objecao_mais_comum = max(set(objecao_tipos), key=objecao_tipos.count) if objecao_tipos else None

    prontos = sum(1 for i in insights if i.get("proximo_passo") == "enviar_vagas")
    followup = sum(1 for i in insights if i.get("proximo_passo") == "agendar_followup")
    escalar = sum(1 for i in insights if i.get("proximo_passo") == "escalar_humano")

    return CampaignReportMetrics(
        total_respostas=total,
        interesse_positivo=positivo,
        interesse_negativo=negativo,
        interesse_neutro=neutro,
        interesse_incerto=incerto,
        taxa_interesse_pct=round(positivo / total * 100, 1) if total > 0 else 0,
        interesse_score_medio=round(score_medio * 10, 1),  # Converter para escala 0-10
        total_objecoes=len(objecoes),
        objecao_mais_comum=objecao_mais_comum,
        prontos_para_vagas=prontos,
        para_followup=followup,
        para_escalar=escalar,
    )


async def _identificar_medicos_destaque(insights: List[Dict]) -> List[MedicoDestaque]:
    """Identifica médicos em destaque (interesse positivo ou ação pendente)."""
    # Filtrar médicos com interesse positivo ou prontos para ação
    destaque_ids = set()
    destaque_insights = []

    for i in insights:
        cliente_id = i.get("cliente_id")
        if cliente_id in destaque_ids:
            continue

        interesse = i.get("interesse")
        proximo_passo = i.get("proximo_passo")

        # Incluir se interesse positivo ou ação pendente relevante
        if interesse == "positivo" or proximo_passo in ["enviar_vagas", "agendar_followup"]:
            destaque_ids.add(cliente_id)
            destaque_insights.append(i)

    if not destaque_insights:
        return []

    # Buscar nomes dos clientes
    try:
        clientes_result = (
            supabase.table("clientes")
            .select("id, primeiro_nome, especialidade")
            .in_("id", list(destaque_ids))
            .execute()
        )

        clientes_map = {c["id"]: c for c in (clientes_result.data or [])}
    except Exception as e:
        logger.warning(f"[Report] Erro ao buscar clientes: {e}")
        clientes_map = {}

    # Montar lista de destaque
    medicos = []
    for i in destaque_insights[:10]:  # Limitar a 10
        cliente_id = i.get("cliente_id")
        cliente = clientes_map.get(cliente_id, {})

        # Montar insight baseado nos dados
        insight_parts = []
        if i.get("disponibilidade_mencionada"):
            insight_parts.append(f"Disponibilidade: {i['disponibilidade_mencionada']}")
        if i.get("preferencias"):
            prefs = i["preferencias"][:2]  # Primeiras 2
            insight_parts.append(", ".join(prefs))

        medicos.append(
            MedicoDestaque(
                cliente_id=cliente_id,
                nome=cliente.get("primeiro_nome", "Médico"),
                interesse=i.get("interesse", "incerto"),
                interesse_score=i.get("interesse_score", 0) or 0,
                proximo_passo=i.get("proximo_passo", "sem_acao"),
                insight="; ".join(insight_parts) if insight_parts else None,
                especialidade=cliente.get("especialidade"),
            )
        )

    # Ordenar por score
    medicos.sort(key=lambda m: m.interesse_score, reverse=True)

    return medicos


def _agregar_objecoes(insights: List[Dict]) -> List[ObjecaoAgregada]:
    """Agrega objeções por tipo."""
    objecoes_map: Dict[str, List[str]] = {}

    for i in insights:
        tipo = i.get("objecao_tipo")
        if not tipo:
            continue

        if tipo not in objecoes_map:
            objecoes_map[tipo] = []

        descricao = i.get("objecao_descricao")
        if descricao:
            objecoes_map[tipo].append(descricao)

    result = []
    for tipo, descricoes in objecoes_map.items():
        result.append(
            ObjecaoAgregada(
                tipo=tipo,
                quantidade=len(descricoes),
                exemplo=descricoes[0] if descricoes else None,
            )
        )

    # Ordenar por quantidade
    result.sort(key=lambda o: o.quantidade, reverse=True)

    return result


def _extrair_preferencias_comuns(insights: List[Dict]) -> List[str]:
    """Extrai preferências mais comuns."""
    todas_prefs: Dict[str, int] = {}

    for i in insights:
        prefs = i.get("preferencias") or []
        for p in prefs:
            p_lower = p.lower().strip()
            todas_prefs[p_lower] = todas_prefs.get(p_lower, 0) + 1

        # Incluir disponibilidade como preferência
        disp = i.get("disponibilidade_mencionada")
        if disp:
            todas_prefs[disp.lower()] = todas_prefs.get(disp.lower(), 0) + 1

    # Ordenar por frequência e pegar top 5
    sorted_prefs = sorted(todas_prefs.items(), key=lambda x: x[1], reverse=True)
    return [p[0] for p in sorted_prefs[:5]]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
async def _gerar_relatorio_llm(
    nome: str,
    metrics: CampaignReportMetrics,
    medicos: List[MedicoDestaque],
    objecoes: List[ObjecaoAgregada],
    preferencias: List[str],
) -> tuple[str, int]:
    """Gera relatório usando LLM."""
    # Formatar lista de médicos interessados
    if medicos:
        lista_interessados = "\n".join(
            [
                f"- {m.nome} ({m.especialidade or 'especialidade não informada'}): "
                f"score {m.interesse_score:.1f}, {m.proximo_passo}"
                + (f" - {m.insight}" if m.insight else "")
                for m in medicos
                if m.interesse == "positivo"
            ]
        )
    else:
        lista_interessados = "Nenhum médico com interesse positivo identificado"

    # Formatar lista de objeções
    if objecoes:
        lista_objecoes = "\n".join(
            [
                f"- {o.tipo}: {o.quantidade} ocorrência(s)"
                + (f' (ex: "{o.exemplo}")' if o.exemplo else "")
                for o in objecoes
            ]
        )
    else:
        lista_objecoes = "Nenhuma objeção identificada"

    # Formatar preferências
    prefs_str = (
        ", ".join(preferencias) if preferencias else "Nenhuma preferência comum identificada"
    )

    prompt = REPORT_PROMPT.format(
        nome=nome,
        total=metrics.total_respostas,
        positivo=metrics.interesse_positivo,
        pct_positivo=metrics.taxa_interesse_pct,
        negativo=metrics.interesse_negativo,
        neutro=metrics.interesse_neutro,
        score_medio=metrics.interesse_score_medio,
        lista_interessados=lista_interessados,
        lista_objecoes=lista_objecoes,
        preferencias=prefs_str,
        prontos_vagas=metrics.prontos_para_vagas,
        para_followup=metrics.para_followup,
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=0.7,  # Um pouco de criatividade
            messages=[{"role": "user", "content": prompt}],
        )

        relatorio = response.content[0].text.strip()
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return relatorio, tokens

    except Exception as e:
        logger.error(f"[Report] Erro ao gerar relatório LLM: {e}")
        # Fallback para relatório básico
        return _gerar_relatorio_fallback(metrics), 0


def _gerar_relatorio_fallback(metrics: CampaignReportMetrics) -> str:
    """Gera relatório básico sem LLM."""
    return f"""## ✅ O que funcionou

- {metrics.interesse_positivo} médicos demonstraram interesse positivo
- Taxa de interesse de {metrics.taxa_interesse_pct}%
- {metrics.prontos_para_vagas} médicos prontos para receber vagas

## ⚠️ Pontos de atenção

- {metrics.interesse_negativo} médicos com interesse negativo
- {metrics.total_objecoes} objeções detectadas
- Objeção mais comum: {metrics.objecao_mais_comum or "não identificada"}

## 🎯 Próximos passos sugeridos

1. Enviar vagas para os {metrics.prontos_para_vagas} médicos prontos
2. Agendar follow-up para os {metrics.para_followup} médicos pendentes
3. Analisar objeções para ajustar abordagem

## 💡 Insight estratégico

Dados insuficientes para análise estratégica detalhada.
Considere aguardar mais respostas para obter insights mais precisos."""
