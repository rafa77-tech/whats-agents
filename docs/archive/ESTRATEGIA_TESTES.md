# Estratégia de Testes, Warm-up e Validação

Este documento define como testar a Júlia sem riscos para o número WhatsApp e para o relacionamento com médicos.

---

## Princípios

1. **Nunca spammar** - Mesmo em testes, respeitar rate limits
2. **Progressão gradual** - Aumentar volume só após validar cada fase
3. **Rollback rápido** - Poder pausar tudo instantaneamente
4. **Feedback loop** - Cada fase gera aprendizados para a próxima

---

## Fases de Teste

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FASES DE TESTE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  FASE 0          FASE 1          FASE 2          FASE 3            │
│  Sandbox         Equipe          Beta Médicos    Produção          │
│                  Interna         Controlado      Gradual           │
│                                                                     │
│  • Sem WhatsApp  • 5-10 pessoas  • 10-20 médicos • 100+ médicos    │
│  • Só terminal   • Número teste  • Número teste  • Número real     │
│  • Validar LLM   • Validar fluxo • Validar       • Escalar         │
│                                    persona                          │
│                                                                     │
│  1-2 dias        3-5 dias        1-2 semanas     Contínuo          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fase 0: Sandbox (Sem WhatsApp)

### Objetivo
Validar que o agente Júlia responde corretamente antes de conectar ao WhatsApp.

### Como Testar
```python
# Terminal ou script de teste
python -m app.agent --test

# Simular conversa
> Usuário: Oi, tudo bem?
> Júlia: Oi! Tudo ótimo e vc?

> Usuário: Tô procurando plantão
> Júlia: Que bom! Qual sua especialidade?
```

### Checklist
- [ ] Respostas no tom correto (informal, amigável)
- [ ] Não usa bullet points ou listas
- [ ] Mensagens curtas (1-3 linhas)
- [ ] Usa abreviações naturais (vc, pra, tá)
- [ ] Não revela que é IA em nenhum cenário
- [ ] Handoff funciona quando solicitado

### Cenários de Teste

| Cenário | Input | Resposta Esperada |
|---------|-------|-------------------|
| Saudação | "Oi" | Saudação informal + pergunta |
| Interesse | "Tenho interesse em plantão" | Pergunta sobre especialidade/disponibilidade |
| Objeção valor | "Tá pouco" | Tenta negociar ou aceita graciosamente |
| Pede humano | "Quero falar com alguém" | Transfere sem resistência |
| Pergunta se é bot | "Isso é automático?" | Responde que é a Júlia, escalista |
| Irritado | "Que droga de atendimento" | Desculpa + oferece handoff |
| Opt-out | "Para de me mandar mensagem" | Confirma e para imediatamente |

### Critério de Saída
- 50+ cenários testados sem falhas críticas
- Persona aprovada pela equipe

---

## Fase 1: Equipe Interna

### Objetivo
Validar o fluxo completo (WhatsApp → Agente → Resposta) com pessoas que sabem do projeto.

### Participantes
- Equipe operacional (5-10 pessoas)
- Cada um simula ser um médico

### Setup
1. Número WhatsApp de teste conectado ao Evolution API
2. Chatwoot configurado para monitoramento
3. Equipe adicionada como contatos

### Protocolo de Teste

**Cada membro da equipe deve:**

1. **Dia 1-2: Fluxos básicos**
   - Receber mensagem de abertura
   - Responder com interesse
   - Receber oferta de vaga
   - Aceitar ou recusar

2. **Dia 3-4: Cenários difíceis**
   - Pedir desconto agressivamente
   - Fingir irritação
   - Pedir para falar com humano
   - Perguntar se é bot
   - Mandar áudio (testar tratamento)
   - Mandar mensagem fora do horário

3. **Dia 5: Estresse**
   - Múltiplas mensagens rápidas
   - Mensagens longas
   - Emojis e figurinhas
   - Tentar "quebrar" o sistema

### Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Fluxo completo sem erro | 100% |
| Handoff funciona | 100% |
| Tempo de resposta | < 30s |
| Erros críticos | 0 |

### Critério de Saída
- Todos os fluxos testados
- Zero erros críticos por 48h
- Equipe aprova experiência

---

## Fase 2: Beta com Médicos Controlado

### Objetivo
Validar com médicos reais, mas em ambiente controlado.

### Seleção de Médicos Beta

**Critérios:**
- Médicos que já têm relacionamento com a empresa
- Idealmente, informados que estão testando novo sistema
- Ou: médicos novos, sem histórico (menor risco)

**Quantidade:** 10-20 médicos

**Query para selecionar:**
```sql
SELECT * FROM clientes
WHERE especialidade = 'Anestesiologia'
  AND opt_out = false
  AND telefone IS NOT NULL
  AND crm IS NOT NULL
  -- Priorizar quem tem mais dados preenchidos
ORDER BY
  (CASE WHEN primeiro_nome IS NOT NULL THEN 1 ELSE 0 END +
   CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) DESC
LIMIT 20;
```

### Rate Limiting Conservador

| Parâmetro | Valor Fase 2 | Valor Final |
|-----------|--------------|-------------|
| Mensagens/hora | 5 | 20 |
| Mensagens/dia | 20 | 100 |
| Intervalo mínimo | 3 minutos | 45 segundos |
| Horário | 09h-18h | 08h-20h |

### Protocolo

**Semana 1:**
- Dia 1-2: 5 médicos, 1 mensagem cada
- Dia 3-4: +5 médicos (10 total)
- Dia 5: Análise de respostas

**Semana 2:**
- Expandir para 20 médicos
- Follow-ups para quem não respondeu
- Ofertas de vagas para interessados

### Monitoramento Intensivo

**A cada mensagem enviada:**
- [ ] Verificar se resposta faz sentido
- [ ] Verificar se tom está adequado
- [ ] Verificar se não revelou ser IA
- [ ] Anotar qualquer problema

**Diariamente:**
- [ ] Revisar TODAS as conversas
- [ ] Marcar problemas encontrados
- [ ] Ajustar prompts se necessário

### Sinais de Alerta (Pausar Imediatamente)

| Sinal | Ação |
|-------|------|
| Médico pergunta "é bot?" | Pausar, analisar contexto |
| Médico reclama formalmente | Pausar, handoff humano |
| Resposta sem sentido | Pausar, corrigir |
| Erro técnico | Pausar, investigar |
| 3+ médicos não respondem | Analisar abordagem |

### Métricas de Sucesso

| Métrica | Meta | Mínimo Aceitável |
|---------|------|------------------|
| Taxa de resposta | > 30% | > 15% |
| Detecção como bot | 0% | < 5% |
| Reclamações | 0 | 0 |
| Conversas naturais | > 80% | > 60% |

### Critério de Saída
- 2 semanas sem incidentes
- Taxa de resposta > 15%
- Zero detecções como bot
- Pelo menos 1 vaga fechada

---

## Fase 3: Produção Gradual

### Objetivo
Escalar para base completa de forma segura.

### Warm-up do Volume

```
Semana 1:  20 médicos/dia  (100/semana)
Semana 2:  30 médicos/dia  (150/semana)
Semana 3:  50 médicos/dia  (250/semana)
Semana 4:  75 médicos/dia  (375/semana)
Semana 5+: 100 médicos/dia (500/semana)
```

### Critérios para Aumentar Volume

Só aumentar se nos últimos 7 dias:
- [ ] Taxa de resposta > 20%
- [ ] Zero detecções como bot
- [ ] Zero reclamações formais
- [ ] Uptime > 99%
- [ ] Latência < 30s (P95)

### Critérios para Pausar

Pausar imediatamente se:
- [ ] 2+ médicos perguntam se é bot no mesmo dia
- [ ] Qualquer reclamação formal
- [ ] Taxa de resposta < 10% por 3 dias
- [ ] Erro técnico afetando conversas
- [ ] Ban ou warning do WhatsApp

---

## Warm-up do Número WhatsApp

### Por que é Importante
Números novos que enviam muitas mensagens rapidamente são banidos. Precisamos "aquecer" o número gradualmente.

### Estratégia de Warm-up

**Semana -2 (antes de começar):**
- Usar o número normalmente para conversas reais
- Enviar/receber mensagens com a equipe
- Participar de grupos
- Objetivo: mostrar que é um número "humano"

**Semana -1:**
- Continuar uso normal
- Adicionar alguns contatos novos organicamente
- Enviar mensagens para 5-10 pessoas/dia

**Semana 1 (início do piloto):**
- Máximo 10 mensagens novas/dia
- Intervalo mínimo: 5 minutos entre envios
- Só enviar para quem responde

**Semana 2+:**
- Aumentar gradualmente conforme tabela acima
- Sempre monitorar sinais de warning

### Sinais de Problema com WhatsApp

| Sinal | Severidade | Ação |
|-------|------------|------|
| Mensagem não entregue | Baixa | Verificar número |
| Múltiplas não entregues | Média | Reduzir volume 50% |
| Conta temporariamente limitada | Alta | Pausar 24-48h |
| Ban permanente | Crítica | Trocar número, investigar |

### Boas Práticas

**FAZER:**
- Variar horários de envio
- Personalizar cada mensagem (não parecer template)
- Responder rapidamente quando médico responde
- Manter conversas naturais
- Usar o número para outras coisas além de prospecção

**NÃO FAZER:**
- Enviar mesma mensagem para muitos contatos
- Enviar em rajadas (muitas msgs em poucos minutos)
- Ignorar respostas
- Enviar fora do horário comercial
- Enviar para números inválidos repetidamente

---

## Validação da Persona

### Teste do "Amigo Médico"

Pedir para alguém que não conhece o projeto (idealmente um médico) avaliar prints de conversas:

1. Mostrar 10 conversas (sem dizer que é IA)
2. Perguntar: "Algo estranho nessas conversas?"
3. Perguntar: "Parece uma pessoa real?"
4. Se identificar como bot → falhou, ajustar

### Checklist de Naturalidade

| Aspecto | ✅ Natural | ❌ Robótico |
|---------|-----------|-------------|
| Cumprimento | "Oi! Tudo bem?" | "Olá, como vai você?" |
| Erros de digitação | "plantao* plantão" ocasional | Perfeito sempre |
| Tamanho | 1-3 linhas por msg | Parágrafos longos |
| Emojis | 1-2 por conversa | Muitos ou nenhum |
| Formalidade | "vc", "pra", "tá" | "você", "para", "está" |
| Listas | Nunca | Bullet points |
| Tempo de resposta | Variável (5-60s) | Sempre instantâneo |

### Métricas de Persona

| Métrica | Como Medir | Meta |
|---------|------------|------|
| Detecção direta | Médico pergunta se é bot | 0% |
| Detecção indireta | Médico age estranho, desconfia | < 5% |
| Naturalidade | Avaliação humana das conversas | > 8/10 |
| Engajamento | Médico faz perguntas de volta | > 50% |

---

## Plano de Rollback

### Níveis de Alerta

| Nível | Trigger | Ação |
|-------|---------|------|
| 🟢 Normal | Tudo OK | Continuar |
| 🟡 Atenção | Métrica abaixo do esperado | Monitorar de perto |
| 🟠 Alerta | Problema identificado | Reduzir volume 50% |
| 🔴 Crítico | Incidente grave | Pausar tudo |

### Procedimento de Pausa

**Pausa Parcial (🟠):**
```sql
-- Parar novos envios, manter conversas ativas
UPDATE julia_status
SET status = 'pausado',
    motivo = 'Alerta: [descrever]',
    alterado_via = 'manual'
WHERE id = (SELECT id FROM julia_status ORDER BY created_at DESC LIMIT 1);
```

**Pausa Total (🔴):**
1. Pausar worker de cadência
2. Júlia continua respondendo conversas ativas
3. Handoff automático para novas mensagens
4. Notificar gestor no Slack
5. Investigar causa

### Comunicação em Incidente

```
🔴 INCIDENTE - Júlia Pausada

Horário: [timestamp]
Motivo: [descrição]
Impacto: [número de conversas afetadas]
Ação: [o que estamos fazendo]
ETA: [quando esperamos resolver]

Próxima atualização em [X] minutos.
```

---

## Cronograma Sugerido

| Semana | Fase | Atividade | Participantes |
|--------|------|-----------|---------------|
| 1 | 0 | Testes em sandbox | Dev |
| 2 | 1 | Equipe interna | 5-10 pessoas |
| 3-4 | 2 | Beta médicos | 10-20 médicos |
| 5+ | 3 | Produção gradual | Escalar conforme métricas |

---

## Checklist Geral

### Antes de Fase 1
- [ ] Número de teste conectado ao Evolution
- [ ] Chatwoot configurado
- [ ] Agente Júlia respondendo corretamente
- [ ] Rate limits configurados (conservadores)
- [ ] Monitoramento funcionando
- [ ] Equipe treinada no Chatwoot

### Antes de Fase 2
- [ ] Fase 1 aprovada sem incidentes
- [ ] 20 médicos selecionados para beta
- [ ] Protocolo de monitoramento definido
- [ ] Critérios de pausa claros

### Antes de Fase 3
- [ ] Fase 2 concluída com sucesso
- [ ] Métricas dentro do esperado
- [ ] Warm-up do número OK
- [ ] Plano de escala definido
