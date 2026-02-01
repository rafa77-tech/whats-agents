# IA e Fluxos por Persona

Base visual: manual de identidade Jull.ia + snapshots 01/02/2026
Objetivo: reorganizar navegacao para controle, clareza e foco em dados.

## Personas principais

### Gestor
- Foco: performance, risco operacional, metas.
- Tarefas criticas: ver saude geral, aprovar/pausar campanhas, checar KPIs.

### Operador
- Foco: execucao diaria, atendimento, vagas.
- Tarefas criticas: responder conversas, acompanhar vagas, resolver pendencias.

### Suporte
- Foco: estabilidade tecnica e incidentes.
- Tarefas criticas: monitorar jobs, chips, warmup, alertas e integridade.

## Arquitetura de Informacao (proposta)

### 1) Home (Centro de comando)
- Saude do Sistema (resumo)
- Campanhas Ativas (resumo)
- Conversas Criticas (resumo)
- Proxima Acao (CTA unico)

### 2) Operacao
- Monitor
- Health Center
- Alertas (consolidado)

### 3) Campanhas
- Lista
- Detalhe
- Wizard

### 4) Conversas
- Inbox
- Detalhe
- Filtros inteligentes

### 5) Vagas
- Lista
- Calendario
- Detalhe

### 6) Chips e Instancias
- Visao Geral
- Alertas
- Warmup
- Configuracoes
- Detalhe

### 7) Grupos
### 8) Medicos
### 9) Qualidade
### 10) Auditoria
### 11) Sistema
### 12) Ajuda

## Fluxos principais

### Fluxo A — Gestor: controle estrategico
1) Home: verificar saude geral + campanhas ativas
2) Campanhas: entrar em detalhe de campanha critica
3) Ajustar status (pausar/retomar) e revisar audiencia
4) Voltar ao Home para confirmar impacto nos indicadores

### Fluxo B — Operador: conversas e vagas
1) Home: abrir conversas criticas
2) Conversas: responder/assumir conversa
3) Vagas: consultar vagas relacionadas
4) Retornar ao Inbox para seguir a fila

### Fluxo C — Suporte: incidentes
1) Home: alerta critico no topo
2) Alertas: identificar incidente
3) Chips/Monitor: isolar causa (instancia, job)
4) Health/Integridade: validar recuperacao

## Principios de navegacao
- CTA unico por tela
- Menos cards, mais foco no resumo
- Drill-down claro com breadcrumbs
- Estados vazios acionaveis
- Alertas sempre visiveis no topo

