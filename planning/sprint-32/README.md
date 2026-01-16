# Sprint 32 - Redesign de Campanhas e Comportamento Julia

**Status:** Concluída
**Início:** 2026-01-14
**Conclusão:** 2026-01-16
**Última atualização:** 2026-01-16

---

## Contexto do Problema

### 1. Julia usa "Templates" - Isso é errado

O sistema atual foi construído com mentalidade de **templates**:
- 424 ocorrências da palavra "template" no código
- Tabela `campanhas` armazena mensagens pré-escritas no campo `corpo`
- Sistema de abertura combina fragmentos pré-escritos (20 saudações × 10 apresentações × 10 contextos × 10 ganchos)

**Problema:** Mesmo com 22.000 combinações possíveis, ainda são peças pré-escritas combinadas aleatoriamente - não mensagens pensadas para cada médico.

### 2. Julia não sabe o tipo de campanha

```python
# Atual - Julia não recebe o tipo de campanha
prompt = construir_prompt_julia(primeira_msg=True)

# O prompt julia_primeira_msg é genérico:
# "Pergunte se ele está fazendo plantões ou tem interesse"
```

**Problema:** A mesma instrução serve para Discovery (onde não pode ofertar) e Oferta (onde pode).

### 3. Julia mente sobre vagas

Comportamento atual observado:
```
Julia: "Dr, tenho uma vaga com seu perfil!"
Médico: "Qual?"
Julia: "Deixa eu ver... desculpa, não temos no momento"
```

**Problema:** Julia diz "tenho vaga" ANTES de consultar `buscar_vagas()`.

### 4. Discovery com Oferta

Campanhas de Discovery estão mencionando vagas, quando o objetivo deveria ser apenas **conhecer o médico**.

---

## Princípio Central (Nova Arquitetura)

```
Julia é REATIVA para ofertas, não PROATIVA.

Oferta só acontece se:
1. Objetivo da campanha diz explicitamente "ofertar"
2. OU médico pergunta/pede

Em qualquer outro caso → RELACIONAMENTO
```

---

## Arquitetura de Comportamentos por Tipo

### DISCOVERY

```
Objetivo: Conhecer o médico
─────────────────────────────────
PODE:
  ✓ Perguntar se faz plantão
  ✓ Perguntar especialidade
  ✓ Perguntar região/cidade
  ✓ Perguntar preferências (turno, tipo de hospital)
  ✓ Criar rapport, conversar naturalmente

NÃO PODE:
  ✗ Mencionar vagas
  ✗ Falar de valores
  ✗ Ofertar qualquer coisa
  ✗ Dizer "tenho uma oportunidade"

GATILHO PARA OFERTA:
  → Somente se médico perguntar explicitamente
  → Nesse caso: consulta buscar_vagas() e responde
```

### OFERTA

```
Objetivo: Apresentar vagas REAIS que existem no sistema
─────────────────────────────────
ESCOPO DA OFERTA (definido na campanha):
  • Vaga específica: "Plantão terça 15/03/2026 no Hospital São Luiz"
  • Vagas de um período: "Vagas disponíveis para março/2026 no Hospital X"
  • Vagas por especialidade: "Todas as vagas para cardiologia"
  • Vagas por região: "Vagas na zona sul de SP"
  • Combinações: "Vagas de pediatria em março no ABC"

PRÉ-REQUISITO ABSOLUTO:
  → Antes de enviar campanha: sistema verifica se existem vagas no escopo
  → Se não existir: campanha NÃO dispara

PODE:
  ✓ Apresentar vagas que EXISTEM dentro do escopo
  ✓ Falar valores, datas, locais
  ✓ Negociar dentro da margem autorizada (definida no briefing)
  ✓ Responder dúvidas sobre as vagas

NÃO PODE:
  ✗ Mencionar vagas fora do escopo definido
  ✗ Inventar vagas
  ✗ Prometer vaga sem consultar sistema
  ✗ Dizer "tenho vaga" sem ter chamado buscar_vagas()

NEGOCIAÇÃO:
  → Margem deve estar EXPLÍCITA no briefing
  → Sem margem definida = não pode negociar valor
```

### FOLLOWUP

```
Objetivo: Manter relacionamento ativo
─────────────────────────────────
PODE:
  ✓ Perguntar como está
  ✓ Perguntar como foi plantão anterior (se teve)
  ✓ Manter conversa leve
  ✓ Atualizar informações do perfil

NÃO PODE:
  ✗ Ofertar proativamente

GATILHO PARA OFERTA:
  → Somente se médico perguntar
```

### FEEDBACK

```
Objetivo: Coletar opinião sobre experiência
─────────────────────────────────
PODE:
  ✓ Perguntar como foi o plantão
  ✓ Perguntar sobre o hospital
  ✓ Coletar elogios/reclamações
  ✓ Agradecer

NÃO PODE:
  ✗ Ofertar novo plantão proativamente

GATILHO PARA OFERTA:
  → Somente se médico perguntar
```

### REATIVAÇÃO

```
Objetivo: Retomar contato com médico inativo
─────────────────────────────────
PODE:
  ✓ Perguntar se ainda tem interesse em plantões
  ✓ Perguntar se mudou algo (cidade, especialidade)
  ✓ Reestabelecer diálogo

NÃO PODE:
  ✗ Ofertar de cara
  ✗ Assumir que ele quer plantão

FLUXO:
  1. Primeiro: "Oi, sumiu! Tudo bem?"
  2. Espera resposta
  3. Se positivo: "Ainda tá fazendo plantão?"
  4. Só oferta se ele pedir ou confirmar interesse
```

---

## Estrutura de Campanha (Nova)

```python
campanha = {
    "id": 123,
    "nome": "Cardiologia Março 2026",
    "tipo": "oferta",  # discovery | oferta | followup | feedback | reativacao

    # Objetivo em linguagem natural (injetado no prompt)
    "objetivo": "Apresentar vagas de cardiologia para março/2026 na Grande SP",

    # Escopo da oferta (somente para tipo=oferta)
    "escopo_vagas": {
        "especialidade": "cardiologia",
        "periodo_inicio": "2026-03-01",
        "periodo_fim": "2026-03-31",
        "hospital_id": None,  # None = qualquer
        "regiao": "grande_sp"
    },

    # Regras comportamentais (injetadas no prompt)
    "regras": [
        "Apresentar vagas dentro do escopo definido",
        "Pode negociar até 10% acima do valor base",
        "Se não tiver vaga no escopo, não disparar campanha"
    ],

    # Audiência (filtro de médicos)
    "filtros_medicos": {
        "especialidade": "cardiologia",
        "regiao": "grande_sp",
        "faz_plantao": True,
        "opt_out": False
    },

    # Controle
    "status": "rascunho",  # rascunho | agendada | ativa | pausada | concluida
    "agendar_para": "2026-03-01T08:00:00Z"
}
```

---

## Mudanças Necessárias no Sistema

### 1. PromptBuilder

```python
# DE (atual)
async def construir_prompt_julia(
    primeira_msg: bool = False,
    diretrizes: str = "",
    ...
)

# PARA (novo)
async def construir_prompt_julia(
    campaign_type: str = None,        # discovery | oferta | followup | feedback | reativacao
    campaign_objective: str = None,   # Objetivo em linguagem natural
    campaign_rules: list[str] = None, # Regras específicas
    can_offer: bool = False,          # Se pode ofertar proativamente
    offer_scope: dict = None,         # Escopo de vagas (se can_offer=True)
    negotiation_margin: float = 0,    # Margem de negociação (do briefing)
    ...
)
```

### 2. Prompts no Banco

Ao invés de um `julia_primeira_msg` genérico, ter prompts por tipo:

| Prompt | Uso |
|--------|-----|
| `julia_discovery` | Primeira msg em campanha Discovery |
| `julia_oferta` | Primeira msg em campanha Oferta |
| `julia_followup` | Primeira msg em campanha Followup |
| `julia_feedback` | Primeira msg em campanha Feedback |
| `julia_reativacao` | Primeira msg em campanha Reativação |

### 3. Validação Pré-Disparo (Oferta)

```python
async def validar_disparo_oferta(campanha: dict) -> bool:
    """
    Valida se campanha de oferta pode disparar.

    Retorna False se não existirem vagas no escopo definido.
    """
    escopo = campanha.get("escopo_vagas", {})

    vagas = await buscar_vagas(
        especialidade=escopo.get("especialidade"),
        periodo_inicio=escopo.get("periodo_inicio"),
        periodo_fim=escopo.get("periodo_fim"),
        hospital_id=escopo.get("hospital_id"),
        regiao=escopo.get("regiao")
    )

    if not vagas:
        logger.warning(f"Campanha {campanha['id']} bloqueada: sem vagas no escopo")
        return False

    return True
```

### 4. Tabela `campanhas` (Reestruturação)

**Remover:**
- `corpo` (mensagem pré-escrita)
- `nome_template`

**Adicionar:**
- `objetivo` (text) - Objetivo em linguagem natural
- `escopo_vagas` (jsonb) - Filtro de vagas para ofertas
- `regras` (jsonb) - Array de regras comportamentais
- `pode_ofertar` (boolean) - Se permite oferta proativa

### 5. Briefing → Negociação

A margem de negociação deve vir **explicitamente** do briefing:

```
## Margem de Negociação

- Cardiologia: até 15% acima do valor base
- Clínico Geral: até 10% acima do valor base
- Anestesista: até 20% acima do valor base (alta demanda)
- Demais: sem margem (valor fechado)
```

---

## Eliminação do Termo "Template"

### Renomeações

| Atual | Novo |
|-------|------|
| `campanhas.nome_template` | `campanhas.nome` |
| `app/templates/` | `app/mensagens/` ou `app/fragmentos/` |
| `TemplateAbertura` | `FragmentoAbertura` ou eliminar |
| `campaign_templates.py` | `campaign_behaviors.py` |
| `template_sid` | (removido - era Twilio) |

### Conceitos

| Atual | Novo |
|-------|------|
| "Template de campanha" | "Comportamento de campanha" |
| "Template de abertura" | "Geração de abertura" (via LLM) |
| "Selecionar template" | "Definir comportamento" |

---

## Julia Autônoma (Nova Visão)

### De Executor de Briefing para Agente Autônomo

| Aspecto | Julia Atual (Briefing) | Julia Autônoma (Nova) |
|---------|------------------------|------------------------|
| **Gatilho** | Gestor escreve briefing | Julia observa estado do sistema |
| **Decisão** | Gestor decide o que fazer | Julia decide baseado em regras |
| **Discovery** | Gestor agenda campanha | Julia roda automaticamente quando tem médico não-enriquecido |
| **Oferta** | Gestor diz qual vaga | Julia vê escala com furo e age |
| **Contexto** | Vem do Google Docs | Vem do estado do banco de dados |

### Como um Escalista Humano Pensa

```
1. OLHA O BANCO DE DADOS (carteira de médicos)
   → "Tenho 50 médicos, mas só sei especialidade de 30"
   → "Preciso enriquecer esses 20"
   → AÇÃO: Discovery nos 20

2. OLHA AS ESCALAS (vagas)
   → "Escala de março do Hospital X tem 15 furos"
   → "Quais médicos da minha carteira são compatíveis?"
   → AÇÃO: Oferta direcionada

3. OLHA O RELACIONAMENTO
   → "Dr Carlos não responde há 2 meses"
   → AÇÃO: Reativação

4. OLHA FEEDBACK
   → "Dr Maria fez plantão ontem no Hospital Y"
   → AÇÃO: Pedir feedback
```

**Julia deve fazer exatamente isso, automaticamente.**

---

## Gatilhos Automáticos

| Gatilho | Condição | Ação Julia |
|---------|----------|------------|
| **Médico não-enriquecido** | Só tem nome+telefone OU só telefone | Discovery automático |
| **Escala com furo** | Vaga sem médico confirmado < X dias | Oferta para compatíveis |
| **Médico inativo** | Sem interação > 60 dias | Reativação |
| **Plantão realizado** | Médico fez plantão ontem | Feedback |
| **Médico interessado sem match** | Disse que quer, mas não tinha vaga | Monitorar e avisar quando surgir |

### Limites e Priorização

| Aspecto | Definição |
|---------|-----------|
| **Limite de volume** | Definido pelos guardrails existentes (msgs/hora, tempo entre envios, chips aquecidos) |
| **Escala** | Aumenta com rotação de chips e número de instâncias |
| **Priorização Discovery** | Aleatório entre médicos não-enriquecidos |
| **Pré-requisito** | Chip deve ter passado pelo aquecimento |

---

## Validação de Telefone (checkNumberStatus)

### Problema
- 28k médicos não-enriquecidos no banco
- Enviar Discovery para número inválido = desperdício

### Solução
Usar `checkNumberStatus` da Evolution API como **job contínuo** de pré-processamento.

```
FLUXO:
1. Médico entra no banco (só telefone)
2. Job contínuo (durante o dia): valida números novos via checkNumberStatus
3. Se válido → status = "telefone_validado" → elegível para Discovery
4. Se inválido → status = "telefone_invalido" → não recebe mensagens

BENEFÍCIOS:
- Evita desperdiçar mensagem em número inválido
- Limpa a base automaticamente
- Roda continuamente, não apenas à noite
```

### Implementação Sugerida

```python
# Job contínuo - roda a cada X minutos
async def validar_telefones_pendentes():
    """
    Valida telefones de médicos que ainda não foram verificados.
    """
    # Buscar médicos com telefone não validado
    medicos = await buscar_medicos_telefone_pendente(limit=100)

    for medico in medicos:
        try:
            # Consulta Evolution API
            resultado = await evolution.check_number_status(medico.telefone)

            if resultado.exists:
                await atualizar_status_telefone(medico.id, "validado")
            else:
                await atualizar_status_telefone(medico.id, "invalido")

        except Exception as e:
            logger.warning(f"Erro ao validar {medico.id}: {e}")
            # Não marca como inválido - tenta de novo depois
```

---

## Arquitetura de Hospitais Bloqueados

### Problema
- Gestor precisa poder bloquear hospital (problema temporário, etc.)
- Julia não deve ofertar vagas de hospitais bloqueados

### Solução: Separação por Arquitetura de Dados

Julia **não precisa filtrar** hospitais bloqueados - ela simplesmente **não vê** as vagas.

```
┌─────────────────────────────────────────────────────┐
│                    VAGAS                            │
│  (Julia tem acesso - pode ofertar)                  │
│  Hospital São Luiz, Hospital Brasil, etc.           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│           VAGAS_HOSPITAIS_BLOQUEADOS                │
│  (Julia NÃO tem acesso - registro histórico)        │
│  Vagas movidas quando hospital é bloqueado          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│            HOSPITAIS_BLOQUEADOS                     │
│  hospital_id, motivo, bloqueado_em, bloqueado_por   │
└─────────────────────────────────────────────────────┘
```

### Ação de Bloquear Hospital

```
1. Humano marca hospital como bloqueado (Slack ou Dashboard)
2. Sistema automaticamente:
   a. Insere registro em hospitais_bloqueados
   b. Move vagas desse hospital para vagas_hospitais_bloqueados
3. Julia continua consultando tabela vagas normalmente
4. Não vê nada do hospital bloqueado
```

### Ação de Desbloquear Hospital

```
1. Humano remove bloqueio
2. Sistema automaticamente:
   a. Remove registro de hospitais_bloqueados
   b. Move vagas de volta para tabela vagas (se ainda válidas)
3. Julia volta a ver as vagas
```

---

## Divisão de Responsabilidades

### O que HUMANO define (Configuração/Briefing)

| Item | Por quê precisa de humano |
|------|---------------------------|
| **Margem de negociação por especialidade** | Decisão financeira/comercial |
| **Hospitais bloqueados** | Pode ter problema que Julia não sabe |
| **Volume máximo/dia** | Estratégia comercial |
| **Tom da comunicação** | Posicionamento de marca |
| **Pausar tudo** | Crise, problema, decisão estratégica |
| **Prioridades especiais** | "Esta semana foco em anestesistas" (ocasional) |

### O que JULIA decide sozinha

| Item | Como Julia decide |
|------|-------------------|
| **Quem precisa de Discovery** | Médicos não-enriquecidos no banco |
| **Quem recebe Oferta** | Match entre vaga disponível + perfil médico |
| **Quais hospitais ofertar** | Todos que estão na tabela `vagas` (bloqueados não aparecem) |
| **Quem precisa de Reativação** | Médicos inativos > X dias |
| **Quem recebe Feedback** | Médicos que fizeram plantão recente |
| **Horário de envio** | Dentro das regras (8h-20h, seg-sex) |
| **Priorização de vagas** | Escala mais urgente primeiro |

---

## Interface Gestor: Dashboard + Slack (Híbrido)

### Dashboard (Configurações Estáticas)

| Funcionalidade | Descrição |
|----------------|-----------|
| Hospitais bloqueados | Add/remove com motivo |
| Kill switch | Pausar tudo (emergência) |
| Métricas | Visualização de performance |
| Histórico | Conversas, instruções, decisões |
| Instruções ativas | Ver diretrizes contextuais vigentes |

### Slack (Intervenções Dinâmicas)

| Funcionalidade | Descrição |
|----------------|-----------|
| Margem por vaga | "Na vaga X pode ir até R$ 3.000" |
| Margem por médico | "Pro Dr Carlos, 15% a mais" |
| Comandos naturais | "Julia, faça X" |
| Canal de ajuda | Julia pergunta quando não sabe |

---

## Margem de Negociação (Contextual)

### Não é configuração global

**Errado:** "Cardiologia sempre pode 15%"
**Certo:** "Esta vaga específica pode ir até R$ X"

### Tipos de Margem

| Escopo | Exemplo | Expira quando |
|--------|---------|---------------|
| **Por vaga** | "Vaga 123 pode até R$ 3.000" | Vaga é preenchida |
| **Por médico** | "Dr Carlos pode 15% a mais" | Médico diz que não tem interesse |

### Armazenamento

```python
diretriz_contextual = {
    "tipo": "margem_negociacao",
    "escopo": "vaga",           # ou "medico"
    "vaga_id": 123,             # se escopo=vaga
    "cliente_id": "uuid",       # se escopo=medico
    "valor_maximo": 3000,       # ou percentual
    "criado_por": "gestor_rafael",
    "criado_em": "2026-01-16T10:00:00Z",
    "status": "ativa",          # ativa | expirada | cancelada
    "expirado_em": null,
    "motivo_expiracao": null    # "vaga_preenchida" | "medico_sem_interesse" | "cancelado_gestor"
}
```

---

## Gestor Comanda Julia (Linguagem Natural)

### Fluxo de Comando

```
GESTOR → Instrução em linguagem natural
JULIA (Opus) → Interpreta, tira dúvidas, apresenta plano
GESTOR → Confirma ou ajusta
JULIA (Haiku) → Executa
```

### Exemplo

```
Gestor: "Julia, entra em contato com todos os cardiologistas
        que responderam positivo no último mês mas não fecharam"

Julia (Opus): "Entendi! Só pra confirmar:
              - Cardiologistas que responderam interesse
              - No último mês (dezembro/janeiro)
              - Que não fecharam nenhuma vaga

              Encontrei 23 médicos nesse perfil. Faço um followup
              perguntando se ainda têm interesse?"

Gestor: "Isso, mas menciona que temos vagas novas em fevereiro"

Julia (Opus): "Perfeito! Vou:
              1. Contatar os 23 médicos
              2. Perguntar se ainda têm interesse
              3. Mencionar vagas de fevereiro

              Posso começar?"

Gestor: "Vai"

Julia (Haiku): [Executa os 23 contatos]
```

---

## Julia Pede Ajuda (Anti-Alucinação)

### Regra Crítica

```
SE Julia não sabe algo factual que o médico perguntou
E não encontra no banco/conhecimento
ENTÃO:
  1. NÃO inventa resposta
  2. PAUSA a conversa
  3. PERGUNTA ao gestor (Slack)
  4. ESPERA resposta
  5. RETOMA com informação correta
```

### Exemplo

```
Médico: "Esse hospital tem refeição inclusa?"

Julia: [Não encontra informação sobre refeição]
       [PAUSA conversa]
       [Pergunta ao gestor no Slack]

Julia (Slack): "🔔 @gestor Preciso de ajuda!
                Dr Carlos perguntou se o Hospital São Luiz
                tem refeição inclusa. Não tenho essa info.

                Conversa pausada aguardando resposta."

Gestor: "Sim, tem refeitório 24h, refeição inclusa no plantão"

Julia: [Salva informação no conhecimento do hospital]
       [Retoma conversa]
       "Tem sim! O São Luiz tem refeitório 24h,
        refeição tá inclusa no plantão"
```

### Categorias de "Não Sei"

| Tipo | Exemplo | Ação |
|------|---------|------|
| **Fato sobre hospital** | "Tem estacionamento?" | Pausa + pergunta gestor |
| **Fato sobre vaga** | "Qual o valor exato?" | Consulta banco, se não tem → pergunta gestor |
| **Preferência do médico** | "Ele prefere noturno?" | Consulta memória, se não tem → pergunta ao médico |
| **Negociação** | "Posso dar mais?" | Pergunta gestor (margem) |
| **Opinião** | "Vale a pena esse hospital?" | Não responde, desvia educadamente |

### Estados da Conversa

```
ATIVA                    → Fluxo normal
PAUSADA_AGUARDANDO_GESTOR → Julia pediu ajuda, esperando resposta
PAUSADA_AGUARDANDO_MEDICO → Julia perguntou algo, esperando médico
HANDOFF                  → Transferida para humano
```

### Arquitetura: Canal de Ajuda

```
┌─────────────────────────────────────────────────────────┐
│                    CONVERSA WHATSAPP                    │
│  Médico ↔ Julia                                         │
│  Status: ATIVA | PAUSADA_AGUARDANDO_GESTOR              │
└─────────────────────────────────────────────────────────┘
                           │
                           │ Julia não sabe algo
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    SLACK (Canal Ajuda)                  │
│  Julia: "Preciso de ajuda com Dr Carlos..."             │
│  Gestor: "A resposta é X"                               │
│  Julia: "Obrigada! Retomando conversa"                  │
└─────────────────────────────────────────────────────────┘
                           │
                           │ Gestor responde
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    CONVERSA WHATSAPP                    │
│  Julia responde ao médico com info correta              │
│  Status: ATIVA                                          │
└─────────────────────────────────────────────────────────┘
```

### Timeout de Ajuda

Se gestor não responde em 5 minutos:

```
FLUXO COM TIMEOUT:

1. Julia pede ajuda no Slack
2. Timer de 5 minutos inicia
3. Se gestor não responde em 5 min:
   a. Julia responde ao médico: "Vou confirmar essa info e já te falo!"
   b. Conversa fica em status AGUARDANDO_INFO_GESTOR
   c. Lembrete automático enviado ao gestor no Slack
4. Quando gestor responde (mesmo horas depois):
   a. Julia retoma conversa com médico
   b. "Opa, confirmei! [resposta do gestor]"
   c. Salva informação no conhecimento (se aplicável)
```

**Lembrete automático:**
```
Julia (Slack): "🔔 Lembrete: ainda preciso da resposta sobre
                refeição no Hospital São Luiz.
                Dr Carlos está aguardando.

                Pergunta original: [link para msg]"
```

**Frequência do lembrete:** A cada 30 minutos até gestor responder ou cancelar.

---

## Pendências para Brainstorm

- [x] ~~Timeout de ajuda: Se gestor não responde em X minutos, o que Julia faz?~~ → Responde "vou confirmar" + lembrete automático
- [x] ~~UI/UX do Dashboard~~ → Integrar com Sprint 28 (já existe)
- [x] ~~Fluxo de criação de campanha manual~~ → Wizard no dashboard
- [x] ~~Integração com sistema de vagas~~ → Tabela `vagas` é fonte da verdade
- [x] ~~Trigger automático de Oferta~~ → Threshold 20 dias
- [x] ~~Julia aprendendo com gestor~~ → Salvar em `conhecimento_hospitais`

---

## Integração com Dashboard Sprint 28

O dashboard já existe (`/dashboard`) com:
- Next.js 14 + shadcn/ui + Tailwind
- Autenticação Supabase + RBAC
- Layout responsivo (mobile-first)
- Páginas: dashboard, conversas, médicos, vagas, campanhas, métricas, auditoria

**Adaptações necessárias para Sprint 32:**

| Tela Existente | Adaptação Sprint 32 |
|----------------|---------------------|
| Campanhas | Novo wizard com tipos de comportamento |
| Vagas | Adicionar gestão de hospitais bloqueados |
| Sistema | Adicionar modo piloto toggle |
| Conversas | Mostrar status (ativa, aguardando gestor, etc.) |

**Novas telas:**
| Tela | Funcionalidade |
|------|----------------|
| Instruções Ativas | Ver/cancelar diretrizes contextuais |
| Canal de Ajuda | Perguntas pendentes da Julia |

---

## Vagas: Fonte da Verdade

A tabela `vagas` é a fonte única de verdade.

**Se gestor solicitar via Slack:**
```
Gestor: "Julia, adiciona uma vaga de cardio no São Luiz dia 20/03, valor R$ 2.500"

Julia (Opus): "Entendi! Vou criar a vaga:
              - Hospital: São Luiz
              - Especialidade: Cardiologia
              - Data: 20/03/2026
              - Valor: R$ 2.500

              Confirma?"

Gestor: "Isso"

Julia: [INSERT na tabela vagas]
       "Pronto! Vaga criada. Quer que eu já comece a ofertar?"
```

---

## Trigger Automático de Oferta

**Condição:** Vaga com data < 20 dias e sem médico confirmado

```python
async def verificar_vagas_urgentes():
    """
    Job que verifica vagas precisando de médico.
    Roda a cada hora (se PILOT_MODE=false).
    """
    threshold_dias = 20
    data_limite = datetime.now() + timedelta(days=threshold_dias)

    vagas_urgentes = await buscar_vagas(
        data_ate=data_limite,
        status="aberta",  # Sem médico confirmado
        order_by="data ASC"  # Mais urgentes primeiro
    )

    for vaga in vagas_urgentes:
        medicos_compativeis = await buscar_medicos_compativeis(
            especialidade=vaga.especialidade,
            regiao=vaga.regiao,
            disponivel=True
        )

        # Priorização
        medicos_ordenados = priorizar_medicos(
            medicos_compativeis,
            criterios=[
                "historico_positivo",  # Já fechou antes
                "nunca_contatado",     # Novo na base
                "inativo"              # Reativar
            ]
        )

        # Enfileira oferta para top N
        for medico in medicos_ordenados[:5]:
            await enfileirar_oferta(medico, vaga)
```

---

## Julia Aprende com Gestor

**Tabela:**
```sql
CREATE TABLE conhecimento_hospitais (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitais(id),
    atributo TEXT NOT NULL,        -- "refeicao", "estacionamento", "vestiario", etc.
    valor TEXT NOT NULL,           -- "Refeitório 24h incluso"
    fonte TEXT NOT NULL,           -- "gestor", "medico", "sistema"
    criado_por TEXT,               -- ID do gestor ou médico
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(hospital_id, atributo)
);
```

**Fluxo:**
```
1. Julia pergunta ao gestor sobre hospital
2. Gestor responde
3. Julia extrai: hospital + atributo + valor
4. Julia salva na tabela
5. Próxima pergunta igual → Julia já sabe
```

---

## Modo Piloto

**Flag:** `PILOT_MODE=true` (env var ou feature flag no banco)

### O que FUNCIONA no piloto

| Funcionalidade | Status |
|----------------|--------|
| Campanhas manuais (gestor cria) | ✅ Funciona |
| Respostas a médicos (inbound) | ✅ Funciona |
| Canal de ajuda Julia → Gestor | ✅ Funciona |
| Gestor comanda Julia (Slack) | ✅ Funciona |
| Todas as guardrails | ✅ Funciona |
| checkNumberStatus (validação) | ✅ Funciona |

### O que NÃO funciona no piloto

| Funcionalidade | Status |
|----------------|--------|
| Discovery automático | ❌ Desabilitado |
| Oferta automática (furo de escala) | ❌ Desabilitado |
| Reativação automática | ❌ Desabilitado |
| Feedback automático | ❌ Desabilitado |

### Implementação

```python
# app/core/config.py
PILOT_MODE: bool = True  # Mudar para False quando sair do piloto

# app/workers/autonomo.py
async def executar_acoes_autonomas():
    if settings.PILOT_MODE:
        logger.info("Modo piloto ativo - ações autônomas desabilitadas")
        return

    await executar_discovery_automatico()
    await executar_ofertas_automaticas()
    await executar_reativacao_automatica()
    await executar_feedback_automatico()
```

### Toggle no Dashboard

Tela Sistema → Toggle "Modo Piloto" (ON/OFF)
- Requer role `admin`
- Log de auditoria quando alterado

---

## Épicos Sprint 32

### Fase 1: Foundation (Backend)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E01 | Prompts por Tipo de Campanha | Criar julia_discovery, julia_oferta, etc. | 4h |
| E02 | PromptBuilder com Contexto de Campanha | Receber campaign_type, objective, rules | 4h |
| E03 | Modo Piloto | Flag + toggle + guardrails | 3h |
| E04 | checkNumberStatus Job | Validação contínua de telefones | 4h |

### Fase 2: Julia Autônoma (Backend)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E05 | Gatilhos Automáticos | Discovery, Oferta, Reativação, Feedback | 8h |
| E06 | Trigger Oferta por Furo | Vagas < 20 dias sem confirmação | 4h |
| E07 | Priorização de Médicos | Algoritmo de seleção para ofertas | 4h |

### Fase 3: Interação Gestor (Backend + Slack)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E08 | Canal de Ajuda Julia | Julia pergunta, gestor responde, timeout | 6h |
| E09 | Gestor Comanda Julia | Interpretar instruções, planejar (Opus), executar (Haiku) | 8h |
| E10 | Diretrizes Contextuais | Margem por vaga/médico, expiração automática | 4h |
| E11 | Julia Aprende | Salvar conhecimento de respostas do gestor | 3h |

### Fase 4: Arquitetura de Dados

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E12 | Hospitais Bloqueados | Tabelas + ação de bloquear/desbloquear | 4h |
| E13 | Conhecimento Hospitais | Tabela + CRUD | 3h |
| E14 | Reestruturar Campanhas | Remover corpo, adicionar objetivo/regras | 4h |
| E15 | Estados de Conversa | AGUARDANDO_GESTOR, AGUARDANDO_INFO, etc. | 3h |

### Fase 5: Dashboard (Frontend)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E16 | Adaptar Tela Campanhas | Novo wizard com tipos de comportamento | 6h |
| E17 | Tela Hospitais Bloqueados | CRUD com motivo | 4h |
| E18 | Tela Instruções Ativas | Listar/cancelar diretrizes contextuais | 4h |
| E19 | Tela Canal de Ajuda | Perguntas pendentes + responder | 4h |
| E20 | Toggle Modo Piloto | Em Sistema/Configurações | 2h |

### Fase 6: Limpeza e Polish

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E21 | Eliminar "Template" | Renomear arquivos, variáveis, conceitos | 4h |
| E22 | Migrar Dados Campanhas | Adaptar campanhas existentes | 2h |
| E23 | Testes E2E | Fluxos críticos | 6h |
| E24 | Documentação | Atualizar CLAUDE.md e docs | 3h |

---

## Resumo de Estimativas

| Fase | Horas |
|------|-------|
| Foundation | 15h |
| Julia Autônoma | 16h |
| Interação Gestor | 21h |
| Arquitetura de Dados | 14h |
| Dashboard | 20h |
| Limpeza e Polish | 15h |
| **TOTAL** | **101h** |

---

## Ordem de Execução Sugerida

```
SEMANA 1 (Foundation + Piloto)
├── E01: Prompts por tipo
├── E02: PromptBuilder
├── E03: Modo Piloto ⭐ (crítico para começar testes)
├── E04: checkNumberStatus
└── E14: Reestruturar campanhas

SEMANA 2 (Interação Gestor)
├── E08: Canal de ajuda
├── E09: Gestor comanda Julia
├── E10: Diretrizes contextuais
├── E11: Julia aprende
└── E15: Estados de conversa

SEMANA 3 (Autonomia + Dados)
├── E05: Gatilhos automáticos
├── E06: Trigger oferta
├── E07: Priorização
├── E12: Hospitais bloqueados
└── E13: Conhecimento hospitais

SEMANA 4 (Dashboard + Polish)
├── E16-E20: Todas as telas dashboard
├── E21: Eliminar "template"
├── E22: Migrar dados
├── E23: Testes E2E
└── E24: Documentação
```

---

## Critérios de Saída do Piloto

Para desativar `PILOT_MODE`:

- [ ] 100+ conversas de teste sem problemas críticos
- [ ] Julia não alucinando (canal de ajuda funcionando)
- [ ] Gestor consegue comandar Julia via Slack
- [ ] Dashboard funcionando para operação básica
- [ ] Guardrails validados (opt-out, rate limit, etc.)
- [ ] Métricas de qualidade aceitáveis

---

## Referências

- Análise realizada em: 2026-01-16
- Prompts atuais: `prompts` table (julia_base, julia_primeira_msg, julia_tools)
- Diretrizes atuais: `diretrizes` table (foco_semana, tom_semana, margem_negociacao)
- Código de abertura: `app/services/abertura.py`, `app/fragmentos/aberturas.py`
- Prompt builder: `app/prompts/builder.py`

---

## Status Final

**Sprint 32 Concluída:** 2026-01-16

### Épicos Implementados

| # | Épico | Status |
|---|-------|--------|
| E01 | Prompts por Tipo de Campanha | Concluído |
| E02 | PromptBuilder com Contexto | Concluído |
| E03 | Modo Piloto | Concluído |
| E04 | checkNumberStatus Job | Concluído |
| E05 | Gatilhos Automáticos | Concluído |
| E06 | Trigger Oferta por Furo | Concluído |
| E07 | Priorização de Médicos | Concluído |
| E08 | Canal de Ajuda Julia | Concluído |
| E09 | Gestor Comanda Julia | Concluído |
| E10 | Diretrizes Contextuais | Concluído |
| E11 | Julia Aprende | Concluído |
| E12 | Hospitais Bloqueados | Concluído |
| E13 | Conhecimento Hospitais | Concluído |
| E14 | Reestruturar Campanhas | Concluído |
| E15 | Estados de Conversa | Concluído |
| E16 | Adaptar Tela Campanhas | Pendente (Fase 5 Dashboard) |
| E17 | Tela Hospitais Bloqueados | Pendente (Fase 5 Dashboard) |
| E18 | Tela Instruções Ativas | Pendente (Fase 5 Dashboard) |
| E19 | Tela Canal de Ajuda | Pendente (Fase 5 Dashboard) |
| E20 | Toggle Modo Piloto | Pendente (Fase 5 Dashboard) |
| E21 | Eliminar "Template" | Concluído |
| E22 | Migrar Dados Campanhas | Concluído |
| E23 | Testes E2E | Concluído |
| E24 | Documentação | Concluído |

### Principais Mudanças

1. **Comportamentos de Campanha:** Julia agora opera com 5 tipos de comportamento com regras específicas (discovery, oferta, followup, feedback, reativacao)
2. **Anti-Alucinação:** Canal de ajuda garante que Julia não invente informações
3. **Modo Piloto:** Flag para controlar ações autônomas (PILOT_MODE=True por padrão)
4. **Hospital Bloqueado:** Separação por dados - Julia não vê vagas de hospitais bloqueados
5. **Eliminação de "Template":** Renomeado para "fragmento" (mensagens) e "behavior" (campanhas)
6. **Testes E2E:** 72 testes cobrindo fluxos críticos

### Arquivos Criados/Modificados

**Novos módulos:**
- `app/fragmentos/` - Fragmentos de mensagens (renomeado de templates)
- `app/services/campaign_behaviors.py` - Comportamentos de campanha
- `app/services/hospitais_bloqueados.py` - Gestão de hospitais bloqueados
- `app/workers/pilot_mode.py` - Controle do modo piloto
- `app/services/gatilhos_autonomos.py` - Gatilhos automáticos

**Documentação:**
- `docs/julia/comportamentos.md` - Documentação dos 5 tipos de comportamento
- `docs/operacao/runbook-sprint32.md` - Runbook operacional

**Testes:**
- `tests/e2e/` - Testes E2E para fluxos críticos
- `tests/unit/test_migrar_campanhas.py` - Testes do script de migração

### Notas

- **Fase 5 (Dashboard)** foi adiada para sprint futura pois requer decisões de design
- **Script de migração** criado em `scripts/migrar_campanhas_v2.py` para migrar campanhas existentes
- **Modo Piloto** está ATIVO por padrão - ações autônomas desabilitadas
