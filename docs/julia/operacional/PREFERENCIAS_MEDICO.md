# Sistema de Preferências do Médico

Este documento define como Júlia captura, armazena e utiliza as preferências dos médicos.

---

## Por que é Essencial

1. **Evitar ofertas irrelevantes** - Não ofertar noturno para quem só quer diurno
2. **Aumentar conversão** - Ofertas alinhadas têm mais chance de aceite
3. **Parecer humana** - Escalista real lembra das preferências
4. **Construir relacionamento** - Médico sente que é conhecido

---

## Tipos de Preferências

### 1. Preferências de Turno

| Preferência | Valores Possíveis | Exemplo de Fala |
|-------------|-------------------|-----------------|
| `turnos` | diurno, noturno, ambos | "Só faço noturno" |
| `dias_semana` | seg, ter, qua, qui, sex, sab, dom | "Tenho livre só fins de semana" |
| `carga_maxima` | número de plantões/semana | "No máximo 2 por semana" |

### 2. Preferências de Local

| Preferência | Valores Possíveis | Exemplo de Fala |
|-------------|-------------------|-----------------|
| `regioes` | ABC, Zona Sul, Centro, etc | "Só trabalho no ABC" |
| `hospitais_preferidos` | lista de hospital_ids | "Gosto do Hospital Brasil" |
| `hospitais_bloqueados` | lista de hospital_ids | "No Hospital X não trabalho mais" |
| `distancia_maxima` | km do endereço base | "Nada muito longe de casa" |

### 3. Preferências de Valor

| Preferência | Valores Possíveis | Exemplo de Fala |
|-------------|-------------------|-----------------|
| `valor_minimo` | decimal | "Abaixo de 2000 não compensa" |
| `forma_pagamento` | avista, mes_seguinte, ambos | "Prefiro à vista" |

### 4. Preferências de Setor

| Preferência | Valores Possíveis | Exemplo de Fala |
|-------------|-------------------|-----------------|
| `setores_preferidos` | CC, SADT, UTI, Hemo, etc | "Curto mais centro cirúrgico" |
| `setores_bloqueados` | lista | "UTI não é minha praia" |
| `tipos_procedimento` | eletivo, emergencia, ambos | "Só eletivas" |

---

## Estrutura no Banco

### Tabela `clientes` - Campos Existentes

```sql
-- Já existe
preferencias_detectadas JSONB DEFAULT '{}'
preferencias_conhecidas JSONB DEFAULT '{}'
```

### Estrutura do JSONB

```json
{
  "turnos": ["noturno"],
  "dias_semana": ["sab", "dom"],
  "carga_maxima_semana": 3,

  "regioes": ["ABC", "Zona Sul"],
  "hospitais_preferidos": ["uuid-1", "uuid-2"],
  "hospitais_bloqueados": ["uuid-3"],

  "valor_minimo": 2000,
  "forma_pagamento": ["avista"],

  "setores_preferidos": ["CC"],
  "setores_bloqueados": ["UTI"],

  "ultima_atualizacao": "2024-12-06T10:00:00Z",
  "fonte": "conversa"
}
```

### Diferença: `detectadas` vs `conhecidas`

| Campo | Uso | Exemplo |
|-------|-----|---------|
| `preferencias_detectadas` | Inferidas pela IA durante conversa | Médico disse "prefiro noturno" → IA extrai |
| `preferencias_conhecidas` | Confirmadas/validadas pelo gestor | Gestor revisou e confirmou |

---

## Captura de Preferências

### Durante a Conversa

Júlia deve extrair preferências de frases naturais:

| Frase do Médico | Preferência Extraída |
|-----------------|---------------------|
| "Só faço noturno" | `turnos: ["noturno"]` |
| "Fins de semana tô livre" | `dias_semana: ["sab", "dom"]` |
| "No Hospital X não volto mais" | `hospitais_bloqueados: ["X"]` |
| "Abaixo de 2000 não compensa" | `valor_minimo: 2000` |
| "Moro no ABC" | `regioes: ["ABC"]` |
| "Só pego à vista" | `forma_pagamento: ["avista"]` |
| "UTI não é minha praia" | `setores_bloqueados: ["UTI"]` |
| "No máximo 2 plantões por semana" | `carga_maxima_semana: 2` |

### Fluxo de Extração

```
┌─────────────────────────────────────────────────────────────────────┐
│                EXTRAÇÃO DE PREFERÊNCIAS                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Médico envia mensagem                                              │
│         │                                                           │
│         ▼                                                           │
│  LLM processa com instruction:                                      │
│  "Extraia preferências mencionadas pelo médico"                    │
│         │                                                           │
│         ▼                                                           │
│  Se encontrou preferência:                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 1. Salvar em preferencias_detectadas (merge, não sobrescreve)│   │
│  │ 2. Opcional: Júlia confirma "Anotei que vc prefere noturno!" │   │
│  │ 3. Log para auditoria                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Tool para Salvar

```python
def salvar_preferencia(
    cliente_id: str,
    tipo: str,  # "turno", "hospital", "valor", etc
    chave: str,  # "turnos", "hospitais_bloqueados", etc
    valor: Any,  # ["noturno"] ou 2000 ou ["uuid-1"]
    fonte: str = "conversa"  # "conversa", "gestor", "import"
):
    """
    Salva preferência detectada no perfil do médico.
    Faz merge com preferências existentes (não sobrescreve).
    """
```

---

## Uso das Preferências

### Ao Buscar Vagas

```sql
-- Query que respeita preferências do médico
SELECT v.* FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
WHERE v.especialidade_id = $especialidade
  AND v.status = 'aberta'
  AND v.data >= CURRENT_DATE

  -- Respeitar turno preferido
  AND (
    $turnos IS NULL
    OR v.periodo_id IN (SELECT id FROM periodos WHERE nome ILIKE ANY($turnos))
  )

  -- Não oferecer hospitais bloqueados
  AND v.hospital_id NOT IN (SELECT unnest($hospitais_bloqueados))

  -- Respeitar valor mínimo
  AND v.valor >= COALESCE($valor_minimo, 0)

  -- Respeitar setores bloqueados
  AND (v.setor_id IS NULL OR v.setor_id NOT IN (SELECT unnest($setores_bloqueados)))

  -- Não oferecer se já tem plantão no mesmo dia/período
  AND NOT EXISTS (
    SELECT 1 FROM vagas v2
    WHERE v2.cliente_id = $cliente_id
      AND v2.data = v.data
      AND v2.periodo_id = v.periodo_id
      AND v2.status IN ('reservada', 'confirmada')
  )

ORDER BY
  -- Priorizar hospitais preferidos
  CASE WHEN v.hospital_id = ANY($hospitais_preferidos) THEN 0 ELSE 1 END,
  v.prioridade DESC,
  v.valor DESC;
```

### Ao Apresentar Vaga

Júlia deve mencionar que lembrou da preferência:

```
"Lembrei de vc pq sei que curte noturno...

Tem uma vaga no Hospital Brasil, sábado, 19h-07h, R$ 2.400

O que acha?"
```

---

## Perguntas Ativas

Júlia pode perguntar ativamente sobre preferências quando não conhece:

### Momento Certo para Perguntar

| Situação | Pergunta |
|----------|----------|
| Primeira conversa | "Vc prefere diurno ou noturno?" |
| Médico recusa por valor | "Qual valor funciona melhor pra vc?" |
| Médico recusa por local | "Qual região vc prefere trabalhar?" |
| Médico recusa por turno | "Vc prefere dia ou noite?" |

### Formato Natural

```
❌ "Quais são suas preferências de turno, região e valor mínimo?"

✅ "Vc prefere dia ou noite?"
   [espera resposta]
   "E região, trabalha mais por onde?"
```

---

## Validação pelo Gestor

### Quando Validar

- Após 3+ interações com o médico
- Quando preferência impacta muito (ex: bloqueou hospital importante)
- Periodicamente (a cada 30 dias)

### Interface

No Chatwoot ou painel admin:
- Ver preferências detectadas
- Confirmar → move para `preferencias_conhecidas`
- Corrigir → edita e move
- Rejeitar → remove da lista

---

## Prioridade de Preferências

| Prioridade | Tipo | Comportamento |
|------------|------|---------------|
| 1 - Absoluta | `hospitais_bloqueados` | NUNCA oferece |
| 2 - Absoluta | `setores_bloqueados` | NUNCA oferece |
| 3 - Forte | `valor_minimo` | Só oferece acima |
| 4 - Forte | `turnos` | Prioriza, mas pode oferecer outro se urgente |
| 5 - Média | `regioes` | Prioriza, mas pode oferecer fora |
| 6 - Fraca | `hospitais_preferidos` | Usa para ordenar, não filtrar |

---

## Exemplos de Uso

### Cenário 1: Médico tem preferências claras

```
Preferências conhecidas:
- turnos: ["noturno"]
- valor_minimo: 2200
- hospitais_bloqueados: ["Hospital X"]

Vagas disponíveis:
1. Hospital Brasil, diurno, R$ 2.000 → NÃO (diurno + valor baixo)
2. Hospital X, noturno, R$ 2.500 → NÃO (bloqueado)
3. Hospital São Luiz, noturno, R$ 2.400 → SIM ✓

Júlia: "Oi Dr. Carlos! Lembrei de vc pq surgiu um noturno no São Luiz,
       dia 15, R$ 2.400. Topa?"
```

### Cenário 2: Sem preferências, descobrir

```
Preferências: {}

Júlia: "Oi Dr. Carlos! Temos umas vagas legais aqui.
       Vc prefere dia ou noite?"

Médico: "Noturno, de preferência"

→ Salva: preferencias_detectadas.turnos = ["noturno"]

Júlia: "Anotado! E região, trabalha mais por onde?"

Médico: "ABC, moro em Santo André"

→ Salva: preferencias_detectadas.regioes = ["ABC"]
→ Atualiza: clientes.cidade = "Santo André"
```

### Cenário 3: Atualização de preferência

```
Preferências anteriores:
- turnos: ["diurno"]

Médico: "Agora tô pegando noturno também"

→ Atualiza: preferencias_detectadas.turnos = ["diurno", "noturno"]

Júlia: "Boa! Vou te mandar noturno também então"
```

---

## Métricas

| Métrica | Como Medir | Meta |
|---------|------------|------|
| % médicos com preferências | `COUNT(preferencias != '{}') / total` | > 50% após 1 mês |
| Precisão das preferências | Ofertas aceitas vs recusadas por mismatch | > 80% |
| Tempo para capturar | Média de interações até ter preferências | < 3 conversas |

---

## Implementação MVP

### Fase 1 (MVP)
- [ ] Extrair preferências básicas: turno, valor_minimo, região
- [ ] Salvar em `preferencias_detectadas`
- [ ] Usar para filtrar vagas (não oferecer incompatíveis)

### Fase 2
- [ ] Preferências de hospitais (preferidos/bloqueados)
- [ ] Preferências de setores
- [ ] Validação pelo gestor

### Fase 3
- [ ] Perguntas ativas
- [ ] Histórico de mudanças
- [ ] Análise de padrões (ML)
