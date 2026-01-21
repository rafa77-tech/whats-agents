# Manual: Piloto de Campanha Discovery

> Guia operacional para execucao de campanha de descoberta (primeiro contato) via Dashboard Julia

**Versao:** 1.0
**Ultima atualizacao:** 17/01/2026

---

## Indice

1. [Visao Geral](#visao-geral)
2. [Pre-requisitos](#pre-requisitos)
3. [Checklist Pre-Piloto](#checklist-pre-piloto)
4. [Passo a Passo: Criar Campanha](#passo-a-passo-criar-campanha)
5. [Iniciar Execucao](#iniciar-execucao)
6. [Monitoramento](#monitoramento)
7. [Metricas de Sucesso](#metricas-de-sucesso)
8. [Procedimentos de Emergencia](#procedimentos-de-emergencia)
9. [Pos-Piloto: Analise](#pos-piloto-analise)
10. [FAQ](#faq)

---

## Visao Geral

### O que e uma Campanha Discovery?

Discovery e o **primeiro contato** com medicos novos. O objetivo e:

- Apresentar a Revoluna e o que fazemos
- Qualificar interesse em plantoes SEM pressao
- Construir relacionamento (nao vender)
- Evitar hard sell - nenhuma oferta especifica no primeiro contato

### Caracteristicas da Mensagem Discovery

| Aspecto | Orientacao |
|---------|------------|
| Tom | Amigavel, leve, curioso |
| Tamanho | Curto (2-4 linhas por bloco) |
| Conteudo | Apresentacao + pergunta qualificadora |
| NAO fazer | Mencionar valores, vagas especificas, pressionar |

### Exemplo de Mensagem Discovery

```
Oi Dr {{nome}}! Tudo bem?

Sou a Julia da Revoluna, a gente trabalha com escalas medicas aqui na regiao do ABC

Vi que vc e {{especialidade}} ne? Temos algumas oportunidades que podem te interessar

Vc costuma fazer plantoes extras?
```

---

## Pre-requisitos

### Ambiente

| Componente | Status Necessario | Como Verificar |
|------------|-------------------|----------------|
| Dashboard Julia | Acessivel | Abrir URL do dashboard |
| API Backend | Rodando | `curl {API_URL}/health` |
| WhatsApp | Conectado | Dashboard > Status WhatsApp |
| Worker | Ativo | Railway logs ou dashboard |

### Permissoes

- [ ] Acesso ao Dashboard Julia
- [ ] Permissao para criar campanhas
- [ ] Acesso ao Supabase (para queries de emergencia)
- [ ] Acesso ao Slack (para notificacoes)

### Dados

- [ ] Lista de medicos do piloto definida (5-20 medicos para teste inicial)
- [ ] Medicos nao estao em opt-out
- [ ] Medicos nao receberam campanha nos ultimos 3 dias

---

## Checklist Pre-Piloto

Execute este checklist ANTES de criar a campanha:

### 1. Validar Lista de Medicos

```sql
-- Executar no Supabase para validar audiencia
SELECT
    c.id,
    c.nome,
    c.telefone,
    c.especialidade,
    c.opt_out,
    c.status
FROM clientes c
WHERE c.especialidade IN ('Cardiologia', 'Clinica Medica') -- ajustar filtros
AND c.opt_out = false
AND c.status != 'bloqueado'
LIMIT 20;
```

**Validar:**
- [ ] Todos tem telefone valido (formato 55DDDNUMERO)
- [ ] Nenhum esta em opt_out = true
- [ ] Nenhum esta bloqueado

### 2. Verificar Cooldowns

```sql
-- Verificar se medicos ja receberam campanha recente
SELECT
    c.nome,
    c.telefone,
    cch.last_campaign_at,
    cch.campaign_name
FROM campaign_contact_history cch
JOIN clientes c ON c.id = cch.client_id
WHERE cch.last_campaign_at > NOW() - INTERVAL '3 days'
AND c.especialidade IN ('Cardiologia'); -- ajustar filtros
```

**Se retornar resultados:** Estes medicos NAO podem receber nova campanha ainda.

### 3. Verificar Status Julia

```sql
-- Julia deve estar ativa
SELECT status, motivo, created_at
FROM julia_status
ORDER BY created_at DESC
LIMIT 1;
-- Esperado: status = 'ativo'
```

### 4. Verificar Fila de Mensagens

```sql
-- Fila nao deve estar congestionada
SELECT
    status,
    COUNT(*) as qtd
FROM fila_mensagens
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY status;
-- Se 'pending' > 50, aguardar antes de iniciar nova campanha
```

---

## Passo a Passo: Criar Campanha

### Acessar Dashboard

1. Abrir o Dashboard Julia no navegador
2. Navegar para **Campanhas** no menu lateral
3. Clicar no botao **"+ Nova Campanha"** (canto superior direito)

### Etapa 1: Configuracao

| Campo | Valor para Discovery Piloto | Exemplo |
|-------|----------------------------|---------|
| **Nome da Campanha** | Descritivo com data | `Piloto Discovery Cardio - 17Jan` |
| **Tipo de Campanha** | Descoberta | Selecionar "Descoberta" |
| **Categoria** | Marketing | Selecionar "Marketing" |
| **Objetivo** | Opcional | `Primeiro contato com cardiologistas do ABC para qualificar interesse` |

**Screenshot mental:**
```
┌─────────────────────────────────────────┐
│ Etapa 1 - Configuracao                  │
├─────────────────────────────────────────┤
│ Nome da Campanha *                      │
│ [Piloto Discovery Cardio - 17Jan    ]   │
│                                         │
│ Tipo          │ Categoria               │
│ [Descoberta v]│ [Marketing v]           │
│                                         │
│ Objetivo (opcional)                     │
│ [Primeiro contato com cardiologistas ]  │
│ [do ABC para qualificar interesse    ]  │
└─────────────────────────────────────────┘
```

Clicar **"Proximo"**

### Etapa 2: Audiencia

Para piloto, SEMPRE usar audiencia filtrada:

1. Selecionar **"Filtrar audiencia"**
2. Marcar especialidades do piloto (ex: Cardiologia)
3. Marcar regioes do piloto (ex: ABC Paulista)

**Importante para Piloto:**
- Comece com 1 especialidade e 1 regiao
- Isso limita naturalmente o numero de destinatarios
- Voce pode expandir apos validar resultados

| Campo | Valor para Piloto |
|-------|------------------|
| **Audiencia** | Filtrar audiencia |
| **Especialidades** | 1-2 especialidades |
| **Regioes** | 1 regiao |

**Screenshot mental:**
```
┌─────────────────────────────────────────┐
│ Etapa 2 - Audiencia                     │
├─────────────────────────────────────────┤
│ Audiencia                               │
│ [Filtrar audiencia v]                   │
│                                         │
│ Especialidades                          │
│ [x] Cardiologia  [ ] Clinica Medica     │
│ [ ] Pediatria    [ ] Ortopedia          │
│                                         │
│ Regioes                                 │
│ [ ] Sao Paulo    [x] ABC Paulista       │
│ [ ] Campinas     [ ] Santos             │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Filtros: 1 especialidade, 1 regiao  │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

Clicar **"Proximo"**

### Etapa 3: Mensagem

1. Selecionar tom **"Amigavel"**
2. Escrever mensagem usando template de discovery

**Template Recomendado para Piloto:**

```
Oi Dr {{nome}}! Tudo bem?

Sou a Julia da Revoluna, a gente trabalha com escalas medicas aqui na regiao do ABC

Vi que vc e {{especialidade}} ne? Temos algumas oportunidades que podem te interessar

Vc costuma fazer plantoes extras?
```

**Checklist da Mensagem:**
- [ ] Usa "vc", "pra", "ne" (informal)
- [ ] Curta (nao mais que 4 blocos)
- [ ] Termina com pergunta qualificadora
- [ ] NAO menciona valores ou vagas especificas
- [ ] NAO usa bullet points ou listas
- [ ] NAO usa linguagem corporativa

**Revisar Preview:**
O preview mostra como a mensagem ficara com dados de exemplo:
```
Oi Dr Carlos! Tudo bem?

Sou a Julia da Revoluna, a gente trabalha com escalas medicas aqui na regiao do ABC

Vi que vc e Cardiologia ne? Temos algumas oportunidades que podem te interessar

Vc costuma fazer plantoes extras?
```

Clicar **"Proximo"**

### Etapa 4: Revisao

1. Revisar todos os dados
2. **NAO marcar** "Agendar envio" (para controle manual)
3. Clicar **"Criar Campanha"**

**Resultado:** Campanha criada com status **"Rascunho"**

---

## Iniciar Execucao

### Antes de Iniciar

Execute esta verificacao final:

```
[ ] Horario dentro do comercial (08h-20h, seg-sex)
[ ] Julia status = 'ativo'
[ ] Fila de mensagens sem congestionamento
[ ] Equipe de supervisao avisada
[ ] Canal Slack de monitoramento aberto
```

### Iniciar Campanha

1. No Dashboard, localizar a campanha na aba **"Ativas"**
2. Clicar no menu **"..."** (tres pontos) no card da campanha
3. Selecionar **"Iniciar"** (ou botao equivalente)
4. Confirmar inicio

**Status muda para:** "Em Execucao" (badge amarelo)

### O que Acontece Apos Iniciar

1. Backend cria entradas na `fila_mensagens` para cada medico
2. Worker processa a fila respeitando rate limits:
   - 20 mensagens/hora
   - 45-180 segundos entre mensagens
   - Apenas 08h-20h seg-sex
3. Cada mensagem passa por guardrails:
   - Valida telefone
   - Verifica opt-out
   - Verifica cooldown (3 dias)
   - Verifica banimento

---

## Monitoramento

### Dashboard em Tempo Real

O card da campanha mostra metricas atualizadas:

```
┌─────────────────────────────────────────────────────────┐
│ Piloto Discovery Cardio - 17Jan                         │
│ Descoberta • Marketing                      [Em Execucao]│
├─────────────────────────────────────────────────────────┤
│  Destinatarios │  Enviados  │  Entregues  │  Respostas  │
│       15       │     8      │   7 (87%)   │   2 (28%)   │
├─────────────────────────────────────────────────────────┤
│ Criada ha 2 horas                                       │
└─────────────────────────────────────────────────────────┘
```

### Metricas para Acompanhar

| Metrica | Calculo | Alerta |
|---------|---------|--------|
| Taxa de Envio | Enviados / Destinatarios | Se < 50% apos 1h, verificar |
| Taxa de Entrega | Entregues / Enviados | Se < 80%, verificar numeros |
| Taxa de Resposta | Respostas / Entregues | Meta: > 20% |
| Taxa de Bloqueio | Bloqueados / Destinatarios | Se > 20%, pausar |

### Queries de Monitoramento

**Status detalhado da campanha:**
```sql
SELECT
    fm.status,
    fm.outcome,
    COUNT(*) as qtd
FROM fila_mensagens fm
WHERE fm.metadata->>'campaign_id' = 'ID_DA_CAMPANHA'
GROUP BY fm.status, fm.outcome
ORDER BY qtd DESC;
```

**Ultimas mensagens enviadas:**
```sql
SELECT
    c.nome,
    c.telefone,
    fm.status,
    fm.sent_at,
    fm.outcome
FROM fila_mensagens fm
JOIN clientes c ON c.id = fm.client_id
WHERE fm.metadata->>'campaign_id' = 'ID_DA_CAMPANHA'
ORDER BY fm.sent_at DESC
LIMIT 20;
```

**Respostas recebidas:**
```sql
SELECT
    c.nome,
    i.conteudo,
    i.created_at
FROM interacoes i
JOIN clientes c ON c.id = i.cliente_id
WHERE i.origem = 'medico'
AND i.created_at > NOW() - INTERVAL '4 hours'
ORDER BY i.created_at DESC;
```

### Sinais de Alerta

| Sinal | Acao |
|-------|------|
| Muitas mensagens "blocked" | Verificar cooldowns e opt-outs |
| Mensagens "failed" | Verificar conexao WhatsApp |
| Zero respostas apos 2h | Revisar mensagem, pode estar robotica |
| Resposta negativa/irritada | Preparar para handoff |
| Pedido de opt-out | Verificar se foi processado automaticamente |

---

## Metricas de Sucesso

### Metas para Piloto Discovery

| Metrica | Meta Minima | Meta Ideal | Critico |
|---------|-------------|------------|---------|
| Taxa de Entrega | > 80% | > 95% | < 70% |
| Taxa de Resposta | > 15% | > 30% | < 10% |
| Taxa de Opt-out | < 5% | < 2% | > 10% |
| Handoffs negativos | < 10% | < 5% | > 20% |
| Deteccao como bot | 0% | 0% | > 1% |

### Criterios de Sucesso do Piloto

Para considerar o piloto **bem-sucedido**:

```
[ ] Taxa de resposta >= 15%
[ ] Taxa de opt-out < 5%
[ ] Zero deteccoes como bot
[ ] Nenhuma reclamacao grave
[ ] Pelo menos 1 lead qualificado (medico interessado)
```

---

## Procedimentos de Emergencia

### PAUSAR Campanha

Se detectar problema, pausar imediatamente:

**Via Dashboard:**
1. Localizar campanha em "Ativas"
2. Menu "..." > "Pausar"
3. Status muda para "Pausada"

**Via SQL (emergencia):**
```sql
UPDATE campanhas
SET status = 'pausada'
WHERE id = ID_DA_CAMPANHA;

-- Parar mensagens pendentes
UPDATE fila_mensagens
SET status = 'cancelled'
WHERE metadata->>'campaign_id' = 'ID_DA_CAMPANHA'
AND status = 'pending';
```

### PAUSAR Julia Completamente

Se precisar parar TODA operacao:

```sql
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Emergencia piloto - pausado manualmente', 'manual');
```

### Cenarios de Emergencia

| Cenario | Acao Imediata |
|---------|---------------|
| Medico detectou bot | 1. Pausar campanha 2. Revisar mensagem 3. Analisar conversa |
| Reclamacao no Slack | 1. Verificar handoff automatico 2. Assumir conversa se necessario |
| Muitos opt-outs | 1. Pausar campanha 2. Analisar padroes 3. Ajustar mensagem |
| WhatsApp desconectado | 1. Pausar Julia 2. Reconectar via Evolution 3. Retomar |
| Rate limit atingido | Sistema ja trata, apenas monitorar |

### Contatos de Emergencia

| Responsabilidade | Contato |
|-----------------|---------|
| Tecnico Backend | [Nome/Canal] |
| Gestao Julia | [Nome/Canal] |
| Supervisao Medicos | [Nome/Canal] |

---

## Pos-Piloto: Analise

### Relatorio Final

Apos conclusao do piloto, gerar relatorio:

```sql
-- Metricas finais
SELECT
    c.nome_template,
    c.total_destinatarios,
    c.enviados,
    c.entregues,
    c.respondidos,
    ROUND(c.entregues::numeric / NULLIF(c.enviados, 0) * 100, 1) as taxa_entrega,
    ROUND(c.respondidos::numeric / NULLIF(c.entregues, 0) * 100, 1) as taxa_resposta,
    c.iniciada_em,
    c.concluida_em
FROM campanhas c
WHERE c.id = ID_DA_CAMPANHA;
```

### Analise de Respostas

Categorizar respostas recebidas:

| Categoria | Descricao | Exemplo |
|-----------|-----------|---------|
| Interesse positivo | Quer saber mais | "Sim, tenho interesse!" |
| Interesse qualificado | Deu preferencias | "Prefiro noturno no ABC" |
| Nao no momento | Talvez futuro | "Agora nao, me procura mes que vem" |
| Sem interesse | Recusou | "Nao preciso, obrigado" |
| Opt-out | Pediu para parar | "Para de me mandar mensagem" |
| Detectou bot | Perguntou se e IA | "Vc e um bot?" |

### Proximos Passos

Baseado nos resultados:

**Se piloto bem-sucedido:**
1. Documentar aprendizados
2. Ajustar mensagem se necessario
3. Expandir para mais especialidades/regioes
4. Aumentar volume gradualmente

**Se piloto com problemas:**
1. Identificar causa raiz
2. Ajustar mensagem/timing
3. Rodar novo piloto menor
4. Nao escalar ate resolver

---

## FAQ

### Posso editar uma campanha apos criar?

Apenas se estiver em **Rascunho**. Apos iniciar, nao e possivel editar.

### Quantos medicos devo incluir no piloto?

- **Primeiro piloto:** 5-10 medicos
- **Segundo piloto:** 15-25 medicos
- **Piloto expandido:** 50-100 medicos

### Qual o melhor horario para enviar?

- **Ideal:** 10h-12h ou 14h-16h (dias uteis)
- **Evitar:** Segunda de manha, Sexta a tarde

### E se um medico responder irritado?

Julia detecta automaticamente e pode fazer handoff. Monitore o Slack para assumir se necessario.

### Posso cancelar uma campanha em andamento?

Sim. Menu "..." > "Cancelar". Mensagens pendentes nao serao enviadas.

### Como sei se a mensagem parece robotica?

Sinais de alerta:
- Respostas perguntando se e bot
- Taxa de resposta muito baixa (< 10%)
- Opt-outs acima do normal

### Preciso avisar alguem antes de rodar?

Sim! Sempre avise:
- Equipe de supervisao (Slack)
- Gestor responsavel
- Documentar data/hora de inicio

---

## Registro de Execucao

### Template de Registro

Preencher para cada piloto executado:

```
Data: ____/____/______
Hora Inicio: ____:____
Operador: ________________
Campanha ID: ________________

Audiencia:
- Especialidade(s): ________________
- Regiao(oes): ________________
- Total destinatarios: ____

Resultados:
- Enviados: ____
- Entregues: ____ (___%)
- Respostas: ____ (___%)
- Opt-outs: ____ (___%)
- Handoffs: ____

Observacoes:
_________________________________
_________________________________
_________________________________

Aprovado para expansao? [ ] Sim [ ] Nao

Proxima acao:
_________________________________
```

---

## Historico de Versoes

| Versao | Data | Autor | Alteracoes |
|--------|------|-------|------------|
| 1.0 | 17/01/2026 | - | Versao inicial |

---

**Duvidas?** Consultar equipe tecnica ou documentacao em `docs/julia/` e `docs/operacao/`.
