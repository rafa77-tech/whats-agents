"""
Script para analisar resultados do piloto.
"""
import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.supabase import supabase


async def analisar_piloto() -> dict:
    """Gera análise completa do piloto."""
    # Buscar todos os dados do piloto
    medicos_resp = (
        supabase.table("clientes")
        .select("*")
        .contains("tags", ["piloto_v1"])
        .execute()
    )

    medicos_piloto = medicos_resp.data or []

    if not medicos_piloto:
        return {
            "erro": "Nenhum médico do piloto encontrado"
        }

    medico_ids = [m["id"] for m in medicos_piloto]

    # Buscar conversas
    conversas_resp = (
        supabase.table("conversations")
        .select("*, metricas_conversa(*), avaliacoes_qualidade(*)")
        .in_("cliente_id", medico_ids)
        .execute()
    )

    conversas = conversas_resp.data or []

    # Buscar handoffs
    conversa_ids = [c["id"] for c in conversas]
    handoffs_resp = (
        supabase.table("handoffs")
        .select("*")
        .in_("conversation_id", conversa_ids)
        .execute()
    ) if conversa_ids else {"data": []}

    handoffs = handoffs_resp.data or []

    # Calcular métricas
    primeiro_contato_em = None
    for m in medicos_piloto:
        if m.get("primeiro_contato_em"):
            if not primeiro_contato_em or m["primeiro_contato_em"] < primeiro_contato_em:
                primeiro_contato_em = m["primeiro_contato_em"]

    analise = {
        "periodo": {
            "inicio": primeiro_contato_em,
            "fim": datetime.now().isoformat()
        },
        "envios": {
            "total": len(medicos_piloto),
            "contactados": len([m for m in medicos_piloto if m.get("primeiro_contato_em")])
        },
        "respostas": {
            "total": len(set(c["cliente_id"] for c in conversas)),
            "taxa": len(set(c["cliente_id"] for c in conversas)) / len(medicos_piloto) if medicos_piloto else 0
        },
        "conversas": {
            "total": len(conversas),
            "ativas": len([c for c in conversas if c.get("status") == "active"]),
            "encerradas": len([c for c in conversas if c.get("status") == "encerrada"])
        },
        "handoffs": {
            "total": len(handoffs),
            "taxa": len(handoffs) / len(conversas) if conversas else 0,
            "por_tipo": {}
        },
        "qualidade": {
            "score_medio": 0,
            "avaliacoes_auto": 0,
            "avaliacoes_gestor": 0
        }
    }

    # Agrupar handoffs por tipo
    for h in handoffs:
        tipo = h.get("trigger_type", "desconhecido")
        analise["handoffs"]["por_tipo"][tipo] = analise["handoffs"]["por_tipo"].get(tipo, 0) + 1

    # Calcular score médio
    scores = []
    for c in conversas:
        avaliacoes = c.get("avaliacoes_qualidade") or []
        if isinstance(avaliacoes, list):
            for av in avaliacoes:
                if isinstance(av, dict) and av.get("score_geral"):
                    scores.append(av["score_geral"])
                    if av.get("avaliador") == "auto":
                        analise["qualidade"]["avaliacoes_auto"] += 1
                    else:
                        analise["qualidade"]["avaliacoes_gestor"] += 1

    if scores:
        analise["qualidade"]["score_medio"] = sum(scores) / len(scores)

    return analise


def formatar_relatorio(analise: dict) -> str:
    """Formata análise em relatório legível."""
    if "erro" in analise:
        return f"# Erro\n\n{analise['erro']}"

    periodo_inicio = analise['periodo']['inicio'] or "N/A"
    periodo_fim = analise['periodo']['fim'] or "N/A"

    relatorio = f"""
# Relatório do Piloto Júlia V1

## Período
- Início: {periodo_inicio}
- Fim: {periodo_fim}

## Envios
- Total de médicos: {analise['envios']['total']}
- Contactados: {analise['envios']['contactados']}

## Respostas
- Médicos que responderam: {analise['respostas']['total']}
- **Taxa de resposta: {analise['respostas']['taxa']*100:.1f}%**

## Conversas
- Total: {analise['conversas']['total']}
- Ativas: {analise['conversas']['ativas']}
- Encerradas: {analise['conversas']['encerradas']}

## Handoffs
- Total: {analise['handoffs']['total']}
- **Taxa de handoff: {analise['handoffs']['taxa']*100:.1f}%**
- Por tipo:
"""
    for tipo, qtd in analise['handoffs']['por_tipo'].items():
        relatorio += f"  - {tipo}: {qtd}\n"

    relatorio += f"""
## Qualidade
- **Score médio: {analise['qualidade']['score_medio']:.1f}/10**
- Avaliações automáticas: {analise['qualidade']['avaliacoes_auto']}
- Avaliações do gestor: {analise['qualidade']['avaliacoes_gestor']}

## Conclusões

### Métricas vs Metas
| Métrica | Resultado | Meta | Status |
|---------|-----------|------|--------|
| Taxa de resposta | {analise['respostas']['taxa']*100:.1f}% | > 30% | {'✅' if analise['respostas']['taxa'] > 0.3 else '❌'} |
| Taxa de handoff | {analise['handoffs']['taxa']*100:.1f}% | < 10% | {'✅' if analise['handoffs']['taxa'] < 0.1 else '❌'} |
| Score de qualidade | {analise['qualidade']['score_medio']:.1f} | > 7 | {'✅' if analise['qualidade']['score_medio'] > 7 else '❌'} |

### Próximos Passos
1. [Baseado nos resultados]
2. [Ajustes necessários]
3. [Expansão ou iteração]
"""

    return relatorio


async def exportar_dados_piloto(formato: str = "json") -> str:
    """Exporta dados do piloto para análise externa."""
    analise = await analisar_piloto()

    if "erro" in analise:
        return analise["erro"]

    # Adicionar dados brutos
    medicos_resp = (
        supabase.table("clientes")
        .select("id, primeiro_nome, especialidade_id, primeiro_contato_em, status")
        .contains("tags", ["piloto_v1"])
        .execute()
    )

    medicos_piloto = medicos_resp.data or []

    analise["dados_brutos"] = {
        "medicos": medicos_piloto
    }

    if formato == "json":
        return json.dumps(analise, indent=2, ensure_ascii=False)
    elif formato == "markdown":
        return formatar_relatorio(analise)

    return str(analise)


async def main():
    print("Analisando piloto...")
    analise = await analisar_piloto()

    if "erro" in analise:
        print(f"❌ {analise['erro']}")
        return

    # Exibir relatório
    relatorio = formatar_relatorio(analise)
    print(relatorio)

    # Salvar
    try:
        with open("relatorio_piloto_v1.md", "w", encoding="utf-8") as f:
            f.write(relatorio)
        print("\n✅ Relatório salvo em: relatorio_piloto_v1.md")
    except Exception as e:
        print(f"\n⚠️  Erro ao salvar relatório: {e}")

    # Exportar JSON
    try:
        dados = await exportar_dados_piloto("json")
        with open("dados_piloto_v1.json", "w", encoding="utf-8") as f:
            f.write(dados)
        print("✅ Dados exportados em: dados_piloto_v1.json")
    except Exception as e:
        print(f"⚠️  Erro ao exportar JSON: {e}")


if __name__ == "__main__":
    asyncio.run(main())

