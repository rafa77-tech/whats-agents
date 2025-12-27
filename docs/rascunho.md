  1. Decisões de Produto (preciso de você)

  | Questão                       | Impacto                                                                        |
  |-------------------------------|--------------------------------------------------------------------------------|
  | Supabase ou PostgreSQL local? | A doc menciona Supabase, mas o docker-compose usa PostgreSQL local. Qual usar? |
  | Claude ou OpenAI?             | PRD diz Claude (Anthropic), mas pyproject.toml só tem OpenAI. Qual LLM?        |
  | Lista de médicos para piloto  | Temos alguma base inicial? Ou precisamos criar dados de teste?                 |
  | Google Docs configurado?      | Já tem um doc de briefing criado? Precisa de API credentials?                  |
  | Slack workspace               | Já tem um canal #julia-gestao configurado? Webhook pronto?                     |
  | Escopo do MVP                 | Confirmar: Fase 1 do PRD é o target inicial?                                   |


  Esse diretorio está uma bagunça pq foi usado para testes iniciais de criação e configuração do Evolution API, Chatwoot e n8n rodando localmente. Os demais arquivos existem pelo mesmo motivo, vamos passar tudo para deprecated. Vamos usar o supabase, confirme se o MCP do supabase está configurado para que você possa verificar o que temos no banco de dados. Precisamos de pesquisa em relação a custos, mas devemos usar o melhor modelo de conversação sem que isso signifique custos exorbirtantes. Precisa configurar o google docs, apis, etc, como disse, estamos iniciando hoje este projeto, o mesmo vale pro slack e tudo. Temos que configurar o ambiente ainda. Mas antes, quero que você foque na documentação do projeto, já que estamos começando HOJE.

  Resumo: Documentação Organizada

  Projeto arrumado e documentação consolidada. Aqui está o estado atual:

  Estrutura de Documentação

  docs/
  ├── PRD.md                 # Requisitos do produto (existente)
  ├── ARCHITECTURE.md        # Arquitetura técnica (existente)
  ├── DATABASE.md            # Schema 27 tabelas (existente)
  ├── BRIEFING_TEMPLATE.md   # Template Google Docs (existente)
  ├── PM_AGENT_PROMPT.md     # Prompt do PM (existente)
  ├── LLM_COST_ANALYSIS.md   # NOVO - Análise de custos
  ├── SETUP.md               # NOVO - Guia de configuração
  └── ROADMAP.md             # NOVO - Fases do projeto

  deprecated/
  ├── basic_agent.py         # Arquivos de teste movidos
  ├── testes.py
  └── prompts.py

  Documentos Criados Hoje

  | Documento            | Conteúdo                                                                         |
  |----------------------|----------------------------------------------------------------------------------|
  | LLM_COST_ANALYSIS.md | Comparativo Claude/GPT/DeepSeek, recomendação de estratégia híbrida Haiku+Sonnet |
  | SETUP.md             | Checklist completo de todas as APIs e credenciais necessárias                    |
  | ROADMAP.md           | 5 fases do projeto com tarefas detalhadas                                        |
  | CLAUDE.md            | Atualizado com estado atual e decisões                                           |

  Recomendação de LLM

  Estratégia híbrida para MVP:
  - Claude Haiku ($0.25/1M) → 80% das mensagens (simples)
  - Claude Sonnet ($3/1M) → 20% das mensagens (complexas)
  - Economia estimada: 73% vs usar só Sonnet
  - Custo mensal projetado: ~$25/mês para 1000 msgs/dia

  Próximos Passos Imediatos

  Preciso que você:

  1. Crie projeto no Supabase → https://supabase.com/dashboard
  2. Me passe as credenciais (URL + Service Key) para configurar o MCP
  3. Crie conta na Anthropic → https://console.anthropic.com

  Depois disso posso:
  - Configurar o MCP do Supabase
  - Criar o schema do banco de dados
  - Começar a implementação do Fase 1

  Quer começar pela criação do Supabase?



  Como o Chatwoot envia evento `conversation_updated` tanto quando label é adicionada quanto removida? E o inverso também...como no chatwoot ao colocar a label a Julia sabe que houve handoff?

curl http://localhost:8000/health/whatsapp


docker compose build julia-api && docker compose up -d julia-api && sleep 3 && curl -X POST
http://localhost:8000/jobs/primeira-mensagem -H "Content-Type: application/json" -d '{"telefone": "5511981677736"}'