# Sprint 16 - Confirmação de Plantão

> **Nota:** Documentação retroativa criada em 16/01/2026. Esta sprint foi implementada mas sem documentação de planejamento original.

## Objetivo

Implementar sistema de confirmação de plantões realizados, com transição automática de status e integração com Slack para confirmação manual.

## Funcionalidades Implementadas

### Fluxo de Status
```
reservada -> pendente_confirmacao -> realizada/cancelada
```

### Componentes

1. **Job Horário** (`app/services/confirmacao_plantao.py`)
   - Transiciona vagas reservadas após fim do plantão + buffer de 2h
   - Considera plantões noturnos (atravessam meia-noite)
   - Timezone-aware (America/Sao_Paulo)

2. **Confirmação via Slack**
   - Gestor confirma se plantão foi realizado ou não
   - Atualiza status da vaga
   - Emite business events

3. **Business Events**
   - Eventos emitidos em cada transição de status
   - Rastreabilidade completa do ciclo de vida da vaga

## Arquivos Principais

- `app/services/confirmacao_plantao.py` - Serviço principal
- `app/workers/scheduler.py` - Job agendado
- `app/services/business_events/types.py` - Tipos de eventos

## Status

✅ Implementado e em produção
