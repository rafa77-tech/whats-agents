# Épico 03: Escrita no Documento

## Objetivo

Permitir que Julia escreva o plano de ação **no próprio documento de briefing**, criando um registro persistente e auditável.

## Por que Escrever no Documento?

| Abordagem | Prós | Contras |
|-----------|------|---------|
| Só Slack | Rápido, não precisa de escrita | Plano se perde, sem histórico |
| Banco de dados | Estruturado, fácil de consultar | Gestor não vê, precisa de dashboard |
| **No documento** | Visível pro gestor, audit trail natural | Precisa permissão escrita |

**Decisão:** Escrever no documento porque:
1. Gestor já está no Google Docs - não precisa ir a outro lugar
2. Histórico fica junto do briefing original
3. Serve como documentação da operação
4. Fácil de compartilhar com outros

## Estrutura do Documento

```markdown
# Nome do Briefing

## Briefing do Gestor
[Conteúdo original - NUNCA editado pela Julia]

Texto livre que o gestor escreveu...

---

## Plano da Julia
*Gerado em: 12/12/2025 14:30*
*Status: ó Aguardando aprovação*

### O que entendi
[Resumo da demanda]

### Avaliação
[O que tem vs. o que falta]

### Plano de ação
1. [Passo 1]
2. [Passo 2]
...

### Necessidades identificadas
[Ferramentas/dados que seriam úteis]

### Métricas de sucesso
[Como medir se deu certo]

---

## Histórico de Execução

| Data | Hora | Ação | Resultado |
|------|------|------|-----------|
| 12/12 | 14:30 | Plano criado | Aguardando aprovação |
```

## Regras de Escrita

### O que Julia PODE editar:
- `## Plano da Julia` - criar e atualizar
- `## Histórico de Execução` - adicionar linhas

### O que Julia NÃO edita:
- `## Briefing do Gestor` - conteúdo original intocado
- Qualquer texto antes do `---` separador

### Convenções:
- Status possíveis: `ó Aguardando aprovação`, ` Aprovado`, `= Em execução`, ` Concluído`
- Sempre adicionar timestamp
- Histórico em ordem cronológica (mais recente em baixo)

## User Stories

### US-01: Criar Seção de Plano

**Como** Julia
**Quero** criar a seção "## Plano da Julia" no documento
**Para** registrar minha análise e plano de ação

**Critérios de Aceite:**
- [ ] Adiciona separador `---` após briefing do gestor
- [ ] Cria seção com timestamp
- [ ] Estrutura padronizada (entendi, avaliação, plano, necessidades, métricas)
- [ ] Status inicial: `ó Aguardando aprovação`

---

### US-02: Atualizar Plano Existente

**Como** Julia
**Quero** atualizar um plano que já existe no documento
**Para** incorporar feedback do gestor ou mudanças

**Critérios de Aceite:**
- [ ] Substitui conteúdo da seção mantendo histórico
- [ ] Atualiza timestamp
- [ ] Mantém status conforme situação

---

### US-03: Criar Seção de Histórico

**Como** Julia
**Quero** criar/atualizar a seção de histórico
**Para** registrar todas as ações tomadas

**Critérios de Aceite:**
- [ ] Cria tabela se não existir
- [ ] Adiciona linha para cada evento
- [ ] Formato: Data | Hora | Ação | Resultado
- [ ] Limita a últimos 50 eventos (trunca antigos)

---

### US-04: Atualizar Status do Plano

**Como** Julia
**Quero** atualizar o status do plano
**Para** refletir onde estamos no fluxo

**Critérios de Aceite:**
- [ ] Muda linha de status no plano
- [ ] Adiciona entrada no histórico
- [ ] Status válidos: aguardando, aprovado, em execução, concluído

---

## Tarefas Técnicas

### T01: Serviço de Escrita em Documento
```python
# app/services/google_docs.py (expandir)

class GoogleDocsService:
    # ... métodos existentes ...

    async def escrever_plano(self, doc_id: str, plano: AnaliseResult) -> bool:
        """
        Escreve seção de plano no documento.

        1. Lê documento atual
        2. Encontra posição para inserir (após briefing, antes de plano existente)
        3. Formata plano em Markdown
        4. Insere/substitui seção
        """
        pass

    async def atualizar_status_plano(self, doc_id: str, novo_status: str) -> bool:
        """
        Atualiza linha de status no plano.
        """
        pass

    async def adicionar_historico(self, doc_id: str, acao: str, resultado: str) -> bool:
        """
        Adiciona linha na tabela de histórico.
        Cria tabela se não existir.
        """
        pass

    async def _encontrar_posicao_insercao(self, doc_content: str) -> int:
        """
        Encontra onde inserir nova seção.
        Após último parágrafo do briefing, antes de plano existente.
        """
        pass

    async def _formatar_plano_markdown(self, plano: AnaliseResult) -> str:
        """
        Converte AnaliseResult em Markdown formatado.
        """
        pass
```

### T02: Formatador de Plano
```python
# app/services/briefing_formatter.py

def formatar_plano_para_doc(plano: AnaliseResult) -> str:
    """
    Formata plano em Markdown para Google Docs.
    """
    linhas = []

    # Header
    linhas.append("---\n")
    linhas.append("## Plano da Julia")
    linhas.append(f"*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}*")
    linhas.append(f"*Status: ó Aguardando aprovação*\n")

    # O que entendi
    linhas.append("### O que entendi")
    linhas.append(plano.resumo_demanda)
    linhas.append("")

    # Avaliação
    linhas.append("### Avaliação")
    linhas.append(f"**Tipo de demanda:** {plano.tipo_demanda.value}")
    if plano.deadline:
        linhas.append(f"**Deadline:** {plano.deadline}")
    linhas.append("")

    linhas.append("**O que tenho:**")
    for item in plano.dados_disponiveis:
        linhas.append(f"- {item}")
    linhas.append("")

    if plano.dados_faltantes:
        linhas.append("**O que não tenho:**")
        for item in plano.dados_faltantes:
            linhas.append(f"- {item}")
        linhas.append("")

    # Perguntas
    if plano.perguntas_para_gestor:
        linhas.append("### Perguntas para você")
        for pergunta in plano.perguntas_para_gestor:
            linhas.append(f"- {pergunta}")
        linhas.append("")

    # Plano de ação
    linhas.append("### Plano de ação")
    for passo in plano.passos:
        status = "ó" if not passo.requer_ajuda else ">"
        prazo = f" (até {passo.prazo})" if passo.prazo else ""
        linhas.append(f"{passo.numero}. {status} {passo.descricao}{prazo}")
    linhas.append("")

    # Necessidades
    if plano.necessidades:
        linhas.append("### Necessidades identificadas")
        for nec in plano.necessidades:
            linhas.append(f"- **{nec.tipo}:** {nec.descricao}")
            linhas.append(f"  - Caso de uso: {nec.caso_uso}")
            if nec.alternativa_temporaria:
                linhas.append(f"  - Alternativa: {nec.alternativa_temporaria}")
        linhas.append("")

    # Métricas
    linhas.append("### Métricas de sucesso")
    for metrica in plano.metricas_sucesso:
        linhas.append(f"- [ ] {metrica}")
    linhas.append("")

    # Riscos
    if plano.riscos:
        linhas.append("### Riscos")
        for risco in plano.riscos:
            linhas.append(f"- {risco}")
        linhas.append("")

    # Avaliação honesta
    linhas.append("### Minha avaliação")
    linhas.append(plano.avaliacao_honesta)

    return "\n".join(linhas)


def formatar_linha_historico(acao: str, resultado: str) -> str:
    """Formata linha para tabela de histórico."""
    agora = datetime.now()
    return f"| {agora.strftime('%d/%m')} | {agora.strftime('%H:%M')} | {acao} | {resultado} |"
```

### T03: Google Docs API - Escrita
```python
# app/services/google_docs.py

async def _inserir_texto(self, doc_id: str, texto: str, posicao: int) -> bool:
    """
    Insere texto em posição específica do documento.
    Usa Google Docs API batchUpdate.
    """
    requests = [{
        'insertText': {
            'location': {'index': posicao},
            'text': texto
        }
    }]

    result = self.service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests}
    ).execute()

    return True


async def _substituir_secao(
    self, doc_id: str, titulo_secao: str, novo_conteudo: str
) -> bool:
    """
    Substitui conteúdo de uma seção (identificada pelo título).
    """
    # 1. Lê documento
    # 2. Encontra início e fim da seção
    # 3. Deleta conteúdo existente
    # 4. Insere novo conteúdo
    pass
```

### T04: Testes
- [ ] Teste criar plano em doc vazio
- [ ] Teste criar plano em doc com briefing
- [ ] Teste atualizar plano existente
- [ ] Teste criar histórico
- [ ] Teste adicionar linha ao histórico
- [ ] Teste truncar histórico (>50 linhas)
- [ ] Teste atualizar status

---

## Considerações

### Formatação no Google Docs

Google Docs API trabalha com índices de caracteres, não linhas.
Para inserir/substituir, precisamos:
1. Ler documento estruturado
2. Calcular posições corretas
3. Fazer operações em ordem reversa (para não invalidar índices)

### Conflitos de Edição

Se gestor estiver editando ao mesmo tempo:
- Nossa escrita pode sobrescrever edições
- Mitigação: Julia avisa antes de escrever ("Vou atualizar o doc agora")

### Limite de Tamanho

Google Docs tem limite de ~1MB por documento.
Histórico extenso pode crescer demais.
- Mitigação: Truncar histórico a 50 eventos
- Mover histórico antigo para documento de arquivo se necessário

---

## Estimativa

| Tarefa | Horas |
|--------|-------|
| T01: Serviço de escrita | 3h |
| T02: Formatador | 2h |
| T03: Google Docs API escrita | 2h |
| T04: Testes | 2h |
| **Total** | **9h** |
