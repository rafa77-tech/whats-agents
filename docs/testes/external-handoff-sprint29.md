# Teste External Handoff - Sprint 29

**Data:** 2026-01-05
**Status:** Em andamento

## Objetivo

Testar o fluxo completo de external handoff (ponte médico-divulgador) no Conversation Mode.

## Dados de Teste

### Contato do Divulgador (contatos_grupo)
- **ID:** `b7b019ec-4fc5-49b7-87fc-05ff0eac393d`
- **Telefone:** `5511981677736`
- **Nome:** `Rafael Teste Handoff` → **ATUALIZAR PARA:** `Rafael Silva`
- **Empresa:** `Empresa Teste` → **ATUALIZAR PARA:** `Hospital São Lucas`

### Vaga de Teste (vagas)
- **ID:** `c6a926e7-d369-4c14-b73d-7e7ccdcd38ab`
- **Hospital:** AMA Especialidades Parque Peruche
- **Data:** 2026-01-05
- **Valor:** R$ 2.800
- **Source:** grupo
- **Source ID:** (vinculado ao vagas_grupo de teste)

### Cadeia de Dados
```
vagas (source_id) → vagas_grupo → mensagens_grupo → contatos_grupo (telefone divulgador)
```

## Correções Implementadas

### 1. Parâmetros de `enviar_whatsapp` (Commit: 923d5ee)
**Problema:** Erro `enviar_whatsapp() got an unexpected keyword argument 'numero'`

**Causa:** Chamadas usando `numero=` e `mensagem=` ao invés de `telefone=` e `texto=`

**Arquivos corrigidos:**
- `app/services/external_handoff/messaging.py`
  - `enviar_mensagem_divulgador()` - linha 198-201
  - `enviar_followup_divulgador()` - linha 217-220

### 2. Tratamento de None em campos (Commit: a155879)
**Problema:** Nome do médico aparecia como "revolunamobile None"

**Causa:** `sobrenome` era `None` e não string vazia, resultando em "None" literal

**Correção:**
```python
# Antes
sobrenome = medico.get("sobrenome", "")

# Depois
sobrenome = medico.get("sobrenome") or ""
```

### 3. Formatação das Mensagens (Commit: a155879)

**Mensagem para o médico (antes):**
```
Perfeito! Reservei essa vaga pra voce.

Pra confirmar na escala, fala direto com Rafael Teste Handoff (Empresa Teste): 5511981677736

Me avisa aqui quando fechar!
```

**Mensagem para o médico (depois):**
```
Perfeito! Reservei essa vaga pra voce 🎉

Pra confirmar na escala, fala direto com:

👤 Rafael Silva da Hospital São Lucas
📱 5511981677736

Me avisa aqui quando fechar!
```

**Mensagem para o divulgador (depois):**
```
Oi! Tudo bem?

Tenho um medico interessado na sua vaga:

📅 05/01 (seg)
🏥 AMA Especialidades Parque Peruche
💰 R$ 2.800

👨‍⚕️ *Nome do Médico*
📱 5511936191522

Me confirma o status:
✅ Fechou: [link]
❌ Nao fechou: [link]

Ou responde *CONFIRMADO* ou *NAO FECHOU*
```

### 4. Período omitido quando vazio
**Problema:** Mensagem mostrava "05/01 (seg) -  - Hospital" com traços vazios

**Correção:** Omitir período da linha quando não existir na vaga

### 5. Negrito removido do nome do divulgador (Commit: abc288a)
**Problema:** Nome com asteriscos `*Rafael Teste Handoff*`

**Correção:** Removido asteriscos do nome

## Pendências

### 1. Atualizar dados de teste no banco
Executar no Supabase (estava com timeout):
```sql
UPDATE contatos_grupo
SET nome = 'Rafael Silva', empresa = 'Hospital São Lucas'
WHERE telefone = '5511981677736';
```

### 2. Testar confirmação por keyword
O `HandoffKeywordProcessor` existe e detecta:
- **CONFIRMADO:** `confirmado`, `fechou`, `fechado`, `confirmo`, etc.
- **NAO FECHOU:** `nao fechou`, `desistiu`, `cancelou`, etc.

**Por que não funcionou no teste:**
Os handoffs foram deletados para limpar erros de follow-up. Quando o divulgador respondeu "confirmado", não havia handoff pendente.

**Para testar:**
1. Criar novo handoff (médico pede para fechar vaga)
2. Responder "CONFIRMADO" do número do divulgador (5511981677736)
3. Verificar se o sistema processa e responde

### 3. Testar fluxo completo novamente
Após atualizar os dados de teste, testar:
1. Médico envia "quero a vaga de ortopedia"
2. Julia chama `criar_handoff_externo`
3. Médico recebe mensagem com contato do divulgador
4. Divulgador recebe mensagem com contato do médico
5. Divulgador responde "CONFIRMADO"
6. Sistema processa e notifica ambos

## Arquivos Relevantes

| Arquivo | Descrição |
|---------|-----------|
| `app/services/external_handoff/messaging.py` | Templates de mensagens |
| `app/services/external_handoff/service.py` | Lógica principal da ponte |
| `app/services/external_handoff/confirmacao.py` | Processamento de confirmação |
| `app/services/external_handoff/repository.py` | Queries de handoff |
| `app/pipeline/pre_processors.py` | `HandoffKeywordProcessor` (linha 630) |
| `app/tools/intermediacao.py` | Tool `criar_handoff_externo` |

## Commits desta sessão

1. `923d5ee` - fix(handoff): corrigir parâmetros de enviar_whatsapp
2. `a155879` - style(handoff): melhorar formatação das mensagens de ponte
3. `abc288a` - style(handoff): remover negrito do nome do divulgador

## Próximos Passos

1. [ ] Atualizar nome/empresa do contato de teste no Supabase
2. [ ] Testar fluxo completo de handoff
3. [ ] Testar confirmação por keyword (CONFIRMADO / NAO FECHOU)
4. [ ] Verificar notificação ao médico após confirmação
5. [ ] Testar follow-ups automáticos (após 2h, 24h, 36h)
