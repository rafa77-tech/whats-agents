# EPICO 6: Monitoramento e Melhorias de Longo Prazo

## Contexto

Apos estabilizar a criacao (Epico 1-2) e limpar dados existentes (Epico 3), este epico estabelece monitoramento continuo, melhora a fonte de dados (prompt LLM), cria automacao de limpeza semanal, e adiciona constraint final de unicidade.

**Objetivo:** Prevenir degradacao futura e melhorar qualidade na fonte.

## Escopo

- **Incluido:**
  - Metricas de qualidade (eventos de hospital)
  - Melhoria do prompt LLM de extracao
  - Job de limpeza semanal
  - UNIQUE constraint em `alias_normalizado`

- **Excluido:**
  - Dashboard de metricas dedicado (usar business_events existente)
  - ML para deteccao de duplicatas
  - Geocoding automatico de enderecos

---

## Tarefa 6.1: Metricas de qualidade de hospitais

### Objetivo

Emitir eventos rastreaveis quando hospitais sao criados, reutilizados, rejeitados ou mesclados.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/hospital_web.py` (447 linhas) |

### Implementacao

Adicionar emissao de eventos em `normalizar_ou_criar_hospital()`:

```python
from app.services.business_events import emitir_evento

# Quando hospital e criado
await emitir_evento(
    tipo="hospital_created",
    hospital_id=hospital_id,
    dados={"nome": nome, "criado_por": "pipeline", "confianca": score}
)

# Quando hospital existente e reutilizado
await emitir_evento(
    tipo="hospital_reused",
    hospital_id=hospital_id,
    dados={"nome": nome, "alias_buscado": texto}
)

# Quando nome e rejeitado pelo validador
await emitir_evento(
    tipo="hospital_rejected",
    dados={"nome_rejeitado": texto, "motivo": validacao.motivo}
)
```

Adicionar na funcao de merge (Epico 3):

```python
# Quando merge e executado
await emitir_evento(
    tipo="hospital_merged",
    hospital_id=principal_id,
    dados={"duplicado_nome": duplicado_nome, **contagens}
)
```

### Testes Obrigatorios

- [ ] Evento `hospital_created` emitido ao criar
- [ ] Evento `hospital_reused` emitido ao reutilizar
- [ ] Evento `hospital_rejected` emitido ao rejeitar
- [ ] Evento `hospital_merged` emitido ao mesclar
- [ ] Eventos registrados em `business_events`

### Definition of Done

- [ ] 4 tipos de evento implementados
- [ ] Eventos nao bloqueiam o fluxo principal (fire-and-forget ou try/except)
- [ ] Dados relevantes incluidos no payload
- [ ] Testes passando

---

## Tarefa 6.2: Melhoria do prompt LLM (v3)

### Objetivo

Adicionar regras no prompt de extracao unificada para reduzir lixo na fonte.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/extrator_v2/extrator_llm.py` (599 linhas) |

### Implementacao

Adicionar no `PROMPT_EXTRACAO_UNIFICADA`, secao de HOSPITAL:

```
HOSPITAL:
- DEVE ser nome de estabelecimento de saude real (hospital, UPA, clinica, pronto socorro, etc.)
- NAO use nomes de pessoas, especialidades medicas, ou fragmentos de texto
- NAO use nomes de empresas nao-medicas (ex: Amazon, Mercado Livre)
- Se nao identificar com certeza o nome do hospital, retorne null
- Prefira o nome completo (ex: "Hospital Municipal Tide Setubal" em vez de "Tide Setubal")
- Se o texto menciona apenas regiao/bairro sem hospital, retorne null
```

### Testes Obrigatorios

- [ ] Prompt contem regras de HOSPITAL
- [ ] Regras sao claras e nao ambiguas

### Definition of Done

- [ ] Regras adicionadas no prompt
- [ ] Nao altera output de extrair vagas/especialidades/datas
- [ ] Testes de extracao existentes continuam passando

---

## Tarefa 6.3: Job de limpeza semanal

### Objetivo

Worker que roda semanalmente para auto-deletar registros com zero FKs que matcham blocklist.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `app/workers/hospital_cleanup_worker.py` |

### Implementacao

```python
import logging
from app.services.grupos.hospital_cleanup import (
    listar_candidatos_limpeza_tier1,
    deletar_hospital_seguro,
)

logger = logging.getLogger(__name__)

async def executar_limpeza_hospitais():
    """Job semanal de limpeza de hospitais lixo."""
    candidatos = await listar_candidatos_limpeza_tier1()

    deletados = 0
    falhas = 0
    for hospital in candidatos:
        try:
            sucesso = await deletar_hospital_seguro(hospital["id"])
            if sucesso:
                deletados += 1
            else:
                falhas += 1  # Adquiriu FK desde a query
        except Exception as e:
            logger.error("Erro ao deletar hospital", extra={
                "hospital_id": hospital["id"],
                "erro": str(e),
            })
            falhas += 1

    logger.info("Limpeza de hospitais concluida", extra={
        "candidatos": len(candidatos),
        "deletados": deletados,
        "falhas": falhas,
    })

    return {"candidatos": len(candidatos), "deletados": deletados, "falhas": falhas}
```

**Registro no scheduler:**
- Frequencia: semanal (domingo, 03:00)
- Timeout: 5 minutos
- Notificacao Slack com contagem (se Slack habilitado)

### Testes Obrigatorios

- [ ] Job lista candidatos tier 1
- [ ] Job deleta apenas hospitais sem FKs
- [ ] Job registra contagens no log
- [ ] Job nao falha com lista vazia
- [ ] Job trata erros individuais sem parar

### Definition of Done

- [ ] Worker criado
- [ ] Registrado no scheduler
- [ ] Logging estruturado
- [ ] Testes passando

---

## Tarefa 6.4: UNIQUE constraint em `alias_normalizado`

### Objetivo

Impedir que o mesmo texto de alias aponte para hospitais diferentes. Belt-and-suspenders com advisory lock do Epico 2.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MIGRATION | Via `apply_migration` |

### Pre-requisito

**Epico 3 deve estar completo.** A limpeza resolve conflitos existentes de aliases duplicados.

### Verificacao pre-migration

```sql
-- Verificar que nao ha conflitos
SELECT alias_normalizado, COUNT(*), array_agg(hospital_id)
FROM hospitais_alias
GROUP BY alias_normalizado
HAVING COUNT(*) > 1;
```

Se houver conflitos, resolver manualmente antes de aplicar.

### Migration

```sql
-- Criar indice unico (CONCURRENTLY para nao lockar)
CREATE UNIQUE INDEX CONCURRENTLY idx_hospitais_alias_normalizado_unique
ON hospitais_alias(alias_normalizado);
```

### Testes Obrigatorios

- [ ] INSERT de alias duplicado -> erro de constraint
- [ ] INSERT de alias unico -> sucesso
- [ ] ON CONFLICT funciona com o novo index

### Definition of Done

- [ ] Zero conflitos existentes (verificado)
- [ ] Index UNIQUE criado
- [ ] Testes passando
- [ ] `buscar_ou_criar_hospital()` (Epico 2) continua funcionando com ON CONFLICT

---

## Dependencias

Epicos 1-3 completos.

## Risco: BAIXO-MEDIO

- **6.1 (Metricas):** Baixo — aditivo, fire-and-forget
- **6.2 (Prompt):** Baixo — mudanca de texto, nao de logica
- **6.3 (Worker):** Baixo — usa funcoes ja testadas do Epico 3
- **6.4 (UNIQUE):** Medio — requer verificacao previa de conflitos, mas CREATE INDEX CONCURRENTLY nao locka
