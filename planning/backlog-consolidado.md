# Backlog Consolidado — Agente Julia

**Gerado em:** 2026-02-21
**Sprint de referencia:** Sprint 69
**Total de itens:** 72

## Sumario Executivo

Levantamento sistematico de todos os itens de trabalho futuro espalhados pelo codebase. Foram encontrados 72 itens em 9 categorias, priorizados por impacto em producao.

| Severidade | Quantidade |
|------------|-----------|
| Alta | 15 |
| Media | 35 |
| Baixa | 22 |

| Categoria | Quantidade |
|-----------|-----------|
| Backend: Core Services | 15 |
| Backend: Pipeline & Processamento | 5 |
| Backend: Integracoes | 8 |
| Dashboard: Frontend | 12 |
| Banco de Dados & Migrations | 6 |
| Testes & CI/CD | 8 |
| Documentacao | 6 |
| Arquitetura & Refatoracao | 8 |
| Feature Flags & Features Incompletas | 4 |

---

## 1. Backend: Core Services (15 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 1 | Contact cap hardcoded (7 dias) - puxar de feature_flags | `app/services/guardrails/check.py:478` | Media | 71 |
| 2 | Deteccao de ponte_feita via tool calls | `app/services/agente/orchestrator.py:297` | Alta | 70 |
| 3 | Tracking de offer_made com vaga_id especifico | `app/services/agente/orchestrator.py:323` | Media | 71 |
| 4 | Remover fallback legado de delivery | `app/services/agente/delivery.py:117` | Baixa | Backlog |
| 5 | Filtro de data de criacao em segmentacao | `app/services/segmentacao.py:146` | Baixa | Backlog |
| 6 | LLM fallback para extracao de hospitais | `app/services/grupos/extrator_v2/extrator_hospitais.py:363` | Media | 72 |
| 7 | LLM para extracao de parametros em briefing | `app/services/briefing_executor.py:181` | Media | 71 |
| 8 | Scheduling real para handoff externo | `app/services/external_handoff/service.py:225` | Media | 72 |
| 9 | Atualizar chip com codigo de verificacao Salvy | `app/services/salvy/webhooks.py:130` | Media | 72 |
| 10 | Deteccao de [TODO] markers em output validation | `app/services/validacao_output.py:144` | Alta | 70 |
| 11 | Criacao de campanhas via gestor_comanda | `app/services/gestor_comanda.py:573` | Alta | 70 |
| 12 | Warmer: entrar_grupo (stub) | `app/services/warmer/executor.py:237` | Alta | 70 |
| 13 | Warmer: mensagem_grupo (stub) | `app/services/warmer/executor.py:251` | Alta | 70 |
| 14 | Warmer: atualizar_perfil (stub) | `app/services/warmer/executor.py:265` | Alta | 70 |
| 15 | Verificacao de handoff em envio de campanha | `app/services/outbound/guardrails.py:~280` | Alta | 70 |

## 2. Backend: Pipeline & Processamento (5 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 16 | Buscar vagas relevantes para contexto do pipeline | `app/pipeline/core.py:33` | Media | 71 |
| 17 | Handling de GrupoDia.TODOS para regras universais | `app/services/grupos/extrator_v2/extrator_valores.py:189-217` | Media | 72 |
| 18 | Extracao de regiao a partir de dados de grupo | Planning sprint-51 | Baixa | Backlog |
| 19 | Verificar instancia conectada via Evolution API | Planning sprint-25 | Media | 72 |
| 20 | Pipeline de vagas no briefing (sprint 8) | Planning sprint-8 | Media | 71 |

## 3. Backend: Integracoes (8 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 21 | Documentacao formato Meta message ID | `app/services/whatsapp_providers/meta_cloud.py:511` | Baixa | Backlog |
| 22 | Mensagens de verificacao placeholder | `app/services/conhecimento/detector_confronto.py:48-57` | Baixa | Backlog |
| 23 | Verificar assinatura Svix em producao (Salvy) | Planning sprint-25 | Alta | 70 |
| 24 | Notificar via Slack ao ativar chip | Planning sprint-25 | Media | 71 |
| 25 | Auto-usar codigo de verificacao no Evolution | Planning sprint-25 | Media | 71 |
| 26 | Scraping de politicas oficiais WhatsApp/Meta | Planning sprint-25 | Baixa | Backlog |
| 27 | Criar instancia Evolution automaticamente | Planning sprint-26 | Alta | 70 |
| 28 | Atualizar metricas de delivery/read | Planning sprint-26 | Media | 71 |

## 4. Dashboard: Frontend (12 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 29 | Contagem groupsJoined quando tabela disponivel | `dashboard/app/api/dashboard/chips/[id]/detail/route.ts:148` | Baixa | Backlog |
| 30 | Contagem real de tipos de midia enviados | `dashboard/app/api/dashboard/chips/[id]/detail/route.ts:149` | Baixa | Backlog |
| 31 | Funcionalidade de logout (sidebar) | `dashboard/components/dashboard/sidebar.tsx:182` | Media | 70 |
| 32 | Funcionalidade de logout (mobile) | `dashboard/components/dashboard/mobile-drawer.tsx:169` | Media | 70 |
| 33 | Exportacao CSV de medicos | `dashboard/app/(dashboard)/medicos/page.tsx:73` | Baixa | Backlog |
| 34 | ~~Meta Flows placeholder "Em breve"~~ | ~~`dashboard/components/meta/tabs/flows-tab.tsx`~~ | ~~Baixa~~ | ~~Sprint 69~~ ✅ |
| 35 | Integrar API de ranking em analytics | `dashboard/components/market-intelligence/analytics-tab-content.tsx:229` | Media | 72 |
| 36 | Aumentar cobertura de testes dashboard | `dashboard/vitest.config.ts:176` | Baixa | Backlog |
| 37 | Comparacao com periodo anterior em analytics | Planning sprint-33 | Baixa | Backlog |
| 38 | Dados reais quando tabela de warmup existir | Planning sprint-42 | Media | 72 |
| 39 | Metricas reais para queue/chips/job scores | Planning sprint-42 | Media | 72 |
| 40 | Integrar ranking API em analytics tab | Planning sprint-46 | Media | 72 |

## 5. Banco de Dados & Migrations (6 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 41 | Health check real para Supabase/Evolution/Chatwoot | Planning sprint-0 | Media | 71 |
| 42 | Contagem de mensagens recebidas (atualmente 0) | Planning sprint-28 | Baixa | Backlog |
| 43 | Status real de Evolution e Chatwoot no health endpoint | Planning sprint-28 | Media | 71 |
| 44 | Filtrar ativacoes por janela de tempo | Planning sprint-27 | Baixa | Backlog |
| 45 | Documentacao de status/estados no schema | `bootstrap/01-schema.sql` | N/A | - |
| 46 | Lock distribuido alternativo (Redis) + timing diferenciado | `docs/auditorias/auditoria-processos.md` | Baixa | Backlog |

## 6. Testes & CI/CD (8 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 47 | Remover TODO references obsoletos no CI | Planning sprint-62 | Media | 70 |
| 48 | Remover continue-on-error flags apos fixes | Planning sprint-62 | Baixa | Backlog |
| 49 | Usar LLM real ao inves de dict vazio em test_briefing | `tests/test_briefing_executor.py:182` | Media | 71 |
| 50 | Resolver/remover TODOs/FIXMEs obsoletos | Planning sprint-31 | Media | 70 |
| 51 | Verificacao de handoff em teste de campanha | `tests/services/guardrails/test_outbound_guardrails.py:280` | Media | 71 |
| 52 | Stubs do warmer nao devem inflar metricas | `tests/services/warmer/test_executor.py:436-460` | Media | 71 |
| 53 | Verificar grupos_min=0 em todas as fases | `tests/services/warmer/test_orchestrator.py:515` | Media | 71 |
| 54 | Cobertura 70%+ para app/api routes | Planning sprint-62 | Alta | 70 |

## 7. Documentacao (6 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 55 | Formato exemplo de medico com CRM XXXXX | Planning sprint-7 | N/A | - |
| 56 | Exemplos de message ID com XXXXXXXXXXXX | `docs/integracoes/meta-cloud-api-quickref.md` | N/A | - |
| 57 | Requisitos de auditoria de guardrails | `docs/auditorias/auditoria-processos.md` | N/A | - |
| 58 | TODOs legados em docs do sprint 1 (webhook) | Planning sprint-1 | Baixa | Cleanup |
| 59 | TODOs legados em docs do sprint 1 (agente) | Planning sprint-1 | Baixa | Cleanup |
| 60 | Padroes de TODO na knowledge base Julia | `data/migration/conhecimento_julia.sql` | N/A | - |

## 8. Arquitetura & Refatoracao (8 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 61 | Remover markers DEPRECATED/deprecated/legacy | Planning sprint-35 | Media | 71 |
| 62 | Sistema de monitoramento (Epic 12.4) | `docs/auditorias/nfr-assessment-2026-02-09.md` | Media | 72 |
| 63 | Hospital dropdown carrega 2703 registros | Planning sprint-60 | Alta | 70 |
| 64 | Resiliencia distribuida - nao parar todos os chips | Planning sprint-36 | Media | 72 |
| 65 | FKs de baixo impacto excluidos da indexacao | Planning sprint-55 | Baixa | Backlog |
| 66 | Garantir _finalizar_envio() em TODOS os envios | Planning sprint-24 | Alta | 70 |
| 67 | Rastrear todos os estados de envio | Planning sprint-24 | Alta | 70 |
| 68 | Refatorar paginas existentes para consistencia UX | Planning sprint-43 | Baixa | Backlog |

## 9. Feature Flags & Features Incompletas (4 itens)

| # | Item | Arquivo | Prioridade | Sprint Sugerida |
|---|------|---------|-----------|-----------------|
| 69 | Tipo de mensagem interativa nao implementado | `app/tools/interactive_validation.py:58` | Media | 72 |
| 70 | Extracao completa de hospitais/locais | Planning sprint-40 | Media | 72 |
| 71 | Gate de testes: todos devem passar antes do proximo epic | Planning sprint-46 | Alta | Processo |
| 72 | Relatorio semanal retorna placeholder | `app/services/relatorios/semanal.py:75` | Baixa | Backlog |

---

## Recomendacoes para Proximas Sprints

### Sprint 70 (Prioridade Alta — 15 itens)

Foco: **Correcoes criticas e stubs de producao**

- Warmer stubs (#12-14): entrar_grupo, mensagem_grupo, atualizar_perfil
- Deteccao de ponte_feita (#2) e criacao de campanhas (#11)
- Verificacao de handoff em envio (#15)
- Assinatura Svix (#23) e instancia Evolution (#27)
- Hospital dropdown performance (#63)
- Finalizar_envio em todos os envios (#66-67)
- Dashboard logout (#31-32)
- Cobertura API routes (#54)
- TODOs obsoletos (#47, #50)

### Sprint 71 (Prioridade Media — 15 itens)

Foco: **Melhorias de inteligencia e integracao**

- LLM em briefing (#7) e pipeline vagas (#16, #20)
- Health check real (#41, #43)
- Metricas de delivery (#28)
- Tracking offer_made (#3), contact cap (#1)
- Testes: warmer metrics (#52-53), briefing (#49), handoff (#51)
- Remover markers deprecated (#61)

### Sprint 72+ (Backlog — 20+ itens)

Foco: **Polimento e features avancadas**

- Analytics reais (#35, #38-40)
- Monitoramento (#62), resiliencia distribuida (#64)
- LLM hospitais (#6), handoff externo (#8)
- Extracao completa (#70), mensagens interativas (#69)
