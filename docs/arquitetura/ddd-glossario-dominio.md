# Dicionário de Domínio (Linguagem Ubíqua) - Projeto Julia

**Status:** Proposta Inicial (v1.0)
**Data:** 2026-02-21
**Autores:** Manus AI, Rafael

## 1. Introdução

Este documento estabelece o vocabulário oficial e compartilhado (Linguagem Ubíqua) para o Projeto Julia, conforme a disciplina do Domain-Driven Design (DDD). O objetivo é eliminar ambiguidades, alinhar a comunicação entre as equipes de negócio, produto e engenharia, e garantir que o software seja um reflexo fiel do domínio de negócio.

Este dicionário é um documento vivo e deve ser atualizado à medida que o domínio evolui.

## 2. Termos Canônicos de Negócio

| Termo Canônico | Alias(es) / Legado | Definição de Negócio | Contexto Principal |
| :--- | :--- | :--- | :--- |
| **Médico** | `cliente` | Profissional de saúde que interage com a plataforma para receber e gerenciar oportunidades de plantão. | `ConversaMedica` |
| **Plantão** | `vaga` | Uma oportunidade de trabalho médico específica, com local, data, hora, especialidade e remuneração definidos. | `VagasAlocacao` |
| **Campanha** | `campanha_outbound` | Uma ação de comunicação proativa e segmentada, enviada a um grupo de médicos para um objetivo específico (ex: ofertar plantões, reativar). | `CampanhasOutbound` |
| **Política de Contato** | `policy`, `guardrail` | O conjunto de regras e estado que governa *se*, *quando* e *como* um médico pode ser contatado, visando a saúde do relacionamento. | `PolicyContato` |
| **Handoff** | `transferencia`, `escalonamento` | O processo de transferir uma conversa da automação (IA) para um operador humano para supervisão ou intervenção. | `HandoffSupervisao` |
| **Jornada do Médico** | `stage_jornada`, `lifecycle_stage` | O modelo que representa o estágio de relacionamento de um médico com a plataforma, desde o primeiro contato até o engajamento contínuo ou churn. | `ConversaMedica` |
| **Chip** | `disparador`, `número` | Representa um número de telefone (instância do WhatsApp) usado pela plataforma para se comunicar com os médicos. | `IntegracoesExternas` |

## 3. Catálogo de Estados Canônicos

A padronização de estados é crucial para a consistência das regras de negócio.
Os valores abaixo correspondem aos enums definidos em `app/services/campanhas/types.py`
e nos demais módulos de domínio.

### 3.1. Status da Campanha (`CampanhasOutbound`)

Referência: `StatusCampanha` em `app/services/campanhas/types.py`

| Estado Canônico | Valor no Código | Alias(es) / Legado | Definição |
| :--- | :--- | :--- | :--- |
| `RASCUNHO` | `rascunho` | `draft` | A campanha está sendo criada e ainda não está pronta para execução. |
| `AGENDADA` | `agendada` | `scheduled` | A campanha está pronta e aguardando a data/hora programada para iniciar. |
| `ATIVA` | `ativa` | `enviando`, `running` | A campanha está em processo de execução e envio das mensagens. |
| `PAUSADA` | `pausada` | — | A campanha foi temporariamente suspensa. |
| `CONCLUIDA` | `concluida` | `completed`, `finalizada` | A campanha finalizou todos os envios programados. |
| `CANCELADA` | `cancelada` | `cancelled` | A campanha foi interrompida manualmente antes de sua conclusão. |

### 3.2. Tipo de Campanha (`CampanhasOutbound`)

Referência: `TipoCampanha` em `app/services/campanhas/types.py`

| Estado Canônico | Valor no Código | Definição |
| :--- | :--- | :--- |
| `DISCOVERY` | `discovery` | Campanha de descoberta / prospecção. |
| `OFERTA` | `oferta` | Oferta genérica de oportunidades. |
| `OFERTA_PLANTAO` | `oferta_plantao` | Oferta específica de plantões. |
| `REATIVACAO` | `reativacao` | Reativação de médicos inativos. |
| `FOLLOWUP` | `followup` | Seguimento de interações anteriores. |

### 3.3. Permissão de Contato (`PolicyContato`)

| Estado Canônico | Alias(es) / Legado | Definição |
| :--- | :--- | :--- |
| `NONE` | `novo` | O médico nunca interagiu com a plataforma. |
| `ACTIVE` | `ativo` | O médico está em uma janela de conversa ativa e pode ser contatado. |
| `COOLING_OFF` | `em_resfriamento` | O médico demonstrou atrito; um período de pausa é aplicado antes de novos contatos. |
| `OPTED_OUT` | `opt_out`, `descadastrado` | O médico solicitou explicitamente não ser mais contatado. Estado terminal. |

---
*Este documento deve ser a fonte da verdade para novos desenvolvimentos e revisões de código. Qualquer novo estado ou termo de negócio deve ser adicionado aqui antes de ser implementado.*
