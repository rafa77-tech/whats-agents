# Template: Briefing da Júlia

Formato do Google Docs que o gestor usa para direcionar a Júlia.

---

## Formato do Documento

```markdown
# Briefing Júlia - Semana DD/MM

## Foco da Semana
- Prioridade 1: [descrição]
- Prioridade 2: [descrição]
- Evitar: [descrição]

## Vagas Prioritárias
- [Hospital] - [Especialidade] - [Urgência] - [Observação]

## Médicos VIP
- Dr. [Nome] ([CRM]) - [motivo]

## Médicos Bloqueados
- Dr. [Nome] - [motivo]

## Tom da Semana
- [instrução]

## Metas
- [X] novos contatos
- [Y] médicos qualificados
- [Z] plantões fechados

## Instruções Especiais
- [instrução livre]
```

---

## Seções e Como São Processadas

| Seção | Tipo de Diretriz | Comportamento |
|-------|------------------|---------------|
| Foco da Semana | `foco`, `evitar` | "Prioridade" → foco, "Evitar" → evitar |
| Vagas Prioritárias | `vaga_prioritaria` | Cada linha vira diretriz |
| Médicos VIP | `vip` | Extrai CRM, vincula ao cliente |
| Médicos Bloqueados | `bloqueado` | Extrai CRM, vincula ao cliente |
| Tom da Semana | `tom` | Instruções de comunicação |
| Metas | `meta` | Métricas a atingir |
| Instruções Especiais | `instrucao_geral` | Regras específicas |

---

## Exemplo Completo

```markdown
# Briefing Júlia - Semana 09/12

## Foco da Semana
- Prioridade 1: Anestesistas da Grande São Paulo
- Prioridade 2: Cardiologistas que não responderam há 30+ dias
- Evitar: Hospital Santa Cruz (problema de pagamento pendente)

## Vagas Prioritárias
- Hospital São Luiz Morumbi - Anestesiologia - URGENTE - Paga bem
- Hospital Albert Einstein - Cardiologia UTI - VIP - Só médico experiente
- Hospital Samaritano - Clínica Geral PS - Normal - Boa pra iniciantes

## Médicos VIP
- Dr. Carlos Mendes (CRM 123456) - Indicação do Dr. Paulo. Tratar super bem.
- Dra. Ana Costa (CRM 789012) - Já trabalhou conosco, quer voltar.
- Dr. Ricardo Souza (CRM 345678) - Presidente da associação de anestesistas.

## Médicos Bloqueados
- Dr. João Silva (CRM 111111) - Pediu para não contatar
- Dra. Maria Santos (CRM 222222) - Processo judicial em andamento
- Dr. Pedro Oliveira (CRM 333333) - Reclamou do último plantão

## Tom da Semana
- Ser mais direta, menos enrolação
- Mencionar que temos muitas vagas boas
- Garantir pagamento em até 15 dias úteis
- Não pressionar demais

## Metas
- 50 novos contatos iniciados
- 10 médicos qualificados
- 3 plantões fechados
- 0 reclamações de spam

## Instruções Especiais
- Feriado na quinta, ajustar horários
- Não mencionar vaga do Hospital X até sexta
- Se perguntarem do Dr. Fernando, dizer que não trabalha mais conosco
```

---

## Dicas para o Gestor

### Faça
- Use o formato exato das seções (com ##)
- Seja específico nas instruções
- Inclua CRM quando mencionar médico
- Atualize semanalmente
- Mantenha conciso

### Não faça
- Não mude os nomes das seções
- Não use formatação complexa (tabelas, imagens)
- Não coloque informações contraditórias
- Não esqueça de remover bloqueados quando resolver

---

## Como Funciona

1. **Leitura:** Worker lê o documento a cada 60 minutos
2. **Detecção:** Compara hash para detectar mudanças
3. **Parsing:** Extrai diretrizes de cada seção
4. **Atualização:** Desativa diretrizes antigas, insere novas
5. **Aplicação:** Próxima mensagem da Júlia usa as novas diretrizes

**Expirações:**
- Diretrizes do Google Docs: substituídas na próxima leitura
- Diretrizes do Slack: expiram em 7 dias
