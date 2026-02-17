# EPICO 1: Gate de Validacao de Nomes

## Contexto

O pipeline de scraping de grupos WhatsApp cria hospitais automaticamente durante a normalizacao de vagas (`normalizar_ou_criar_hospital()` em `app/services/grupos/hospital_web.py`). Sem validacao, qualquer texto e aceito como nome de hospital, resultando em:

- Nomes de contatos: "amar: Queila ()-"
- Empresas nao-medicas: "AMAZON", "MERCADO ENVIOS", "ATACADAO"
- Especialidades: "GINECOLOGIA", "ORTOPEDIA"
- Fragmentos de anuncio: linhas com "R$", "VALOR BRUTO"
- Fragmentos truncados: palavras soltas com < 4 caracteres

**Objetivo:** Impedir que novos registros lixo sejam criados no banco.

## Escopo

- **Incluido:**
  - Criar validador com regras de rejeicao
  - Integrar no pipeline de normalizacao (hospital_web.py)
  - Integrar no extrator de hospitais (extrator_hospitais.py)
  - Testes unitarios cobrindo todos os padroes

- **Excluido:**
  - Limpeza de dados existentes (Epico 3)
  - Validacao semantica com LLM
  - Normalizacao de nomes (ex: acentos, abreviacoes)

---

## Tarefa 1.1: Criar `hospital_validator.py`

### Objetivo

Modulo com funcao `validar_nome_hospital(nome: str) -> ResultadoValidacao` que aplica regras de validacao e retorna se o nome e valido, com motivo de rejeicao.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `app/services/grupos/hospital_validator.py` |

### Implementacao

```python
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class ResultadoValidacao:
    valido: bool
    motivo: Optional[str] = None
    score: float = 0.0  # 0.0 = invalido, 1.0 = certamente hospital

# Regras de validacao
BLOCKLIST_PALAVRAS = {
    "hospedagem", "verificar", "nao informado", "a serem definidas",
    "inbox", "amazon", "mercado envios", "atacadao", "ypioca",
    "carrefour", "magazine luiza", "casas bahia", "mercado livre",
}

BLOCKLIST_REGEX = [
    r"\w+:\s*\w+\s*\(",       # Nomes de contato: "amar: Queila ()"
    r"R\$\s*[\d.,]+",          # Valores monetarios
    r"VALOR\s+BRUTO",          # Fragmentos de anuncio
    r"[\U0001F4B0\U0001F4B5]", # Emojis de dinheiro
]

PREFIXOS_HOSPITALARES = [
    "hospital", "hosp", "upa", "ubs", "ama", "santa casa",
    "pronto socorro", "ps ", "hm ", "hge", "hgp",
    "clinica", "instituto", "maternidade", "centro medico",
    "laboratorio", "samu", "cema", "hc ",
]

def validar_nome_hospital(nome: str) -> ResultadoValidacao:
    """Valida se um texto e um nome de hospital plausivel."""
    ...
```

**Regras (em ordem):**

1. **Minimo 3 chars** apos strip/normalize — rejeita fragmentos
2. **Deve conter pelo menos uma letra** — rejeita "123", "---"
3. **Maximo 120 chars** — rejeita textos longos/frases
4. **Blocklist de palavras** — match case-insensitive contra `BLOCKLIST_PALAVRAS`
5. **Blocklist de regex** — match contra `BLOCKLIST_REGEX`
6. **Especialidades como hospital** — checar contra lista de especialidades em `extrator_llm.py:ESPECIALIDADES_VALIDAS`
7. **Fragmentos truncados** — nome de 1 palavra com < 4 chars
8. **Heuristica positiva** — bonus se contem prefixo hospitalar

**Retorno:**
- `valido=True, score=0.8-1.0` — nome parece hospital
- `valido=True, score=0.3-0.7` — nome ambiguo, aceito com cautela
- `valido=False, motivo="..."` — rejeitado com motivo

### Testes Obrigatorios

**Unitarios:**
- [ ] Rejeita nomes < 3 chars ("AB", "", "  ")
- [ ] Rejeita nomes sem letras ("123", "---", "...")
- [ ] Rejeita nomes > 120 chars
- [ ] Rejeita padroes de contato ("amar: Queila ()-", "João: Maria (11)")
- [ ] Rejeita palavras blocklist ("AMAZON", "hospedagem", "inbox")
- [ ] Rejeita especialidades ("GINECOLOGIA", "ORTOPEDIA", "CARDIOLOGIA")
- [ ] Rejeita fragmentos monetarios ("R$ 2.500", "VALOR BRUTO R$1500")
- [ ] Rejeita fragmento de 1 palavra < 4 chars ("SP", "RJ")
- [ ] Aceita hospitais reais ("Hospital Sao Luiz", "UPA Santo Andre")
- [ ] Aceita com prefixo hospitalar (score alto)
- [ ] Aceita nomes ambiguos sem prefixo (score medio)

### Definition of Done

- [ ] Funcao `validar_nome_hospital()` implementada com todas as regras
- [ ] Tipo `ResultadoValidacao` com `valido`, `motivo`, `score`
- [ ] Blocklist extensivel (facil adicionar novas palavras)
- [ ] Log warning quando rejeita (para monitoramento)
- [ ] Testes unitarios passando

---

## Tarefa 1.2: Integrar validador em `hospital_web.py`

### Objetivo

Adicionar gate de validacao antes dos tiers 3 (criacao com web search) e 4 (criacao minima/fallback) de `normalizar_ou_criar_hospital()`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/hospital_web.py` (447 linhas) |

### Implementacao

Antes de chamar `criar_hospital()` ou `criar_hospital_minimo()`:

```python
from app.services.grupos.hospital_validator import validar_nome_hospital

async def normalizar_ou_criar_hospital(texto: str, regiao_grupo: str = ""):
    # ... tiers 1 e 2 (busca existente) ...

    # Gate de validacao ANTES de criar
    validacao = validar_nome_hospital(texto)
    if not validacao.valido:
        logger.warning(
            "Hospital rejeitado pelo validador",
            extra={"nome": texto, "motivo": validacao.motivo}
        )
        return None  # Vaga fica com hospital_id = NULL

    # ... tier 3 (web search) e tier 4 (fallback) ...
```

**Comportamento quando falha:**
- `normalizar_ou_criar_hospital()` retorna `None`
- Vaga fica com `hospital_id = NULL` para revisao posterior
- Log warning para monitoramento

### Testes Obrigatorios

**Unitarios:**
- [ ] `normalizar_ou_criar_hospital("AMAZON")` retorna `None`
- [ ] `normalizar_ou_criar_hospital("Hospital Sao Luiz")` continua funcionando
- [ ] `normalizar_ou_criar_hospital("amar: Queila ()-")` retorna `None`
- [ ] Log warning emitido quando rejeitado

**Integracao:**
- [ ] Fluxo completo: texto lixo -> validacao falha -> retorna None -> vaga sem hospital_id

### Definition of Done

- [ ] Gate inserido antes de `criar_hospital()` e `criar_hospital_minimo()`
- [ ] Retorna `None` quando validacao falha
- [ ] Log warning com nome e motivo
- [ ] Testes passando
- [ ] Tiers 1 e 2 (busca existente) nao afetados

---

## Tarefa 1.3: Integrar validador em `extrator_hospitais.py`

### Objetivo

Validar output de `_extrair_nome_hospital()` antes de retornar ao pipeline de extracao.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/extrator_v2/extrator_hospitais.py` (351 linhas) |

### Implementacao

```python
from app.services.grupos.hospital_validator import validar_nome_hospital

def _extrair_nome_hospital(texto: str) -> Tuple[str, float]:
    # ... logica existente de extracao ...

    nome_candidato = ...
    confianca = ...

    # Validar antes de retornar
    validacao = validar_nome_hospital(nome_candidato)
    if not validacao.valido:
        return ("", 0.0)

    # Ajustar confianca com score do validador
    confianca = min(confianca, validacao.score)
    return (nome_candidato, confianca)
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `_extrair_nome_hospital("AMAZON - entrega")` retorna `("", 0.0)`
- [ ] `_extrair_nome_hospital("Hospital Sao Luiz - Analia Franco")` retorna nome valido
- [ ] Confianca ajustada pelo score do validador

### Definition of Done

- [ ] Validacao apos extracao de nome
- [ ] Retorna `("", 0.0)` quando invalido
- [ ] Confianca ajustada pelo score
- [ ] Testes passando

---

## Tarefa 1.4: Criar testes de integracao

### Objetivo

Arquivo de testes dedicado cobrindo o validador e suas integracoes.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `tests/grupos/test_hospital_validator.py` |

### Testes

```python
class TestValidarNomeHospital:
    """Testes unitarios do validador."""
    # ... todos os casos da Tarefa 1.1 ...

class TestValidadorIntegracaoHospitalWeb:
    """Testes de integracao com hospital_web.py."""
    # ... casos da Tarefa 1.2 ...

class TestValidadorIntegracaoExtrator:
    """Testes de integracao com extrator_hospitais.py."""
    # ... casos da Tarefa 1.3 ...
```

### Definition of Done

- [ ] Todos os testes das tarefas 1.1, 1.2, 1.3 em arquivo dedicado
- [ ] `uv run pytest tests/grupos/test_hospital_validator.py` passando
- [ ] Cobertura: todos os padroes de rejeicao testados
- [ ] Pelo menos 5 exemplos de hospitais reais que devem ser aceitos

---

## Dependencias

Nenhuma — este e o primeiro epico a ser implementado.

## Risco: BAIXO

Falsos positivos vao para fila de revisao (hospital_id = NULL), nao perdem dados. Facilmente ajustavel adicionando/removendo regras.
