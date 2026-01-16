# E11 - Julia Aprende com Gestor

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 3 - Interação Gestor
**Dependências:** E08 (Canal de Ajuda), E13 (Conhecimento Hospitais)
**Estimativa:** 3h

---

## Objetivo

Implementar sistema que permite Julia **aprender** com as respostas do gestor. Quando o gestor responde uma dúvida sobre hospital/vaga, Julia extrai o conhecimento e salva para uso futuro.

---

## Problema

Atualmente, quando Julia não sabe algo:
1. Pergunta ao gestor
2. Gestor responde
3. Julia responde ao médico
4. **Conhecimento perdido** - próxima vez Julia pergunta de novo

**Exemplo do problema:**
```
Dia 1:
  Médico A: "Hospital X tem estacionamento?"
  Julia: [pergunta ao gestor]
  Gestor: "Sim, tem estacionamento gratuito"
  Julia: "Tem sim! Estacionamento gratuito"

Dia 2:
  Médico B: "Hospital X tem estacionamento?"
  Julia: [pergunta ao gestor DE NOVO]  ← Ineficiente
```

---

## Solução

Julia extrai conhecimento da resposta do gestor e salva na tabela `conhecimento_hospitais`. Na próxima vez, consulta a tabela antes de perguntar.

```
FLUXO NOVO:

1. Médico pergunta algo sobre hospital
2. Julia consulta conhecimento_hospitais
3. Se encontrar → responde direto
4. Se não encontrar → pergunta ao gestor
5. Gestor responde
6. Julia EXTRAI conhecimento da resposta
7. Julia SALVA em conhecimento_hospitais
8. Julia responde ao médico
9. Próxima vez → passo 3 já encontra
```

---

## Tasks

### T1: Criar extrator de conhecimento (1h)

Serviço que usa LLM para extrair conhecimento estruturado da resposta do gestor.

**Arquivo:** `app/services/conhecimento/extrator.py`

```python
"""
Extrator de conhecimento das respostas do gestor.
"""
import json
from dataclasses import dataclass
from app.services.llm import chamar_llm
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConhecimentoExtraido:
    """Conhecimento extraído de uma resposta."""
    hospital_id: str | None
    atributo: str
    valor: str
    confianca: float  # 0.0 a 1.0


PROMPT_EXTRATOR = """Você é um extrator de conhecimento. Analise a conversa e extraia informações factuais sobre hospitais.

CONTEXTO DA PERGUNTA:
{contexto_pergunta}

RESPOSTA DO GESTOR:
{resposta_gestor}

HOSPITAL MENCIONADO (se identificado):
{hospital_nome}

Extraia APENAS informações factuais objetivas. Exemplos:
- Tem estacionamento: sim/não
- Refeição inclusa: sim/não
- Horário de entrada: específico
- Vestiário disponível: sim/não

Responda em JSON:
{
    "atributo": "nome do atributo em snake_case",
    "valor": "valor extraído",
    "confianca": 0.0 a 1.0,
    "eh_factual": true/false
}

Se não conseguir extrair conhecimento factual, retorne:
{
    "atributo": null,
    "valor": null,
    "confianca": 0.0,
    "eh_factual": false
}
"""


async def extrair_conhecimento(
    contexto_pergunta: str,
    resposta_gestor: str,
    hospital_nome: str | None = None,
    hospital_id: str | None = None
) -> ConhecimentoExtraido | None:
    """
    Extrai conhecimento estruturado da resposta do gestor.

    Args:
        contexto_pergunta: Pergunta original do médico ou contexto
        resposta_gestor: Resposta do gestor no Slack
        hospital_nome: Nome do hospital (se identificado)
        hospital_id: ID do hospital (se identificado)

    Returns:
        ConhecimentoExtraido ou None se não conseguir extrair
    """
    prompt = PROMPT_EXTRATOR.format(
        contexto_pergunta=contexto_pergunta,
        resposta_gestor=resposta_gestor,
        hospital_nome=hospital_nome or "Não identificado"
    )

    try:
        resposta = await chamar_llm(
            prompt=prompt,
            modelo="haiku",  # Rápido e barato para extração
            json_mode=True
        )

        dados = json.loads(resposta)

        if not dados.get("eh_factual") or not dados.get("atributo"):
            logger.debug(f"Resposta não contém conhecimento factual: {resposta_gestor[:100]}")
            return None

        return ConhecimentoExtraido(
            hospital_id=hospital_id,
            atributo=dados["atributo"],
            valor=dados["valor"],
            confianca=dados.get("confianca", 0.8)
        )

    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao parsear JSON do extrator: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao extrair conhecimento: {e}")
        return None


# Mapeamento de perguntas comuns para atributos
MAPEAMENTO_ATRIBUTOS = {
    "estacionamento": ["estacionamento", "estacionar", "carro", "vaga carro"],
    "refeicao": ["refeição", "refeicao", "comida", "almoço", "jantar", "refeitório"],
    "vestiario": ["vestiário", "vestiario", "trocar roupa", "armário"],
    "wifi": ["wifi", "internet", "wi-fi"],
    "ar_condicionado": ["ar condicionado", "ar-condicionado", "climatizado"],
    "cafe": ["café", "cafe", "copa"],
    "descanso": ["descanso", "dormir", "repouso", "sala de descanso"],
    "plantao_anterior": ["plantão anterior", "médico anterior", "quem fez antes"],
}


def identificar_atributo_pergunta(pergunta: str) -> str | None:
    """
    Identifica o atributo sendo perguntado baseado em palavras-chave.

    Args:
        pergunta: Texto da pergunta do médico

    Returns:
        Nome do atributo ou None
    """
    pergunta_lower = pergunta.lower()

    for atributo, palavras_chave in MAPEAMENTO_ATRIBUTOS.items():
        for palavra in palavras_chave:
            if palavra in pergunta_lower:
                return atributo

    return None
```

---

### T2: Criar repositório de conhecimento (45min)

Funções para salvar e buscar conhecimento.

**Arquivo:** `app/services/conhecimento/repositorio.py`

```python
"""
Repositório para conhecimento de hospitais.
"""
from datetime import datetime
from app.services.supabase import supabase
from app.core.logging import get_logger

logger = get_logger(__name__)


async def salvar_conhecimento(
    hospital_id: str,
    atributo: str,
    valor: str,
    fonte: str = "gestor",
    criado_por: str | None = None
) -> dict | None:
    """
    Salva ou atualiza conhecimento sobre hospital.

    Usa UPSERT - se já existe, atualiza.

    Args:
        hospital_id: ID do hospital
        atributo: Nome do atributo (estacionamento, refeicao, etc.)
        valor: Valor do atributo
        fonte: Origem da informação (gestor, medico, sistema)
        criado_por: ID de quem informou

    Returns:
        Registro salvo ou None em caso de erro
    """
    try:
        dados = {
            "hospital_id": hospital_id,
            "atributo": atributo,
            "valor": valor,
            "fonte": fonte,
            "criado_por": criado_por,
            "updated_at": datetime.utcnow().isoformat()
        }

        resultado = supabase.table("conhecimento_hospitais").upsert(
            dados,
            on_conflict="hospital_id,atributo"
        ).execute()

        if resultado.data:
            logger.info(
                f"Conhecimento salvo: hospital={hospital_id}, "
                f"atributo={atributo}, valor={valor}"
            )
            return resultado.data[0]

        return None

    except Exception as e:
        logger.error(f"Erro ao salvar conhecimento: {e}")
        return None


async def buscar_conhecimento(
    hospital_id: str,
    atributo: str | None = None
) -> list[dict]:
    """
    Busca conhecimento sobre hospital.

    Args:
        hospital_id: ID do hospital
        atributo: Atributo específico (opcional)

    Returns:
        Lista de conhecimentos encontrados
    """
    try:
        query = supabase.table("conhecimento_hospitais").select("*").eq(
            "hospital_id", hospital_id
        )

        if atributo:
            query = query.eq("atributo", atributo)

        resultado = query.execute()
        return resultado.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar conhecimento: {e}")
        return []


async def buscar_conhecimento_por_atributo(atributo: str) -> list[dict]:
    """
    Busca todos os hospitais que têm determinado atributo.

    Útil para perguntas como "quais hospitais têm estacionamento?"

    Args:
        atributo: Nome do atributo

    Returns:
        Lista de conhecimentos com hospital_id
    """
    try:
        resultado = supabase.table("conhecimento_hospitais").select(
            "*, hospitais(nome)"
        ).eq("atributo", atributo).execute()

        return resultado.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar por atributo: {e}")
        return []


async def formatar_conhecimento_para_prompt(hospital_id: str) -> str:
    """
    Formata conhecimento do hospital para injetar no prompt.

    Args:
        hospital_id: ID do hospital

    Returns:
        String formatada para prompt
    """
    conhecimentos = await buscar_conhecimento(hospital_id)

    if not conhecimentos:
        return ""

    linhas = ["INFORMAÇÕES CONHECIDAS SOBRE O HOSPITAL:"]

    for c in conhecimentos:
        linhas.append(f"- {c['atributo'].replace('_', ' ').title()}: {c['valor']}")

    return "\n".join(linhas)
```

---

### T3: Integrar com fluxo de ajuda (45min)

Quando gestor responde uma dúvida, extrair e salvar conhecimento automaticamente.

**Arquivo:** `app/services/slack/ajuda_handler.py` (modificar)

```python
# Adicionar import
from app.services.conhecimento.extrator import extrair_conhecimento
from app.services.conhecimento.repositorio import salvar_conhecimento


async def processar_resposta_gestor(
    pedido_id: str,
    resposta_gestor: str,
    gestor_id: str
) -> dict:
    """
    Processa resposta do gestor a um pedido de ajuda.

    Args:
        pedido_id: ID do pedido de ajuda
        resposta_gestor: Texto da resposta
        gestor_id: ID do gestor que respondeu

    Returns:
        Resultado do processamento
    """
    # 1. Buscar pedido original
    pedido = await buscar_pedido_ajuda(pedido_id)

    if not pedido:
        return {"sucesso": False, "erro": "Pedido não encontrado"}

    # 2. Atualizar status do pedido
    await atualizar_pedido_ajuda(
        pedido_id=pedido_id,
        status="respondido",
        resposta=resposta_gestor,
        respondido_por=gestor_id,
        respondido_em=datetime.utcnow()
    )

    # 3. NOVO: Tentar extrair e salvar conhecimento
    if pedido.get("hospital_id"):
        await _tentar_salvar_conhecimento(
            pedido=pedido,
            resposta_gestor=resposta_gestor,
            gestor_id=gestor_id
        )

    # 4. Retomar conversa com médico
    await retomar_conversa(
        conversa_id=pedido["conversa_id"],
        resposta_para_medico=resposta_gestor
    )

    return {"sucesso": True}


async def _tentar_salvar_conhecimento(
    pedido: dict,
    resposta_gestor: str,
    gestor_id: str
) -> None:
    """
    Tenta extrair e salvar conhecimento da resposta.

    Não falha silenciosamente - é um bonus, não obrigatório.
    """
    try:
        conhecimento = await extrair_conhecimento(
            contexto_pergunta=pedido.get("pergunta_original", ""),
            resposta_gestor=resposta_gestor,
            hospital_nome=pedido.get("hospital_nome"),
            hospital_id=pedido.get("hospital_id")
        )

        if conhecimento and conhecimento.confianca >= 0.7:
            await salvar_conhecimento(
                hospital_id=conhecimento.hospital_id,
                atributo=conhecimento.atributo,
                valor=conhecimento.valor,
                fonte="gestor",
                criado_por=gestor_id
            )

            logger.info(
                f"Conhecimento aprendido: {conhecimento.atributo}="
                f"{conhecimento.valor} (hospital={conhecimento.hospital_id})"
            )

    except Exception as e:
        # Não falha o fluxo principal
        logger.warning(f"Não foi possível extrair conhecimento: {e}")
```

---

### T4: Consultar conhecimento antes de perguntar (30min)

Julia deve consultar conhecimento existente antes de pedir ajuda ao gestor.

**Arquivo:** `app/services/julia/respondedor.py` (modificar)

```python
# Adicionar import
from app.services.conhecimento.repositorio import (
    buscar_conhecimento,
    formatar_conhecimento_para_prompt
)
from app.services.conhecimento.extrator import identificar_atributo_pergunta


async def verificar_conhecimento_antes_de_perguntar(
    mensagem_medico: str,
    hospital_id: str | None
) -> str | None:
    """
    Verifica se já temos conhecimento para responder a pergunta.

    Args:
        mensagem_medico: Mensagem do médico
        hospital_id: ID do hospital em contexto (se houver)

    Returns:
        Resposta baseada em conhecimento ou None se não souber
    """
    if not hospital_id:
        return None

    # Identificar que tipo de informação está sendo pedida
    atributo = identificar_atributo_pergunta(mensagem_medico)

    if not atributo:
        return None

    # Buscar conhecimento
    conhecimentos = await buscar_conhecimento(hospital_id, atributo)

    if conhecimentos:
        conhecimento = conhecimentos[0]
        logger.info(
            f"Conhecimento encontrado para {atributo}: {conhecimento['valor']}"
        )
        return conhecimento["valor"]

    return None


# No fluxo principal de resposta, antes de pedir ajuda:
async def processar_pergunta_factual(
    mensagem: str,
    contexto: dict
) -> dict:
    """
    Processa pergunta que pode precisar de conhecimento factual.
    """
    hospital_id = contexto.get("hospital_id")

    # 1. Verificar se já sabemos a resposta
    resposta_conhecida = await verificar_conhecimento_antes_de_perguntar(
        mensagem_medico=mensagem,
        hospital_id=hospital_id
    )

    if resposta_conhecida:
        # Já sabemos! Responder diretamente
        return {
            "acao": "responder",
            "resposta": resposta_conhecida,
            "fonte": "conhecimento_hospitais"
        }

    # 2. Não sabemos - pedir ajuda ao gestor
    return {
        "acao": "pedir_ajuda",
        "pergunta": mensagem,
        "hospital_id": hospital_id
    }
```

---

### T5: Injetar conhecimento no prompt (30min)

Incluir conhecimento do hospital no prompt quando relevante.

**Arquivo:** `app/prompts/builder.py` (modificar)

```python
# Adicionar import
from app.services.conhecimento.repositorio import formatar_conhecimento_para_prompt


async def construir_prompt_julia(
    # ... parâmetros existentes ...
    hospital_id: str | None = None,  # Adicionar parâmetro
) -> str:
    """
    Constrói prompt da Julia com contexto.
    """
    partes = []

    # ... código existente ...

    # NOVO: Adicionar conhecimento do hospital
    if hospital_id:
        conhecimento_hospital = await formatar_conhecimento_para_prompt(hospital_id)
        if conhecimento_hospital:
            partes.append(conhecimento_hospital)

    # ... resto do código ...

    return "\n\n".join(partes)
```

---

### T6: Criar testes (30min)

**Arquivo:** `tests/conhecimento/test_extrator.py`

```python
"""
Testes para extrator de conhecimento.
"""
import pytest
from app.services.conhecimento.extrator import (
    extrair_conhecimento,
    identificar_atributo_pergunta
)


class TestIdentificarAtributo:
    """Testes para identificação de atributos."""

    def test_identifica_estacionamento(self):
        assert identificar_atributo_pergunta("tem estacionamento?") == "estacionamento"
        assert identificar_atributo_pergunta("posso ir de carro?") == "estacionamento"
        assert identificar_atributo_pergunta("tem vaga pra carro?") == "estacionamento"

    def test_identifica_refeicao(self):
        assert identificar_atributo_pergunta("tem refeição inclusa?") == "refeicao"
        assert identificar_atributo_pergunta("onde almoço?") == "refeicao"
        assert identificar_atributo_pergunta("tem refeitório?") == "refeicao"

    def test_identifica_vestiario(self):
        assert identificar_atributo_pergunta("tem vestiário?") == "vestiario"
        assert identificar_atributo_pergunta("onde troco de roupa?") == "vestiario"

    def test_nao_identifica_pergunta_generica(self):
        assert identificar_atributo_pergunta("como é o hospital?") is None
        assert identificar_atributo_pergunta("é bom trabalhar lá?") is None


class TestExtrairConhecimento:
    """Testes para extração de conhecimento."""

    @pytest.mark.asyncio
    async def test_extrai_estacionamento_positivo(self, mock_llm):
        mock_llm.return_value = '{"atributo": "estacionamento", "valor": "Sim, gratuito", "confianca": 0.9, "eh_factual": true}'

        resultado = await extrair_conhecimento(
            contexto_pergunta="Tem estacionamento?",
            resposta_gestor="Sim, tem estacionamento gratuito no subsolo",
            hospital_nome="Hospital São Luiz"
        )

        assert resultado is not None
        assert resultado.atributo == "estacionamento"
        assert "gratuito" in resultado.valor.lower()
        assert resultado.confianca >= 0.7

    @pytest.mark.asyncio
    async def test_nao_extrai_opiniao(self, mock_llm):
        mock_llm.return_value = '{"atributo": null, "valor": null, "confianca": 0.0, "eh_factual": false}'

        resultado = await extrair_conhecimento(
            contexto_pergunta="O hospital é bom?",
            resposta_gestor="Sim, é um ótimo hospital, recomendo muito",
            hospital_nome="Hospital São Luiz"
        )

        assert resultado is None  # Opinião não é conhecimento factual


class TestRepositorio:
    """Testes para repositório de conhecimento."""

    @pytest.mark.asyncio
    async def test_salvar_e_buscar(self, supabase_mock):
        from app.services.conhecimento.repositorio import (
            salvar_conhecimento,
            buscar_conhecimento
        )

        # Salvar
        await salvar_conhecimento(
            hospital_id="hospital-123",
            atributo="estacionamento",
            valor="Sim, gratuito",
            fonte="gestor",
            criado_por="gestor-456"
        )

        # Buscar
        resultado = await buscar_conhecimento(
            hospital_id="hospital-123",
            atributo="estacionamento"
        )

        assert len(resultado) == 1
        assert resultado[0]["valor"] == "Sim, gratuito"

    @pytest.mark.asyncio
    async def test_upsert_atualiza_existente(self, supabase_mock):
        from app.services.conhecimento.repositorio import (
            salvar_conhecimento,
            buscar_conhecimento
        )

        # Salvar primeira vez
        await salvar_conhecimento(
            hospital_id="hospital-123",
            atributo="estacionamento",
            valor="Sim",
            fonte="gestor"
        )

        # Salvar segunda vez (mesmo hospital + atributo)
        await salvar_conhecimento(
            hospital_id="hospital-123",
            atributo="estacionamento",
            valor="Sim, gratuito no subsolo",
            fonte="gestor"
        )

        # Deve ter apenas 1 registro (atualizado)
        resultado = await buscar_conhecimento(
            hospital_id="hospital-123",
            atributo="estacionamento"
        )

        assert len(resultado) == 1
        assert resultado[0]["valor"] == "Sim, gratuito no subsolo"
```

---

## Migration

A migration para `conhecimento_hospitais` está no E13. Este épico assume que a tabela já existe.

Se implementar E11 antes de E13, criar migration mínima:

```sql
-- Migration: criar_conhecimento_hospitais_basico
-- Versão simplificada para E11

CREATE TABLE IF NOT EXISTS conhecimento_hospitais (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitais(id),
    atributo TEXT NOT NULL,
    valor TEXT NOT NULL,
    fonte TEXT NOT NULL DEFAULT 'gestor',
    criado_por TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(hospital_id, atributo)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_conhecimento_hospital ON conhecimento_hospitais(hospital_id);
CREATE INDEX IF NOT EXISTS idx_conhecimento_atributo ON conhecimento_hospitais(atributo);

-- Comentários
COMMENT ON TABLE conhecimento_hospitais IS 'Conhecimento aprendido sobre hospitais';
COMMENT ON COLUMN conhecimento_hospitais.atributo IS 'estacionamento, refeicao, vestiario, etc.';
COMMENT ON COLUMN conhecimento_hospitais.fonte IS 'gestor, medico, ou sistema';
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Extrator identifica conhecimento factual em respostas do gestor
- [ ] Conhecimento é salvo com UPSERT (atualiza se já existe)
- [ ] Julia consulta conhecimento antes de pedir ajuda
- [ ] Conhecimento é injetado no prompt quando relevante
- [ ] Perguntas repetidas sobre mesmo hospital são respondidas sem gestor

### Testes
- [ ] `test_extrator.py` - Identificação de atributos
- [ ] `test_extrator.py` - Extração com mock de LLM
- [ ] `test_repositorio.py` - CRUD de conhecimento
- [ ] `test_integracao.py` - Fluxo completo (pergunta → salva → consulta)

### Qualidade
- [ ] Confiança mínima de 0.7 para salvar conhecimento
- [ ] Opinões não são salvas como conhecimento
- [ ] Log quando conhecimento é aprendido
- [ ] Log quando conhecimento é usado para responder

### Verificação Manual

1. **Simular pergunta nova:**
   ```
   Médico: "Hospital X tem estacionamento?"
   Julia: [Não sabe] → Pergunta ao gestor
   Gestor: "Sim, tem estacionamento gratuito"
   Julia: "Tem sim! Estacionamento gratuito"
   ```

2. **Verificar que foi salvo:**
   ```sql
   SELECT * FROM conhecimento_hospitais
   WHERE hospital_id = 'ID_DO_HOSPITAL'
   AND atributo = 'estacionamento';
   ```

3. **Simular mesma pergunta com outro médico:**
   ```
   Médico B: "Esse hospital tem onde estacionar?"
   Julia: "Tem sim! Estacionamento gratuito" ← Responde direto
   ```
   Verificar que Julia NÃO perguntou ao gestor novamente.

---

## Notas para Dev

1. **Threshold de confiança:** Começar com 0.7 e ajustar baseado em qualidade das extrações
2. **Atributos fixos:** Usar mapeamento de atributos para consistência (não deixar LLM inventar)
3. **Fonte da informação:** Sempre registrar se veio de gestor, médico ou sistema
4. **Conflitos:** Se médico e gestor informarem valores diferentes, gestor prevalece
5. **Performance:** Conhecimento é consultado em toda conversa - manter queries leves

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Perguntas respondidas sem gestor | > 50% após 1 mês |
| Conhecimentos salvos por semana | > 10 |
| Taxa de extração bem-sucedida | > 70% |
| Precisão do conhecimento | > 95% |
