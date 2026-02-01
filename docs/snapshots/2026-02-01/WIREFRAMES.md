# Wireframes (alto nivel)

Estilo: minimalista + data-first. CTA unico por tela. Cards apenas quando necessario.

## 1) Home (Centro de Comando)

+----------------------------------------------------------------------------------+
| Logo | Busca global [............................] | Alertas | Usuario          |
+----------------------------------------------------------------------------------+
| Navegacao lateral (modulos)                                                   |  |
|                                                                              |  |
|  [Saude do Sistema]   [Campanhas Ativas]   [Conversas Criticas]               |  |
|  score + status       top 3             top 5 com tempo sem resposta         |  |
|                                                                              |  |
|  Proxima Acao (CTA unico)                                                     |  |
|  "Resolver alerta connection_lost"  [Ir para Alertas]                         |  |
|                                                                              |  |
|  KPIs essenciais (4)                                                         |  |
|  taxa resp | conversao | latencia | filas                                    |  |
+----------------------------------------------------------------------------------+

## 2) Monitor (Operacao)

+----------------------------------------------------------------------------------+
| Topo: Busca global | Alertas criticos | Data/Hora | Atualizar                  |
+----------------------------------------------------------------------------------+
| Filtros: Status [All] Categoria [All] Periodo [Ultima 24h]                     |
+----------------------------------------------------------------------------------+
| RESUMO (linha unica)  Jobs: 32 | Sucesso: 96% | Erro: 1 | Atrasados: 0          |
+----------------------------------------------------------------------------------+
| LISTA PRINCIPAL (tabela)                                                      |
| Job | Categoria | Ultima execucao | Status | Duracao | Execucoes | Acoes         |
| ...                                                                          |  |
+----------------------------------------------------------------------------------+

## 3) Conversas (Inbox)

+----------------------------------------------------------------------------------+
| Topo: Busca global | Filtros rapidos | Alertas                                 |
+----------------------------------------------------------------------------------+
| Coluna esquerda:                                                               |
| - Filtros (Criticas, Sem resposta, Novas, Em andamento)                        |
| - Lista de conversas (tempo, status, tag)                                      |
|                                                                                |
| Painel principal:                                                              |
| - Mensagens                                                                     |
| - CTA unico: "Assumir conversa" ou "Enviar resposta"                           |
| - Contexto do medico (resumo lateral)                                          |
+----------------------------------------------------------------------------------+

## 4) Campanhas (Lista + Detalhe)

LISTA
+----------------------------------------------------------------------------------+
| Topo: Busca | Filtros | CTA unico: "Nova campanha"                             |
+----------------------------------------------------------------------------------+
| Campanha | Status | Publico | Enviados | Respostas | Proxima execucao           |
| ...                                                                          |  |
+----------------------------------------------------------------------------------+

DETALHE
+----------------------------------------------------------------------------------+
| Header: Nome | Status | CTA unico (Pausar/Retomar)                              |
+----------------------------------------------------------------------------------+
| Resumo (3 KPIs) | Mensagens | Audiencia | Erros                                 |
|                                                                                |
| Tabs: Visao | Audiencia | Mensagens | Historico                                 |
+----------------------------------------------------------------------------------+

## 5) Chips (Visao geral)

+----------------------------------------------------------------------------------+
| Header: Pool de Chips | Periodo | CTA unico: "Nova instancia"                  |
+----------------------------------------------------------------------------------+
| Resumo: Ativos | Warmup | Alertas | Trust                                       |
+----------------------------------------------------------------------------------+
| Tabela: Instancia | Status | Trust | Msgs | Erros | Acoes                        |
+----------------------------------------------------------------------------------+

