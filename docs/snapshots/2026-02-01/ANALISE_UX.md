# Analise de Usabilidade e Experiencia do Usuario

Data dos snapshots: 01/02/2026
Fonte: `docs/snapshots/2026-02-01/`
Escopo: dashboard web de operacao Julia (WhatsApp API)

## Resumo executivo
O produto apresenta boa cobertura funcional e consistencia visual entre modulos. O principal risco de UX e a alta densidade de informacao e a falta de hierarquia de foco em telas de lista e monitoramento. Isso pode reduzir a velocidade de decisao e aumentar a carga cognitiva. Recomendacoes priorizam clareza de proxima acao, foco visual e estados vazios mais orientativos.

## Metodologia
- Leitura visual dos snapshots por modulo
- Mapeamento de fluxo primario (operacao diaria, monitoramento, campanhas)
- Identificacao de riscos de friccao e oportunidades de melhoria

## Mapa de modulos (estrutura dos snapshots)
- `dashboard/` (overview)
- `metricas/` (overview)
- `campanhas/` (lista, detalhe, modal)
- `vagas/` (lista, calendario, detalhe)
- `conversas/` (detalhe)
- `medicos/` (lista)
- `chips/` (visao geral, alertas, warmup, configuracoes, detalhe, modais)
- `monitor/` (overview, lista)
- `health/` (overview, detalhe)
- `integridade/` (overview)
- `grupos/` (overview)
- `qualidade/` (overview)
- `auditoria/` (overview)
- `instrucoes/` (overview, modal)
- `hospitais-bloqueados/` (overview)
- `sistema/` (overview, detalhe)
- `ajuda/` (overview)

## Achados por severidade

### Alta
1) Falta de hierarquia clara de foco em telas densas
- Impacto: usuarios podem perder tempo identificando a proxima acao critica.
- Evidencias: `monitor/overview.png`, `dashboard/overview-1.png`, `dashboard/overview-2-pool-chips.png`
- Recomendacao: incluir bloco de “acao recomendada” no topo e reduzir competicao visual (ex.: esconder detalhes secundarios atras de expandir).

2) Estados vazios pouco acionaveis
- Impacto: baixo direcionamento para primeiro uso e menor conversao de tarefas.
- Evidencias: `auditoria/overview.png`, `instrucoes/overview.png`, `qualidade/overview.png`, `grupos/overview.png`
- Recomendacao: adicionar CTA principal e checklist rapido do proximo passo.

### Media
3) Acoes principais competem com acoes secundarias
- Impacto: risco de cliques errados e fluxo confuso.
- Evidencias: botoes “Atualizar” em varias telas junto de filtros e CTAs.
- Recomendacao: padronizar CTA principal (cor/posicao) e rebaixar acoes de manutencao.

4) Telas de detalhe longas sem ancoragem
- Impacto: navegação lenta e perda de contexto.
- Evidencias: `chips/detalhe.png`, `campanhas/detalhe.png`
- Recomendacao: adicionar sumario com atalhos (anchors) e headers colapsaveis.

### Baixa
5) Consistencia de nomenclatura entre modulos
- Impacto: pequena confusao semantica.
- Evidencias: “Health Center” vs “Monitor do Sistema”.
- Recomendacao: padronizar termos e subtitulos (ex.: “Saude do Sistema”).

## Observacoes por modulo

### Dashboard
- Forte sinalizacao de metas e status.
- Oportunidade: destacar os 2-3 KPIs essenciais e esconder os demais por padrao.

### Campanhas
- Lista clara; modal de criacao precisa de microcopy de requisitos.
- Oportunidade: inserir preview rapido de audiencia e estimativa de envio.

### Vagas
- Alternancia lista/calendario boa, mas sem onboarding.
- Oportunidade: tooltip curto explicando icones de status.

### Conversas
- Chat detalhado funciona bem, mas falta priorizacao de conversas criticas.
- Oportunidade: filtros de risco (“sem resposta”, “alto valor”).

### Chips
- Modulos bem segmentados.
- Oportunidade: banner fixo de alertas no topo da visao geral.

### Monitor / Health
- Cobertura completa, mas redundante.
- Oportunidade: consolidar saude geral com drill-down para jobs.

### Sistema
- Mensagens de risco presentes, mas podem ser mais diretas.
- Oportunidade: separar claramente “modo piloto” e “safe mode” com instrucoes curtas.

## Recomendacoes priorizadas
1) Adicionar bloco “Proxima acao” no topo das telas densas (Dashboard, Monitor).
2) Criar estados vazios com CTA e checklist (Auditoria, Qualidade, Instrucoes, Grupos).
3) Padronizar CTA principal e reduzir destaque de “Atualizar”.
4) Implementar sumario/ancoras em telas de detalhe longas.
5) Alinhar nomenclatura entre modulos operacionais.

## Proximos passos sugeridos
- Validar com 3 usuarios operacionais (30-45 min cada) com roteiro de tarefas.
- Medir tempo para completar tarefas criticas antes/depois das mudancas.
- Priorizar quick wins de baixa implementacao (estados vazios e CTA principal).
