# Epic 01 - Integridade & Anomalias

## Objetivo
Criar pagina `/integridade` que expoe todas as funcionalidades de auditoria de dados, anomalias e KPIs de saude do funil.

> **Nota:** Esta pagina e DIFERENTE de `/auditoria` que mostra audit trail de acoes de usuarios.
> `/integridade` mostra saude dos DADOS do sistema (anomalias, violacoes, reconciliacao).

## APIs Disponiveis (Backend Pronto)

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/integridade/auditoria` | GET | Auditoria de cobertura de eventos |
| `/integridade/violacoes` | GET | Violacoes de invariantes do funil |
| `/integridade/reconciliacao` | POST | Reconciliacao DB vs Eventos |
| `/integridade/anomalias` | GET | Lista anomalias (filtros: resolvidas, tipo, severidade) |
| `/integridade/anomalias/recorrentes` | GET | Anomalias recorrentes |
| `/integridade/anomalias/{id}/resolver` | POST | Resolve anomalia com notas |
| `/integridade/kpis` | GET | Resumo dos 3 KPIs principais |
| `/integridade/kpis/conversion` | GET | Taxas de conversao |
| `/integridade/kpis/time-to-fill` | GET | Breakdown de tempos |
| `/integridade/kpis/health` | GET | Health Score composto |

## Stories

---

### S43.E1.1 - Pagina Integridade (Visao Geral)

**Objetivo:** Criar pagina principal com overview de saude dos dados.

**Layout:**
```
+------------------------------------------+
| Integridade dos Dados           [Refresh] |
+------------------------------------------+
| [Health Score] [Conversion] [Time-to-Fill]|
|    85/100        72%          4.2h        |
+------------------------------------------+
| Anomalias Abertas: 12  |  Violacoes: 3   |
| [Ver todas]            |  [Ver todas]     |
+------------------------------------------+
| Ultima Auditoria: 2h atras  [Executar]   |
+------------------------------------------+
```

**Tarefas:**
1. Criar rota `/integridade` no dashboard
2. Criar componente `IntegrityOverview` com 3 KPI cards
3. Criar componente `AnomalyCounter` com contagem e link
4. Criar componente `AuditStatus` com ultima execucao
5. Botao para executar auditoria manual

**API Calls:**
- `GET /integridade/kpis` - KPIs principais
- `GET /integridade/anomalias?resolvidas=false&limit=1` - Contagem
- `GET /integridade/auditoria` - Status da auditoria

**DoD:**
- [ ] Pagina criada e acessivel via sidebar
- [ ] 3 KPI cards com dados reais
- [ ] Contadores de anomalias e violacoes
- [ ] Botao de auditoria manual funcional
- [ ] Loading states e error handling
- [ ] Testes unitarios

---

### S43.E1.2 - Lista de Anomalias com Filtros

**Objetivo:** Tabela paginada de anomalias com filtros e acoes.

**Layout:**
```
+--------------------------------------------------+
| Anomalias                          [Exportar CSV] |
+--------------------------------------------------+
| Filtros: [Status v] [Tipo v] [Severidade v]      |
+--------------------------------------------------+
| # | Tipo     | Entidade | Severidade | Criada    |
|---|----------|----------|------------|-----------|
| 1 | orphan   | vaga_123 | high       | 2h atras  |
| 2 | mismatch | conv_456 | medium     | 5h atras  |
+--------------------------------------------------+
| Mostrando 1-20 de 45       [<] [1] [2] [3] [>]   |
+--------------------------------------------------+
```

**Tarefas:**
1. Criar componente `AnomalyList` com tabela
2. Implementar filtros (status, tipo, severidade)
3. Paginacao com 20 itens por pagina
4. Exportacao CSV simples
5. Link para detalhe da anomalia

**API Calls:**
- `GET /integridade/anomalias?resolvidas=false&tipo=X&severidade=Y&limit=20&offset=0`

**DoD:**
- [ ] Tabela com dados reais
- [ ] Filtros funcionando
- [ ] Paginacao funcional
- [ ] Exportacao CSV
- [ ] Testes unitarios

---

### S43.E1.3 - Detalhe e Resolucao de Anomalia

**Objetivo:** Modal/pagina de detalhe com acao de resolver.

**Layout:**
```
+------------------------------------------+
| Anomalia #123                    [Fechar] |
+------------------------------------------+
| Tipo: orphan_record                       |
| Entidade: vaga_id = 456                   |
| Severidade: HIGH                          |
| Detectada: 15/01/2026 14:30               |
| Ocorrencias: 3 (recorrente)               |
+------------------------------------------+
| Detalhes:                                 |
| Vaga sem cliente associado apos reserva   |
+------------------------------------------+
| Resolver:                                 |
| [Notas de resolucao...              ]     |
| [Resolver como falso positivo]            |
| [Resolver como corrigido]                 |
+------------------------------------------+
```

**Tarefas:**
1. Criar modal `AnomalyDetail`
2. Exibir todos os campos da anomalia
3. Form para adicionar notas
4. Botoes de resolucao com confirmacao
5. Feedback de sucesso/erro

**API Calls:**
- `GET /integridade/anomalias/{id}` (se disponivel) ou usar dados da lista
- `POST /integridade/anomalias/{id}/resolver` com notas

**DoD:**
- [ ] Modal com detalhes completos
- [ ] Form de resolucao funcional
- [ ] Confirmacao antes de resolver
- [ ] Atualiza lista apos resolver
- [ ] Testes unitarios

---

### S43.E1.4 - KPIs Detalhados e Health Score

**Objetivo:** Pagina/aba com breakdown detalhado dos KPIs.

**Layout:**
```
+------------------------------------------+
| Health Score: 85/100                      |
+------------------------------------------+
| Componentes:                              |
| - Pressao de Vagas:    90 [====----]     |
| - Friccao no Funil:    75 [===-----]     |
| - Qualidade Respostas: 88 [====----]     |
| - Score de Spam:       87 [====----]     |
+------------------------------------------+
| Recomendacoes:                            |
| ! Aumentar capacidade de chips            |
| ! Revisar taxa de conversao em reserva    |
+------------------------------------------+
```

**Tarefas:**
1. Criar componente `HealthScoreDetail`
2. Barras de progresso para cada componente
3. Exibir recomendacoes da API
4. Graficos de conversao por hospital/especialidade
5. Breakdown de Time-to-Fill

**API Calls:**
- `GET /integridade/kpis/health` - Health Score com componentes
- `GET /integridade/kpis/conversion` - Taxas segmentadas
- `GET /integridade/kpis/time-to-fill` - Breakdown de tempos

**DoD:**
- [ ] Health Score com componentes visuais
- [ ] Recomendacoes exibidas
- [ ] Graficos de conversao
- [ ] Breakdown de tempos
- [ ] Testes unitarios

---

## Navegacao

Adicionar na sidebar:
```
Operacao
├── Dashboard
├── Monitor
├── Integridade  <- NOVO
└── Health Center
```

## Componentes Reutilizaveis a Criar

1. `KpiCard` - Card de KPI com valor, tendencia e icone
2. `SeverityBadge` - Badge colorido por severidade
3. `AnomalyTypeBadge` - Badge por tipo de anomalia
4. `ProgressBar` - Barra de progresso com label

## Consideracoes Tecnicas

- Usar SWR ou React Query para cache e revalidacao
- Polling a cada 60s na pagina principal
- Virtualizacao se lista > 100 items
- Skeleton loading para todos os componentes
