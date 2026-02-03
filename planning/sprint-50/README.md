# Sprint 50: Market Intelligence - Algoritmos e Automação

## Status: 📋 Planejado

## Objetivo

Implementar algoritmos inteligentes para detecção automática de padrões, alertas proativos e recomendações baseadas em dados.

## Contexto

Com a fundação (Sprint 46), enriquecimento (Sprint 48) e análise de mercado (Sprint 49), agora podemos adicionar inteligência automatizada que gera valor sem intervenção manual.

## Dependências

- Sprint 46 (Fundação) ✅
- Sprint 48 (Enriquecimento) 📋
- Sprint 49 (Análise de Mercado) 📋

---

## Escopo de Alto Nível

### Incluído

| Feature | Descrição |
|---------|-----------|
| **Detecção de Anomalias** | Identificar picos/quedas atípicas em volume ou valor |
| **Alertas Inteligentes** | Notificar automaticamente sobre oportunidades/riscos |
| **Score de Grupo** | Algoritmo que pontua qualidade de cada grupo |
| **Recomendação de Grupos** | Sugerir novos grupos para monitorar |
| **Previsão de Demanda** | Estimar volume de vagas para próximos dias |
| **Dashboard de Insights** | Página com descobertas automáticas |

### Excluído

- Machine Learning complexo (será sprint futura)
- Automação de ações (apenas alertas)
- Integração com CRM para ações automáticas

---

## Épicos Previstos

| ID | Nome | Estimativa |
|----|------|------------|
| E50.1 | Algoritmo de detecção de anomalias | 4h |
| E50.2 | Sistema de alertas inteligentes | 4h |
| E50.3 | Algoritmo de score de grupo | 3h |
| E50.4 | Worker de cálculo de scores | 3h |
| E50.5 | Algoritmo de recomendação | 4h |
| E50.6 | Modelo de previsão (simples) | 4h |
| E50.7 | API /insights | 3h |
| E50.8 | Componente InsightCard | 3h |
| E50.9 | Componente AlertsFeed | 3h |
| E50.10 | Dashboard de Insights | 4h |
| E50.11 | Testes E2E | 2h |

**Total Estimado:** ~37h (~5 dias)

---

## Algoritmos Planejados

### 1. Detecção de Anomalias

```python
# Baseado em desvio padrão móvel
def detectar_anomalia(serie_temporal, janela=7, threshold=2.0):
    """
    Detecta valores que estão fora de 2 desvios padrão
    da média móvel dos últimos 7 dias.
    """
    media_movel = serie.rolling(window=janela).mean()
    std_movel = serie.rolling(window=janela).std()

    z_score = (valor_atual - media_movel) / std_movel

    return abs(z_score) > threshold
```

**Tipos de Anomalias:**
- 📈 Pico de volume (muito acima do normal)
- 📉 Queda de volume (muito abaixo do normal)
- 💰 Valor atípico (plantão muito caro ou barato)
- ⚠️ Grupo inativo (sem mensagens há X dias)

### 2. Score de Grupo

```
Score = (
    vagas_importadas_30d * 2 +
    confianca_media * 50 +
    recencia_bonus +
    diversidade_bonus
) / 100

Onde:
- recencia_bonus: +10 se última vaga < 7 dias
- diversidade_bonus: +10 se > 3 especialidades
```

**Classificação:**
- 🟢 Excelente: Score >= 80
- 🟡 Bom: Score 50-79
- 🔴 Baixo: Score < 50

### 3. Recomendação de Grupos

```
Critérios para recomendar grupo:
1. Região com alta demanda + poucos grupos monitorados
2. Especialidade com gap de cobertura
3. Grupos mencionados em mensagens de grupos existentes
4. Padrão de nome similar a grupos produtivos
```

### 4. Previsão de Demanda (Modelo Simples)

```python
# Média móvel ponderada + sazonalidade semanal
def prever_demanda(historico, dias_futuros=7):
    # Peso maior para dias recentes
    media_ponderada = weighted_average(historico[-30:])

    # Ajuste por dia da semana
    fator_semanal = sazonalidade_por_dia_semana(historico)

    previsao = []
    for dia in range(dias_futuros):
        dia_semana = (hoje + dia) % 7
        previsao.append(media_ponderada * fator_semanal[dia_semana])

    return previsao
```

---

## Sistema de Alertas

### Tipos de Alerta

| Tipo | Trigger | Ação |
|------|---------|------|
| `OPORTUNIDADE_VALOR` | Plantão 30% acima da média | Notificar gestor |
| `QUEDA_VOLUME` | Volume 50% abaixo do normal | Investigar grupo |
| `GRUPO_INATIVO` | Sem mensagem há 7 dias | Verificar status |
| `NOVO_HOSPITAL` | Hospital não visto antes | Adicionar ao catálogo |
| `PICO_DEMANDA` | Volume 2x acima do normal | Oportunidade de prospecção |

### Canais de Notificação

1. **Dashboard** - Badge e feed de alertas
2. **Helena (Slack)** - Resumo diário de insights
3. **Email** (futuro) - Digest semanal

---

## APIs Previstas

### GET /api/market-intelligence/insights

```json
{
  "periodo": { "inicio": "2024-01-01", "fim": "2024-01-31" },
  "insights": [
    {
      "id": "uuid",
      "tipo": "OPORTUNIDADE",
      "titulo": "Alta demanda em Cardiologia - Zona Sul",
      "descricao": "Volume 45% acima da média. Considere aumentar prospecção.",
      "impacto": "alto",
      "dadosRelacionados": { "regiao": "SP-ZS", "especialidade": "Cardiologia" },
      "criadoEm": "2024-01-15T10:00:00Z"
    },
    {
      "id": "uuid",
      "tipo": "ALERTA",
      "titulo": "Grupo 'Plantões UTI SP' inativo",
      "descricao": "Sem mensagens há 10 dias. Verificar se grupo ainda existe.",
      "impacto": "medio",
      "dadosRelacionados": { "grupoId": "uuid", "ultimaMensagem": "2024-01-05" },
      "criadoEm": "2024-01-15T08:00:00Z"
    }
  ],
  "resumo": {
    "oportunidades": 5,
    "alertas": 3,
    "tendenciasPositivas": 8,
    "tendenciasNegativas": 2
  }
}
```

### GET /api/market-intelligence/predictions

```json
{
  "previsoes": {
    "volumeProximos7Dias": [120, 135, 110, 95, 88, 140, 130],
    "confianca": 0.72,
    "fatoresConsiderados": ["sazonalidade_semanal", "tendencia_30d", "feriados"]
  }
}
```

---

## Critérios de Sucesso

| Métrica | Meta |
|---------|------|
| Alertas relevantes | >= 80% considerados úteis |
| Falsos positivos | < 20% |
| Precisão de previsão | >= 70% (margem de 20%) |
| Score correlação | >= 0.7 com produtividade real |
| Cobertura de testes | >= 80% |

---

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Muitos alertas (fadiga) | Priorização e agrupamento |
| Modelo impreciso | Começar simples, iterar |
| Custo computacional | Processar em batch noturno |

---

## Evolução Futura (Não Incluído)

- **ML Avançado:** Modelos de previsão mais sofisticados
- **NLP Profundo:** Extração de informações mais ricas das mensagens
- **Automação de Ações:** Entrar em grupos automaticamente
- **Integração Helena:** Helena reportar insights via Slack proativamente
