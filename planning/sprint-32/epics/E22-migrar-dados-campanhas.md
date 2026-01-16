# E22 - Migrar Dados de Campanhas Existentes

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 6 - Limpeza e Polish
**Dependências:** E14 (Reestruturar Campanhas), E21 (Eliminar Template)
**Estimativa:** 2h

---

## Objetivo

Migrar campanhas existentes no banco de dados para o novo formato de **comportamento**, preenchendo os novos campos e limpando campos legados.

---

## Contexto

Após E14 (Reestruturar Campanhas):
- Novos campos: `objetivo`, `regras`, `escopo_vagas`, `pode_ofertar`
- Campos deprecated: `_deprecated_corpo`, `_deprecated_nome_template`

Campanhas existentes precisam ser migradas para usar os novos campos.

---

## Tasks

### T1: Criar script de migração (1h)

**Arquivo:** `scripts/migrar_campanhas_v2.py`

```python
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
    # Texto para análise (nome + corpo deprecated)
    texto = (
        (campanha.get("nome") or "") + " " +
        (campanha.get("_deprecated_corpo") or "") + " " +
        (campanha.get("tipo") or "")
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
    nome = campanha.get("nome", "")

    objetivos = {
        TipoCampanha.DISCOVERY: f"Conhecer médicos e entender suas preferências",
        TipoCampanha.OFERTA: f"Ofertar vagas disponíveis",
        TipoCampanha.FOLLOWUP: f"Manter relacionamento ativo com médicos",
        TipoCampanha.FEEDBACK: f"Coletar feedback sobre plantões realizados",
        TipoCampanha.REATIVACAO: f"Retomar contato com médicos inativos",
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
    nome = campanha.get("nome", "Sem nome")

    # Verificar se já foi migrada
    if campanha.get("objetivo"):
        return {
            "id": campanha_id,
            "nome": nome,
            "status": "ja_migrada",
            "tipo": campanha.get("tipo")
        }

    # Inferir tipo
    tipo = inferir_tipo(campanha)

    # Gerar dados novos
    objetivo = gerar_objetivo(campanha, tipo)
    regras = REGRAS_PADRAO.get(tipo, [])
    pode_ofertar = tipo == TipoCampanha.OFERTA

    update_data = {
        "tipo": tipo.value,
        "objetivo": objetivo,
        "regras": regras,
        "pode_ofertar": pode_ofertar,
        "updated_at": datetime.utcnow().isoformat()
    }

    resultado = {
        "id": campanha_id,
        "nome": nome,
        "tipo_anterior": campanha.get("tipo"),
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
    print(f"Migração de Campanhas - Sprint 32")
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
            print(f"  - {d['nome']}: {d['tipo_anterior'] or 'null'} → {d.get('tipo_novo', '?')}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

### T2: Executar migração em DEV (30min)

1. **Rodar dry-run:**
   ```bash
   python scripts/migrar_campanhas_v2.py --dry-run
   ```

2. **Verificar resultados:**
   - Conferir tipos inferidos
   - Ajustar keywords se necessário

3. **Rodar migração:**
   ```bash
   python scripts/migrar_campanhas_v2.py
   ```

4. **Verificar no banco:**
   ```sql
   SELECT id, nome, tipo, objetivo, pode_ofertar
   FROM campanhas
   ORDER BY updated_at DESC
   LIMIT 20;
   ```

---

### T3: Limpar campos deprecated (30min)

Após migração bem-sucedida, remover campos deprecated.

**Migration:** `remover_campos_deprecated_campanhas`

```sql
-- Migration: remover_campos_deprecated_campanhas
-- Remove campos deprecated após migração bem-sucedida

-- 1. Verificar que todas as campanhas foram migradas
DO $$
DECLARE
    nao_migradas INT;
BEGIN
    SELECT COUNT(*) INTO nao_migradas
    FROM campanhas
    WHERE objetivo IS NULL;

    IF nao_migradas > 0 THEN
        RAISE EXCEPTION 'Existem % campanhas não migradas', nao_migradas;
    END IF;
END $$;

-- 2. Remover colunas deprecated
ALTER TABLE campanhas DROP COLUMN IF EXISTS _deprecated_corpo;
ALTER TABLE campanhas DROP COLUMN IF EXISTS _deprecated_nome_template;

-- 3. Remover view de compatibilidade
DROP VIEW IF EXISTS campanhas_compat;

-- 4. Log
INSERT INTO migration_notes (migration_name, note, created_at)
VALUES (
    'remover_campos_deprecated_campanhas',
    'Campos deprecated removidos após migração completa',
    now()
);
```

---

## DoD (Definition of Done)

### Migração
- [ ] Script de migração criado e testado
- [ ] Dry-run executado em DEV sem erros
- [ ] Migração executada em DEV
- [ ] Verificação manual dos resultados
- [ ] Migração executada em PROD

### Limpeza
- [ ] Campos deprecated removidos (após confirmar migração)
- [ ] View de compatibilidade removida

### Verificação
- [ ] 100% das campanhas com `objetivo` preenchido
- [ ] 100% das campanhas com `regras` preenchido
- [ ] Tipos corretos (discovery não tem pode_ofertar)

### Verificação Manual

1. **Verificar migração:**
   ```sql
   -- Deve retornar 0
   SELECT COUNT(*) FROM campanhas WHERE objetivo IS NULL;
   ```

2. **Verificar tipos:**
   ```sql
   SELECT tipo, COUNT(*),
          SUM(CASE WHEN pode_ofertar THEN 1 ELSE 0 END) as com_oferta
   FROM campanhas
   GROUP BY tipo;
   ```

3. **Verificar discovery:**
   ```sql
   -- Deve retornar 0 (discovery nunca pode ofertar)
   SELECT COUNT(*) FROM campanhas
   WHERE tipo = 'discovery' AND pode_ofertar = true;
   ```

---

## Rollback

Se algo der errado:

```sql
-- Restaurar de backup
-- (campos deprecated ainda existem até serem removidos)

-- Limpar migração parcial
UPDATE campanhas
SET objetivo = NULL, regras = '[]', pode_ofertar = false
WHERE objetivo IS NOT NULL;
```

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Campanhas migradas | 100% |
| Tipos corretamente inferidos | > 90% |
| Erros de migração | 0 |
