# Sprint 40 - Reescrita do Extrator de Vagas

**Branch:** `feature/sprint-40-extrator-vagas`
**Criação:** 2026-01-25
**Status:** Planejamento

---

## Sumário Executivo

### Problema

O extrator atual (`app/services/grupos/extrator.py`) foi projetado assumindo que uma mensagem de grupo = uma vaga. Na realidade, mensagens de grupos de staffing médico frequentemente contêm:

1. **Múltiplos hospitais** em uma única mensagem
2. **Múltiplas datas** por hospital
3. **Valores diferentes por dia da semana** (seg-sex vs sáb-dom)
4. **Valores diferentes por período** (diurno vs noturno)
5. **Contato de quem oferece** (nome + WhatsApp)

### Impacto Atual

- **~687 vagas** com valor `NULL` apesar das mensagens originais conterem valores em R$
- Padrão mais comum não extraído: "Segunda a Sexta - R$ 1.700 / Sábado - R$ 1.800"
- Perda de oportunidades de matching com médicos

### Solução

Reescrever completamente o extrator para:
1. Identificar TODOS os hospitais/locais mencionados
2. Para cada local, extrair TODAS as datas/períodos
3. Associar valor correto baseado no dia da semana e período
4. Gerar N vagas atômicas (uma por combinação única)
5. Extrair contato responsável (nome + telefone WhatsApp)

---

## Modelo de Dados: Vaga Atômica

Uma vaga é uma unidade **atômica e indivisível** com os seguintes campos obrigatórios:

| Campo | Tipo | Obrigatório | Exemplo |
|-------|------|-------------|---------|
| `data` | date | SIM | 2026-01-26 |
| `dia_semana` | enum | SIM | segunda |
| `periodo` | enum | SIM | tarde |
| `hora_inicio` | time | NÃO | 13:00 |
| `hora_fim` | time | NÃO | 19:00 |
| `valor` | integer | SIM | 1700 |
| `hospital_raw` | string | SIM | Hospital Campo Limpo |
| `endereco_raw` | string | NÃO | Estrada Itapecirica, 1661 - SP |
| `especialidade_raw` | string | NÃO | Clínica Médica |
| `contato_nome` | string | NÃO | Eloisa |
| `contato_whatsapp` | string | NÃO | 5511939050162 |

### Enum: dia_semana
```
segunda, terca, quarta, quinta, sexta, sabado, domingo
```

### Enum: periodo
```
manha, tarde, noite, diurno, noturno, cinderela, sd (12h dia), sn (12h noite)
```

---

## Exemplo Concreto de Extração

### Mensagem Original

```
📍 Hospital Campo Limpo
Estrada Itapecirica, 1661 - SP

🗓 26/01 - Segunda - Tarde 13-19h
🗓 27/01 - Terça - Noite 19-7h
🗓 28/01 - Quarta - Manhã 7-13h
🗓 01/02 - Sábado - SD 7-19h
🗓 02/02 - Domingo - SN 19-7h

💰 Valores:
Segunda a Sexta: R$ 1.700
Sábado e Domingo: R$ 1.800

📲 Interessados falar com Eloisa
wa.me/5511939050162
```

### Vagas Geradas (5 vagas atômicas)

| # | data | dia_semana | periodo | hora_inicio | hora_fim | valor | hospital | contato |
|---|------|------------|---------|-------------|----------|-------|----------|---------|
| 1 | 2026-01-26 | segunda | tarde | 13:00 | 19:00 | 1700 | Hospital Campo Limpo | Eloisa |
| 2 | 2026-01-27 | terca | noite | 19:00 | 07:00 | 1700 | Hospital Campo Limpo | Eloisa |
| 3 | 2026-01-28 | quarta | manha | 07:00 | 13:00 | 1700 | Hospital Campo Limpo | Eloisa |
| 4 | 2026-02-01 | sabado | diurno | 07:00 | 19:00 | 1800 | Hospital Campo Limpo | Eloisa |
| 5 | 2026-02-02 | domingo | noturno | 19:00 | 07:00 | 1800 | Hospital Campo Limpo | Eloisa |

**Lógica de associação de valor:**
- Segunda (26/01) → seg-sex → R$ 1.700
- Terça (27/01) → seg-sex → R$ 1.700
- Quarta (28/01) → seg-sex → R$ 1.700
- Sábado (01/02) → sáb-dom → R$ 1.800
- Domingo (02/02) → sáb-dom → R$ 1.800

---

## Arquitetura da Solução

### Componentes Novos

```
app/services/grupos/extrator_v2/
├── __init__.py           # Exports públicos
├── types.py              # Dataclasses e tipos
├── parser_mensagem.py    # Parser de estrutura da mensagem
├── extrator_hospitais.py # Extração de hospitais/locais
├── extrator_datas.py     # Extração de datas e períodos
├── extrator_valores.py   # Extração e associação de valores
├── extrator_contato.py   # Extração de contato
├── gerador_vagas.py      # Geração das vagas atômicas
├── llm_client.py         # Cliente LLM com fallback
├── prompts.py            # Prompts especializados
└── pipeline.py           # Orquestrador do pipeline
```

### Fluxo do Pipeline

```
┌─────────────────┐
│   Mensagem      │
│     Bruta       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  1. Parser      │  Separa seções (local, datas, valores, contato)
│    Mensagem     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Extrator    │  Extrai nome, endereço de cada hospital
│   Hospitais     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Extrator    │  Extrai cada combinação data/período/horário
│     Datas       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Extrator    │  Extrai valores e regras (seg-sex, sab-dom, etc)
│    Valores      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Extrator    │  Extrai nome e WhatsApp do contato
│    Contato      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  6. Gerador de Vagas                                │
│                                                     │
│  Para cada hospital:                                │
│    Para cada data/período:                          │
│      valor = associar_valor(dia_semana, periodo)    │
│      vaga = criar_vaga_atomica(...)                 │
│      vagas.append(vaga)                             │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  N Vagas        │
│  Atômicas       │
└─────────────────┘
```

---

## Épicos

A sprint está dividida em **8 épicos** que devem ser executados sequencialmente.

| Épico | Nome | Dependências | Estimativa |
|-------|------|--------------|------------|
| E01 | Estrutura e Tipos | - | Fundação |
| E02 | Parser de Mensagem | E01 | Crítico |
| E03 | Extrator de Hospitais | E01, E02 | Crítico |
| E04 | Extrator de Datas | E01, E02 | Crítico |
| E05 | Extrator de Valores | E01, E02 | Crítico |
| E06 | Extrator de Contato | E01, E02 | Médio |
| E07 | Gerador de Vagas | E01-E06 | Crítico |
| E08 | Integração e Pipeline | E01-E07 | Final |

---

## Definition of Done (Sprint)

A sprint é considerada **COMPLETA** quando:

1. [ ] Todos os 8 épicos marcados como completos
2. [ ] Cobertura de testes >= 90%
3. [ ] Zero erros de tipo (mypy)
4. [ ] Zero erros de lint (ruff)
5. [ ] Pipeline processando mensagens em ambiente de desenvolvimento
6. [ ] Amostra de 50 mensagens reais processadas com validação manual
7. [ ] Taxa de extração de valor >= 95% (vs ~0% atual)
8. [ ] Documentação de API completa

---

## Arquivos de Referência

Estes arquivos devem ser estudados antes de iniciar cada épico:

| Arquivo | Propósito |
|---------|-----------|
| `app/services/grupos/extrator.py` | Extrator atual (problema) |
| `app/services/grupos/prompts.py` | Prompts atuais |
| `app/services/grupos/pipeline_worker.py` | Worker que orquestra |
| `app/services/grupos/classificador.py` | Classificador de ofertas |
| `docs/julia/conhecimento/*.md` | Base de conhecimento médico |

---

## Métricas de Sucesso

| Métrica | Atual | Meta |
|---------|-------|------|
| Taxa de extração de valor | ~0% | >= 95% |
| Vagas com hospital+especialidade | ~70% | >= 95% |
| Vagas com contato | ~5% | >= 80% |
| Tempo médio de extração | ~3s | <= 5s |
| Custo por mensagem (tokens) | ~1000 | <= 2000 |

---

## Próximos Passos

1. Ler documentação detalhada de cada épico em `planning/sprint-40/epicos/`
2. Começar pelo E01 (Estrutura e Tipos)
3. Só avançar para próximo épico quando testes do atual = 100%
