# Sprint 49: Market Intelligence - Análise de Mercado

## Status: 📋 Planejado

## Objetivo

Criar análises de mercado com foco em valores de plantão, demanda por especialidade e tendências regionais.

## Contexto

Com os dados enriquecidos (Sprint 48), podemos agora analisar padrões de mercado: quais especialidades pagam mais, onde há mais demanda, tendências de valores.

## Dependências

- Sprint 46 (Fundação) ✅
- Sprint 48 (Enriquecimento) 📋

---

## Escopo de Alto Nível

### Incluído

| Feature | Descrição |
|---------|-----------|
| **Análise de Valores** | Valor médio/mediano por especialidade, região, hospital |
| **Mapa de Calor** | Demanda por região (visualização geográfica) |
| **Tendências Temporais** | Evolução de valores ao longo do tempo |
| **Comparativos** | Hospital A vs Hospital B, Região X vs Y |
| **Alertas de Oportunidade** | Vagas acima da média de valor |
| **Dashboard de Mercado** | Página dedicada para análise de mercado |

### Excluído

- Previsão de demanda (Sprint 50)
- Recomendação automática de preços
- Integração com dados externos de mercado

---

## Épicos Previstos

| ID | Nome | Estimativa |
|----|------|------------|
| E49.1 | View materializada de valores | 2h |
| E49.2 | API /market-intelligence/values | 3h |
| E49.3 | API /market-intelligence/demand | 3h |
| E49.4 | API /market-intelligence/trends | 3h |
| E49.5 | Componente ValueAnalysis | 4h |
| E49.6 | Componente DemandHeatmap | 4h |
| E49.7 | Componente TrendChart | 3h |
| E49.8 | Componente Comparativo | 3h |
| E49.9 | Página Market Dashboard | 4h |
| E49.10 | Sistema de Alertas | 3h |
| E49.11 | Testes E2E | 2h |

**Total Estimado:** ~34h (~4.5 dias)

---

## APIs Previstas

### GET /api/market-intelligence/values

```json
{
  "periodo": { "inicio": "2024-01-01", "fim": "2024-01-31" },
  "porEspecialidade": [
    {
      "especialidade": "Cardiologia",
      "valorMedio": 185000,
      "valorMediano": 180000,
      "valorMin": 120000,
      "valorMax": 300000,
      "amostra": 150,
      "tendencia": "stable"
    }
  ],
  "porRegiao": [...],
  "porTipoPlantao": [...]
}
```

### GET /api/market-intelligence/demand

```json
{
  "periodo": { "inicio": "2024-01-01", "fim": "2024-01-31" },
  "regioes": [
    {
      "regiao": "São Paulo - Zona Sul",
      "demandaTotal": 450,
      "especialidadesTop": ["Clínica Médica", "Pediatria"],
      "hospitaisTop": ["Hospital São Luiz", "Hospital Moriah"],
      "crescimento": 15.5
    }
  ]
}
```

### GET /api/market-intelligence/trends

```json
{
  "periodo": { "inicio": "2024-01-01", "fim": "2024-03-31" },
  "tendencias": [
    {
      "metrica": "valor_medio_cardiologia",
      "dados": [
        { "mes": "2024-01", "valor": 175000 },
        { "mes": "2024-02", "valor": 180000 },
        { "mes": "2024-03", "valor": 185000 }
      ],
      "variacao": 5.7,
      "previsao3m": 190000
    }
  ]
}
```

---

## Visualizações Planejadas

### 1. Análise de Valores
```
┌─────────────────────────────────────────────────────┐
│ Valor Médio por Especialidade                       │
│ ┌─────────────┬────────┬────────┬────────┐         │
│ │ Cardiologia │ R$1850 │ ▲ 5%   │ ████████│        │
│ │ UTI         │ R$2200 │ ▲ 8%   │ ██████████│      │
│ │ Pediatria   │ R$1400 │ ▼ 2%   │ ██████  │        │
│ └─────────────┴────────┴────────┴────────┘         │
└─────────────────────────────────────────────────────┘
```

### 2. Mapa de Calor de Demanda
```
┌─────────────────────────────────────────────────────┐
│ Demanda por Região (Últimos 30 dias)               │
│                                                     │
│    [Mapa interativo com cores por demanda]         │
│    🔴 Alta (>100 vagas)                            │
│    🟡 Média (50-100)                               │
│    🟢 Baixa (<50)                                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Critérios de Sucesso

| Métrica | Meta |
|---------|------|
| Especialidades com análise | >= 10 especialidades |
| Regiões mapeadas | >= 5 regiões metropolitanas |
| Precisão de tendência | >= 80% (direção correta) |
| Cobertura de testes | >= 80% |
| Performance dashboards | < 2s load completo |

---

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Dados insuficientes por segmento | Agrupar categorias similares |
| Sazonalidade não capturada | Comparar com mesmo período ano anterior |
| Valores outliers | Usar mediana além de média |

---

## Integrações Futuras (Não Incluídas)

- Dados de tabelas de preços oficiais
- Benchmark com outras empresas de staffing
- Dados de CNES (Cadastro Nacional de Estabelecimentos de Saúde)
