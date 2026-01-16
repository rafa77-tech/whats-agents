# Runbook - Sprint 32

Procedimentos operacionais para novas funcionalidades implementadas na Sprint 32.

---

## Modo Piloto

Flag que controla execucao de acoes autonomas.

| Flag | Valor | Efeito |
|------|-------|--------|
| `PILOT_MODE` | `True` | Acoes autonomas desabilitadas |
| `PILOT_MODE` | `False` | Julia age autonomamente |

### O que funciona em Modo Piloto

- Campanhas manuais
- Respostas a medicos (inbound)
- Canal de ajuda
- Comandos via Slack
- Validacao de telefones

### O que NAO funciona em Modo Piloto

- Discovery automatico
- Oferta automatica (furo de escala)
- Reativacao automatica
- Feedback automatico

### Ativar Modo Piloto (emergencia)

**Via Dashboard:**
1. Acessar Sistema -> Configuracoes
2. Clicar no toggle "Modo Piloto"
3. Confirmar

**Via Codigo (se dashboard indisponivel):**
```bash
railway run python -c "
from app.services.supabase import supabase
supabase.table('system_config').upsert({
    'key': 'PILOT_MODE',
    'value': 'true'
}).execute()
"
```

### Quando ativar Modo Piloto

- Julia enviando mensagens indesejadas
- Bug detectado em acao autonoma
- Problema com integracao externa
- Necessidade de pausar operacao

---

## Hospitais Bloqueados

Quando hospital e bloqueado:
1. Vagas movidas para `vagas_hospitais_bloqueados`
2. Julia nao ve as vagas (nao precisa filtrar)
3. Ao desbloquear, vagas futuras restauradas

### Bloquear Hospital

**Via Dashboard:**
1. Hospitais -> Bloqueados
2. "Bloquear Hospital"
3. Selecionar hospital
4. Informar motivo
5. Confirmar

**Via Slack:**
```
Julia, bloquear hospital Sao Luiz motivo: reforma em andamento
```

### Desbloquear Hospital

**Via Dashboard:**
1. Hospitais -> Bloqueados
2. Encontrar hospital na lista
3. "Desbloquear"
4. Confirmar

**Via Slack:**
```
Julia, desbloquear hospital Sao Luiz
```

### Verificar vagas movidas

```sql
SELECT COUNT(*) FROM vagas_hospitais_bloqueados
WHERE hospital_id = 'UUID_DO_HOSPITAL';
```

---

## Canal de Ajuda

Quando Julia nao sabe algo factual, ela pergunta ao gestor.

### Responder pedido pendente

**Via Dashboard:**
1. Canal de Ajuda
2. Clicar "Responder" no pedido
3. Digitar resposta
4. Enviar

**Via Slack:**
- Responder na thread do pedido

### Verificar pedidos pendentes

```sql
SELECT * FROM pedidos_ajuda
WHERE status = 'pendente'
ORDER BY criado_em DESC;
```

### Timeout

- 5 minutos sem resposta -> Julia diz "Vou confirmar essa info"
- Lembretes a cada 30 minutos para o gestor

---

## Troubleshooting

### Julia nao esta respondendo

1. Verificar status da conversa:
```sql
SELECT status FROM conversations WHERE id = 'UUID';
```

2. Se `aguardando_gestor`:
   - Ir em Canal de Ajuda
   - Responder pedido pendente

3. Se `handoff`:
   - Conversa com humano
   - Devolver para Julia se necessario

### Julia oferecendo hospital bloqueado

1. Verificar se hospital esta realmente bloqueado:
```sql
SELECT * FROM hospitais_bloqueados
WHERE hospital_id = 'UUID' AND status = 'bloqueado';
```

2. Se nao estiver, bloquear

3. Verificar cache (pode demorar ate 5 min)

### Julia alucinando informacoes

1. Verificar se canal de ajuda esta funcionando
2. Verificar se conhecimento foi salvo corretamente:
```sql
SELECT * FROM conhecimento_hospitais
WHERE hospital_id = 'UUID'
ORDER BY created_at DESC;
```

3. Se precisar, forcar recarga do contexto

---

## Comandos Uteis

### Verificar modo piloto atual

```sql
SELECT value FROM system_config WHERE key = 'PILOT_MODE';
```

### Listar campanhas ativas

```sql
SELECT nome_template, tipo_campanha, objetivo, pode_ofertar
FROM campanhas
WHERE status = 'ativa'
ORDER BY created_at DESC;
```

### Verificar gatilhos autonomos

```sql
SELECT * FROM execucoes_gatilhos
WHERE tipo IN ('discovery', 'oferta', 'reativacao', 'feedback')
ORDER BY executado_em DESC
LIMIT 10;
```

### Verificar metricas de Julia

```python
from app.core.metrics import metrics
print(metrics.obter_resumo())
```

---

## Ver Tambem

- [Comportamentos de Campanha](../julia/comportamentos.md)
- [CLAUDE.md](../../CLAUDE.md)
- [Railway Deploy](../integracoes/railway-deploy.md)
