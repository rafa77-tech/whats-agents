# Template: Briefing da Julia

Documento Google Docs que o gestor usa para direcionar a Julia semanalmente.

---

## Formato do Documento

**IMPORTANTE:** O documento DEVE usar `#` e `##` literalmente para marcar secoes.
O Google Docs preserva esses caracteres - apenas digite-os no inicio da linha.

```markdown
# Briefing Julia - Semana DD/MM

## Foco da Semana
- Prioridade 1: [descricao]
- Prioridade 2: [descricao]
- Evitar: [descricao]

## Vagas Prioritarias
- [Hospital] - [Data] - ate R$ [valor]

## Tom da Semana
- [instrucao de comunicacao]
- Pode oferecer ate X% a mais

## Observacoes
- [nota importante]
```

---

## Secoes e Como Sao Processadas

| Secao | Diretriz | Comportamento |
|-------|----------|---------------|
| Foco da Semana | `foco_semana` | Direciona priorizacao de contatos |
| Vagas Prioritarias | `vagas_prioritarias` | Marca vagas como urgentes |
| Tom da Semana | `tom_semana` | Instrucoes de comunicacao |
| Observacoes | `observacoes` | Notas gerais |

---

## Exemplo Completo

```markdown
# Briefing Julia - Semana 10/12

## Foco da Semana
- Prioridade 1: Anestesistas da Grande Sao Paulo
- Prioridade 2: Follow-up de medicos que nao responderam ha 7+ dias
- Evitar: Contatos em horario de almoco (12h-14h)

## Vagas Prioritarias
- Hospital Sao Luiz Morumbi - 14/12 - ate R$ 3.000
- Hospital Albert Einstein - 15/12 - ate R$ 3.500
- Hospital Samaritano - 16/12 - ate R$ 2.800

## Tom da Semana
- Ser mais direta, menos enrolacao
- Mencionar que temos muitas vagas boas
- Pode oferecer ate 10% a mais se necessario
- Garantir pagamento em ate 15 dias uteis

## Observacoes
- Feriado na quinta, ajustar horarios
- Nao mencionar vaga do Hospital X ate sexta
- Semana de testes iniciais
```

---

## O Que NAO Vai no Briefing

| Item | Onde Fica | Como Usar |
|------|-----------|-----------|
| Medicos bloqueados | Banco de dados (`opt_out=true`) | Via opt-out automatico ou manual |
| Contatos prioritarios | Comando Slack | `@julia contata CRM 123456` |
| Lista de medicos | Banco de dados | Importacao/cadastro |

---

## Como Funciona

1. **Leitura:** Worker le o documento a cada 60 minutos
2. **Deteccao:** Compara hash para detectar mudancas
3. **Parsing:** Extrai secoes marcadas com `##`
4. **Atualizacao:** Salva diretrizes no banco
5. **Notificacao:** Avisa no Slack que briefing mudou
6. **Aplicacao:** Proxima mensagem da Julia usa novas diretrizes

---

## Dicas para o Gestor

### Faca
- Use `#` para titulo e `##` para secoes (obrigatorio!)
- Comece cada item com `-`
- Seja especifico nas instrucoes
- Atualize semanalmente
- Mantenha conciso

### Nao Faca
- Nao remova os `#` e `##`
- Nao use formatacao visual (negrito, italico) no lugar de `##`
- Nao coloque informacoes contraditorias
- Nao liste medicos bloqueados aqui (use opt-out no sistema)

---

## Sincronizacao Manual

Se precisar forcar sincronizacao:

```bash
curl -X POST http://localhost:8000/jobs/sincronizar-briefing
```

Ou aguardar o proximo ciclo automatico (a cada 60 min).
