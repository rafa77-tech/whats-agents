# Exemplos de Mensagens Slack

Exemplos de payloads testados e funcionando para o webhook da Julia.

## Mensagem Simples

```json
{"text": "Teste simples - Julia está configurada!"}
```

## Report com Blocks

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "📊 Report Júlia - Teste"}
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*Métricas do dia:*\n• Enviadas: 10\n• Respondidas: 3\n• Taxa: 30%"}
    }
  ]
}
```

## Alerta de Handoff (Vermelho)

```json
{
  "text": "🚨 Handoff necessário!",
  "attachments": [
    {
      "color": "#ff0000",
      "fields": [
        {"title": "Médico", "value": "Dr. Carlos (CRM 123456)", "short": true},
        {"title": "Motivo", "value": "Médico irritado", "short": true},
        {"title": "Resumo", "value": "Reclamou do valor oferecido e pediu para falar com supervisor"}
      ]
    }
  ]
}
```

## Notificação de Sucesso (Verde)

```json
{
  "text": "🎉 Plantão fechado!",
  "attachments": [
    {
      "color": "#00ff00",
      "fields": [
        {"title": "Médico", "value": "Dra. Ana Silva", "short": true},
        {"title": "Hospital", "value": "Hospital Brasil", "short": true},
        {"title": "Data", "value": "Sábado, 14/12 - 07h às 19h", "short": true},
        {"title": "Valor", "value": "R$ 2.400", "short": true}
      ]
    }
  ]
}
```

## Cores Disponíveis

- `#ff0000` - Vermelho (alertas, erros, handoff urgente)
- `#ffcc00` - Amarelo (avisos)
- `#00ff00` - Verde (sucesso, plantão fechado)
- `#0066ff` - Azul (informativo)

## Formatação Markdown (mrkdwn)

- `*bold*` - Negrito
- `_italic_` - Itálico
- `~strike~` - Riscado
- `\n` - Quebra de linha
- `• item` - Lista com bullet

---

Testado em: 2024-12-06
Canal: #julia-gestao
