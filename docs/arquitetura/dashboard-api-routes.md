# Dashboard - API Routes

Documentacao completa de todas as rotas API do dashboard Next.js.

**Ultima atualizacao:** 10/02/2026
**Total de rotas:** 121

---

## Indice

- [Admin](#admin)
- [Ajuda](#ajuda)
- [Auditoria](#auditoria)
- [Auth](#auth)
- [Campanhas](#campanhas)
- [Chips](#chips)
- [Conversas](#conversas)
- [Dashboard](#dashboard)
- [Diretrizes](#diretrizes)
- [Especialidades](#especialidades)
- [Filtros](#filtros)
- [Group Entry](#group-entry)
- [Guardrails](#guardrails)
- [Health](#health)
- [Hospitais](#hospitais)
- [Incidents](#incidents)
- [Integridade](#integridade)
- [Market Intelligence](#market-intelligence)
- [Medicos](#medicos)
- [Metricas](#metricas)
- [Sistema](#sistema)
- [Upload](#upload)
- [Vagas](#vagas)

---

## Admin

Rotas de administracao e qualidade (Sprint 43).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| POST | `/api/admin/avaliacoes` | Salva avaliacao de conversa | Sim |
| GET | `/api/admin/conversas` | Lista conversas para avaliacao | Sim |
| GET | `/api/admin/conversas/[id]` | Detalhe de conversa com interacoes | Sim |
| GET | `/api/admin/metricas/performance` | Metricas de performance de qualidade | Sim |
| GET | `/api/admin/sugestoes` | Lista sugestoes de prompt | Sim |
| POST | `/api/admin/sugestoes` | Cria sugestao de prompt | Sim |
| PATCH | `/api/admin/sugestoes/[id]` | Atualiza status de sugestao | Sim |
| GET | `/api/admin/tags` | Lista tags disponiveis para avaliacao | Sim |
| GET | `/api/admin/validacao/metricas` | Metricas do validador de output | Sim |

---

## Ajuda

Sistema de pedidos de ajuda (Sprint 43).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/ajuda` | Lista pedidos de ajuda (query: status) | Sim |
| POST | `/api/ajuda/[id]/responder` | Responde a um pedido de ajuda e retoma conversa | Sim |

---

## Auditoria

Logs de auditoria do sistema (Sprint 18).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/auditoria` | Lista logs de auditoria (filtros: action, actor_email, from_date, to_date) | Sim |
| GET | `/api/auditoria/export` | Exporta logs de auditoria em CSV (limite: 10000 registros) | Sim |

---

## Auth

Autenticacao.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| POST | `/api/auth/dev-login` | Bypass de autenticacao APENAS para desenvolvimento local (bloqueado em producao) | Nao |

---

## Campanhas

Gestao de campanhas de mensagens (Sprints 5, 35).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/campanhas` | Lista campanhas (filtro: status) | Sim |
| POST | `/api/campanhas` | Cria nova campanha | Sim |
| GET | `/api/campanhas/[id]` | Detalhes de campanha com envios e metricas | Sim |
| PATCH | `/api/campanhas/[id]` | Atualiza status da campanha (iniciar, pausar, retomar, cancelar, concluir) | Sim |
| PUT | `/api/campanhas/[id]` | Atualiza dados de campanha em rascunho | Sim |
| GET | `/api/campanhas/[id]/audiencia` | Retorna audiencia (medicos) da campanha baseado nos filtros | Sim |
| PATCH | `/api/campanhas/[id]/audiencia` | Adiciona ou remove medicos da audiencia | Sim |
| POST | `/api/campanhas/[id]/audiencia` | Busca medicos para adicionar a campanha (query: q) | Sim |

---

## Chips

Gestao de chips WhatsApp (Sprints 40, 41).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/chips` | Lista chips disponiveis para filtro de inbox | Sim |

---

## Conversas

Inbox e gestao de conversas (Sprints 28, 29, 54).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/conversas` | Lista conversas com enrichment (filtros: tab, chip_id, search) | Sim |
| GET | `/api/conversas/[id]` | Detalhes de conversa com mensagens e estado de pausa | Sim |
| GET | `/api/conversas/[id]/channel` | Busca canal ativo (instruction) da conversa | Sim |
| PATCH | `/api/conversas/[id]/channel` | Ativa canal (instruction) para conversa | Sim |
| DELETE | `/api/conversas/[id]/channel/[instructionId]` | Desativa canal (instruction) da conversa | Sim |
| GET | `/api/conversas/[id]/context` | Retorna contexto completo da conversa (historico, doctor_context, vagas) | Sim |
| PATCH | `/api/conversas/[id]/control` | Transfere controle da conversa (AI <-> Humano) | Sim |
| POST | `/api/conversas/[id]/feedback` | Envia feedback sobre resposta da Julia | Sim |
| GET | `/api/conversas/[id]/notes` | Busca notas da conversa | Sim |
| POST | `/api/conversas/[id]/notes` | Adiciona nota a conversa | Sim |
| POST | `/api/conversas/[id]/pause` | Pausa conversa (temporaria ou permanente) | Sim |
| DELETE | `/api/conversas/[id]/pause` | Remove pausa de conversa | Sim |
| POST | `/api/conversas/[id]/send` | Envia mensagem manual em nome da Julia | Sim |
| GET | `/api/conversas/[id]/stream` | Stream de mensagens (SSE) | Sim |
| GET | `/api/conversas/counts` | Contadores de conversas por status/tab | Sim |
| POST | `/api/conversas/new` | Cria nova conversa com medico | Sim |

---

## Dashboard

Metricas e status do sistema (Sprints 28, 33, 40, 41, 42, 56).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/dashboard/activity` | Atividades recentes do sistema | Sim |
| GET | `/api/dashboard/alerts` | Alertas globais do sistema | Sim |
| GET | `/api/dashboard/chips` | Metricas agregadas de chips | Sim |
| GET | `/api/dashboard/chips/[id]` | Detalhes de chip especifico | Sim |
| GET | `/api/dashboard/chips/[id]/check-connection` | Verifica conexao WhatsApp do chip | Sim |
| GET | `/api/dashboard/chips/[id]/detail` | Detalhes completos do chip (metricas, alerts, historico) | Sim |
| GET | `/api/dashboard/chips/[id]/interactions` | Interacoes recentes do chip | Sim |
| GET | `/api/dashboard/chips/[id]/metrics` | Metricas detalhadas do chip (30d) | Sim |
| POST | `/api/dashboard/chips/[id]/pause` | Pausa chip | Sim |
| POST | `/api/dashboard/chips/[id]/promote` | Promove chip (warming -> ready -> active) | Sim |
| POST | `/api/dashboard/chips/[id]/reactivate` | Reativa chip pausado/suspenso | Sim |
| POST | `/api/dashboard/chips/[id]/resume` | Resume chip pausado | Sim |
| GET | `/api/dashboard/chips/[id]/trust-history` | Historico de trust score do chip | Sim |
| GET | `/api/dashboard/chips/alerts` | Lista alertas de chips | Sim |
| GET | `/api/dashboard/chips/alerts/[id]` | Detalhes de alerta especifico | Sim |
| POST | `/api/dashboard/chips/alerts/[id]/resolve` | Resolve alerta de chip | Sim |
| GET | `/api/dashboard/chips/alerts/count` | Contadores de alertas por severidade | Sim |
| GET | `/api/dashboard/chips/config` | Configuracao global de chips | Sim |
| PATCH | `/api/dashboard/chips/config` | Atualiza configuracao global de chips | Sim |
| GET | `/api/dashboard/chips/health` | Status de saude dos chips | Sim |
| GET | `/api/dashboard/chips/instances` | Lista instancias WhatsApp | Sim |
| GET | `/api/dashboard/chips/instances/[name]/connection-state` | Estado de conexao da instancia | Sim |
| GET | `/api/dashboard/chips/instances/[name]/qr-code` | QR Code para pareamento | Sim |
| GET | `/api/dashboard/chips/list` | Lista chips com metricas | Sim |
| GET | `/api/dashboard/chips/warmup` | Status do aquecimento de chips | Sim |
| GET | `/api/dashboard/chips/warmup/stats` | Estatisticas de aquecimento | Sim |
| GET | `/api/dashboard/conversations/[id]/messages` | Mensagens de conversa para visualizacao | Sim |
| GET | `/api/dashboard/export` | Exporta dados do dashboard (CSV) | Sim |
| GET | `/api/dashboard/funnel` | Metricas de funil de conversao | Sim |
| GET | `/api/dashboard/funnel/[stage]` | Detalhes de estagio especifico do funil | Sim |
| GET | `/api/dashboard/message-flow` | Dados para visualizacao de fluxo de mensagens (Sprint 56) | Sim |
| GET | `/api/dashboard/metrics` | Metricas principais do dashboard | Sim |
| GET | `/api/dashboard/monitor` | Status de jobs agendados | Sim |
| GET | `/api/dashboard/monitor/jobs` | Lista todos os jobs com status | Sim |
| POST | `/api/dashboard/monitor/job/[name]/action` | Executa acao em job (trigger, pause, resume) | Sim |
| GET | `/api/dashboard/monitor/job/[name]/executions` | Historico de execucoes do job | Sim |
| GET | `/api/dashboard/operational` | Metricas operacionais (conversas, mensagens, handoffs) | Sim |
| GET | `/api/dashboard/quality` | Metricas de qualidade das conversas | Sim |
| GET | `/api/dashboard/status` | Status da Julia (heartbeat, uptime 30d) | Sim |
| GET | `/api/dashboard/trends` | Tendencias de metricas (7d, 30d) | Sim |

---

## Diretrizes

Gestao de instrucoes/diretrizes da Julia (Sprint 11).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/diretrizes` | Lista diretrizes ativas | Sim |
| POST | `/api/diretrizes` | Cria nova diretriz | Sim |
| GET | `/api/diretrizes/[id]` | Detalhes de diretriz | Sim |
| PATCH | `/api/diretrizes/[id]` | Atualiza diretriz | Sim |
| DELETE | `/api/diretrizes/[id]` | Deleta diretriz | Sim |

---

## Especialidades

Cadastro de especialidades medicas.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/especialidades` | Lista especialidades disponiveis | Sim |

---

## Filtros

Filtros dinamicos para listas.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/filtros` | Retorna opcoes de filtro (especialidades, regioes, etc) | Sim |

---

## Group Entry

Pipeline de grupos WhatsApp (Sprints 14, 51, 52, 53).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/group-entry/capacity` | Capacidade atual do sistema | Sim |
| GET | `/api/group-entry/config` | Configuracao do Group Entry | Sim |
| PATCH | `/api/group-entry/config` | Atualiza configuracao | Sim |
| GET | `/api/group-entry/dashboard` | Dados consolidados do Group Entry | Sim |
| POST | `/api/group-entry/import/csv` | Importa lista de grupos via CSV | Sim |
| GET | `/api/group-entry/links` | Lista links de grupos | Sim |
| POST | `/api/group-entry/links` | Adiciona novo link de grupo | Sim |
| GET | `/api/group-entry/process` | Lista processos de entrada em grupos | Sim |
| POST | `/api/group-entry/process` | Inicia processo de entrada em grupo | Sim |
| GET | `/api/group-entry/process/[id]` | Detalhes de processo especifico | Sim |
| DELETE | `/api/group-entry/process/[id]` | Cancela processo de entrada | Sim |
| GET | `/api/group-entry/queue` | Lista fila de grupos pendentes | Sim |
| POST | `/api/group-entry/queue` | Adiciona grupo a fila | Sim |
| PATCH | `/api/group-entry/queue/[id]` | Atualiza status de item da fila | Sim |
| GET | `/api/group-entry/schedule` | Lista agendamentos de entrada | Sim |
| POST | `/api/group-entry/schedule` | Cria agendamento de entrada | Sim |
| POST | `/api/group-entry/schedule/batch` | Cria multiplos agendamentos | Sim |
| PATCH | `/api/group-entry/schedule/[id]` | Atualiza agendamento | Sim |
| DELETE | `/api/group-entry/schedule/[id]` | Cancela agendamento | Sim |
| POST | `/api/group-entry/validate/[id]` | Valida link de grupo | Sim |
| POST | `/api/group-entry/validate/batch` | Valida multiplos links | Sim |

---

## Guardrails

Circuit breakers e limites do sistema (Sprint 10).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| POST | `/api/guardrails/circuits/[name]/reset` | Reseta circuit breaker especifico | Sim |
| GET | `/api/guardrails/status` | Status de todos os guardrails (rate limits, circuits) | Sim |

---

## Health

Endpoints de health check.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/health` | Health check basico (retorna 200 OK) | Nao |
| GET | `/api/health/queue` | Status da fila de mensagens | Sim |
| GET | `/api/health/rate-limit` | Status dos rate limiters | Sim |
| GET | `/api/health/services` | Status de servicos externos (Evolution, Chatwoot, Supabase, Redis) | Sim |

---

## Hospitais

Cadastro de hospitais.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/hospitais` | Lista hospitais | Sim |
| POST | `/api/hospitais` | Cria novo hospital | Sim |
| PATCH | `/api/hospitais/[id]` | Atualiza hospital | Sim |
| DELETE | `/api/hospitais/[id]` | Deleta hospital | Sim |
| GET | `/api/hospitais/bloqueados` | Lista hospitais bloqueados | Sim |
| POST | `/api/hospitais/bloquear` | Bloqueia hospital | Sim |
| POST | `/api/hospitais/desbloquear` | Desbloqueia hospital | Sim |

---

## Incidents

Gestao de incidentes de saude do sistema (Sprint 55 E03).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/incidents` | Lista incidentes (filtros: limit, status, since) | Sim |
| POST | `/api/incidents` | Registra novo incidente | Sim |
| GET | `/api/incidents/stats` | Estatisticas de incidentes | Sim |

---

## Integridade

Auditoria e integridade de dados (Sprint 18).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/integridade/anomalias` | Lista anomalias detectadas | Sim |
| POST | `/api/integridade/anomalias/[id]/resolver` | Marca anomalia como resolvida | Sim |
| GET | `/api/integridade/kpis` | KPIs de integridade do sistema | Sim |
| POST | `/api/integridade/reconciliacao` | Inicia processo de reconciliacao de dados | Sim |

---

## Market Intelligence

Inteligencia de mercado via grupos WhatsApp (Sprint 53).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/market-intelligence/groups-ranking` | Ranking de grupos por atividade | Sim |
| GET | `/api/market-intelligence/overview` | KPIs e metricas de overview (query: period, startDate, endDate) | Sim |
| GET | `/api/market-intelligence/pipeline` | Status do pipeline de processamento | Sim |
| GET | `/api/market-intelligence/volume` | Volume de mensagens e ofertas | Sim |

---

## Medicos

Cadastro de medicos (clientes).

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/medicos` | Lista medicos (filtros: stage_jornada, especialidade, opt_out, search) | Sim |
| GET | `/api/medicos/[id]` | Detalhes de medico | Sim |
| PATCH | `/api/medicos/[id]` | Atualiza dados de medico | Sim |
| GET | `/api/medicos/[id]/funnel` | Posicao do medico no funil | Sim |
| POST | `/api/medicos/[id]/opt-out` | Registra opt-out de medico | Sim |
| GET | `/api/medicos/[id]/timeline` | Timeline de interacoes do medico | Sim |

---

## Metricas

Exportacao e visualizacao de metricas.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/metricas` | Metricas gerais do sistema | Sim |
| GET | `/api/metricas/export` | Exporta metricas em CSV | Sim |

---

## Sistema

Configuracoes e status do sistema.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/sistema/config` | Configuracao global do sistema | Sim |
| PATCH | `/api/sistema/config` | Atualiza configuracao global | Sim |
| GET | `/api/sistema/features/[feature]` | Status de feature flag | Sim |
| PATCH | `/api/sistema/features/[feature]` | Atualiza feature flag | Sim |
| GET | `/api/sistema/pilot-mode` | Status do modo piloto | Sim |
| PATCH | `/api/sistema/pilot-mode` | Ativa/desativa modo piloto | Sim |
| GET | `/api/sistema/status` | Status geral do sistema (versao, uptime, componentes) | Sim |

---

## Upload

Upload de arquivos.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| POST | `/api/upload` | Upload de arquivo (CSV, imagens, etc) | Sim |

---

## Vagas

Gestao de vagas de plantao.

| Metodo | Path | Descricao | Auth |
|--------|------|-----------|------|
| GET | `/api/vagas` | Lista vagas (filtros: status, hospital_id, especialidade_id, date_from, date_to, search) | Sim |
| POST | `/api/vagas` | Cria nova vaga | Sim |
| GET | `/api/vagas/[id]` | Detalhes de vaga | Sim |
| PATCH | `/api/vagas/[id]` | Atualiza vaga | Sim |
| DELETE | `/api/vagas/[id]` | Deleta vaga | Sim |

---

## Convencoes

### Autenticacao

- **Sim**: Requer usuario autenticado via Supabase Auth
- **Nao**: Endpoint publico ou protegido por outros meios

### Proxy para Backend Python

Muitas rotas sao proxies para o backend FastAPI (`NEXT_PUBLIC_API_URL`):
- Campanhas (execucao)
- Group Entry (processamento)
- Incidents
- Diretrizes (algumas operacoes)
- Admin (algumas operacoes)

### Validacao

Rotas usam Zod para validacao de input quando aplicavel (ex: `/api/vagas`, `/api/market-intelligence/overview`).

### Paginacao

Rotas de listagem geralmente aceitam:
- `page`: numero da pagina (default: 1)
- `per_page`: itens por pagina (default: 20-50)

Response padrao:
```json
{
  "data": [...],
  "total": 100,
  "pages": 5
}
```

### Error Handling

Response de erro padrao:
```json
{
  "error": "Mensagem de erro",
  "details": {...}  // opcional
}
```

HTTP status codes:
- `200`: Sucesso
- `201`: Criado
- `400`: Bad Request (validacao falhou)
- `401`: Unauthorized (nao autenticado)
- `403`: Forbidden (sem permissao)
- `404`: Not Found
- `500`: Internal Server Error

---

## Notas Tecnicas

### Sprint References

- **Sprint 5**: Campanhas
- **Sprint 11**: Diretrizes
- **Sprint 14**: Pipeline de Grupos (v1)
- **Sprint 18**: Auditoria e Integridade
- **Sprint 28**: Dashboard Julia
- **Sprint 29**: Conversation Mode
- **Sprint 33**: Dashboard de Performance
- **Sprint 35**: Campanhas v2 (fila_mensagens)
- **Sprint 40**: Chips Dashboard
- **Sprint 41**: Chips Ops & Health
- **Sprint 42**: Monitor Jobs
- **Sprint 43**: UX & Operacao Unificada (Qualidade, Group Entry UI, Ajuda)
- **Sprint 51**: Pipeline Grupos - Revisao Arquitetural
- **Sprint 52**: Pipeline v3 - Extracao LLM
- **Sprint 53**: Discovery Intelligence Pipeline (Market Intelligence)
- **Sprint 54**: Enrichment (sentimento, confidence, pause state)
- **Sprint 55**: Health Incidents (E03)
- **Sprint 56**: Message Flow Visualization

### Supabase Direct vs Backend Proxy

- Rotas que acessam Supabase diretamente: conversas, medicos, vagas, auditoria, chips (leitura)
- Rotas que fazem proxy para backend Python: campanhas (execucao), group-entry (processamento), incidents, alguns endpoints admin

### Cache Control

Todas as rotas usam `export const dynamic = 'force-dynamic'` para desabilitar cache do Next.js.

Health status endpoints incluem headers explicitamente:
```typescript
'Cache-Control': 'no-store, no-cache, must-revalidate'
```

---

## Como Adicionar Nova Rota

1. Criar `dashboard/app/api/[dominio]/[...path]/route.ts`
2. Exportar funcoes assincronas: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
3. Adicionar `export const dynamic = 'force-dynamic'`
4. Implementar validacao (Zod se aplicavel)
5. Implementar autenticacao se necessario
6. Documentar neste arquivo

Exemplo minimo:
```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()

    // Verificar auth
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Implementacao
    const { data, error } = await supabase.from('tabela').select('*')

    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error('Error:', error)
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}
```

---

## Versoes

| Versao | Data | Mudancas |
|--------|------|----------|
| 1.0 | 10/02/2026 | Documentacao inicial completa (121 rotas) |
