# ÉPICO 04: Documentação de Operação

## Contexto

O NFR Assessment identificou que não há documentação de:
- Processo de rotação de secrets
- Procedimentos de manutenção do banco (VACUUM, ANALYZE)

Este épico adiciona documentação essencial para operação do sistema.

## Escopo

- **Incluído**:
  - Documentação de secrets rotation no runbook
  - Procedimentos de manutenção do banco
  - Atualização do NFR Assessment no CLAUDE.md

- **Excluído**:
  - Automação de rotação de secrets
  - Jobs automáticos de VACUUM

---

## Tarefa T04.1: Documentação de Secrets Rotation

### Objetivo

Adicionar seção de rotação de secrets ao runbook de operação.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Modificar | `docs/operacao/runbook.md` |

### Implementação

Adicionar a seguinte seção ao runbook:

```markdown
---

## Rotação de Secrets

### Frequência Recomendada

| Secret | Frequência | Provider | URL |
|--------|------------|----------|-----|
| `ANTHROPIC_API_KEY` | 90 dias | Anthropic | https://console.anthropic.com |
| `SUPABASE_SERVICE_KEY` | 90 dias | Supabase | https://app.supabase.com |
| `EVOLUTION_API_KEY` | 90 dias | Self-hosted | Admin do Evolution |
| `SLACK_BOT_TOKEN` | Quando comprometido | Slack | https://api.slack.com/apps |
| `VOYAGE_API_KEY` | 90 dias | Voyage AI | https://dash.voyageai.com |
| `GOOGLE_SERVICE_ACCOUNT` | 180 dias | Google Cloud | https://console.cloud.google.com |

### Processo de Rotação

**Pré-requisitos:**
- Acesso ao Railway Dashboard
- Credenciais dos providers

**Passos:**

1. **Gerar nova key no provider**
   - Acessar console do provider
   - Criar nova API key
   - Copiar a key (só aparece uma vez)

2. **Atualizar no Railway**
   ```bash
   # Via CLI
   railway variables set NOME_DA_VARIAVEL="nova-key"

   # Ou via Dashboard:
   # Railway → Service → Variables → Edit
   ```

3. **Aguardar deploy**
   - Railway faz deploy automático quando variável muda
   - Monitorar logs durante o deploy

4. **Validar funcionamento**
   ```bash
   # Verificar health
   curl https://whats-agents-production.up.railway.app/health/deep

   # Verificar logs por erros de autenticação
   railway logs -n 50 | grep -i "auth\|key\|unauthorized"
   ```

5. **Revogar key antiga**
   - Aguardar 24h de funcionamento estável
   - Voltar ao provider e revogar a key antiga
   - Confirmar que não há erros nos logs

### Troubleshooting

**Erro: "Invalid API Key" após rotação**
- Verificar se a key foi colada corretamente (sem espaços)
- Verificar se o nome da variável está correto
- Fazer redeploy manual: `railway up`

**Erro: "Rate limit exceeded" após rotação**
- Key nova pode ter limite diferente
- Verificar plano/tier no provider

---
```

### Testes Obrigatórios

- [ ] Markdown renderiza corretamente
- [ ] Links estão funcionando
- [ ] Processo está claro e sem ambiguidade

### Definition of Done

- [ ] Seção adicionada ao runbook
- [ ] Revisado por outro membro do time

### Estimativa

30 minutos

---

## Tarefa T04.2: Documentação de Manutenção do Banco

### Objetivo

Adicionar procedimentos de manutenção do PostgreSQL/Supabase.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Modificar | `docs/operacao/runbook.md` |

### Implementação

Adicionar a seguinte seção:

```markdown
---

## Manutenção do Banco de Dados

### Verificação de Saúde

**Executar semanalmente ou após grandes operações:**

```sql
-- 1. Verificar tabelas que precisam VACUUM
SELECT
    relname as tabela,
    n_live_tup as linhas,
    n_dead_tup as linhas_mortas,
    pg_size_pretty(pg_total_relation_size(relid)) as tamanho,
    last_vacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC
LIMIT 10;

-- 2. Verificar índices não utilizados (rodar após 1+ semana de uso)
SELECT
    relname as tabela,
    indexrelname as indice,
    idx_scan as usos,
    pg_size_pretty(pg_relation_size(indexrelid)) as tamanho
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 10;

-- 3. Verificar bloat (espaço desperdiçado)
SELECT
    relname as tabela,
    pg_size_pretty(pg_total_relation_size(relid)) as tamanho_total,
    pg_size_pretty(pg_relation_size(relid)) as tamanho_dados
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
```

### Quando Executar ANALYZE

O Supabase executa autovacuum, mas pode ser necessário ANALYZE manual:

```sql
-- Após importação em massa de dados
ANALYZE nome_da_tabela;

-- Após DELETE de muitas linhas
ANALYZE nome_da_tabela;

-- Para atualizar estatísticas de todas tabelas
ANALYZE;
```

### Quando Executar VACUUM

```sql
-- VACUUM simples (não bloqueia)
VACUUM nome_da_tabela;

-- VACUUM ANALYZE (recomendado)
VACUUM ANALYZE nome_da_tabela;

-- VACUUM FULL (bloqueia, usar com cuidado em prod)
-- Só se houver muito bloat
VACUUM FULL nome_da_tabela;
```

### Tabelas de Alto Volume

Monitorar especialmente:

| Tabela | Volume Esperado | Ação |
|--------|-----------------|------|
| `job_executions` | ~10k/dia | VACUUM semanal |
| `interacoes` | ~1k/dia | VACUUM quinzenal |
| `business_events` | ~5k/dia | VACUUM semanal |
| `mensagens_grupo` | ~2k/dia | VACUUM quinzenal |

### Índices - Boas Práticas

1. **FKs sempre precisam de índice** (PostgreSQL não cria automaticamente)
2. **Verificar uso** antes de remover índice não utilizado
3. **Usar CONCURRENTLY** para criar índices em produção:
   ```sql
   CREATE INDEX CONCURRENTLY idx_nome ON tabela(coluna);
   ```

---
```

### Testes Obrigatórios

- [ ] Queries SQL são válidas
- [ ] Procedimentos são claros

### Definition of Done

- [ ] Seção adicionada ao runbook
- [ ] Queries testadas no banco

### Estimativa

30 minutos

---

## Resumo do Épico

| Tarefa | Estimativa | Risco |
|--------|------------|-------|
| T04.1: Secrets rotation | 30min | Baixo |
| T04.2: Manutenção banco | 30min | Baixo |
| **Total** | **1h** | |

## Ordem de Execução

- T04.1 e T04.2 podem ser feitos em paralelo

## Paralelizável

- Ambas as tarefas são independentes
