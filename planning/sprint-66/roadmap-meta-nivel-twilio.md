# Roadmap: Julia Meta Cloud API — Nivel Twilio e Alem

## Visao Original

> "Precisamos de um sistema completo, nivel twilio e ir alem dele. A Julia tem que ser referencia no uso agentico da API Oficial da Meta. Pense profundamente como podemos explorar ao maximo essa nossa feature no nosso negocio."

## Status Atual vs Visao

| Aspecto | Sprint 66 (Atual) | Nivel Twilio | Julia Referencia |
|---------|-------------------|-------------|-----------------|
| Envio basico | Texto, template, media | Texto, template, media | Texto, template, media |
| Templates | CRUD + sync | CRUD + sync + analytics | CRUD + sync + analytics + auto-optimization |
| Interactive | Buttons/Lists (provider only) | Buttons/Lists/CTA/Carousel | Buttons/Lists/CTA/Carousel + decisao agentica |
| Formularios | Nao suportado | WhatsApp Flows | WhatsApp Flows com intake automatico |
| Catalogo | Nao suportado | Product messages | Product messages integrados com vagas |
| Auth | Nao suportado | OTP templates | OTP one-tap para confirmacao de plantao |
| Analytics | Delivery status basico | Template + conversation analytics | Analytics + ML para otimizacao automatica |
| Quality | Manual (webhook) | Polling + alerts | Auto-healing (degrade, rotate, alert) |
| Marketing AI | Nao suportado | Nao suportado | MM Lite (+9% delivery rate) |
| Pricing | Nao otimizado | Cost tracking | Cost optimization agentica |

---

## Sprint 66-fix: Gaps Criticos (antes de merge)

**Objetivo:** Corrigir gaps que bloqueiam producao.

| # | Gap | Acao | Testes |
|---|-----|------|--------|
| G1 | `enviar_media_via_chip` sem janela 24h | Adicionar check `_enviar_meta_smart` para media | 2 |
| G2 | `_enviar_meta_smart()` sem testes | Escrever 7 testes unitarios | 7 |
| G3 | Selector aceita chips Meta sem credenciais | Validar `meta_phone_number_id` e `meta_access_token` | 2 |
| G4 | Migrations nao verificadas | Verificar/aplicar via Supabase MCP | 0 |
| — | Orchestrator Meta sem testes | 4 testes unitarios | 4 |
| — | Health monitor Meta sem testes | 2 testes unitarios | 2 |
| — | Executor Meta sem testes | 5 testes unitarios | 5 |
| — | Multi-chip propagation sem testes | 2 testes unitarios | 2 |
| **Total** | | | **24** |

---

## Sprint 67: Intelligence Layer

**Objetivo:** Transformar a integracao basica em inteligencia agentica. Julia nao apenas usa a API — ela toma decisoes inteligentes sobre COMO usar.

### Epic 67.1: Quality Monitor Service

**O que:** Servico que monitora quality rating dos chips Meta via API e reage automaticamente.

**Funcionalidades:**
- Polling periodico da Meta Quality API (`GET /{waba_id}/message_templates?fields=quality_score`)
- Historico de quality em `meta_quality_history`
- Auto-degradacao quando quality cai para RED
- Alerta Slack quando quality cai para YELLOW
- Kill switch: desativar todos os chips Meta de uma WABA com 1 comando

**Diferencial agentico:** Julia detecta padrao de degradacao (GREEN → YELLOW em 3 chips) e proativamente reduz volume de envio ANTES de virar RED. Twilio nao faz isso.

**Testes:** ~15 testes
**Arquivos:** `app/services/meta/quality_monitor.py`, `app/workers/meta_quality_worker.py`

---

### Epic 67.2: Interactive Messages no Agente Julia

**O que:** Julia usa buttons, lists e CTA URLs nas conversas, nao apenas texto.

**Funcionalidades:**
- Tool `enviar_opcoes(opcoes: list[str])` → gera reply buttons (max 3)
- Tool `enviar_lista(titulo, secoes)` → gera list message (max 10 itens)
- Tool `enviar_cta(texto, url, label)` → gera CTA URL button
- Pipeline de decisao: quando Julia tem opcoes claras, usa buttons ao inves de texto
- Fallback: se chip nao e Meta, envia texto formatado ("1. Opcao A\n2. Opcao B")

**Cenarios de uso Julia:**
```
Julia: "Dr Carlos, tenho 3 vagas que combinam com vc:"
[Lista interativa]
- UTI Cardio - Sao Luiz - R$2.500
- PS Geral - Albert Einstein - R$1.800
- Enfermaria - Sirio Libanes - R$2.200
[Botao: "Ver mais vagas"]

Medico toca "UTI Cardio - Sao Luiz"

Julia: "Show! O plantao e dia 15/03, das 19h as 7h"
[Buttons]
[Tenho interesse] [Preciso de mais detalhes] [Nao posso]
```

**Diferencial agentico:** Julia decide QUANDO usar buttons vs texto. Conversa natural usa texto, decisoes claras usam buttons. Twilio nao tem essa inteligencia.

**Testes:** ~20 testes
**Arquivos:** `app/tools/interactive_messages.py`, modificar `app/services/agent/`

---

### Epic 67.3: Template Analytics

**O que:** Metricas de performance por template (delivery, read, click, cost).

**Funcionalidades:**
- Polling da Template Analytics API (`GET /{waba_id}/template_analytics`)
- Dashboard de metricas por template (delivery rate, read rate, cost per message)
- Alertas quando template tem delivery < 70% (indicador de pacing/quality issue)
- Comparacao A/B entre versoes de template

**Endpoints da Meta:**
```
GET /{waba_id}/template_analytics?start={unix}&end={unix}&granularity=DAILY
→ {data_points: [{template_id, sent, delivered, read, clicked, cost}]}
```

**Diferencial agentico:** Julia analisa quais templates performam melhor e sugere ao gestor quais manter/pausar/reescrever.

**Testes:** ~12 testes
**Arquivos:** `app/services/meta/template_analytics.py`, `app/api/routes/meta_analytics.py`

---

### Epic 67.4: Conversation Analytics

**O que:** Metricas de conversa por tipo (user-initiated vs business-initiated), custo, volume.

**Funcionalidades:**
- Polling da Conversation Analytics API
- Custo por conversa por tipo (marketing, utility, authentication, service)
- Volume por dia/semana/mes
- Alertas de custo (se gasto > budget)

**Pricing (desde Julho 2025 — per-message, nao por conversa):**
- Marketing: mais caro
- Utility: medio
- Authentication: mais barato
- Service (user-initiated dentro de 24h): GRATUITO

**Diferencial agentico:** Julia otimiza QUAL tipo de mensagem enviar para minimizar custo. Se esta na janela 24h, envia free-form (gratuito). Se fora, usa utility template (mais barato que marketing) quando possivel.

**Testes:** ~10 testes
**Arquivos:** `app/services/meta/conversation_analytics.py`

---

## Sprint 68: Advanced Features

**Objetivo:** Features avancadas que nenhum concorrente usa de forma agentica.

### Epic 68.1: MM Lite API (Marketing Messages Lite)

**O que:** Canal de marketing AI-optimized da Meta com +9% delivery rate.

**Funcionalidades:**
- Integracao com MM Lite API (lancada Abril 2025)
- Envio de marketing messages com otimizacao de delivery pela Meta
- Meta decide QUANDO entregar a mensagem (melhor hora para o usuario)
- Metricas de delivery do MM Lite vs regular

**O que MM Lite faz:**
- Meta usa ML para determinar melhor hora de entregar a msg
- +9% delivery rate vs regular marketing messages
- Mesmo custo que regular marketing
- Requer opt-in por WABA

**Cenario Julia:**
```
Campanha DISCOVERY para 500 medicos
→ Julia envia via MM Lite
→ Meta otimiza horario de entrega para cada medico
→ Taxa de entrega: 94% (vs 85% regular)
→ Taxa de resposta: 32% (vs 28% regular)
```

**Diferencial agentico:** Julia DECIDE quando usar MM Lite (campanhas de volume) vs regular (mensagens urgentes como confirmacao de plantao).

**Testes:** ~10 testes
**Arquivos:** `app/services/meta/mm_lite.py`, modificar `app/services/chips/sender.py`

---

### Epic 68.2: WhatsApp Flows

**O que:** Formularios nativos no WhatsApp para coleta estruturada de dados.

**Funcionalidades:**
- Builder de flows (JSON v7.0)
- Flow para onboarding de medico (nome, CRM, especialidade, disponibilidade)
- Flow para confirmacao de plantao (confirmacao + checklist pre-plantao)
- Flow para avaliacao pos-plantao (satisfacao + feedback)
- Receber respostas do flow via webhook (dados criptografados AES-128)
- Armazenar respostas no banco

**Flows planejados:**

1. **Onboarding Medico**
   ```
   Tela 1: Dados pessoais (nome, CRM, telefone)
   Tela 2: Especialidades (checkbox multi-select)
   Tela 3: Disponibilidade (dias da semana, turnos)
   Tela 4: Preferencias (regioes, hospitais, valor minimo)
   ```

2. **Confirmacao de Plantao**
   ```
   Tela 1: Confirma presenca? (radio: sim/nao/remarcar)
   Tela 2: Se sim → checklist (documentos, uniforme, horario)
   Tela 3: Informacoes extras (alergias, restricoes)
   ```

3. **Avaliacao Pos-Plantao**
   ```
   Tela 1: Nota geral (1-5 estrelas)
   Tela 2: Pontos positivos (checkbox)
   Tela 3: Feedback aberto (text area)
   ```

**Especificacao tecnica:**
- JSON v7.0 com validacao de schema
- Endpoints da Meta: `POST /{waba_id}/flows` (criar), `PUT /{flow_id}` (atualizar)
- Webhook: dados criptografados com AES-128-GCM, chave privada no servidor
- Componentes: TextInput, TextArea, DatePicker, RadioButtons, CheckboxGroup, Dropdown, OptIn

**Diferencial agentico:** Julia decide QUANDO enviar flow vs conversa natural. Para coleta estruturada (onboarding), flow e mais eficiente. Para relacionamento (oferta de vaga), conversa natural e melhor.

**Testes:** ~25 testes
**Arquivos:** `app/services/meta/flows_service.py`, `app/services/meta/flows_builder.py`, `app/api/routes/meta_flows.py`

---

### Epic 68.3: Rich Media Templates

**O que:** Templates com header visual (imagem, video, documento).

**Funcionalidades:**
- Upload de media para Meta (`POST /{phone_number_id}/media`)
- Templates com header image (ex: foto do hospital)
- Templates com header video (ex: tour virtual do hospital)
- Templates com header document (ex: contrato PDF)
- Variable mapping para media headers

**Cenario Julia:**
```
Template: julia_oferta_visual_v1
Header: [Foto do Hospital Sao Luiz]
Body: "Oi Dr {{1}}! Surgiu uma vaga de {{2}} no {{3}}..."
Buttons: [Tenho interesse] [Nao posso]
```

**Testes:** ~12 testes
**Arquivos:** `app/services/meta/media_upload.py`, modificar `template_mapper.py`

---

### Epic 68.4: Catalog/Commerce Messages

**O que:** Mensagens de produto/catalogo do WhatsApp — usados para mostrar vagas como "produtos".

**Funcionalidades:**
- Catalogo de vagas como produtos Meta
- Single-product message (1 vaga detalhada)
- Multi-product message (ate 30 vagas)
- Catalog message (link para catalogo completo)
- Sincronizacao vagas → catalogo Meta

**Cenario Julia:**
```
Julia: "Dr Carlos, separei as melhores vagas pra vc essa semana:"
[Multi-product message com 5 vagas]
- Cada vaga com: foto do hospital, nome da vaga, valor, horario
- Medico pode tocar em cada vaga para ver detalhes
- Botao "Tenho interesse" em cada vaga
```

**Diferencial agentico:** NENHUM concorrente usa catalogo de vagas no WhatsApp. Isso e inovacao pura — mostrar plantoes como produtos com fotos dos hospitais.

**Testes:** ~15 testes
**Arquivos:** `app/services/meta/catalog_service.py`, `app/api/routes/meta_catalog.py`

---

## Sprint 69: Polish & Dashboard

**Objetivo:** Dashboard, autenticacao avancada, e polimento final.

### Epic 69.1: Authentication Templates (OTP)

**O que:** Templates de autenticacao com one-tap, zero-tap, e copy code.

**Funcionalidades:**
- Template categoria AUTHENTICATION com OTP
- One-tap: botao que auto-preenche codigo (Android)
- Zero-tap: auto-verifica sem acao do usuario (Android 10+)
- Copy code: botao que copia codigo (iOS + Android)
- Integracao com confirmacao de plantao (OTP para confirmar presenca)

**Cenario Julia:**
```
Julia: "Dr Carlos, confirma sua presenca no plantao de amanha?"
[Authentication template com OTP]
[Botao one-tap: "Confirmar presenca"]
→ Medico toca → confirmado automaticamente
```

**Diferencial agentico:** Confirmacao de plantao com 1 toque, sem digitar nada. Taxa de confirmacao deve subir de ~60% para ~90%.

**Testes:** ~10 testes

---

### Epic 69.2: Dashboard UI — Meta Management

**O que:** Interface visual para gerenciar chips Meta, templates, analytics.

**Funcionalidades:**
- Pagina de chips Meta (status, quality rating, messaging tier, token)
- Pagina de templates (CRUD visual, status, quality score, analytics)
- Pagina de campaigns com seletor de template Meta
- Graficos de analytics (delivery rate, cost, volume)
- Quality rating timeline (verde → amarelo → vermelho)

**Testes:** E2E + unit
**Arquivos:** `dashboard/app/meta/`, multiplos componentes

---

### Epic 69.3: Cost Optimization Engine

**O que:** Motor de otimizacao de custo que decide qual tipo de mensagem usar.

**Funcionalidades:**
- Tracking de custo por mensagem (marketing vs utility vs service)
- Priorizacao: responder dentro da janela (GRATUITO) > utility template > marketing template
- Budget alerts (custo diario/semanal/mensal)
- Relatorio de custo por campanha, por chip, por template
- Sugestao automatica: "Esta campanha custaria R$X com Marketing template, R$Y com Utility template"

**Diferencial agentico:** Julia MINIMIZA custo automaticamente. Se pode responder dentro da janela (gratuito), espera ate 23h59 da janela antes de enviar. Twilio cobra por tudo — Julia otimiza.

**Testes:** ~15 testes

---

## Sprint 70+: Fronteira da Inovacao

### Features exploratorias (alem de qualquer concorrente)

| Feature | Descricao | Impacto |
|---------|-----------|---------|
| **Carousel Messages** | Ate 10 cards horizontais com imagem + CTA | Mostrar 10 vagas side-by-side |
| **AI Agent Handoff Protocol** | Julia transfere para outro agente AI (Helena analytics) | Multi-agent orchestration via WhatsApp |
| **Proactive Window Management** | Julia envia "check-in" estrategico para manter janela aberta | Reduz necessidade de templates pagos |
| **Template Auto-Optimization** | ML analisa qual template performa melhor e sugere reescrita | Auto-melhoria continua |
| **Conversation Routing Intelligence** | Julia decide qual chip usar baseado em historico de conversa | Chip A ja falou com Dr X → prioriza A |
| **Multi-WABA Strategy** | Multiplas WABAs para segmentacao (discovery vs oferta vs suporte) | Isolamento de quality por tipo de campanha |
| **BSUIDs Migration** | Preparar para Business Scoped User IDs (2026) | Compliance futuro |

---

## Metricas de Sucesso — Visao Completa

| Metrica | Sprint 66 | Sprint 67 | Sprint 68 | Sprint 69 | Sprint 70+ |
|---------|-----------|-----------|-----------|-----------|------------|
| Providers | 3 | 3 | 3 | 3 | 3+ |
| Testes Meta | 105 | ~170 | ~250 | ~300 | ~350 |
| Templates | CRUD basico | + analytics | + rich media | + OTP | + auto-optimize |
| Interactive | Provider only | Agente Julia | + Flows | + Catalog | + Carousel |
| Quality | Manual | Auto-monitor | Auto-heal | Dashboard | ML prediction |
| Cost | Nenhum | Tracking | Optimization | Budget alerts | Auto-minimize |
| Delivery rate | Baseline | +5% (analytics) | +9% (MM Lite) | +15% (combined) | +20% (ML) |

---

## Comparacao: Julia vs Twilio vs Concorrentes

| Feature | Julia (Sprint 69) | Twilio | MessageBird | Vonage |
|---------|-------------------|--------|-------------|--------|
| Send text/template | Sim | Sim | Sim | Sim |
| Interactive messages | Agentico (decide quando) | Manual | Manual | Manual |
| WhatsApp Flows | Agentico (decide quando) | Manual | Nao | Nao |
| Quality auto-healing | Sim | Nao | Nao | Nao |
| Cost optimization | Agentico | Nao | Nao | Nao |
| Window management | Proativo | Nao | Nao | Nao |
| Template analytics + ML | Auto-otimiza | Dashboard | Dashboard | Basico |
| Catalog/Commerce | Vagas como produtos | Generico | Nao | Nao |
| OTP one-tap | Confirmacao plantao | Generico | Generico | Generico |
| MM Lite | Sim | Nao | Nao | Nao |
| Multi-agent | Julia ↔ Helena | Nao | Nao | Nao |

**Conclusao:** No Sprint 69, Julia tera a integracao Meta Cloud API mais sofisticada do mercado para staffing medico. O diferencial nao e apenas "usar a API" — e a inteligencia agentica que DECIDE como, quando, e qual feature usar para cada situacao.

---

## Dependencias Externas (todas as sprints)

| Dependencia | Sprint | Status |
|-------------|--------|--------|
| Meta Business Account | 66-fix | Precisa criar |
| Meta Business Verification | 66-fix | Precisa submeter |
| WABA + Phone Number | 66-fix | Precisa configurar |
| System User Token | 66-fix | Precisa gerar |
| MM Lite opt-in | 68 | Precisa solicitar |
| WhatsApp Flows approval | 68 | Precisa submeter |
| Catalog setup | 68 | Precisa configurar |
| BSUID migration | 70+ | Aguardando Meta rollout (2026) |
