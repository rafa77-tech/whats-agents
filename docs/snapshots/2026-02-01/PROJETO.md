# Projeto: Julia Dashboard (WhatsApp API)

## Visao geral
Este projeto e um dashboard web para operacao de atendimento e campanhas via WhatsApp. O sistema centraliza indicadores, monitoramento e configuracoes para a equipe que usa a assistente "Julia" - agente IA autonomo. O painel cobre:

- Operacao e performance (Dashboard, Metricas)
- Campanhas de prospeccao/reativacao (Campanhas)
- Gestao de vagas e plantao (Vagas)
- Conversas e acompanhamento de chats (Conversas)
- Base de medicos (Medicos)
- Pool de chips/instancias WhatsApp (Pool de Chips)
- Monitoramento de jobs e saude do sistema (Monitor, Health Center)
- Integridade e auditoria (Integridade, Auditoria)
- Regras e instrucoes contextuais (Instrucoes)
- Controle de sistema e seguranca operacional (Sistema)
- Grupos/links WhatsApp (Grupos)
- Qualidade de conversas (Qualidade)
- Ajuda e triagem de pendencias (Ajuda)

## Estrutura de navegacao
A navegacao principal e lateral, com modulos separados por area funcional. Cada modulo geralmente possui uma pagina de visao geral com filtros, cards de status e tabelas. Alguns modulos tem sub-rotas (ex.: chips com visao geral, alertas, warmup e configuracoes).

## Publico e objetivos
Publico principal: operadores e gestores de operacao, com foco em
- estabilidade do sistema
- qualidade de conversas
- eficiencia em campanhas
- visibilidade operacional e capacidade de resposta rapida

## Premissas para a analise de UX
A analise considera os snapshots de 01/02/2026 em `docs/snapshots/2026-02-01/` e foca em clareza, consistencia, eficiencia de tarefas e sinalizacao de estados.
