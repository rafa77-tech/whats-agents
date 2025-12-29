# Critérios de Sucesso - MVP Júlia

Este documento define **como saberemos se o MVP foi bem-sucedido**.

---

## North Star Metric

> **Plantões fechados por semana via Júlia**

Esta é a métrica que mais importa. Se Júlia está fechando plantões, está funcionando.

---

## Métricas de Sucesso (MVP)

### 1. Eficácia de Prospecção

| Métrica | Meta MVP | Como Medir | Frequência |
|---------|----------|------------|------------|
| Taxa de resposta | > 25% | `responderam / contatados` | Diária |
| Taxa de qualificação | > 10% | `qualificados / responderam` | Diária |
| Taxa de conversão | > 5% | `fecharam / contatados` | Semanal |

**Definições:**
- **Respondeu:** Enviou qualquer mensagem de volta
- **Qualificado:** Demonstrou interesse real em plantões
- **Fechou:** Aceitou pelo menos 1 plantão

### 2. Qualidade da Interação

| Métrica | Meta MVP | Como Medir | Frequência |
|---------|----------|------------|------------|
| Taxa de detecção como bot | < 5% | `detectados / conversas` | Semanal |
| Taxa de handoff | < 15% | `handoffs / conversas` | Diária |
| Sentimento médio | > 0 | Score de sentimento LLM | Diária |

**Como medir detecção:**
- Médico menciona: "bot", "robô", "IA", "automático"
- Médico pergunta: "isso é automático?", "tô falando com máquina?"
- Flag manual pelo gestor ao revisar conversas

### 3. Performance Técnica

| Métrica | Meta MVP | Como Medir | Frequência |
|---------|----------|------------|------------|
| Latência de resposta | < 30s | Tempo entre receber e enviar | Contínua |
| Uptime | > 99% | Monitoramento | Contínua |
| Taxa de erro | < 1% | `erros / mensagens processadas` | Diária |

### 4. Operacional

| Métrica | Meta MVP | Como Medir | Frequência |
|---------|----------|------------|------------|
| Msgs/dia enviadas | > 50 | Contador | Diária |
| Rate limit respeitado | 100% | Sem ban do WhatsApp | Contínua |
| Opt-out respeitado | 100% | Auditoria | Semanal |

---

## Critérios de Go/No-Go

### Para Lançar MVP (Go)

Todos devem ser verdade:
- [ ] Sistema estável por 3 dias consecutivos
- [ ] Pelo menos 10 conversas de teste sem falhas críticas
- [ ] Taxa de detecção como bot < 10% em testes
- [ ] Handoff funcionando corretamente
- [ ] Gestor consegue monitorar via Chatwoot
- [ ] Reports chegando no Slack

### Para Escalar (Após MVP)

- [ ] Taxa de resposta > 25% por 2 semanas
- [ ] Taxa de detecção < 5%
- [ ] Pelo menos 5 plantões fechados via Júlia
- [ ] Zero ban de WhatsApp
- [ ] Feedback positivo do gestor

### Para Pausar/Pivotar (No-Go)

Se qualquer um ocorrer:
- [ ] Ban do WhatsApp
- [ ] Taxa de detecção > 20%
- [ ] Reclamações formais de médicos
- [ ] Taxa de resposta < 10% por 2 semanas
- [ ] Gestor reporta que não está funcionando

---

## Dashboard de Acompanhamento

### Visão Diária (Slack - Report Automático)

```
📊 Júlia - Report Diário (05/12)

PROSPECÇÃO
├── Enviadas: 47
├── Responderam: 14 (30%)
├── Qualificados: 4 (8%)
└── Fechados: 1 (2%)

CONVERSAS
├── Ativas: 23
├── Handoffs: 2
└── Sentimento médio: +0.3

PERFORMANCE
├── Latência média: 8s
├── Erros: 0
└── Uptime: 100%

🎯 Plantão fechado: Dr. João - Hospital Brasil - Sáb 14/12
⚠️ Handoff: Dra. Maria (irritada com valor)
```

### Visão Semanal

```
📈 Júlia - Report Semanal (02-08/12)

FUNIL
├── Contatados: 235
├── Responderam: 71 (30.2%)
├── Qualificados: 18 (7.6%)
└── Fecharam: 4 (1.7%)

PLANTÕES FECHADOS: 7
├── Hospital Brasil: 4
├── São Luiz: 2
└── Cruz Azul: 1

DETECÇÃO COMO BOT: 2 casos (0.8%)
├── Dr. Carlos: "isso é automático?"
└── Dra. Ana: "parece bot"

TOP OBJEÇÕES
├── Valor baixo: 34%
├── Sem disponibilidade: 28%
├── Hospital longe: 18%
└── Já trabalha com outra empresa: 12%

RECOMENDAÇÕES
├── Aumentar valor máximo do Hospital Brasil
├── Focar em médicos da zona sul (mais próximos)
└── Testar horário de envio às 10h (melhor resposta)
```

---

## Baseline vs. Meta

### Cenário Atual (Manual)

> **PERGUNTA:** Quais são os números atuais do processo manual?

| Métrica | Atual (Manual) | Meta MVP | Meta 3 meses |
|---------|----------------|----------|--------------|
| Médicos contatados/dia | ? | 50 | 200 |
| Taxa de resposta | ? | 25% | 35% |
| Plantões fechados/semana | ? | 5 | 20 |
| Custo por contato | ? | R$ 0.50* | R$ 0.30 |
| Tempo do escalista | ? | -80% | -90% |

*Custo estimado: LLM + infraestrutura

---

## Experimentos do MVP

### Teste A/B: Horário de Envio

| Variante | Horário | Hipótese |
|----------|---------|----------|
| A | 09:00-11:00 | Médicos checam WhatsApp de manhã |
| B | 14:00-16:00 | Após plantão/consultas |
| C | 18:00-19:00 | Fim do dia, mais relaxados |

**Métrica:** Taxa de resposta
**Duração:** 2 semanas
**Amostra:** 100 médicos por variante

### Teste A/B: Tom de Abertura

| Variante | Tom | Exemplo |
|----------|-----|---------|
| A | Casual | "Oi Dr Carlos! Tudo bem?" |
| B | Direto | "Oi Dr Carlos, tenho vagas de anestesia" |
| C | Curioso | "Dr Carlos, posso te fazer uma pergunta rápida?" |

**Métrica:** Taxa de resposta
**Duração:** 2 semanas

---

## Coleta de Dados

### Eventos a Logar

| Evento | Dados | Tabela |
|--------|-------|--------|
| msg_enviada | tipo, template, hora | interacoes |
| msg_recebida | conteúdo, hora, sentimento | interacoes |
| vaga_oferecida | vaga_id, valor | interacoes |
| vaga_aceita | vaga_id, valor_final | vagas |
| handoff_iniciado | motivo, contexto | handoffs |
| erro | tipo, mensagem, stack | logs |
| deteccao_bot | contexto, frase | metricas |

### Query: Funil Diário

```sql
SELECT
    DATE(created_at) as dia,
    COUNT(DISTINCT CASE WHEN tipo = 'abertura' THEN cliente_id END) as contatados,
    COUNT(DISTINCT CASE WHEN direcao = 'recebida' THEN cliente_id END) as responderam,
    COUNT(DISTINCT CASE WHEN stage = 'qualificado' THEN c.id END) as qualificados,
    COUNT(DISTINCT CASE WHEN v.status = 'preenchida' THEN v.medico_id END) as fecharam
FROM interacoes i
LEFT JOIN clientes c ON i.cliente_id = c.id
LEFT JOIN vagas v ON v.medico_id = c.id
WHERE DATE(i.created_at) = CURRENT_DATE
GROUP BY 1;
```

---

## Timeline de Avaliação

| Semana | Foco | Decisão |
|--------|------|---------|
| 1 | Estabilidade técnica | Go/No-Go para testes reais |
| 2 | Primeiros contatos reais | Ajustes de persona |
| 3-4 | Volume crescente | Avaliação de métricas |
| 5-6 | Análise de resultados | Decisão de escalar |

---

## Responsabilidades

| Papel | Responsabilidade |
|-------|------------------|
| Dev | Implementar coleta de métricas |
| PM | Analisar dados, propor ajustes |
| Gestor | Feedback qualitativo, revisão de conversas |
| Todos | Alertar se métricas fora do esperado |
