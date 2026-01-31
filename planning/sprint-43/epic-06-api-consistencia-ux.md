# Epic 06 - Consistencia de APIs + UX Improvements

## Objetivo
Eliminar inconsistencias de origem de dados e melhorar UX nas telas existentes.

## Stories

### S43.E6.1 - Padronizar Endpoints do Dashboard
**Objetivo:** Remover dependencias de `/dashboard/*` inexistentes ou documentar backend externo.

**Tarefas**
1. Mapear endpoints usados pelo frontend.
2. Ajustar para `/api/*` internos ou criar proxy.

### S43.E6.2 - UX Enhancements Prioritarios
**Objetivo:** Melhorar clareza e feedback nas telas criticas.

**Tarefas**
1. Dashboard: alertas criticos sempre visiveis.
2. Sistema: explicar impacto dos toggles.
3. Chips: recomendacoes de acao.

### S43.E6.3 - Rate Limit Configuravel
**Objetivo:** Permitir editar limites com confirmacao e audit trail.

**Tarefas**
1. Form para limites e horario.
2. Validacao + log.

