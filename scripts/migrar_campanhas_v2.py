"""
Script de migração de campanhas para novo formato.

Este script:
1. Analisa campanhas existentes
2. Infere tipo baseado em nome/corpo
3. Preenche novos campos
4. Registra migração

Uso:
    python scripts/migrar_campanhas_v2.py --dry-run  # Simula
    python scripts/migrar_campanhas_v2.py            # Executa
"""
import asyncio
import argparse
from datetime import datetime
from enum import Enum
from app.services.supabase import supabase
from app.core.logging import get_logger

logger = get_logger(__name__)


class TipoCampanha(str, Enum):
    DISCOVERY = "discovery"
    OFERTA = "oferta"
    FOLLOWUP = "followup"
    FEEDBACK = "feedback"
    REATIVACAO = "reativacao"


# Mapeamento de palavras-chave para tipos
KEYWORDS_TIPO = {
    TipoCampanha.DISCOVERY: [
        "discovery", "prospecção", "prospeccao", "conhecer",
        "apresentar", "novo", "primeira"
    ],
    TipoCampanha.OFERTA: [
        "oferta", "vaga", "plantão", "plantao", "escala",
        "disponível", "disponivel", "urgente"
    ],
    TipoCampanha.FOLLOWUP: [
        "followup", "follow-up", "follow up", "acompanhamento",
        "retorno", "sequência", "sequencia"
    ],
    TipoCampanha.FEEDBACK: [
        "feedback", "avaliação", "avaliacao", "opinião",
        "opiniao", "como foi"
    ],
    TipoCampanha.REATIVACAO: [
        "reativação", "reativacao", "reativar", "retomar",
        "sumiu", "inativo"
    ],
}

# Regras padrão por tipo
REGRAS_PADRAO = {
    TipoCampanha.DISCOVERY: [
        "Nunca mencionar vagas ou oportunidades",
        "Não falar de valores",
        "Foco em conhecer o médico",
        "Perguntar sobre especialidade e preferências",
        "Só ofertar se médico perguntar explicitamente"
    ],
    TipoCampanha.OFERTA: [
        "Apresentar apenas vagas existentes no sistema",
        "Consultar sistema antes de mencionar qualquer vaga",
        "Nunca inventar ou prometer vagas",
        "Respeitar margem de negociação definida"
    ],
    TipoCampanha.FOLLOWUP: [
        "Perguntar como o médico está",
        "Manter conversa leve e natural",
        "Só ofertar se médico perguntar"
    ],
    TipoCampanha.FEEDBACK: [
        "Perguntar como foi o plantão",
        "Coletar elogios e reclamações",
        "Não ofertar novo plantão proativamente"
    ],
    TipoCampanha.REATIVACAO: [
        "Reestabelecer contato de forma natural",
        "Perguntar se ainda tem interesse em plantões",
        "Não ofertar imediatamente",
        "Esperar confirmação de interesse"
    ],
}


def inferir_tipo(campanha: dict) -> TipoCampanha:
    """
    Infere o tipo da campanha baseado em nome e corpo.

    Args:
        campanha: Dados da campanha

    Returns:
        TipoCampanha inferido
    """
    # Texto para análise (nome_template + corpo + tipo_campanha)
    texto = (
        (campanha.get("nome_template") or "") + " " +
        (campanha.get("corpo") or "") + " " +
        (campanha.get("tipo_campanha") or "")
    ).lower()

    # Contar matches por tipo
    scores = {}
    for tipo, keywords in KEYWORDS_TIPO.items():
        score = sum(1 for kw in keywords if kw in texto)
        if score > 0:
            scores[tipo] = score

    # Retornar tipo com maior score, ou discovery como padrão
    if scores:
        return max(scores, key=scores.get)

    return TipoCampanha.DISCOVERY


def gerar_objetivo(campanha: dict, tipo: TipoCampanha) -> str:
    """
    Gera objetivo em linguagem natural.

    Args:
        campanha: Dados da campanha
        tipo: Tipo inferido

    Returns:
        Objetivo em texto
    """
    nome = campanha.get("nome_template", "")

    objetivos = {
        TipoCampanha.DISCOVERY: "Conhecer médicos e entender suas preferências",
        TipoCampanha.OFERTA: "Ofertar vagas disponíveis",
        TipoCampanha.FOLLOWUP: "Manter relacionamento ativo com médicos",
        TipoCampanha.FEEDBACK: "Coletar feedback sobre plantões realizados",
        TipoCampanha.REATIVACAO: "Retomar contato com médicos inativos",
    }

    base = objetivos.get(tipo, "")

    # Tentar extrair contexto do nome
    if "cardio" in nome.lower():
        base += " de cardiologia"
    elif "anestesi" in nome.lower():
        base += " de anestesiologia"

    return base


async def migrar_campanha(campanha: dict, dry_run: bool = True) -> dict:
    """
    Migra uma campanha para o novo formato.

    Args:
        campanha: Dados da campanha
        dry_run: Se True, não salva no banco

    Returns:
        Resultado da migração
    """
    campanha_id = campanha["id"]
    nome = campanha.get("nome_template", "Sem nome")

    # Verificar se já foi migrada
    if campanha.get("objetivo"):
        return {
            "id": campanha_id,
            "nome": nome,
            "status": "ja_migrada",
            "tipo": campanha.get("tipo_campanha")
        }

    # Inferir tipo
    tipo = inferir_tipo(campanha)

    # Gerar dados novos
    objetivo = gerar_objetivo(campanha, tipo)
    regras = REGRAS_PADRAO.get(tipo, [])
    pode_ofertar = tipo == TipoCampanha.OFERTA

    update_data = {
        "tipo_campanha": tipo.value,
        "objetivo": objetivo,
        "regras": regras,
        "pode_ofertar": pode_ofertar,
        "updated_at": datetime.utcnow().isoformat()
    }

    resultado = {
        "id": campanha_id,
        "nome": nome,
        "tipo_anterior": campanha.get("tipo_campanha"),
        "tipo_novo": tipo.value,
        "objetivo": objetivo,
        "pode_ofertar": pode_ofertar
    }

    if not dry_run:
        supabase.table("campanhas").update(update_data).eq(
            "id", campanha_id
        ).execute()
        resultado["status"] = "migrada"
    else:
        resultado["status"] = "dry_run"

    return resultado


async def migrar_todas(dry_run: bool = True) -> dict:
    """
    Migra todas as campanhas.

    Args:
        dry_run: Se True, não salva no banco

    Returns:
        Estatísticas da migração
    """
    # Buscar todas as campanhas
    resultado = supabase.table("campanhas").select("*").execute()
    campanhas = resultado.data or []

    stats = {
        "total": len(campanhas),
        "migradas": 0,
        "ja_migradas": 0,
        "erros": 0,
        "detalhes": []
    }

    for campanha in campanhas:
        try:
            res = await migrar_campanha(campanha, dry_run)
            stats["detalhes"].append(res)

            if res["status"] == "migrada":
                stats["migradas"] += 1
            elif res["status"] == "ja_migrada":
                stats["ja_migradas"] += 1

        except Exception as e:
            logger.error(f"Erro ao migrar {campanha['id']}: {e}")
            stats["erros"] += 1
            stats["detalhes"].append({
                "id": campanha["id"],
                "status": "erro",
                "erro": str(e)
            })

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Migrar campanhas para novo formato")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem salvar")
    args = parser.parse_args()

    print(f"{'='*50}")
    print("Migração de Campanhas - Sprint 32")
    print(f"Modo: {'DRY RUN (simulação)' if args.dry_run else 'PRODUÇÃO'}")
    print(f"{'='*50}\n")

    if not args.dry_run:
        confirm = input("ATENÇÃO: Isso vai alterar o banco. Continuar? (sim/não): ")
        if confirm.lower() != "sim":
            print("Cancelado.")
            return

    stats = await migrar_todas(dry_run=args.dry_run)

    print(f"\n{'='*50}")
    print("RESULTADO:")
    print(f"  Total de campanhas: {stats['total']}")
    print(f"  Migradas: {stats['migradas']}")
    print(f"  Já migradas: {stats['ja_migradas']}")
    print(f"  Erros: {stats['erros']}")
    print(f"{'='*50}\n")

    # Mostrar detalhes das migradas
    print("Detalhes:")
    for d in stats["detalhes"]:
        if d["status"] != "ja_migrada":
            print(f"  - {d['nome']}: {d.get('tipo_anterior') or 'null'} → {d.get('tipo_novo', '?')}")


if __name__ == "__main__":
    asyncio.run(main())
