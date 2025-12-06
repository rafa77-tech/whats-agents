# Fluxos de Negócio - Agente Júlia

Este documento detalha **passo-a-passo** cada processo do sistema.

---

## Contexto Estratégico

### Ciclo de Vida da Vaga

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CICLO DE VIDA DA VAGA                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ORIGEM: Escala Médica do Hospital                                       │
│                                                                          │
│  Hospital define dimensionamento:                                        │
│  • X médicos no período Y em Z dias da semana                           │
│                                                                          │
│  IDEAL: 30 dias antes                URGENTE: próximo do dia            │
│         │                                      │                         │
│         ▼                                      ▼                         │
│  ┌────────────────┐                  ┌────────────────┐                 │
│  │ Tempo para     │                  │ Tempo para     │                 │
│  │ prospecção     │                  │ prospecção     │                 │
│  │ adequada       │                  │ limitado       │                 │
│  │                │                  │                │                 │
│  │ • Ofertas      │                  │ • Valores mais │                 │
│  │   planejadas   │                  │   flexíveis    │                 │
│  │ • Negociação   │                  │ • Urgência na  │                 │
│  │   tranquila    │                  │   comunicação  │                 │
│  └────────────────┘                  └────────────────┘                 │
│                                                                          │
│  FONTES DE URGÊNCIA:                                                    │
│  1. Escala não preenchida a tempo                                       │
│  2. Médico ficou doente                                                 │
│  3. Médico cancelou de última hora                                      │
│  4. Problemas pessoais do plantonista                                   │
│                                                                          │
│  COMPORTAMENTO DA URGÊNCIA:                                             │
│  Dia -30: prioridade = normal                                           │
│  Dia -15: prioridade = alta                                             │
│  Dia -7:  prioridade = urgente                                          │
│  Dia -3:  prioridade = crítica                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Contexto de Mercado

| Aspecto | Realidade |
|---------|-----------|
| Saturação | Médicos recebem mensagens de empresas de staffing **o tempo todo** |
| Relacionamento | Todos devem ser considerados **contatos frios** (ninguém conhece a Júlia) |
| Diferencial | Parecer humana é crítico para se destacar no mar de spam |
| Consequência | Tom informal, personalização e timing são essenciais |

**Implicações para Júlia:**
- Mensagens devem ser **únicas** e **personalizadas** (nunca template óbvio)
- Volume baixo e controlado (qualidade > quantidade)
- Timing importa: respeitar horários, não ser insistente
- Primeira impressão é crucial: uma msg mal escrita = bloqueio

---

## Fluxo 1: Cadastro de Vagas

### Origem da Demanda
Vagas vêm de contratos com hospitais e parceiros. Gestor cadastra no Supabase.

### Processo

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CADASTRO DE VAGAS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GESTOR                           SISTEMA                          │
│    │                                │                              │
│    │  1. Acessa Supabase/Admin      │                              │
│    │─────────────────────────────▶│                              │
│    │                                │                              │
│    │  2. Preenche vaga:             │                              │
│    │     • Hospital                 │                              │
│    │     • Data/horário             │                              │
│    │     • Especialidade            │                              │
│    │     • Valor (min/max)          │                              │
│    │     • Setor (CC, SADT, etc)    │                              │
│    │     • Prioridade               │                              │
│    │─────────────────────────────▶│                              │
│    │                                │                              │
│    │                                │  3. Valida dados             │
│    │                                │                              │
│    │                                │  4. Salva em `vagas`         │
│    │                                │     status = 'aberta'        │
│    │                                │                              │
│    │                                │  5. Se prioridade = 'urgente'│
│    │                                │     → Dispara oferta ativa   │
│    │◀─────────────────────────────│                              │
│    │  6. Confirmação                │                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Campos da Vaga

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| hospital_id | FK | Sim | Hospital da vaga |
| especialidade_id | FK | Sim | Especialidade requerida |
| setor_id | FK | Não | Setor específico |
| data_plantao | date | Sim | Data do plantão |
| periodo_id | FK | Sim | Diurno, Noturno, etc |
| valor_min | decimal | Sim | Valor mínimo |
| valor_max | decimal | Sim | Valor máximo (negociação) |
| prioridade | enum | Sim | normal, alta, urgente |
| status | enum | Auto | aberta, reservada, preenchida, cancelada |

---

## Fluxo 2: Importação de Médicos

### Status
✅ **Dados já importados no Supabase** - 29.645 médicos, incluindo 1.660 anestesistas (81% com CRM).

### Processo (para futuras importações)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IMPORTAÇÃO DE MÉDICOS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GESTOR                  SCRIPT                    SUPABASE         │
│    │                       │                          │             │
│    │  1. Prepara CSV       │                          │             │
│    │     com colunas:      │                          │             │
│    │     • nome            │                          │             │
│    │     • telefone        │                          │             │
│    │     • crm             │                          │             │
│    │     • especialidade   │                          │             │
│    │                       │                          │             │
│    │  2. Executa script    │                          │             │
│    │─────────────────────▶│                          │             │
│    │                       │                          │             │
│    │                       │  3. Valida telefone     │             │
│    │                       │     (formato Brasil)     │             │
│    │                       │                          │             │
│    │                       │  4. Verifica duplicata   │             │
│    │                       │     (telefone único)     │             │
│    │                       │─────────────────────────▶│             │
│    │                       │                          │             │
│    │                       │  5. INSERT clientes      │             │
│    │                       │     stage = 'novo'       │             │
│    │                       │     source = 'import'    │             │
│    │                       │─────────────────────────▶│             │
│    │                       │                          │             │
│    │                       │  6. Cria entrada em      │             │
│    │                       │     fila_prospeccao      │             │
│    │                       │     status = 'pendente'  │             │
│    │                       │─────────────────────────▶│             │
│    │                       │                          │             │
│    │◀──────────────────────│                          │             │
│    │  7. Relatório:        │                          │             │
│    │     • Importados: X   │                          │             │
│    │     • Duplicados: Y   │                          │             │
│    │     • Erros: Z        │                          │             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Validações

| Validação | Ação se falhar |
|-----------|----------------|
| Telefone formato inválido | Pula, registra erro |
| Telefone já existe | Pula, conta como duplicado |
| CRM inválido | Importa sem CRM, flag `crm_pendente` |
| Especialidade não encontrada | Cria nova ou mapeia similar |

---

## Fluxo 3: Prospecção (Abertura)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PROSPECÇÃO - ABERTURA                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  WORKER CADÊNCIA              JÚLIA                  WHATSAPP       │
│    │                           │                        │           │
│    │  1. A cada 45-180s        │                        │           │
│    │     busca próximo da      │                        │           │
│    │     fila_prospeccao       │                        │           │
│    │     WHERE status =        │                        │           │
│    │     'pendente'            │                        │           │
│    │                           │                        │           │
│    │  2. Verifica:             │                        │           │
│    │     • Horário (08-20h)    │                        │           │
│    │     • Dia (seg-sex)       │                        │           │
│    │     • Rate limit OK       │                        │           │
│    │                           │                        │           │
│    │  3. Se OK, solicita msg   │                        │           │
│    │─────────────────────────▶│                        │           │
│    │                           │                        │           │
│    │                           │  4. Carrega contexto:  │           │
│    │                           │     • Dados do médico  │           │
│    │                           │     • Diretrizes ativas│           │
│    │                           │     • Vagas disponíveis│           │
│    │                           │                        │           │
│    │                           │  5. Gera mensagem      │           │
│    │                           │     personalizada      │           │
│    │                           │     (variada, única)   │           │
│    │◀─────────────────────────│                        │           │
│    │                           │                        │           │
│    │  6. Envia via Evolution   │                        │           │
│    │─────────────────────────────────────────────────▶│           │
│    │                           │                        │           │
│    │  7. Atualiza banco:       │                        │           │
│    │     • clientes.stage =    │                        │           │
│    │       'msg_enviada'       │                        │           │
│    │     • interacoes: INSERT  │                        │           │
│    │     • fila: status =      │                        │           │
│    │       'enviado'           │                        │           │
│    │                           │                        │           │
│    │  8. Agenda follow-up      │                        │           │
│    │     em 48h                │                        │           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Exemplo de Mensagem de Abertura

```
Oi Dr Carlos! Tudo bem?

Sou a Júlia da Revoluna, trabalho com escalas médicas no ABC

Vi que vc é anestesista, temos umas vagas legais aqui. Vc tá fazendo plantões?
```

### Variações (Júlia deve gerar diferentes cada vez)

| Elemento | Variações |
|----------|-----------|
| Saudação | Oi / Olá / E aí / Boa tarde |
| Apresentação | Sou a Júlia / Aqui é a Júlia / Júlia aqui |
| Gancho | Vi que vc é... / Soube que vc trabalha com... |
| Pergunta | Tá fazendo plantões? / Como tá sua agenda? / Tem interesse? |

---

## Fluxo 4: Conversa Ativa

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CONVERSA ATIVA                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MÉDICO        WHATSAPP       EVOLUTION       FASTAPI       JÚLIA  │
│    │              │              │              │              │    │
│    │  1. Envia    │              │              │              │    │
│    │  mensagem    │              │              │              │    │
│    │─────────────▶│              │              │              │    │
│    │              │─────────────▶│              │              │    │
│    │              │              │──webhook────▶│              │    │
│    │              │              │              │              │    │
│    │              │              │              │  2. Extrai   │    │
│    │              │              │              │  telefone +  │    │
│    │              │              │              │  conteudo    │    │
│    │              │              │              │              │    │
│    │              │              │◀─mark read───│              │    │
│    │              │              │              │              │    │
│    │              │              │◀─presence────│              │    │
│    │              │              │  online      │              │    │
│    │              │              │              │              │    │
│    │              │              │◀─typing──────│              │    │
│    │              │◀─────────────│              │              │    │
│    │◀─"digitando"─│              │              │              │    │
│    │              │              │              │              │    │
│    │              │              │              │─────────────▶│    │
│    │              │              │              │  3. Processa │    │
│    │              │              │              │              │    │
│    │              │              │              │  4. Busca:   │    │
│    │              │              │              │  • Médico    │    │
│    │              │              │              │  • Conversa  │    │
│    │              │              │              │  • Histórico │    │
│    │              │              │              │  • Memória   │    │
│    │              │              │              │  • Diretrizes│    │
│    │              │              │              │  • Vagas     │    │
│    │              │              │              │              │    │
│    │              │              │              │  5. Verifica │    │
│    │              │              │              │  controlled_ │    │
│    │              │              │              │  by = 'ai'   │    │
│    │              │              │              │              │    │
│    │              │              │              │  6. Chama LLM│    │
│    │              │              │              │◀─────────────│    │
│    │              │              │              │              │    │
│    │              │              │◀─send msg────│              │    │
│    │              │◀─────────────│              │              │    │
│    │◀─────────────│              │              │              │    │
│    │  7. Recebe   │              │              │              │    │
│    │  resposta    │              │              │              │    │
│    │              │              │              │              │    │
│    │              │              │              │  8. Salva:   │    │
│    │              │              │              │  • interacao │    │
│    │              │              │              │  • memoria   │    │
│    │              │              │              │  • atualiza  │    │
│    │              │              │              │    stage     │    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Estados da Conversa

| Situação | Ação da Júlia |
|----------|---------------|
| Médico pergunta sobre vaga | Busca vagas compatíveis, apresenta |
| Médico pede mais detalhes | Fornece info (hospital, valor, setor) |
| Médico diz que tem interesse | Confirma disponibilidade, reserva |
| Médico diz que não pode | Aceita, pergunta sobre outros dias |
| Médico pede desconto | Negocia dentro de valor_min/max |
| Médico quer falar com humano | Handoff imediato |
| Médico irritado | Desculpa, oferece handoff |
| Médico manda áudio | "Desculpa, não consigo ouvir áudio aqui, pode escrever?" |

---

## Fluxo 5: Oferta de Vaga

```
┌─────────────────────────────────────────────────────────────────────┐
│                      OFERTA DE VAGA                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CONTEXTO: Júlia está conversando com médico e identifica interesse│
│                                                                     │
│  JÚLIA                         BANCO                    MÉDICO      │
│    │                            │                          │        │
│    │  1. Detecta interesse      │                          │        │
│    │     "tô procurando         │                          │        │
│    │      plantão"              │                          │        │
│    │                            │                          │        │
│    │  2. Tool: buscar_vagas     │                          │        │
│    │─────────────────────────▶│                          │        │
│    │     • especialidade        │                          │        │
│    │     • região (se souber)   │                          │        │
│    │     • período preferido    │                          │        │
│    │                            │                          │        │
│    │◀─────────────────────────│                          │        │
│    │  3. Retorna vagas          │                          │        │
│    │     ordenadas por:         │                          │        │
│    │     • prioridade           │                          │        │
│    │     • match com perfil     │                          │        │
│    │     • valor                │                          │        │
│    │                            │                          │        │
│    │  4. Escolhe 1 vaga         │                          │        │
│    │     (não mostra lista)     │                          │        │
│    │                            │                          │        │
│    │  5. Apresenta natural:     │                          │        │
│    │─────────────────────────────────────────────────────▶│        │
│    │     "Achei uma que         │                          │        │
│    │      combina..."           │                          │        │
│    │                            │                          │        │
│    │                            │                          │        │
│    │  [Se médico aceita]        │                          │        │
│    │◀─────────────────────────────────────────────────────│        │
│    │                            │                          │        │
│    │  6. Tool: reservar_plantao │                          │        │
│    │─────────────────────────▶│                          │        │
│    │     • vaga_id              │                          │        │
│    │     • medico_id            │                          │        │
│    │                            │                          │        │
│    │                            │  7. UPDATE vagas         │        │
│    │                            │     status='reservada'   │        │
│    │                            │     medico_id = X        │        │
│    │                            │                          │        │
│    │  8. Confirma para médico   │                          │        │
│    │─────────────────────────────────────────────────────▶│        │
│    │     "Reservei pra vc!"     │                          │        │
│    │                            │                          │        │
│    │  9. Tool: notificar_gestor │                          │        │
│    │     tipo='plantao_fechado' │                          │        │
│    │─────────────────────────▶│                          │        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Após Aceite da Vaga

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PÓS-ACEITE                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MÉDICO ACEITA VAGA                                                │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Júlia confirma e AVISA sobre responsabilidade:              │   │
│  │                                                              │   │
│  │ "Show! Reservei pra vc então!                               │   │
│  │                                                              │   │
│  │ Só lembrando que uma vez confirmado, se precisar cancelar   │   │
│  │ é importante encontrar um substituto, tá? Isso é regra do   │   │
│  │ CRM e a gente leva bem a sério aqui.                        │   │
│  │                                                              │   │
│  │ Qualquer coisa me avisa!"                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Sistema:                                                     │   │
│  │ • UPDATE vagas SET status = 'reservada', cliente_id = X     │   │
│  │ • Notifica gestor (Slack): "Plantão reservado!"             │   │
│  │ • Gestor assume para confirmação final com hospital         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  GESTOR confirma com hospital                                       │
│         │                                                           │
│         ▼                                                           │
│  UPDATE vagas SET status = 'confirmada'                            │
│         │                                                           │
│         ▼                                                           │
│  Júlia pode avisar médico: "Confirmado com o hospital!"            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Regras de Múltiplas Vagas

| Regra | Descrição |
|-------|-----------|
| Médico pode aceitar múltiplas vagas | Sim, sem limite |
| Júlia verifica conflito | Não oferece vagas no mesmo dia E período |
| Query de verificação | `WHERE data = X AND periodo_id = Y AND cliente_id = Z` |

**Exemplo de verificação:**
```sql
-- Antes de oferecer vaga, verificar se médico já tem plantão no mesmo dia/período
SELECT COUNT(*) FROM vagas
WHERE cliente_id = $medico_id
  AND data = $data_vaga
  AND periodo_id = $periodo_id
  AND status IN ('reservada', 'confirmada');
-- Se COUNT > 0, não oferecer esta vaga
```

### Cancelamento pelo Médico

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CANCELAMENTO                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CRÍTICO: Médico é responsável por encontrar substituto (CFM/CRM)  │
│                                                                     │
│  Médico: "Júlia, não vou conseguir ir no plantão do dia 15"        │
│         │                                                           │
│         ▼                                                           │
│  Júlia:                                                             │
│  "Opa, entendi. Lembra que a gente conversou sobre isso né?        │
│                                                                     │
│  Pelas regras do CRM, vc precisa encontrar um substituto.          │
│  Quer que eu te ajude a achar alguém? Posso divulgar no grupo.     │
│                                                                     │
│  Mas preciso que vc me confirme o substituto, tá?"                 │
│         │                                                           │
│         ▼                                                           │
│  • Notifica gestor IMEDIATAMENTE (prioridade alta)                 │
│  • Gestor assume para resolver                                      │
│  • Registra ocorrência em flags_comportamento do médico            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Negociação de Valor

```
┌─────────────────────────────────────────────────────────────────────┐
│                      NEGOCIAÇÃO                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Vaga: valor_min = 2000, valor_max = 2500                          │
│                                                                     │
│  MÉDICO                                    JÚLIA                    │
│    │                                         │                      │
│    │  "Tá pouco, 2000 não dá"                │                      │
│    │────────────────────────────────────────▶│                      │
│    │                                         │                      │
│    │                                         │  Verifica margem     │
│    │                                         │  disponível: R$500   │
│    │                                         │                      │
│    │  "Entendo... consigo chegar em 2300,    │                      │
│    │   o que acha?"                          │                      │
│    │◀────────────────────────────────────────│                      │
│    │                                         │                      │
│    │  "Fecha por 2400?"                      │                      │
│    │────────────────────────────────────────▶│                      │
│    │                                         │                      │
│    │                                         │  2400 < 2500 (max)   │
│    │                                         │  OK, pode aceitar    │
│    │                                         │                      │
│    │  "Fechado! Reservei por 2400 então"     │                      │
│    │◀────────────────────────────────────────│                      │
│                                                                     │
│  SE MÉDICO PEDE ACIMA DO MAX:                                       │
│    │                                         │                      │
│    │  "Preciso de 3000"                      │                      │
│    │────────────────────────────────────────▶│                      │
│    │                                         │                      │
│    │                                         │  3000 > 2500 (max)   │
│    │                                         │  Não pode aceitar    │
│    │                                         │                      │
│    │  "Putz, 3000 não consigo. O máximo      │                      │
│    │   que chego é 2500, mas é um hospital   │                      │
│    │   tranquilo e bem estruturado"          │                      │
│    │◀────────────────────────────────────────│                      │
│    │                                         │                      │
│    │  "Não dá mesmo, obrigado"               │                      │
│    │────────────────────────────────────────▶│                      │
│    │                                         │                      │
│    │  "Entendo! Se mudar de ideia ou quiser  │                      │
│    │   ver outras opções, me avisa!"         │                      │
│    │◀────────────────────────────────────────│                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo 6: Handoff IA → Humano

```
┌─────────────────────────────────────────────────────────────────────┐
│                      HANDOFF IA → HUMANO                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TRIGGERS AUTOMÁTICOS:                                              │
│  • Médico pede humano: "quero falar com alguém"                    │
│  • Sentimento muito negativo (< -50)                               │
│  • Confiança baixa na resposta (< 0.6)                             │
│  • Assunto fora do escopo (jurídico, financeiro complexo)          │
│  • Erro repetido (médico corrige 2+ vezes)                         │
│                                                                     │
│  TRIGGER MANUAL:                                                    │
│  • Gestor adiciona label "humano" no Chatwoot                      │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  JÚLIA           BANCO           SLACK          CHATWOOT    GESTOR  │
│    │               │               │               │           │    │
│    │  1. Detecta   │               │               │           │    │
│    │     trigger   │               │               │           │    │
│    │               │               │               │           │    │
│    │  2. Avisa     │               │               │           │    │
│    │     médico:   │               │               │           │    │
│    │     "Vou      │               │               │           │    │
│    │     pedir pra │               │               │           │    │
│    │     minha     │               │               │           │    │
│    │     supervisora│              │               │           │    │
│    │     te ajudar"│               │               │           │    │
│    │               │               │               │           │    │
│    │  3. UPDATE    │               │               │           │    │
│    │─────────────▶│               │               │           │    │
│    │  conversations│               │               │           │    │
│    │  controlled_  │               │               │           │    │
│    │  by = 'human' │               │               │           │    │
│    │               │               │               │           │    │
│    │  4. INSERT    │               │               │           │    │
│    │─────────────▶│               │               │           │    │
│    │  handoffs     │               │               │           │    │
│    │  • motivo     │               │               │           │    │
│    │  • resumo     │               │               │           │    │
│    │               │               │               │           │    │
│    │  5. Notifica  │               │               │           │    │
│    │───────────────────────────▶│               │           │    │
│    │               │               │──────────────────────────▶│    │
│    │               │               │  @gestor Handoff!        │    │
│    │               │               │  Dr. Carlos (CRM 123)    │    │
│    │               │               │  Motivo: irritado        │    │
│    │               │               │  Resumo: reclamou de...  │    │
│    │               │               │               │           │    │
│    │               │               │               │           │    │
│    │  6. Júlia     │               │               │           │    │
│    │     para de   │               │               │           │    │
│    │     responder │               │               │           │    │
│    │               │               │               │           │    │
│    │               │               │               │◀──────────│    │
│    │               │               │               │  7. Gestor│    │
│    │               │               │               │  acessa   │    │
│    │               │               │               │  Chatwoot │    │
│    │               │               │               │           │    │
│    │               │               │               │  8. Vê    │    │
│    │               │               │               │  histórico│    │
│    │               │               │               │           │    │
│    │               │               │               │  9.Responde│   │
│    │               │               │               │  via      │    │
│    │               │               │               │  Chatwoot │    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Mensagens de Handoff

| Situação | Mensagem da Júlia |
|----------|-------------------|
| Médico pediu | "Claro! Vou pedir pra minha supervisora te chamar, ela resolve isso rapidinho" |
| Médico irritado | "Entendo sua frustração. Vou passar pro meu supervisor, ele vai te ajudar melhor" |
| Assunto complexo | "Isso é melhor com a equipe especializada, vou transferir pra eles" |
| Confiança baixa | "Deixa eu confirmar isso com a equipe e já te retorno" |

---

## Fluxo 7: Handoff Humano → IA

```
┌─────────────────────────────────────────────────────────────────────┐
│                      HANDOFF HUMANO → IA                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GESTOR         CHATWOOT          WEBHOOK         BANCO     JÚLIA   │
│    │               │                 │              │          │    │
│    │  1. Remove    │                 │              │          │    │
│    │     label     │                 │              │          │    │
│    │     "humano"  │                 │              │          │    │
│    │──────────────▶│                 │              │          │    │
│    │               │                 │              │          │    │
│    │               │─────────────────▶              │          │    │
│    │               │  conversation_  │              │          │    │
│    │               │  updated        │              │          │    │
│    │               │                 │              │          │    │
│    │               │                 │  2. Detecta  │          │    │
│    │               │                 │     remoção  │          │    │
│    │               │                 │     do label │          │    │
│    │               │                 │              │          │    │
│    │               │                 │  3. UPDATE   │          │    │
│    │               │                 │─────────────▶│          │    │
│    │               │                 │  controlled_ │          │    │
│    │               │                 │  by = 'ai'   │          │    │
│    │               │                 │              │          │    │
│    │               │                 │              │          │    │
│    │               │                 │              │  4. Júlia│    │
│    │               │                 │              │  volta a │    │
│    │               │                 │              │  responder│   │
│    │               │                 │              │          │    │
│    │               │                 │              │  5. Lê   │    │
│    │               │                 │              │  msgs do │    │
│    │               │                 │              │  humano  │    │
│    │               │                 │              │  para    │    │
│    │               │                 │              │  contexto│    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo 8: Follow-ups Automáticos

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FOLLOW-UPS                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  WORKER CADÊNCIA                                                    │
│    │                                                                │
│    │  A cada 5 minutos:                                            │
│    │                                                                │
│    │  1. Busca conversas com follow-up pendente:                   │
│    │     SELECT * FROM conversations                               │
│    │     WHERE proximo_followup <= NOW()                           │
│    │     AND stage IN ('msg_enviada', 'aguardando_resposta')       │
│    │     AND controlled_by = 'ai'                                  │
│    │                                                                │
│    │  2. Para cada conversa:                                       │
│    │     • Verifica rate limit                                     │
│    │     • Verifica horário comercial                              │
│    │     • Gera mensagem de follow-up                              │
│    │     • Envia                                                   │
│    │     • Agenda próximo follow-up                                │
│    │                                                                │
└─────────────────────────────────────────────────────────────────────┘

CADÊNCIA:

  Abertura
      │
      ├── 48h ──▶ Follow-up 1: "Oi de novo! Viu minha msg?"
      │
      ├── 5d ───▶ Follow-up 2: "Surgiu uma vaga que lembrei de vc"
      │                         (inclui vaga real)
      │
      ├── 15d ──▶ Follow-up 3: "Última tentativa! Se não tiver
      │                         interesse, sem problema"
      │
      └── FIM ──▶ stage = 'nao_respondeu'
                  Pausa 60 dias
```

### Exemplos de Follow-up

**Follow-up 1 (48h):**
```
Oi de novo!

Mandei uma msg outro dia, não sei se vc viu

Tô com umas vagas legais de anestesia aqui, vc tá precisando?
```

**Follow-up 2 (5d) - Com vaga:**
```
Oi Dr Carlos!

Lembrei de vc pq surgiu uma vaga boa no Hospital Brasil

Sábado, 12h diurno, R$ 2.300

Tem interesse?
```

**Follow-up 3 (15d) - Último:**
```
Oi! Última msg, prometo rs

Se não tiver interesse em plantões agora, sem problema!

Mas se quiser, é só me chamar que eu ajudo
```

---

## Fluxo 9: Report para Gestor

```
┌─────────────────────────────────────────────────────────────────────┐
│                      REPORTS AUTOMÁTICOS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SCHEDULER                         SLACK                            │
│    │                                 │                              │
│    │  Horários:                      │                              │
│    │  • 10:00 - manhã               │                              │
│    │  • 13:00 - almoço              │                              │
│    │  • 17:00 - tarde               │                              │
│    │  • 20:00 - fim do dia          │                              │
│    │  • Seg 09:00 - semanal         │                              │
│    │                                 │                              │
│    │  1. Coleta métricas:           │                              │
│    │     • msgs enviadas            │                              │
│    │     • msgs respondidas         │                              │
│    │     • taxa resposta            │                              │
│    │     • médicos qualificados     │                              │
│    │     • plantões fechados        │                              │
│    │     • handoffs                 │                              │
│    │                                 │                              │
│    │  2. Gera análise (LLM):        │                              │
│    │     • Destaques                │                              │
│    │     • Preocupações             │                              │
│    │     • Sugestões                │                              │
│    │                                 │                              │
│    │  3. Envia                       │                              │
│    │────────────────────────────────▶│                              │
│    │                                 │                              │
│    │                                 │  📊 Report Júlia - Manhã    │
│    │                                 │                              │
│    │                                 │  Msgs: 15 enviadas          │
│    │                                 │  Respostas: 5 (33%)         │
│    │                                 │  Qualificados: 2            │
│    │                                 │  Fechados: 1                │
│    │                                 │                              │
│    │                                 │  ✅ Dr. João fechou vaga    │
│    │                                 │     no São Luiz             │
│    │                                 │                              │
│    │                                 │  ⚠️ Dra. Maria pediu        │
│    │                                 │     handoff (irritada)      │
│    │                                 │                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo 10: Briefing do Gestor

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LEITURA DE BRIEFING                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GESTOR         GOOGLE DOCS       WORKER         BANCO              │
│    │                │               │              │                │
│    │  1. Edita      │               │              │                │
│    │     documento  │               │              │                │
│    │────────────────▶               │              │                │
│    │                │               │              │                │
│    │                │               │              │                │
│    │                │  2. Worker    │              │                │
│    │                │◀──────────────│              │                │
│    │                │  busca doc    │              │                │
│    │                │  (a cada 60m) │              │                │
│    │                │               │              │                │
│    │                │───────────────▶              │                │
│    │                │  conteúdo     │              │                │
│    │                │               │              │                │
│    │                │               │  3. Compara  │                │
│    │                │               │     hash     │                │
│    │                │               │              │                │
│    │                │               │  4. Se mudou:│                │
│    │                │               │     • Parseia│                │
│    │                │               │     • Extrai │                │
│    │                │               │       seções │                │
│    │                │               │              │                │
│    │                │               │  5. INSERT/  │                │
│    │                │               │     UPDATE   │                │
│    │                │               │─────────────▶│                │
│    │                │               │  diretrizes  │                │
│    │                │               │              │                │
│    │                │               │  6. Confirma │                │
│    │                │               │     no Slack │                │
│    │                │               │              │                │
└─────────────────────────────────────────────────────────────────────┘
```

### Estrutura do Google Docs

```markdown
# Briefing Júlia - Semana 09/12

## Foco da Semana
- Priorizar anestesistas do ABC
- Empurrar vagas do Hospital Brasil (urgente)

## Vagas Prioritárias
- Hospital Brasil - Sábado 14/12 - até R$ 2.800
- São Luiz - Domingo 15/12 - até R$ 3.000

## Médicos VIP
- Dr. Carlos (CRM 123456) - sempre dar atenção especial
- Dra. Ana (CRM 789012) - potencial alto volume

## Médicos Bloqueados
- Dr. João (CRM 111111) - não contatar (pediu opt-out)

## Tom da Semana
- Mais urgente (vagas precisam preencher)
- Pode oferecer até 15% a mais em negociação

## Observações
- Evitar contato segunda-feira (feriado regional)
```

---

## Perguntas Respondidas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | De onde vêm as vagas? | Contratos + parceiros → Supabase |
| 2 | Onde estão os médicos? | Supabase `clientes` (29.645, 1.660 anestesistas) |
| 3 | Gestor usa Chatwoot? | Sim, para monitorar e handoff |
| 4 | Tem número de teste? | Sim |
| 5 | Orçamento LLM? | Até $50/mês |
| 6 | Quem cadastra vagas? | Gestor, direto no Supabase |

---

## Fluxos do MVP

| # | Fluxo | Prioridade |
|---|-------|------------|
| 3 | Prospecção (Abertura) | P0 |
| 4 | Conversa Ativa | P0 |
| 5 | Oferta de Vaga | P0 |
| 6 | Handoff IA → Humano | P0 |
| 8 | Follow-ups | P1 |
| 9 | Report para Gestor | P1 |
