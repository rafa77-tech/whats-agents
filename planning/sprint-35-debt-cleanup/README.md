# Sprint 35 - Debt Cleanup: Alinhamento Codigo x Schema

**Inicio:** 2026-01-21
**Duracao estimada:** 3-5 dias
**Dependencias:** Nenhuma (hotfix + refatoracao)
**Status Planejamento:** COMPLETO

---

## Arquivos da Sprint

| Arquivo | Descricao |
|---------|-----------|
| [decisoes-tecnicas.md](./decisoes-tecnicas.md) | Analise de quando codigo se adequa ao banco vs vice-versa |
| [epic-01-hotfix-campanha.md](./epic-01-hotfix-campanha.md) | Hotfix imediato para campanha 16 |
| [epic-02-mapeamento-schema.md](./epic-02-mapeamento-schema.md) | Mapeamento codigo x schema |
| [epic-03-refatorar-repository.md](./epic-03-refatorar-repository.md) | Novo modulo repository |
| [epic-04-refatorar-executor.md](./epic-04-refatorar-executor.md) | Novo modulo executor |
| [epic-05-atualizar-endpoints.md](./epic-05-atualizar-endpoints.md) | Refatorar endpoints de campanha |
| [epic-06-remover-referencias-legadas.md](./epic-06-remover-referencias-legadas.md) | Remover envios_campanha |
| [epic-07-limpeza-codigo-deprecated.md](./epic-07-limpeza-codigo-deprecated.md) | Remover modulos deprecated |
| [epic-08-testes-validacao.md](./epic-08-testes-validacao.md) | Testes unitarios e integracao |
| [epic-09-documentacao.md](./epic-09-documentacao.md) | Atualizar documentacao |

---

## Objetivo

Corrigir incompatibilidades criticas entre codigo e schema do banco, remover codigo legado e alinhar com arquitetura atual de campanhas.

### Por que agora?

A **campanha 16** (Piloto Discovery) foi criada para rodar em 21/01/2026 e esta falhando a cada minuto com erro:

```
[ERRO] Erro ao iniciar campanha 16: 'mensagem_template'
```

O codigo tenta acessar colunas que nao existem, e usa tabelas que foram removidas do banco.

### Problema Raiz

O projeto evoluiu de **Twilio** para **Evolution API**, mas partes do codigo ficaram desatualizadas:

| Componente | Estado Atual |
|------------|--------------|
| Tabela `campanhas` | Schema atualizado |
| Tabela `envios_campanha` | **REMOVIDA** (nao existe mais) |
| Views `campaign_sends` | Funcionando com `fila_mensagens` |
| Codigo em `app/services/campanha.py` | **DESATUALIZADO** (usa schema antigo) |
| Codigo em `app/api/routes/campanhas.py` | **DESATUALIZADO** (usa schema antigo) |

---

## Diagnostico

### Incompatibilidades Criticas

| Arquivo | Linha | Coluna Usada | Coluna Real | Impacto |
|---------|-------|--------------|-------------|---------|
| `app/services/campanha.py` | 294 | `mensagem_template` | **NAO EXISTE** | QUEBRA |
| `app/services/campanha.py` | 303 | `tipo` | `tipo_campanha` | QUEBRA |
| `app/services/campanha.py` | 277 | `config` | `audience_filters` | QUEBRA |
| `app/services/campanha.py` | 310 | `envios_criados` | `enviados` | QUEBRA |
| `app/api/routes/campanhas.py` | 48 | `mensagem_template` | **NAO EXISTE** | QUEBRA |
| `app/api/routes/campanhas.py` | 46 | `nome` | `nome_template` | QUEBRA |

### Tabela `envios_campanha` Removida

O codigo referencia `envios_campanha` em **11 locais**, mas a tabela foi removida do banco.

Locais afetados:
- `app/services/campanha.py:52-395` (9 referencias)
- `app/api/routes/piloto.py:32` (1 referencia)
- `app/services/jobs/campanhas.py:11,64` (2 referencias indiretas)

### Arquitetura Correta (ja implementada no banco)

```
campanhas           Definicao da campanha
    |
    v
fila_mensagens      Envios individuais (com metadata.campanha_id)
    |
    v
campaign_sends      View unificada de envios
    |
    v
campaign_metrics    Metricas agregadas
```

---

## Epicos

| # | Epico | Descricao | Prioridade | Estimativa |
|---|-------|-----------|------------|------------|
| E01 | Hotfix Campanha 16 | Corrigir funcao `criar_envios_campanha` para funcionar | P0 | 2h |
| E02 | Mapeamento Schema | Criar mapeamento codigo-para-schema correto | P0 | 1h |
| E03 | Refatorar Repository | Criar `app/services/campanhas/repository.py` | P1 | 3h |
| E04 | Refatorar Executor | Criar `app/services/campanhas/executor.py` | P1 | 4h |
| E05 | Atualizar Endpoints | Refatorar `app/api/routes/campanhas.py` | P1 | 3h |
| E06 | Remover Referencias Legadas | Eliminar uso de `envios_campanha` | P1 | 2h |
| E07 | Limpeza Codigo Deprecated | Remover modulos wrapper deprecated | P2 | 2h |
| E08 | Testes e Validacao | Testes unitarios e integracao | P1 | 4h |
| E09 | Documentacao | Atualizar docs de arquitetura | P3 | 2h |

**Total estimado:** 23h (~3 dias)

---

## Fluxo Correto de Campanhas (Pos-Refatoracao)

### Criar Campanha

```python
# 1. Inserir na tabela campanhas
campanha = {
    "nome_template": "Piloto Discovery",
    "tipo_campanha": "discovery",
    "corpo": "[DISCOVERY] Usar aberturas dinamicas",  # ou template fixo
    "status": "agendada",
    "agendar_para": "2026-01-21T12:00:00Z",
    "audience_filters": {"regioes": [], "especialidades": [], "quantidade_alvo": 50},
    "pode_ofertar": False,
}
```

### Executar Campanha

```python
# 2. Para cada destinatario:
# 2.1 Gerar mensagem dinamica (para discovery)
mensagens = await obter_abertura(cliente_id, nome)

# 2.2 Enfileirar em fila_mensagens
await fila_service.enfileirar(
    cliente_id=cliente_id,
    conteudo="\n\n".join(mensagens),
    tipo="campanha",
    prioridade=3,
    metadata={"campanha_id": campanha_id}
)

# 3. Atualizar contadores na campanha
UPDATE campanhas SET enviados = enviados + 1 WHERE id = campanha_id
```

### Metricas

```python
# 4. Usar views existentes
SELECT * FROM campaign_metrics WHERE campaign_id = 16
```

---

## Checklist Final

### Pre-requisitos
- [ ] Acesso ao Supabase (MCP configurado)
- [ ] Branch criada para a sprint

### Entregas
- [ ] E01 - Campanha 16 funcionando
- [ ] E02 - Mapeamento documentado
- [ ] E03 - Repository criado
- [ ] E04 - Executor criado
- [ ] E05 - Endpoints atualizados
- [ ] E06 - Zero referencias a `envios_campanha`
- [ ] E07 - Modulos deprecated removidos
- [ ] E08 - Testes passando (>80% cobertura)
- [ ] E09 - Docs atualizados

### Validacao
- [ ] Criar campanha via API funciona
- [ ] Agendar campanha funciona
- [ ] Executar campanha discovery gera mensagens dinamicas
- [ ] Envios aparecem em `fila_mensagens`
- [ ] Metricas aparecem em `campaign_metrics`
- [ ] Nenhum erro `'mensagem_template'` nos logs

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Quebrar outras funcionalidades | Media | Alto | Testes extensivos antes de merge |
| Campanha 16 continuar falhando | Alta | Alto | E01 como hotfix imediato |
| Regressao em metricas | Media | Medio | Validar views antes/depois |

---

## Metricas de Sucesso

| Metrica | Meta |
|---------|------|
| Campanhas executando sem erro | 100% |
| Testes passando | 100% |
| Referencias a `envios_campanha` | 0 |
| Referencias a `mensagem_template` | 0 |
| Cobertura de testes | >80% |
