# E24 - Documentação

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 6 - Limpeza e Polish
**Dependências:** Todos os épicos anteriores
**Estimativa:** 3h

---

## Objetivo

Atualizar toda a documentação para refletir as mudanças da Sprint 32 - novo modelo de comportamentos, Julia autônoma, canal de ajuda, etc.

---

## Documentos a Atualizar

| Documento | Mudanças Necessárias |
|-----------|---------------------|
| `CLAUDE.md` | Seções de campanhas, comportamentos, piloto |
| `docs/arquitetura/` | Novo fluxo de campanhas |
| `docs/julia/` | Comportamentos, regras, canal de ajuda |
| `docs/operacao/` | Runbook modo piloto, hospitais bloqueados |
| `planning/sprint-32/README.md` | Marcar como concluído |

---

## Tasks

### T1: Atualizar CLAUDE.md (1h)

**Seções a adicionar/modificar:**

```markdown
## Comportamentos de Campanha (Sprint 32)

Julia opera com 5 tipos de comportamento:

| Tipo | Descrição | Pode Ofertar Proativamente |
|------|-----------|---------------------------|
| discovery | Conhecer médicos | ❌ Nunca |
| oferta | Apresentar vagas | ✅ Sim |
| followup | Manter relacionamento | ❌ Só se perguntado |
| feedback | Coletar opinião | ❌ Só se perguntado |
| reativacao | Retomar inativos | ❌ Só se confirmado interesse |

### Regra Crítica: Oferta

```
Julia é REATIVA para ofertas, não PROATIVA.

Oferta só acontece se:
1. Tipo da campanha = 'oferta'
2. OU médico pergunta explicitamente

Em qualquer outro caso → RELACIONAMENTO
```

### Estrutura de Campanha

```python
campanha = {
    "nome": "Cardiologia Março 2026",
    "tipo": "oferta",
    "objetivo": "Apresentar vagas de cardio para março",
    "regras": [
        "Apresentar apenas vagas do escopo",
        "Consultar sistema antes de mencionar",
        "Nunca inventar vagas"
    ],
    "escopo_vagas": {
        "especialidade": "cardiologia",
        "periodo_inicio": "2026-03-01",
        "periodo_fim": "2026-03-31"
    },
    "pode_ofertar": True
}
```

---

## Modo Piloto

| Flag | Valor | Efeito |
|------|-------|--------|
| `PILOT_MODE` | `True` | Ações autônomas desabilitadas |
| `PILOT_MODE` | `False` | Julia age autonomamente |

### O que funciona em Modo Piloto

- ✅ Campanhas manuais
- ✅ Respostas a médicos
- ✅ Canal de ajuda
- ✅ Comandos via Slack
- ❌ Discovery automático
- ❌ Oferta automática
- ❌ Reativação automática
- ❌ Feedback automático

### Alternar Modo Piloto

- **Dashboard:** Sistema → Toggle
- **Código:** `settings.PILOT_MODE = True/False`

---

## Canal de Ajuda (Anti-Alucinação)

Quando Julia não sabe algo factual:

1. **NÃO inventa** resposta
2. **PAUSA** conversa
3. **PERGUNTA** ao gestor (Slack ou Dashboard)
4. **ESPERA** resposta
5. **RETOMA** com informação correta
6. **SALVA** conhecimento para futuro

### Timeout

- 5 minutos sem resposta → Julia diz "Vou confirmar essa info"
- Lembretes a cada 30 minutos

---

## Hospitais Bloqueados

Quando hospital é bloqueado:
1. Vagas movidas para `vagas_hospitais_bloqueados`
2. Julia não vê as vagas (não precisa filtrar)
3. Ao desbloquear, vagas futuras restauradas

### Bloquear/Desbloquear

- **Dashboard:** Hospitais → Bloqueados
- **Slack:** "Julia, bloquear hospital X motivo: Y"

---

## Diretrizes Contextuais

Margens de negociação e regras especiais por escopo:

| Escopo | Exemplo | Expira quando |
|--------|---------|---------------|
| vaga | "Vaga 123 pode até R$ 3.000" | Vaga preenchida |
| medico | "Dr Carlos pode 15% a mais" | Médico sem interesse |
| hospital | "Hospital X pode 10% acima" | Manual |
| global | "Essa semana pode 5% a mais" | Data definida |
```

---

### T2: Criar doc de comportamentos (45min)

**Arquivo:** `docs/julia/comportamentos.md`

```markdown
# Comportamentos de Campanha

Este documento descreve os 5 tipos de comportamento que Julia pode ter em campanhas.

## Discovery

**Objetivo:** Conhecer médicos novos

**PODE:**
- Perguntar se faz plantão
- Perguntar especialidade
- Perguntar região/cidade
- Perguntar preferências (turno, tipo de hospital)
- Criar rapport, conversar naturalmente

**NÃO PODE:**
- Mencionar vagas
- Falar de valores
- Ofertar qualquer coisa
- Dizer "tenho uma oportunidade"

**Gatilho para oferta:**
- Somente se médico perguntar explicitamente

---

## Oferta

**Objetivo:** Apresentar vagas REAIS que existem no sistema

**PRÉ-REQUISITO ABSOLUTO:**
- Sistema verifica se existem vagas no escopo
- Se não existir: campanha NÃO dispara

**PODE:**
- Apresentar vagas que EXISTEM dentro do escopo
- Falar valores, datas, locais
- Negociar dentro da margem autorizada
- Responder dúvidas sobre as vagas

**NÃO PODE:**
- Mencionar vagas fora do escopo
- Inventar vagas
- Prometer vaga sem consultar sistema
- Dizer "tenho vaga" sem ter chamado buscar_vagas()

---

## Followup

**Objetivo:** Manter relacionamento ativo

**PODE:**
- Perguntar como está
- Perguntar como foi plantão anterior
- Manter conversa leve
- Atualizar informações do perfil

**NÃO PODE:**
- Ofertar proativamente

---

## Feedback

**Objetivo:** Coletar opinião sobre experiência

**PODE:**
- Perguntar como foi o plantão
- Perguntar sobre o hospital
- Coletar elogios/reclamações
- Agradecer

**NÃO PODE:**
- Ofertar novo plantão proativamente

---

## Reativação

**Objetivo:** Retomar contato com médico inativo

**PODE:**
- Perguntar se ainda tem interesse
- Perguntar se mudou algo
- Reestabelecer diálogo

**NÃO PODE:**
- Ofertar de cara
- Assumir que ele quer plantão

**Fluxo:**
1. "Oi, sumiu! Tudo bem?"
2. Espera resposta
3. Se positivo: "Ainda tá fazendo plantão?"
4. Só oferta se ele pedir ou confirmar interesse
```

---

### T3: Criar runbook de operação (45min)

**Arquivo:** `docs/operacao/runbook-sprint32.md`

```markdown
# Runbook - Sprint 32

Procedimentos operacionais para novas funcionalidades.

## Modo Piloto

### Ativar Modo Piloto (emergência)

1. **Via Dashboard:**
   - Acessar Sistema → Configurações
   - Clicar no toggle "Modo Piloto"
   - Confirmar

2. **Via Código (se dashboard indisponível):**
   ```bash
   railway run python -c "
   from app.services.supabase import supabase
   supabase.table('system_config').upsert({
       'key': 'PILOT_MODE',
       'value': 'true'
   }).execute()
   "
   ```

### Quando ativar Modo Piloto

- Julia enviando mensagens indesejadas
- Bug detectado em ação autônoma
- Problema com integração externa
- Necessidade de pausar operação

---

## Hospitais Bloqueados

### Bloquear Hospital

1. **Via Dashboard:**
   - Hospitais → Bloqueados
   - "Bloquear Hospital"
   - Selecionar hospital
   - Informar motivo
   - Confirmar

2. **Via Slack:**
   ```
   Julia, bloquear hospital São Luiz motivo: reforma em andamento
   ```

### Verificar vagas movidas

```sql
SELECT COUNT(*) FROM vagas_hospitais_bloqueados
WHERE hospital_id = 'UUID_DO_HOSPITAL';
```

---

## Canal de Ajuda

### Responder pedido pendente

1. **Via Dashboard:**
   - Canal de Ajuda
   - Clicar "Responder" no pedido
   - Digitar resposta
   - Enviar

2. **Via Slack:**
   - Responder na thread do pedido

### Verificar pedidos pendentes

```sql
SELECT * FROM pedidos_ajuda
WHERE status = 'pendente'
ORDER BY criado_em DESC;
```

---

## Troubleshooting

### Julia não está respondendo

1. Verificar status da conversa:
   ```sql
   SELECT status FROM conversations WHERE id = 'UUID';
   ```

2. Se `aguardando_gestor`:
   - Ir em Canal de Ajuda
   - Responder pedido pendente

3. Se `handoff`:
   - Conversa com humano
   - Devolver para Julia se necessário

### Julia oferecendo hospital bloqueado

1. Verificar se hospital está realmente bloqueado:
   ```sql
   SELECT * FROM hospitais_bloqueados
   WHERE hospital_id = 'UUID' AND status = 'bloqueado';
   ```

2. Se não estiver, bloquear

3. Verificar cache (pode demorar até 5 min)
```

---

### T4: Atualizar README do sprint (30min)

**Arquivo:** `planning/sprint-32/README.md` (adicionar no final)

```markdown
---

## Status Final

**Sprint 32 Concluída:** [DATA]

### Épicos Implementados

| # | Épico | Status |
|---|-------|--------|
| E01 | Prompts por Tipo de Campanha | ✅ |
| E02 | PromptBuilder com Contexto | ✅ |
| E03 | Modo Piloto | ✅ |
| E04 | checkNumberStatus Job | ✅ |
| E05 | Gatilhos Automáticos | ✅ |
| E06 | Trigger Oferta por Furo | ✅ |
| E07 | Priorização de Médicos | ✅ |
| E08 | Canal de Ajuda Julia | ✅ |
| E09 | Gestor Comanda Julia | ✅ |
| E10 | Diretrizes Contextuais | ✅ |
| E11 | Julia Aprende | ✅ |
| E12 | Hospitais Bloqueados | ✅ |
| E13 | Conhecimento Hospitais | ✅ |
| E14 | Reestruturar Campanhas | ✅ |
| E15 | Estados de Conversa | ✅ |
| E16 | Adaptar Tela Campanhas | ✅ |
| E17 | Tela Hospitais Bloqueados | ✅ |
| E18 | Tela Instruções Ativas | ✅ |
| E19 | Tela Canal de Ajuda | ✅ |
| E20 | Toggle Modo Piloto | ✅ |
| E21 | Eliminar "Template" | ✅ |
| E22 | Migrar Dados Campanhas | ✅ |
| E23 | Testes E2E | ✅ |
| E24 | Documentação | ✅ |

### Principais Mudanças

1. **Comportamentos de Campanha:** Julia agora opera com 5 tipos de comportamento com regras específicas
2. **Anti-Alucinação:** Canal de ajuda garante que Julia não invente informações
3. **Modo Piloto:** Flag para controlar ações autônomas
4. **Hospital Bloqueado:** Separação por dados (Julia não vê vagas de bloqueados)
5. **Dashboard Atualizado:** Novas telas para campanhas, ajuda, instruções

### Critérios de Saída do Piloto

Para desativar `PILOT_MODE`:

- [ ] 100+ conversas de teste sem problemas críticos
- [ ] Julia não alucinando (canal de ajuda funcionando)
- [ ] Gestor consegue comandar Julia via Slack
- [ ] Dashboard funcionando para operação básica
- [ ] Guardrails validados
- [ ] Métricas de qualidade aceitáveis
```

---

## DoD (Definition of Done)

### CLAUDE.md
- [ ] Seção de comportamentos atualizada
- [ ] Seção de modo piloto adicionada
- [ ] Seção de canal de ajuda adicionada
- [ ] Seção de hospitais bloqueados adicionada

### docs/
- [ ] `docs/julia/comportamentos.md` criado
- [ ] `docs/operacao/runbook-sprint32.md` criado
- [ ] Arquivos obsoletos movidos para archive

### Planning
- [ ] `planning/sprint-32/README.md` com status final
- [ ] Épicos com DoD marcados

### Verificação
- [ ] Links funcionando
- [ ] Sem referências a "template" (exceto histórico)
- [ ] Comandos e exemplos testados

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Docs atualizados | 100% |
| Links quebrados | 0 |
| Exemplos funcionais | 100% |
