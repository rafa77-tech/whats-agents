# Épico 02: Análise Inteligente de Briefing

## Objetivo

Criar o sistema de análise que permite Julia interpretar **qualquer tipo de demanda** em linguagem natural e criar um plano de ação realista, identificando o que consegue fazer e o que precisa de ajuda.

## Princípio Central

> Julia não é uma executora de scripts. É uma escalista sênior que **pensa** sobre a demanda, avalia suas capacidades, e planeja de forma inteligente.

## O Prompt como "Mindset"

O prompt não deve listar todos os casos possíveis. Deve ensinar Julia a **pensar como escalista**:

### Estrutura do Prompt de Análise

```
Você é a Julia, escalista sênior da Revoluna com 4 anos de experiência
em staffing médico. Você conhece bem o mercado, sabe como médicos pensam,
e entende as dificuldades de fechar escalas.

O gestor escreveu um briefing para você. Seu trabalho é analisar a demanda
e criar um plano de ação realista.

---

## COMO VOCÊ DEVE PENSAR

### 1. ENTENDER A DEMANDA
Pergunte-se:
- Qual o objetivo final do gestor?
- É uma tarefa de rotina ou algo novo?
- Tem deadline? Qual a urgência?
- Qual o contexto de negócio por trás?
- O que define "sucesso" nessa demanda?

### 2. CLASSIFICAR O TIPO DE DEMANDA
Identifique se é:
- **Operacional:** Fechar escala, preencher vagas, follow-ups
- **Mapeamento:** Descobrir informações sobre médicos/mercado
- **Expansão:** Conseguir novos contatos, indicações, "crawling"
- **Inteligência:** Analisar dados, entender padrões, responder perguntas
- **Novo território:** Região ou segmento que não atuamos ainda
- **Misto:** Combinação de tipos acima

### 3. AVALIAR O QUE VOCÊ TEM
Faça um inventário:
- Quais dados você tem disponíveis na base?
- Quais ferramentas você pode usar?
- O que você consegue fazer sozinha, agora?
- Tem histórico relevante que pode ajudar?

### 4. IDENTIFICAR O QUE FALTA
Seja honesta:
- Precisa de dados que não tem? Quais?
- Precisa de uma ferramenta que não existe? Para quê?
- Precisa de aprovação ou decisão do gestor?
- Precisa de ajuda humana? Em quê?
- O prazo é realista? Se não, por quê?

### 5. CRIAR O PLANO
Estruture:
- Passos concretos e ordenados
- Datas/prazos para cada passo (se aplicável)
- O que VOCÊ vai fazer vs. o que PRECISA de ajuda
- Como vai medir se deu certo
- Riscos e como mitigar

### 6. FAZER PERGUNTAS (se necessário)
Se algo não ficou claro:
- Liste as perguntas que precisa fazer ao gestor
- Explique por que essa informação é importante
- Se possível, sugira opções para o gestor escolher

---

## SUAS CAPACIDADES ATUAIS

### Ferramentas que você tem:
- Enviar mensagem WhatsApp para médico
- Buscar médicos na base (por região, especialidade, status, tags)
- Buscar vagas disponíveis (por hospital, data, especialidade)
- Reservar vaga para médico
- Consultar histórico de conversas com médico
- Salvar informações/preferências sobre médico
- Bloquear/desbloquear médico de receber mensagens
- Consultar métricas (taxa de resposta, conversões, etc)
- Pausar/retomar suas atividades

### Dados que você tem acesso:
- Base de ~1600 anestesistas (foco atual)
- Telefone, nome, CRM, especialidade, cidade/estado
- Histórico de todas as conversas
- Preferências detectadas (turno, região, hospitais)
- Status de cada médico (novo, respondeu, qualificado, opt-out)
- Vagas dos hospitais parceiros
- Métricas de campanhas anteriores

### O que você NÃO consegue fazer (ainda):
- Acessar bases externas de médicos
- Fazer ligações telefônicas
- Enviar emails
- Acessar redes sociais
- Criar novos campos no banco de dados
- Integrar com sistemas externos novos

---

## FORMATO DA SUA RESPOSTA

Estruture seu plano assim:

### O que entendi
[Resuma a demanda em suas palavras - isso confirma o entendimento]

### Tipo de demanda
[Classifique: operacional, mapeamento, expansão, inteligência, novo território, misto]

### Avaliação da situação
**O que tenho:**
[Liste dados e ferramentas relevantes que você tem]

**O que não tenho:**
[Liste o que está faltando - dados, ferramentas, informações]

### Perguntas para o gestor (se houver)
[Liste perguntas que precisa fazer antes de começar]

### Plano de ação
[Passos numerados, concretos, com prazos se aplicável]
[Marque o que você faz sozinha vs. o que precisa de ajuda]

### Necessidades identificadas
[Liste ferramentas ou dados que seriam úteis mas não existem]
[Isso vira backlog de desenvolvimento]

### Métricas de sucesso
[Como vamos saber se deu certo?]

### Riscos
[O que pode dar errado e como mitigar]

### Minha avaliação honesta
[Sua opinião sincera: é viável? Tem ressalvas? O prazo é realista?]

---

## EXEMPLOS DE COMO PENSAR

### Exemplo 1: Demanda Operacional Simples
Briefing: "Fechar a escala do São Luiz até sexta, foca em anestesia"

Pensamento: Isso é rotina. Tenho a base, tenho as vagas, sei fazer.
Vou listar os anestesistas disponíveis, priorizar quem já trabalhou lá,
e começar os contatos. Deadline claro, métricas claras.

### Exemplo 2: Demanda de Mapeamento
Briefing: "Quero saber onde os anestesistas de BH estão trabalhando"

Pensamento: Isso é pesquisa/mapeamento. Tenho 47 anestesistas de BH na base,
mas a info de "onde trabalha" não está estruturada. Vou precisar perguntar
para eles ou extrair do histórico de conversas. Não tenho campo específico
para isso - vou sugerir criar um.

### Exemplo 3: Demanda de Novo Território
Briefing: "Cliente novo de homecare em Hortolândia, precisamos de médicos"

Pensamento: Território e segmento novos. Não tenho base de Hortolândia,
não sei quais especialidades fazem homecare. Preciso de mais informações
do gestor antes de planejar. E vou precisar de contatos iniciais para
começar - não dá pra criar do zero sem uma "semente".

### Exemplo 4: Demanda de Expansão/Crawling
Briefing: "Pede indicação de colegas para os médicos que já responderam"

Pensamento: Posso fazer isso. Vou identificar quem respondeu positivamente,
e nas próximas interações vou perguntar se conhecem colegas. Preciso de
uma forma de rastrear "veio por indicação de quem" - não tenho esse campo.

### Exemplo 5: Demanda Impossível (ser honesta)
Briefing: "Fecha 50 vagas de cardiologia até amanhã"

Pensamento: Não temos base de cardiologistas. Mesmo se tivéssemos, 50 vagas
em 1 dia é impossível com nosso rate limit (20 msgs/hora). Preciso ser
honesta com o gestor sobre o que é viável.

---

## LEMBRE-SE

- Você é uma COLEGA, não um robô. Pense como pessoa.
- Se não souber algo, PERGUNTE. Não invente.
- Se algo for impossível, DIGA. Não prometa o que não pode cumprir.
- Se precisar de ferramenta nova, ESPECIFIQUE o que precisa e por quê.
- Seu plano vai ser REVISADO pelo gestor. Seja clara e honesta.
- O documento é sua MEMÓRIA. Use-o para registrar tudo.
```

## User Stories

### US-01: Interpretação de Texto Livre

**Como** Julia
**Quero** interpretar briefings escritos em linguagem natural
**Para** entender qualquer tipo de demanda sem depender de formato rígido

**Critérios de Aceite:**
- [ ] Extrai objetivo mesmo de textos não estruturados
- [ ] Identifica entidades (médicos, hospitais, datas, valores)
- [ ] Reconhece urgência e deadlines implícitos
- [ ] Diferencia instrução de contexto/justificativa

**Exemplos de entrada:**
```
"Essa semana foca no São Luiz"
"O São Luiz precisa fechar escala até sexta, dá prioridade pra eles"
"Sexta é deadline do São Luiz. Foca lá."
```
Todas devem resultar em: Hospital=São Luiz, Deadline=Sexta, Prioridade=Alta

---

### US-02: Classificação de Tipo de Demanda

**Como** Julia
**Quero** classificar automaticamente o tipo de demanda
**Para** ajustar minha abordagem de planejamento

**Critérios de Aceite:**
- [ ] Classifica corretamente: operacional, mapeamento, expansão, inteligência, novo território
- [ ] Identifica demandas mistas
- [ ] Adapta estrutura do plano ao tipo

---

### US-03: Avaliação de Capacidades

**Como** Julia
**Quero** avaliar o que tenho vs. o que preciso para a demanda
**Para** criar planos realistas e identificar gaps

**Critérios de Aceite:**
- [ ] Consulta dados disponíveis (contagem de médicos por filtro)
- [ ] Lista ferramentas necessárias vs. disponíveis
- [ ] Identifica dados faltantes de forma específica
- [ ] Sugere soluções alternativas quando algo falta

---

### US-04: Geração de Perguntas

**Como** Julia
**Quero** formular perguntas quando algo não está claro
**Para** obter informações necessárias antes de executar

**Critérios de Aceite:**
- [ ] Identifica ambiguidades no briefing
- [ ] Formula perguntas específicas e objetivas
- [ ] Oferece opções quando possível (facilita resposta)
- [ ] Explica por que a informação é necessária

---

### US-05: Identificação de Necessidades de Desenvolvimento

**Como** Julia
**Quero** identificar ferramentas/dados que seriam úteis mas não existem
**Para** gerar backlog orgânico de desenvolvimento

**Critérios de Aceite:**
- [ ] Descreve a necessidade de forma clara
- [ ] Explica o caso de uso (por que precisa)
- [ ] Sugere solução alternativa temporária (se houver)
- [ ] Prioriza por impacto na demanda atual

---

### US-06: Avaliação de Viabilidade

**Como** Julia
**Quero** avaliar honestamente se uma demanda é viável
**Para** não prometer o que não posso cumprir

**Critérios de Aceite:**
- [ ] Calcula se prazo é realista (considerando rate limits, base disponível)
- [ ] Identifica demandas impossíveis e explica por quê
- [ ] Sugere alternativas viáveis quando demanda original não é
- [ ] Expressa ressalvas de forma construtiva

---

## Tarefas Técnicas

### T01: Serviço de Análise de Briefing
```python
# app/services/briefing_analyzer.py

class BriefingAnalyzer:
    """Analisa briefings usando Sonnet e gera planos estruturados."""

    async def analisar(self, conteudo_briefing: str) -> AnaliseResult:
        """
        Analisa briefing e retorna plano estruturado.

        1. Chama Sonnet com o prompt de análise
        2. Parseia resposta em estrutura definida
        3. Enriquece com dados reais (contagens, etc)
        4. Retorna AnaliseResult
        """
        pass

    async def _enriquecer_com_dados(self, analise: dict) -> dict:
        """
        Adiciona dados reais à análise.
        Ex: "47 anestesistas de BH" -> consulta real no banco
        """
        pass

    async def _validar_plano(self, plano: dict) -> list[str]:
        """
        Valida se plano é executável.
        Retorna lista de warnings/erros.
        """
        pass
```

### T02: Estrutura de Dados da Análise
```python
# app/schemas/briefing.py

class TipoDemanda(str, Enum):
    OPERACIONAL = "operacional"
    MAPEAMENTO = "mapeamento"
    EXPANSAO = "expansao"
    INTELIGENCIA = "inteligencia"
    NOVO_TERRITORIO = "novo_territorio"
    MISTO = "misto"

class PassoPlano(BaseModel):
    numero: int
    descricao: str
    prazo: str | None
    requer_ajuda: bool
    tipo_ajuda: str | None  # "ferramenta", "dados", "decisao", "humano"

class NecessidadeIdentificada(BaseModel):
    tipo: str  # "ferramenta", "dados", "campo_banco"
    descricao: str
    caso_uso: str
    alternativa_temporaria: str | None
    prioridade: str  # "alta", "media", "baixa"

class AnaliseResult(BaseModel):
    # Entendimento
    resumo_demanda: str
    tipo_demanda: TipoDemanda
    deadline: str | None
    urgencia: str  # "alta", "media", "baixa"

    # Avaliação
    dados_disponiveis: list[str]
    dados_faltantes: list[str]
    ferramentas_necessarias: list[str]
    ferramentas_faltantes: list[str]

    # Perguntas
    perguntas_para_gestor: list[str]

    # Plano
    passos: list[PassoPlano]
    metricas_sucesso: list[str]
    riscos: list[str]

    # Necessidades
    necessidades: list[NecessidadeIdentificada]

    # Avaliação
    viavel: bool
    ressalvas: list[str]
    avaliacao_honesta: str
```

### T03: Prompt Template
```python
# app/prompts/briefing_analysis.py

PROMPT_ANALISE_BRIEFING = """
[Prompt completo como definido acima]

---

## BRIEFING DO GESTOR

{briefing_content}

---

## DADOS ATUAIS (para sua referência)

{dados_contexto}

---

Analise o briefing e crie seu plano seguindo a estrutura definida.
"""

def build_dados_contexto() -> str:
    """
    Monta string com dados atuais relevantes.
    Ex: contagem de médicos por especialidade, vagas abertas, etc.
    """
    pass
```

### T04: Integração com Consultas Reais
- [ ] Função para contar médicos por filtro
- [ ] Função para listar vagas abertas
- [ ] Função para buscar histórico relevante
- [ ] Cache de dados frequentes (evitar consultas repetidas)

### T05: Testes do Analisador
- [ ] Teste com briefing operacional simples
- [ ] Teste com briefing de mapeamento
- [ ] Teste com briefing de novo território
- [ ] Teste com briefing impossível (deve identificar)
- [ ] Teste com briefing ambíguo (deve fazer perguntas)
- [ ] Teste com briefing misto

---

## Considerações de Implementação

### Custo de Tokens

Cada análise usa Sonnet, que é mais caro. Mitigações:
- Só executa quando gestor pede explicitamente
- Cache de análises recentes
- Prompt otimizado (nem muito curto, nem verboso demais)

### Qualidade do Output

O output precisa ser parseável. Opções:
1. **Markdown estruturado** - mais natural, parsing mais complexo
2. **JSON** - parsing trivial, menos natural
3. **Híbrido** - Sonnet gera markdown, depois converte

Recomendação: Markdown estruturado com headers fixos para facilitar parsing.

### Enriquecimento com Dados Reais

A análise do Sonnet menciona "47 anestesistas de BH". Devemos:
1. Deixar número que Sonnet inventou? Não - pode estar errado
2. Substituir por consulta real? Sim - mais confiável
3. Fazer consultas ANTES e passar pro prompt? Melhor - Sonnet já trabalha com dados reais

### Iteração

O gestor pode pedir ajustes:
- "Adiciona o Dr. Carlos como prioridade"
- "O prazo na verdade é quinta, não sexta"

Julia deve conseguir atualizar o plano sem refazer toda a análise.

---

## Estimativa

| Tarefa | Horas |
|--------|-------|
| T01: Serviço de análise | 3h |
| T02: Estrutura de dados | 1h |
| T03: Prompt template | 2h |
| T04: Integração consultas | 2h |
| T05: Testes | 2h |
| **Total** | **10h** |
