# Epic 05 - Sistema Avancado

## Objetivo
Expandir a pagina `/sistema` existente com controles avancados: rate limit configuravel, circuit breakers manuais e safe mode granular.

## Estado Atual da Pagina /sistema

A pagina ja possui:
- Toggle de Modo Piloto (funcional)
- Toggle de features autonomas (funcional)
- Exibicao de rate limiting (somente leitura)
- Exibicao de horario de operacao (somente leitura)

## O Que Falta

1. **Rate Limit Configuravel** - Editar limites dinamicamente
2. **Horario Configuravel** - Editar horario de operacao
3. **Circuit Breakers** - Visualizar e resetar
4. **Safe Mode Emergencial** - Parar tudo imediatamente

## Stories

---

### S43.E5.1 - Rate Limit Configuravel

**Objetivo:** Permitir editar limites de rate limiting com validacao e audit trail.

**Layout Atual (somente leitura):**
```
+------------------------------------------+
| Rate Limiting                             |
| Mensagens por hora: 20                    |
| Mensagens por dia: 100                    |
| Intervalo: 45-180s                        |
+------------------------------------------+
```

**Layout Novo (editavel):**
```
+------------------------------------------+
| Rate Limiting                    [Editar] |
+------------------------------------------+
| Mensagens por hora: 20                    |
| Mensagens por dia: 100                    |
| Intervalo: 45-180s                        |
| Uso atual: 16/20 (hora) | 45/100 (dia)   |
+------------------------------------------+

--- Modal de Edicao ---

+------------------------------------------+
| Editar Rate Limiting             [Fechar] |
+------------------------------------------+
| Mensagens por hora:                       |
| [20] (recomendado: 15-25)                |
+------------------------------------------+
| Mensagens por dia:                        |
| [100] (recomendado: 80-150)              |
+------------------------------------------+
| Intervalo minimo (segundos):              |
| [45] (minimo: 30)                         |
+------------------------------------------+
| Intervalo maximo (segundos):              |
| [180] (maximo: 300)                       |
+------------------------------------------+
| ! Atencao: Limites muito altos podem      |
|   causar ban do WhatsApp                  |
+------------------------------------------+
| [Cancelar] [Salvar Alteracoes]           |
+------------------------------------------+
```

**Tarefas:**
1. Adicionar botao "Editar" no card de Rate Limiting
2. Criar modal `EditRateLimitModal`
3. Validacao de limites (min/max)
4. Warning para valores arriscados
5. Salvar com confirmacao
6. Registrar no audit trail

**API Calls:**
- `GET /sistema/config` - Config atual (ja usado)
- `PATCH /sistema/config` - Atualizar (criar se nao existir)

**DoD:**
- [ ] Modal de edicao
- [ ] Validacao de limites
- [ ] Warning para valores arriscados
- [ ] Confirmacao antes de salvar
- [ ] Audit trail registrado
- [ ] Testes unitarios

---

### S43.E5.2 - Horario de Operacao Configuravel

**Objetivo:** Permitir editar horario e dias de operacao.

**Layout:**
```
+------------------------------------------+
| Horario de Operacao              [Editar] |
+------------------------------------------+
| Horario: 08h as 20h                       |
| Dias: Seg-Sex                             |
| Status: Dentro do horario                 |
+------------------------------------------+

--- Modal de Edicao ---

+------------------------------------------+
| Editar Horario de Operacao       [Fechar] |
+------------------------------------------+
| Hora de inicio: [08]:00                   |
| Hora de fim:    [20]:00                   |
+------------------------------------------+
| Dias de operacao:                         |
| [x] Segunda  [x] Terca   [x] Quarta      |
| [x] Quinta   [x] Sexta   [ ] Sabado      |
| [ ] Domingo                               |
+------------------------------------------+
| ! Julia so enviara mensagens proativas   |
|   dentro deste horario                    |
+------------------------------------------+
| [Cancelar] [Salvar Alteracoes]           |
+------------------------------------------+
```

**Tarefas:**
1. Adicionar botao "Editar" no card de Horario
2. Criar modal `EditScheduleModal`
3. Seletores de hora (dropdown ou time picker)
4. Checkboxes para dias da semana
5. Validacao (inicio < fim)
6. Salvar com confirmacao

**API Calls:**
- `GET /sistema/config` - Config atual
- `PATCH /sistema/config` - Atualizar

**DoD:**
- [ ] Modal de edicao
- [ ] Seletores funcionais
- [ ] Validacao
- [ ] Feedback de sucesso
- [ ] Testes unitarios

---

### S43.E5.3 - Safe Mode Emergencial

**Objetivo:** Botao de emergencia para parar todas as operacoes imediatamente.

**Layout:**
```
+----------------------------------------------------------+
| Controles de Emergencia                                   |
+----------------------------------------------------------+
| +------------------------------------------------------+ |
| |  [!] SAFE MODE EMERGENCIAL                           | |
| |                                                      | |
| |  Para imediatamente TODAS as operacoes da Julia:     | |
| |  - Envio de mensagens                                | |
| |  - Processamento de fila                             | |
| |  - Jobs autonomos                                    | |
| |  - Entrada em grupos                                 | |
| |                                                      | |
| |  Status: INATIVO                    [ATIVAR]         | |
| +------------------------------------------------------+ |
+----------------------------------------------------------+

--- Ao clicar ATIVAR ---

+------------------------------------------+
| ATIVAR SAFE MODE?                [Fechar] |
+------------------------------------------+
| ! ATENCAO: Acao critica                   |
|                                           |
| Isso ira parar IMEDIATAMENTE:             |
| - Envio de novas mensagens                |
| - Processamento da fila                   |
| - Todos os jobs autonomos                 |
| - Entrada em grupos                       |
|                                           |
| Julia continuara APENAS respondendo       |
| mensagens de medicos ja em conversa.      |
|                                           |
| Motivo (obrigatorio):                     |
| [________________________________]        |
|                                           |
| [Cancelar] [CONFIRMAR SAFE MODE]         |
+------------------------------------------+
```

**Tarefas:**
1. Adicionar card de Safe Mode na pagina Sistema
2. Visual destacado (vermelho/warning)
3. Modal de confirmacao com motivo obrigatorio
4. Ativa pilot_mode + desativa todas as features
5. Notifica no Slack
6. Registra no audit trail com motivo

**API Calls:**
- `POST /sistema/safe-mode` com motivo (criar endpoint se necessario)
- Ou usar combinacao de:
  - `POST /sistema/pilot-mode` (ativar)
  - `POST /sistema/features/{feature}` (desativar todas)

**DoD:**
- [ ] Card visualmente destacado
- [ ] Confirmacao com motivo
- [ ] Ativa modo piloto
- [ ] Desativa todas as features
- [ ] Notificacao no Slack
- [ ] Testes unitarios

---

## Mudancas na Pagina Existente

### Reorganizacao do Layout

```
/sistema (nova organizacao)

+----------------------------------------------------------+
| Sistema Julia                                             |
+----------------------------------------------------------+

[Card Modo Piloto - existente, sem mudancas]

[Card Features Autonomas - existente, sem mudancas]

+----------------------------------------------------------+
| Configuracoes                                             |
+----------------------------------------------------------+
| [Rate Limiting]           [Horario de Operacao]          |
| msgs/hora: 20 [Editar]    08h-20h Seg-Sex [Editar]       |
+----------------------------------------------------------+

+----------------------------------------------------------+
| Controles de Emergencia                                   |
+----------------------------------------------------------+
| [SAFE MODE - Card grande e vermelho]                     |
+----------------------------------------------------------+
```

## Consideracoes Tecnicas

- Todas as alteracoes devem ter audit trail
- Confirmacao obrigatoria para acoes criticas
- Feedback visual imediato (toast)
- Polling para atualizar status apos mudancas
