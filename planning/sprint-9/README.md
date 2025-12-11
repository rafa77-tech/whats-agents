# Sprint 9: Julia como Colega no Slack

## Visao Geral

Transformar a Julia em uma **colega de trabalho virtual** que o gestor pode conversar pelo Slack como se estivesse ao lado dela no escritorio.

**Objetivo:** O gestor interage com a Julia em linguagem natural, sem precisar decorar comandos. A Julia entende a intencao, executa acoes e responde de forma conversacional.

## Problema Atual

- Comandos rigidos: `@Julia Bot contata <telefone>`, `@Julia Bot status`
- Sem flexibilidade para instrucoes customizadas
- Gestor precisa usar outras ferramentas para consultar dados
- Nao parece uma conversa natural

## Solucao

Julia como agente conversacional no Slack com:
- Interpretacao de linguagem natural
- Acesso a tools de gestao (banco, WhatsApp, metricas)
- Respostas em linguagem natural
- Memoria do contexto da conversa

## Exemplos de Uso

```
Gestor: Julia, manda uma msg pro 11999887766 oferecendo a vaga do Sao Luiz
Julia: Pronto! Mandei assim: "Oi Dr! Tudo bem? Surgiu uma vaga boa no Sao Luiz,
       plantao noturno dia 15/12, R$ 2.500. Tem interesse?"

Gestor: Quantos medicos responderam hoje?
Julia: Hoje tivemos 12 respostas:
       - 8 positivas
       - 3 neutras
       - 1 pediu opt-out
       Taxa de resposta ta em 34%!

Gestor: Quem sao os que responderam positivo?
Julia: Os 8 que mostraram interesse:
       1. Dr Carlos Silva (11999...) - quer plantao noturno
       2. Dra Maria Santos (11988...) - perguntou sobre o Sao Luiz
       3. Dr Pedro Lima (11977...) - disponivel fim de semana
       ...

Gestor: Manda msg pro Dr Carlos confirmando a vaga do dia 15
Julia: Feito! Mandei: "Dr Carlos, reservei a vaga do Sao Luiz dia 15/12 pra vc!
       Vou precisar de alguns docs pra finalizar..."
       Ja atualizei o status da vaga no sistema.

Gestor: Como ta a taxa de resposta essa semana comparado com a anterior?
Julia: Essa semana: 32% (meta: 30%)
       Semana passada: 28%
       Melhora de 4 pontos! Terça foi o melhor dia com 45%.

Gestor: Bloqueia o 11966554433, ele reclamou muito
Julia: Bloqueado! Nao vou mais mandar msg pra ele.
       Quer que eu registre o motivo?

Gestor: Sim, coloca que ele reclamou de receber muitas mensagens
Julia: Anotado! Registrei o motivo do bloqueio.
```

## Epics

| Epic | Titulo | Descricao |
|------|--------|-----------|
| E01 | Agente Julia no Slack | Infraestrutura do agente conversacional |
| E02 | Tools de Gestao | Ferramentas que a Julia pode usar |
| E03 | Respostas em Linguagem Natural | Formatacao e tom das respostas |
| E04 | Tipos de Campanha/Abordagem | Diferentes tipos de primeira mensagem |

## Metricas de Sucesso

| Metrica | Meta |
|---------|------|
| Intencoes interpretadas corretamente | > 95% |
| Tempo de resposta no Slack | < 5s |
| Satisfacao do gestor com respostas | > 4/5 |
| Reducao de uso de outras ferramentas | > 50% |

## Riscos

| Risco | Mitigacao |
|-------|-----------|
| LLM interpreta errado a intencao | Pedir confirmacao antes de acoes criticas |
| Custo alto de tokens | Usar Haiku para interpretacao, Sonnet so quando necessario |
| Respostas muito longas | Limitar e oferecer "quer mais detalhes?" |
| Acoes destrutivas por engano | Confirmacao obrigatoria para bloqueios/envios em massa |

## Dependencias

- Sprint 8 concluida (validacao de output, pipeline)
- Slack Bot configurado e funcionando
- Acesso ao banco de dados
- Evolution API para envio de mensagens

## Estimativa

| Epic | Complexidade | Estimativa |
|------|--------------|------------|
| E01 | Alta | 8-10h |
| E02 | Media | 6-8h |
| E03 | Media | 4-6h |
| E04 | Baixa | 3-4h |
| **Total** | | **21-28h** |

## Criterios de Aceite da Sprint

- [ ] Gestor consegue conversar com Julia em linguagem natural
- [ ] Julia executa acoes solicitadas corretamente
- [ ] Julia responde com dados do banco quando perguntada
- [ ] Julia pede confirmacao antes de acoes criticas
- [ ] Julia mantém contexto dentro de uma conversa
- [ ] Diferentes tipos de abordagem funcionam (discovery, oferta, etc)
