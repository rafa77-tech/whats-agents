# Epic 06 - UX & Consistencia

## Objetivo
Melhorar a experiencia do usuario nas paginas existentes, padronizar comportamentos e garantir consistencia entre frontend e backend.

## Stories

---

### S43.E6.1 - Alertas Criticos no Dashboard Principal

**Objetivo:** Garantir que alertas criticos estejam sempre visiveis no dashboard principal.

**Problema Atual:**
- Alertas podem passar despercebidos
- Nao ha hierarquia visual clara
- Usuario precisa navegar para ver problemas

**Solucao:**

**Layout:**
```
+----------------------------------------------------------+
| Dashboard Julia                                           |
+----------------------------------------------------------+
| +------------------------------------------------------+ |
| | ! ALERTAS CRITICOS (2)                      [Ver all]| |
| | - Circuit breaker LLM em estado OPEN                 | |
| | - Rate limit atingiu 95%                             | |
| +------------------------------------------------------+ |
+----------------------------------------------------------+
| [Resto do dashboard...]                                  |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar componente `CriticalAlertsBanner`
2. Posicionar no topo do dashboard (sempre visivel)
3. Polling a cada 30s para alertas
4. Link para Health Center
5. Dismissivel temporariamente (volta em 5 min)

**API Calls:**
- `GET /health/alerts?severity=critical`

**DoD:**
- [ ] Banner no topo do dashboard
- [ ] Atualiza automaticamente
- [ ] Link para detalhes
- [ ] Pode ser temporariamente dismissido
- [ ] Testes unitarios

---

### S43.E6.2 - Tooltips de Impacto nos Toggles

**Objetivo:** Explicar claramente o impacto de cada toggle antes da acao.

**Problema Atual:**
- Toggles sem contexto suficiente
- Usuario pode nao entender consequencias
- Falta de previsibilidade

**Solucao:**

Adicionar tooltips informativos em todos os toggles do sistema:

```
[Toggle Discovery Automatico]  (i)
                               |
                               v
+------------------------------------------+
| Discovery Automatico                      |
|                                           |
| Quando ATIVO:                             |
| - Julia aborda medicos nao-enriquecidos   |
| - Inicia conversas para coletar dados     |
| - Usa ~5 msgs/hora em media               |
|                                           |
| Quando INATIVO:                           |
| - Julia so responde quem ja conhece       |
| - Nao inicia novas conversas              |
+------------------------------------------+
```

**Tarefas:**
1. Criar componente `InfoTooltip`
2. Adicionar em todos os toggles de `/sistema`
3. Adicionar em toggles de `/chips/configuracoes`
4. Conteudo explicando ATIVO vs INATIVO
5. Incluir metricas quando relevante

**Toggles a documentar:**
- Modo Piloto
- Discovery Automatico
- Oferta Automatica
- Reativacao Automatica
- Feedback Automatico
- Configuracoes de chips

**DoD:**
- [ ] Componente InfoTooltip criado
- [ ] Todos os toggles com tooltip
- [ ] Conteudo claro e util
- [ ] Acessivel (keyboard navegavel)
- [ ] Testes unitarios

---

### S43.E6.3 - Recomendacoes de Acao nos Chips

**Objetivo:** Mostrar recomendacoes claras de acao para chips com problemas.

**Problema Atual:**
- Usuario ve que chip tem problema mas nao sabe o que fazer
- Falta guidance contextual
- Acoes nao sao obvias

**Solucao:**

Na pagina de detalhe do chip e na lista de chips degradados:

```
+----------------------------------------------------------+
| Chip chip_01 - DEGRADED                                   |
+----------------------------------------------------------+
| Trust Score: 45/100                                       |
| Motivo: Muitas mensagens sem resposta                     |
+----------------------------------------------------------+
| Recomendacoes:                                            |
| +------------------------------------------------------+ |
| | 1. Pausar o chip por 24h para recuperacao            | |
| |    [Pausar Agora]                                    | |
| |                                                      | |
| | 2. Verificar se numero foi bloqueado                 | |
| |    [Verificar Conexao]                               | |
| |                                                      | |
| | 3. Considerar trocar de numero se problema persistir | |
| |    [Ver opcoes de substituicao]                      | |
| +------------------------------------------------------+ |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar componente `ChipRecommendations`
2. Logica para gerar recomendacoes baseado no estado
3. Botoes de acao direta
4. Adicionar na pagina de detalhe do chip
5. Adicionar card resumido na lista de chips

**Regras de recomendacao:**
- Trust < 50: Sugerir pausa
- Trust < 30: Sugerir verificacao de conexao
- Trust < 20: Sugerir substituicao
- Sem respostas 24h: Verificar ban
- Rate limit alto: Reduzir uso

**DoD:**
- [ ] Componente criado
- [ ] Recomendacoes contextuais
- [ ] Acoes diretas funcionais
- [ ] Integrado na pagina de chips
- [ ] Testes unitarios

---

### S43.E6.4 - Padronizacao de Loading e Error States

**Objetivo:** Garantir experiencia consistente em todas as paginas.

**Problema Atual:**
- Loading states inconsistentes
- Erros tratados de formas diferentes
- Falta de feedback em algumas acoes

**Solucao:**

Criar e aplicar componentes padronizados:

**Loading State:**
```
+------------------------------------------+
|                                           |
|    [Skeleton animado]                     |
|    [Skeleton animado]                     |
|    [Skeleton animado]                     |
|                                           |
+------------------------------------------+
```

**Error State:**
```
+------------------------------------------+
|                                           |
|    [!] Erro ao carregar dados             |
|                                           |
|    Nao foi possivel conectar ao servidor. |
|    Verifique sua conexao.                 |
|                                           |
|    [Tentar Novamente]                     |
|                                           |
+------------------------------------------+
```

**Empty State:**
```
+------------------------------------------+
|                                           |
|    [Icon]                                 |
|                                           |
|    Nenhuma anomalia encontrada            |
|                                           |
|    Isso e bom! O sistema esta saudavel.  |
|                                           |
+------------------------------------------+
```

**Tarefas:**
1. Criar componente `LoadingState` padronizado
2. Criar componente `ErrorState` com retry
3. Criar componente `EmptyState` com mensagem customizavel
4. Aplicar em todas as novas paginas
5. Refatorar paginas existentes (backlog)

**Paginas a atualizar:**
- Nova: /integridade
- Nova: /grupos
- Nova: /qualidade
- Nova: /health
- Existente: /sistema (minor)
- Existente: /monitor (minor)

**DoD:**
- [ ] Componentes criados
- [ ] Aplicados em todas as novas paginas
- [ ] Documentacao de uso
- [ ] Testes unitarios

---

## Componentes Compartilhados a Criar

| Componente | Uso |
|------------|-----|
| `CriticalAlertsBanner` | Alertas no topo do dashboard |
| `InfoTooltip` | Tooltips informativos em toggles |
| `ChipRecommendations` | Recomendacoes para chips |
| `LoadingState` | Loading padronizado |
| `ErrorState` | Erro com retry |
| `EmptyState` | Estado vazio customizavel |

## Checklist de Consistencia

Aplicar em TODAS as novas paginas:

- [ ] Loading state com skeleton
- [ ] Error state com retry
- [ ] Empty state com mensagem
- [ ] Tooltips em elementos interativos
- [ ] Confirmacao em acoes destrutivas
- [ ] Feedback toast apos acoes
- [ ] Acessibilidade (ARIA labels)
- [ ] Responsive (mobile-friendly)

## Consideracoes Tecnicas

- Usar Radix UI para tooltips (ja no projeto)
- Skeletons devem corresponder ao layout final
- Error states devem logar no console para debug
- Empty states devem ter CTAs quando apropriado
