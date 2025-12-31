# Arquitetura Julia Warmer - Pós Sprint 25+26

Este documento descreve a arquitetura completa do sistema Julia após a conclusão das Sprints 25 e 26.

**Última atualização:** 31/12/2025

---

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              JULIA SYSTEM                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         UNIFIED INBOX/OUTBOX                            │    │
│  │   • Fila única de mensagens entrada/saída                               │    │
│  │   • Abstração total do chip físico                                      │    │
│  │   • Julia não sabe qual chip está usando                                │    │
│  │   • Chip Affinity: médico fica no mesmo chip quando possível            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         CHIP ORCHESTRATOR                               │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │    │
│  │  │ Pool Mgr    │ │ Auto-Replace│ │Auto-Provision│ │Health Monitor│      │    │
│  │  │ N chips     │ │ + Migração  │ │ via Salvy   │ │ métricas/ban│       │    │
│  │  │ dinâmico    │ │ Anunciada   │ │             │ │             │       │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                          CHIP SELECTOR                                  │    │
│  │   Decisão baseada em:                                                   │    │
│  │   • Trust Score do chip (com "quilometragem segura")                    │    │
│  │   • Chip Affinity (médico prefere mesmo chip)                           │    │
│  │   • Tipo de mensagem (prospecção vs followup vs grupos)                 │    │
│  │   • Rate limits individuais                                             │    │
│  │   • Cooldown period (4h ativo → 1-2h pausa)                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
└──────────────────────────────────────┼──────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              POOL DE CHIPS                                       │
│                                                                                  │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│   │   ACTIVE (3-5)  │  │   READY (2-3+)  │  │  WARMING (5-10) │                 │
│   │                 │  │   (dinâmico)    │  │                 │                 │
│   │ • Trust > 70    │  │ • Trust 50-70   │  │ • Trust < 50    │                 │
│   │ • Prod traffic  │  │ • Standby       │  │ • Simulação     │                 │
│   │ • Full rate     │  │ • Quick swap    │  │ • 22 dias       │                 │
│   │ • Cooldown cycle│  │ • Testados      │  │ • Dia 0: Repouso│                 │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
│          │                    │                     │                            │
│          │                    │                     │                            │
│          ▼                    ▼                     ▼                            │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      EVOLUTION API INSTANCES                            │   │
│   │   • Cada chip = 1 instância Evolution                                   │   │
│   │   • Webhook unificado com roteamento                                    │   │
│   │   • Health check contínuo                                               │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Warming Engine

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            WARMING ENGINE                                        │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                     HUMAN SIMULATOR                                     │   │
│   │   • Gera conversas realistas entre personas                             │   │
│   │   • Padrões de digitação humanos (WPM, pausas, typos)                   │   │
│   │   • Horários brasileiros (pico 19-21h)                                  │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                     CONVERSATION GENERATOR                              │   │
│   │   • 15 tipos de conversa (casual, profissional, etc)                    │   │
│   │   • Contextualização por persona                                        │   │
│   │   • Variação natural de comprimento/tom                                 │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                        PAIRING ENGINE                                   │   │
│   │   • Matching de chips para warming mútuo                                │   │
│   │   • Rotação de pares (evita padrões)                                    │   │
│   │   • Balanceamento de carga                                              │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      WARMING SCHEDULER                                  │   │
│   │                                                                         │   │
│   │   DIA 0:      Repouso inicial (24-48h sem atividade)                    │   │
│   │   Dia 1-3:    Setup básico (perfil, foto, status, primeiro QR)         │   │
│   │   Dia 4-7:    Primeiros contatos (max 10 msgs/dia)                      │   │
│   │   Dia 8-14:   Expansão (max 30 msgs/dia, grupos, mídias)               │   │
│   │   Dia 15-21:  Pré-operação (max 50 msgs/dia, áudios)                   │   │
│   │   Dia 22:     TESTE DE GRADUAÇÃO                                        │   │
│   │   Dia 22+:    Pronto para produção (Trust Score > 85)                   │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Teste de Graduação (Dia 22)

Antes de promover para READY, chip passa por teste formal:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         TESTE DE GRADUAÇÃO                                       │
│                                                                                  │
│   REQUISITOS PARA INICIAR:                                                       │
│   ✓ Trust Score ≥ 85                                                            │
│   ✓ Fase warmup = 'pre_operacao'                                                │
│   ✓ Dias de warming ≥ 21                                                        │
│                                                                                  │
│   TESTE:                                                                         │
│   1. Envia 5 mensagens para contatos de warming                                 │
│   2. Aguarda 6 horas                                                            │
│   3. Verifica:                                                                   │
│      • Taxa de entrega = 100%                                                   │
│      • Nenhum warning recebido                                                  │
│      • Nenhum bloqueio                                                          │
│                                                                                  │
│   RESULTADO:                                                                     │
│   ✅ Passou  → status = 'ready'                                                 │
│   ❌ Falhou  → Mais 3-7 dias de warming, depois retesta                         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Trust Score Engine

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          TRUST SCORE ENGINE                                      │
│                                                                                  │
│   Score: 0-100 (quanto maior, mais confiável)                                    │
│                                                                                  │
│   FATORES POSITIVOS:                      FATORES NEGATIVOS:                     │
│   ┌─────────────────────────────┐         ┌─────────────────────────────┐        │
│   │ • Idade total (10%)         │         │ • Rate limit atingido (-)   │        │
│   │ • Idade em produção (10%)   │         │ • Mensagens não entregues   │        │
│   │   (quilometragem segura)    │         │ • Bloqueios recebidos (-)   │        │
│   │ • Taxa resposta (20%)       │         │ • Warnings do WhatsApp (--) │        │
│   │ • Taxa delivery (15%)       │         │ • Padrões suspeitos (--)    │        │
│   │ • Conversas bidirecionais   │         │ • Horários irregulares (-)  │        │
│   │   (20%)                     │         │                             │        │
│   │ • Dias sem erro (10%)       │         │ Penalidades:                │        │
│   │ • Variedade mídia (10%)     │         │ • -5% por warning           │        │
│   │ • Grupos participando (+)   │         │ • -10% por erro grave       │        │
│   └─────────────────────────────┘         └─────────────────────────────┘        │
│                                                                                  │
│   DIFERENÇA "IDADE TOTAL" vs "IDADE EM PRODUÇÃO":                               │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ Chip A: 60 dias total, 3 dias em produção  → pouca quilometragem       │   │
│   │ Chip B: 30 dias total, 25 dias em produção → MUITO mais confiável      │   │
│   │                                                                         │   │
│   │ Chip B tem mais "quilometragem segura" mesmo sendo mais novo           │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   LIMIARES:                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  0-30: QUARENTENA (só warming interno)                                  │   │
│   │ 30-50: WARMING (conversas simuladas)                                    │   │
│   │ 50-70: READY (standby, pode assumir se necessário)                      │   │
│   │ 70-90: ACTIVE (tráfego de produção)                                     │   │
│   │ 90+:   PREMIUM (mensagens críticas, prospecção fria)                    │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Chip Affinity (Novo)

Conceito para manter consistência na experiência do médico:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CHIP AFFINITY                                         │
│                                                                                  │
│   REGRA: Quando médico responde para Chip A, conversas futuras                  │
│          com esse médico PREFEREM Chip A (mesmo que Chip B tenha Trust maior)   │
│                                                                                  │
│   BENEFÍCIOS:                                                                    │
│   • Evita "Júlia trocando de número toda hora"                                  │
│   • Médico reconhece o número                                                   │
│   • Aumenta confiança                                                           │
│                                                                                  │
│   QUANDO QUEBRA AFFINITY:                                                        │
│   • Chip A foi banido                                                           │
│   • Chip A degradou (Trust < threshold)                                         │
│   • Chip A está em cooldown e mensagem é urgente                                │
│                                                                                  │
│   IMPLEMENTAÇÃO:                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ tabela: medico_chip_affinity                                            │   │
│   │ - medico_id UUID                                                        │   │
│   │ - chip_id UUID                                                          │   │
│   │ - ultima_interacao TIMESTAMPTZ                                          │   │
│   │ - msgs_trocadas INT                                                     │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Chip Cooldown (Novo)

Simula comportamento humano com pausas obrigatórias:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CHIP COOLDOWN                                          │
│                                                                                  │
│   PROBLEMA: Números que enviam 12h seguidas sem parar = padrão claro de bot     │
│                                                                                  │
│   SOLUÇÃO: Forçar pausas periódicas                                             │
│                                                                                  │
│   REGRA:                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  Após 4 horas de uso contínuo:                                          │   │
│   │  → Chip entra em "cooldown" por 1-2 horas                               │   │
│   │  → NÃO é selecionado para novas conversas                               │   │
│   │  → CONTINUA respondendo conversas existentes                            │   │
│   │  → Simula "pessoa foi almoçar/reunião"                                  │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   CAMPOS NO BANCO:                                                               │
│   • last_activity_start TIMESTAMPTZ                                             │
│   • cooldown_until TIMESTAMPTZ                                                  │
│   • em_cooldown BOOLEAN (computed)                                              │
│                                                                                  │
│   EXCEÇÃO: Se não houver chips disponíveis, ignora cooldown                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Early Warning System

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        EARLY WARNING SYSTEM                                      │
│                                                                                  │
│   DETECÇÃO:                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ • Taxa de entrega caindo                                                │   │
│   │ • Aumento de bloqueios                                                  │   │
│   │ • Warnings de rate limit                                                │   │
│   │ • Padrões anômalos de uso                                               │   │
│   │ • Desconexões frequentes                                                │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                          │                                                       │
│                          ▼                                                       │
│   AÇÕES AUTOMÁTICAS:                                                             │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ • Reduzir rate do chip afetado                                          │   │
│   │ • Mover para READY (sair de produção)                                   │   │
│   │ • Iniciar warming de substituto                                         │   │
│   │ • Alertar no Slack                                                      │   │
│   │ • Redistribuir tráfego                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                          │                                                       │
│                          ▼                                                       │
│   EM CASO DE BAN:                                                                │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 1. Chip READY assume imediatamente (zero downtime)                      │   │
│   │ 2. Chip banido vai para QUARENTENA                                      │   │
│   │ 3. Salvy provisiona novo número automaticamente                         │   │
│   │ 4. Novo chip entra em WARMING (com Dia 0 de repouso)                    │   │
│   │ 5. Sistema continua operando normalmente                                │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Auto-Replace com Migração Anunciada (Novo)

Quando chip degrada (não bane), notifica o médico da troca:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     MIGRAÇÃO ANUNCIADA (DEGRADAÇÃO)                              │
│                                                                                  │
│   QUANDO USAR: Chip degradando mas ainda funcional                              │
│   QUANDO NÃO USAR: Ban abrupto (não dá tempo)                                   │
│                                                                                  │
│   FLUXO:                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                         │   │
│   │  1. Chip A (degradado) envia última mensagem:                           │   │
│   │     "Oi Dr João! Vou trocar de número essa semana,                      │   │
│   │      me salva esse novo aqui: 11999... Continuo te                      │   │
│   │      avisando das vagas por lá!"                                        │   │
│   │                                                                         │   │
│   │  2. Aguarda 24-48h                                                      │   │
│   │                                                                         │   │
│   │  3. Chip B (novo) envia primeira mensagem:                              │   │
│   │     "Oi Dr João, sou a Júlia! Continuando nossa                         │   │
│   │      conversa sobre aquela vaga de PS..."                               │   │
│   │                                                                         │   │
│   │  4. Chip A é desativado após confirmação de Chip B                      │   │
│   │                                                                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   CONDIÇÕES PARA MIGRAÇÃO ANUNCIADA:                                            │
│   • Chip degradando (não banido)                                                │
│   • Médico tem histórico de respostas (relacionamento existe)                   │
│   • Não é prospecção fria                                                       │
│                                                                                  │
│   SE BAN ABRUPTO: Pula direto para passo 3                                      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Ready Pool Dinâmico (Novo)

Tamanho do pool ready ajusta baseado na taxa de degradação:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        READY POOL DINÂMICO                                       │
│                                                                                  │
│   REGRA: Quanto mais chips queimando, maior o buffer                            │
│                                                                                  │
│   CÁLCULO:                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                         │   │
│   │   Taxa de degradação últimos 30 dias:                                   │   │
│   │                                                                         │   │
│   │   0-1 chips degradados/mês   → Manter 3 ready                          │   │
│   │   2-3 chips degradados/mês   → Manter 5 ready                          │   │
│   │   4+ chips degradados/mês    → Manter 8 ready                          │   │
│   │                                                                         │   │
│   │   + Alerta se degradação > 4/mês:                                       │   │
│   │     "Investigar: por que tantos chips degradando?"                      │   │
│   │                                                                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   NOTA: No MVP, manter 3 fixos. Após 3 meses de dados, habilitar ajuste        │
│         dinâmico.                                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Meta Policies RAG - Casos de Uso

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      META POLICIES RAG - CASOS DE USO                            │
│                                                                                  │
│   PRIORIDADE 1: POST-MORTEM (implementar primeiro)                              │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │   Quando chip é banido:                                                 │   │
│   │   → Recupera últimas 50 mensagens enviadas                              │   │
│   │   → RAG analisa: "Qual violou política?"                                │   │
│   │   → Aprende padrão para evitar no futuro                                │   │
│   │   → Gera relatório para revisão humana                                  │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   PRIORIDADE 2: WARM-UP GUIDANCE                                                │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │   Durante warming:                                                      │   │
│   │   → RAG sugere tipos de conteúdo seguros para cada fase                 │   │
│   │   → "Nesta fase, evite links. Use apenas texto e emojis."               │   │
│   │   → Guia geração de conversas simuladas                                 │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   PRIORIDADE 3: VALIDAÇÃO PRÉ-ENVIO (mais complexo, deixar pra depois)         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │   Antes de Julia enviar mensagem:                                       │   │
│   │   → Extrai features da mensagem (keywords, links, etc)                  │   │
│   │   → Consulta RAG: "Esta mensagem viola políticas Meta?"                 │   │
│   │   → Se sim (confiança > 80%): bloqueia envio, reescreve                 │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Group Entry Engine

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         GROUP ENTRY ENGINE                                       │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      SOURCE DISCOVERY                                   │   │
│   │   • Crawler periódico de sites agregadores                              │   │
│   │   • Google/Bing search para novas fontes                                │   │
│   │   • Fontes: escaladeplantao.com.br, gruposmedicos.com.br, etc          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      CSV/EXCEL IMPORTER                                 │   │
│   │   • Upload de arquivos com links de grupos                              │   │
│   │   • Validação de formato (chat.whatsapp.com/*)                          │   │
│   │   • Deduplicação automática                                             │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      LINK VALIDATOR                                     │   │
│   │   • Validação de link ativo via Evolution API                           │   │
│   │   • Extração de metadados (nome, participantes)                         │   │
│   │   • Detecção de grupos inválidos/expirados                              │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      ENTRY SCHEDULER                                    │   │
│   │                                                                         │   │
│   │   LIMITES POR FASE:                                                     │   │
│   │   setup:              0 grupos/dia                                      │   │
│   │   primeiros_contatos: 0 grupos/dia                                      │   │
│   │   expansao:           2 grupos/dia (delay 10 min entre entradas)        │   │
│   │   pre_operacao:       5 grupos/dia (delay 5 min)                        │   │
│   │   operacao:          10 grupos/dia (delay 3 min)                        │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      ENTRY WORKER                                       │   │
│   │   • Distribuição multi-chip                                             │   │
│   │   • Circuit breaker por chip (3 erros → pausa 30 min)                   │   │
│   │   • Integração Trust Score (só chips ≥ limite da fase)                  │   │
│   │   • Logs detalhados para auditoria                                      │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Tabelas do Group Entry Engine

```
group_sources            # Fontes de links (sites agregadores)
group_links              # Links de grupos importados/descobertos
group_entry_queue        # Fila de entradas pendentes
group_entry_history      # Histórico de entradas (sucesso/falha)
```

### Notificações Slack

O crawler notifica ao terminar execuções:
- **Quinzenal (sites conhecidos)**: Links extraídos, novos vs duplicados
- **Semanal (discovery)**: Novas fontes descobertas via Google/Bing

---

## Integrações Externas

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         INTEGRAÇÕES EXTERNAS                                     │
│                                                                                  │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│   │     SALVY       │  │  EVOLUTION API  │  │ META POLICIES   │                 │
│   │                 │  │                 │  │     (RAG)       │                 │
│   │ • Provisioning  │  │ • Multi-instance│  │                 │                 │
│   │ • Virtual nums  │  │ • Webhooks      │  │ • Post-mortem   │                 │
│   │ • SMS verify    │  │ • QR/Pairing    │  │ • Warm-up guide │                 │
│   │ • Auto-purchase │  │ • Health check  │  │ • Pré-validação │                 │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
│          │                    │                     │                            │
│          └────────────────────┼─────────────────────┘                            │
│                               │                                                  │
│                               ▼                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                           SLACK                                         │   │
│   │   • Alertas de Early Warning                                            │   │
│   │   • Status do pool de chips                                             │   │
│   │   • Notificações de ban/recovery                                        │   │
│   │   • Métricas de warming                                                 │   │
│   │   • Comandos de gestão (/chip-status, /rotate, etc)                     │   │
│   │   • Post-mortem reports                                                 │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Ciclo de Vida do Chip

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          CICLO DE VIDA DO CHIP                                    │
│                                                                                   │
│    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│    │PROVISIONED│────▶│ REPOUSO  │────▶│ WARMING  │────▶│  TESTE   │               │
│    │ (Salvy)  │     │ (Dia 0)  │     │ (21 dias)│     │GRADUAÇÃO │               │
│    └──────────┘     │ 24-48h   │     └──────────┘     └──────────┘               │
│                     └──────────┘            │               │                     │
│                                             │               │                     │
│                                             │          ✅   │  ❌                  │
│                                             │               │                     │
│                                             │         ┌─────┴─────┐               │
│                                             │         ▼           │               │
│                                        ┌────┴───┐ ┌──────────┐    │               │
│                                        │ READY  │ │  ACTIVE  │◀───┘               │
│                                        │(standby)│ │  (prod)  │                   │
│                                        └────────┘ └──────────┘                    │
│                                             ▲           │                         │
│                                             │           │                         │
│                                             │           ▼                         │
│                                        ┌────┴───────────────┐                     │
│                                        │     DEGRADED       │                     │
│                                        │  (Trust baixo)     │                     │
│                                        └────────────────────┘                     │
│                                                  │                                │
│                                                  ▼                                │
│                                        ┌────────────────────┐                     │
│                                        │      BANNED        │                     │
│                                        │ (número perdido)   │                     │
│                                        └────────────────────┘                     │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo de Mensagem (Produção)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                       FLUXO DE MENSAGEM - PRODUÇÃO                                │
│                                                                                   │
│   1. Julia quer enviar mensagem para Dr. João                                    │
│      │                                                                            │
│      ▼                                                                            │
│   2. Chip Selector verifica AFFINITY:                                            │
│      → Dr. João já conversou com algum chip?                                     │
│      → Se sim e chip está ativo: usa esse chip                                   │
│      │                                                                            │
│      ▼                                                                            │
│   3. Se não há affinity, seleciona por critérios:                                │
│      • Tipo: prospecção → chip com Trust 80+                                     │
│      • Tipo: followup → qualquer chip ACTIVE                                     │
│      • Verifica: chip está em cooldown?                                          │
│      │                                                                            │
│      ▼                                                                            │
│   4. Orchestrator aplica rate limit do chip                                      │
│      │                                                                            │
│      ▼                                                                            │
│   5. Evolution API envia pelo chip selecionado                                   │
│      │                                                                            │
│      ▼                                                                            │
│   6. Webhook recebe confirmação/erro                                             │
│      │                                                                            │
│      ▼                                                                            │
│   7. Trust Score atualizado + Affinity registrada                                │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Faseamento de Escala

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         FASEAMENTO DE ESCALA                                      │
│                                                                                   │
│   FASE 1: MVP (Meses 1-3)                                                        │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │ • 3 active, 2 ready, 5 warming = 10 chips total                         │    │
│   │ • ~240 conversas/dia                                                    │    │
│   │ • Valida: warming, trust score, auto-replace                            │    │
│   │ • Ready pool: fixo em 3                                                 │    │
│   │ • Custo: ~R$250/mês (10 × R$25)                                         │    │
│   └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                   │
│   FASE 2: Escala Inicial (Meses 4-6)                                             │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │ • 10 active, 3 ready, 15 warming = 28 chips total                       │    │
│   │ • ~800 conversas/dia                                                    │    │
│   │ • Valida: infra Evolution, custos, ROI                                  │    │
│   │ • Habilita: ready pool dinâmico                                         │    │
│   │ • Custo: ~R$700/mês                                                     │    │
│   └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                   │
│   FASE 3: Escala Full (Meses 7-12)                                               │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │ • 30-50 active conforme demanda                                         │    │
│   │ • 2.400-4.000 conversas/dia                                             │    │
│   │ • Todas features habilitadas                                            │    │
│   │ • Custo: ~R$2.500-3.000/mês                                             │    │
│   └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Integração: Listeners vs Julia

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    LISTENERS SYSTEM vs JULIA SYSTEM                               │
│                                                                                   │
│   ┌──────────────────────┐              ┌──────────────────────┐                 │
│   │   LISTENERS SYSTEM   │              │    JULIA SYSTEM      │                 │
│   │   (Passivo)          │              │    (Ativo)           │                 │
│   ├──────────────────────┤              ├──────────────────────┤                 │
│   │ 40-200 números       │              │ 10-28 números        │                 │
│   │ Monitora grupos      │─── vagas ───▶│ Conversa com médicos │                 │
│   │ Extrai ofertas       │              │ Follow-up            │                 │
│   │ Pipeline 7 estágios  │              │ Trust-based sending  │                 │
│   │                      │              │ Auto-replace         │                 │
│   │ • Só recebe msgs     │              │ • Envia e recebe     │                 │
│   │ • Risco menor        │              │ • Risco maior        │                 │
│   │ • Warming simples    │              │ • Warming completo   │                 │
│   └──────────────────────┘              └──────────────────────┘                 │
│              │                                    │                              │
│              │                                    │                              │
│              └────────────┬───────────────────────┘                              │
│                           ▼                                                      │
│                  ┌──────────────────┐                                            │
│                  │   SUPABASE DB    │                                            │
│                  │                  │                                            │
│                  │ • grupos_whatsapp│                                            │
│                  │ • mensagens_grupo│                                            │
│                  │ • vagas_grupo    │                                            │
│                  │ • vagas          │                                            │
│                  │ • medicos        │                                            │
│                  │ • conversas      │                                            │
│                  │ • chips          │                                            │
│                  │ • warming_log    │                                            │
│                  └──────────────────┘                                            │
│                                                                                   │
│   IMPORTANTE: Pools separados, risco separado, warm-up diferente                │
│   • Listeners NUNCA enviam mensagens ativas                                      │
│   • Julia NUNCA monitora grupos                                                  │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Métricas Alvo

| Métrica | Atual | Meta MVP | Meta Full |
|---------|-------|----------|-----------|
| Chips ativos | 1 | 3 | 30-50 |
| Chips em warming | 0 | 5 | 50+ |
| Chips ready (backup) | 0 | 2 | 3-8 (dinâmico) |
| Downtime por ban | Total | < 5 minutos | < 1 minuto |
| Tempo de recovery | Manual | Automático | Automático |
| Trust Score tracking | Não existe | Tempo real | Tempo real |
| Provisionamento | Manual | Automático | Automático |
| Conversas/dia | ~80 | ~240 | 2.400-4.000 |

---

## Tabelas Principais (Banco de Dados)

```
# ═══ POOL DE CHIPS ═══
chips                    # Pool de chips com status e trust score
chip_transitions         # Histórico de transições de estado
chip_trust_history       # Histórico de trust score
chip_alerts              # Alertas do sistema de warning
chip_pairs               # Pareamentos para warm-up
chip_interactions        # Interações granulares (msgs, erros)
warmup_conversations     # Conversas geradas no warming
conversation_chips       # Mapeamento conversa ↔ chip
medico_chip_affinity     # Affinity médico ↔ chip
chip_metrics_hourly      # Métricas agregadas por hora
orchestrator_operations  # Log de operações do orchestrator

# ═══ META POLICIES ═══
meta_policies            # RAG de políticas Meta
pool_config              # Configuração do pool

# ═══ GROUP ENTRY ENGINE ═══
group_sources            # Fontes de links (sites agregadores)
group_links              # Links de grupos importados/descobertos
group_entry_queue        # Fila de entradas pendentes
group_entry_history      # Histórico de entradas (sucesso/falha)
```

---

## Sprints de Implementação

### Sprint 25 - Foundation (~55h)
- E01: Modelo de Dados Unificado (+ campos: idade_producao, cooldown, affinity, tipo)
- E02: Integração Salvy
- E03: Meta Policies RAG (foco em post-mortem)
- E04: Trust Score Engine (+ quilometragem segura)
- E05: Human Simulator
- E06: Conversation Generator
- E07: Pairing Engine
- E08: Warming Scheduler (+ Dia 0 repouso, limites grupos)
- E09: Warming Orchestrator (+ teste de graduação)
- E10: Early Warning System
- E11: Warmer API
- E12: Group Entry Engine - S12.1-S12.5 (entrada segura, CSV/Excel, limites 6h)

### Sprint 26 - Orchestration (~44h)
- E01: Chip Orchestrator (+ ready pool dinâmico)
- E02: Chip Selector (+ cooldown + affinity)
- E03: Webhook Router
- E04: Health Monitor
- E05: Dashboard Unificado
- E06: Webhook Robustness
- E07: Migração Anunciada
- S12.6: Crawler & Source Discovery (parte do E12)

---

*Documento gerado em: 31/12/2025*
*Atualizado em: 31/12/2025*
*Referência: Sprint 25 e Sprint 26 Planning*
*Inclui melhorias discutidas: Trust Score quilometragem, Cooldown, Dia 0, Migração Anunciada, Ready Pool Dinâmico, Teste Graduação, Chip Affinity, Group Entry Engine*
