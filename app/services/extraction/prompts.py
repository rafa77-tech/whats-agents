"""
Prompts para extração de dados de conversas.

Sprint 53: Discovery Intelligence Pipeline.
"""

EXTRACTION_PROMPT = """Voce e um analista de dados especializado em conversas de staffing medico.

Analise esta interacao e extraia dados estruturados.

## MENSAGEM DO MEDICO:
{mensagem_medico}

## RESPOSTA DA JULIA (escalista):
{resposta_julia}

## CONTEXTO DO MEDICO:
- Nome: {nome}
- Especialidade cadastrada: {especialidade}
- Regiao cadastrada: {regiao}
- Tipo de campanha: {tipo_campanha}

## EXTRAIA EM JSON:

```json
{{
  "interesse": "positivo|negativo|neutro|incerto",
  "interesse_score": 0.0-1.0,
  "especialidade_mencionada": "string ou null",
  "regiao_mencionada": "string ou null",
  "disponibilidade_mencionada": "string ou null",
  "objecao": {{
    "tipo": "preco|tempo|confianca|distancia|disponibilidade|empresa_atual|pessoal|outro",
    "descricao": "string",
    "severidade": "baixa|media|alta"
  }},
  "preferencias": ["lista de preferencias explicitas"],
  "restricoes": ["lista de restricoes explicitas"],
  "dados_corrigidos": {{"campo": "valor_novo"}},
  "proximo_passo": "enviar_vagas|agendar_followup|aguardar_resposta|escalar_humano|marcar_inativo|sem_acao",
  "confianca": 0.0-1.0
}}
```

## REGRAS CRITICAS:

### Interesse
- positivo: demonstra interesse claro (quer saber mais, pede detalhes, aceita)
- negativo: recusa clara, objecao forte, sem interesse
- neutro: resposta vaga, educada mas sem compromisso
- incerto: nao e possivel determinar, mensagem ambigua

### Score de Interesse
- 0.0: recusa enfatica, hostilidade
- 0.3: sem interesse mas educado
- 0.5: neutro, resposta vaga
- 0.7: curioso, quer saber mais
- 1.0: muito interessado, quer fechar

### Especialidade/Regiao
- SO preencha se o medico MENCIONAR EXPLICITAMENTE
- Nao infira baseado no cadastro
- Normalize: "SP" -> "Sao Paulo", "cardio" -> "Cardiologia", "RJ" -> "Rio de Janeiro"

### Objecao
- Se nao detectar objecao, retorne objecao como null (nao como objeto vazio)
- preco: reclama de valor, acha caro
- tempo: sem tempo, muito ocupado
- confianca: desconfia da empresa, nunca ouviu falar
- distancia: muito longe, outra regiao
- disponibilidade: agenda cheia, sem horario
- empresa_atual: ja trabalha com outra empresa
- pessoal: motivos pessoais, familia
- outro: qualquer outra objecao

### Dados Corrigidos
- SO preencha se informacao DIFERE do cadastro COM CERTEZA
- Exemplo: cadastrado "Cirurgia Geral", medico diz "sou reumatologista" -> {{"especialidade": "Reumatologia"}}
- NAO corrija se for apenas mencao casual
- Campos permitidos: especialidade, cidade, estado, regiao

### Proximo Passo
- enviar_vagas: interesse alto + pediu detalhes de vagas
- agendar_followup: interesse medio, "talvez", "me ligue depois"
- aguardar_resposta: perguntou algo, aguardando mais info
- escalar_humano: situacao complexa, reclamacao, confuso
- marcar_inativo: recusa clara, opt-out, bot detectado
- sem_acao: saudacao simples, agradecimento, conversa encerrada

### Confianca
- 0.0-0.3: mensagem muito curta ou ambigua
- 0.4-0.6: razoavel certeza
- 0.7-0.9: alta certeza
- 1.0: certeza absoluta (raro)

### Preferencias e Restricoes
- Preferencias: coisas que o medico QUER (ex: "prefiro plantoes noturnos", "gosto de UTI")
- Restricoes: coisas que o medico NAO QUER (ex: "nao trabalho fins de semana", "nao faco cirurgia")
- So inclua se mencionado EXPLICITAMENTE
- Seja especifico e conciso

RETORNE APENAS O JSON, SEM EXPLICACOES."""
