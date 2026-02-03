# Sprint 48: Market Intelligence - Enriquecimento de Dados

## Status: 📋 Planejado

## Objetivo

Enriquecer os dados de vagas extraídas com informações de hospitais, serviços e empresas, permitindo análises segmentadas.

## Contexto

A Sprint 46 criou a fundação (schema, APIs, componentes). Esta sprint foca em normalizar e enriquecer os dados para permitir análises mais profundas.

## Dependências

- Sprint 46 (Market Intelligence - Fundação) ✅

---

## Escopo de Alto Nível

### Incluído

| Feature | Descrição |
|---------|-----------|
| **Extração de Entidades** | Identificar hospitais, clínicas e serviços nas mensagens |
| **Tabela de Entidades** | `entidades_mercado` para normalização |
| **Matching Fuzzy** | Algoritmo para casar variações de nomes |
| **API de Análise por Hospital** | `/api/market-intelligence/hospitals` |
| **API de Análise por Empresa** | `/api/market-intelligence/companies` |
| **Componentes de Visualização** | HospitalRanking, CompanyDistribution |
| **Filtros na Aba Analytics** | Filtrar por hospital/empresa/região |

### Excluído

- Análise de valores por especialidade (Sprint 49)
- Algoritmos preditivos (Sprint 50)
- Integração com fontes externas (CRM hospitais)

---

## Épicos Previstos

| ID | Nome | Estimativa |
|----|------|------------|
| E48.1 | Schema entidades_mercado | 2h |
| E48.2 | Extrator de entidades (NLP leve) | 4h |
| E48.3 | Algoritmo de matching fuzzy | 3h |
| E48.4 | Worker de enriquecimento | 3h |
| E48.5 | API /hospitals | 3h |
| E48.6 | API /companies | 3h |
| E48.7 | Componente HospitalRanking | 3h |
| E48.8 | Componente CompanyDistribution | 3h |
| E48.9 | Filtros na Analytics Tab | 3h |
| E48.10 | Testes E2E | 2h |

**Total Estimado:** ~29h (~4 dias)

---

## Estrutura de Dados Proposta

```sql
-- Tabela de entidades normalizadas
CREATE TABLE entidades_mercado (
  id UUID PRIMARY KEY,
  tipo TEXT NOT NULL, -- 'hospital', 'clinica', 'empresa', 'servico'
  nome_normalizado TEXT NOT NULL,
  aliases TEXT[], -- variações de nome
  cidade TEXT,
  estado TEXT,
  regiao TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Relação vaga <-> entidade
CREATE TABLE vagas_entidades (
  vaga_id UUID REFERENCES vagas_grupo(id),
  entidade_id UUID REFERENCES entidades_mercado(id),
  confianca NUMERIC(3,2), -- 0.00 a 1.00
  PRIMARY KEY (vaga_id, entidade_id)
);
```

---

## APIs Previstas

### GET /api/market-intelligence/hospitals

```json
{
  "periodo": { "inicio": "2024-01-01", "fim": "2024-01-31" },
  "hospitais": [
    {
      "id": "uuid",
      "nome": "Hospital São Luiz",
      "vagasTotal": 150,
      "valorMedio": 180000,
      "especialidadesTop": ["Cardiologia", "Clínica Médica"],
      "tendencia": "up"
    }
  ]
}
```

### GET /api/market-intelligence/companies

```json
{
  "periodo": { "inicio": "2024-01-01", "fim": "2024-01-31" },
  "empresas": [
    {
      "id": "uuid",
      "nome": "MedStaff",
      "vagasTotal": 320,
      "hospitaisAtendidos": 15,
      "regiaoFoco": "São Paulo"
    }
  ]
}
```

---

## Critérios de Sucesso

| Métrica | Meta |
|---------|------|
| Entidades identificadas | >= 70% das vagas com hospital/empresa |
| Precisão do matching | >= 85% de matches corretos |
| Cobertura de testes | >= 80% |
| Performance API | < 500ms |

---

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Baixa precisão NLP | Começar com regras simples, evoluir para ML |
| Muitas variações de nome | Construir dicionário incremental |
| Performance matching | Usar índices trigram (pg_trgm) |

---

## Notas

- Priorizar hospitais/empresas mais frequentes primeiro
- Permitir correção manual de matches via dashboard
- Manter log de matches para aprendizado futuro
