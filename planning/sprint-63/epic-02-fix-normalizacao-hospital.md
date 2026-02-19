# EPICO 02: Fix Normalizacao Hospital

## Prioridade: P0 (Critico) — Bug de Producao

## Contexto

A funcao `normalizar_para_busca` em `normalizador.py:42` remove conteudo entre parenteses antes de qualquer processamento. Isso transforma "H. BENEDICTO MONTENEGRO (IVA)" em "h benedicto montenegro", que nao encontra match com o alias cadastrado "hospital benedicto montenegro".

Dois problemas combinados:
1. **Abreviacoes nao expandidas**: "H." nao e expandido para "hospital"
2. **Alias insuficientes**: DB tem "hospital benedicto montenegro" mas nao "h benedicto montenegro"

**Evidencia:** 4 de 7 vagas com hospital_id=null → descartadas. Alias no DB: `hospital benedicto montenegro`, `hospital municipal dr. benedicto montenegro`. Nenhum match para "h benedicto montenegro".

## Escopo

- **Incluido**: Expandir abreviacoes comuns no normalizador, adicionar alias faltantes
- **Excluido**: Refatorar hospital_web.py (epic separado), mudar logica de fuzzy match

---

## Tarefa 1: Expandir abreviacoes de hospital no normalizador

### Objetivo

Adicionar logica de expansao de abreviacoes comuns ANTES da busca por alias. "H." → "hospital", "HM." → "hospital municipal", "HR." → "hospital regional", etc.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/normalizador.py` |

### Implementacao

Adicionar funcao de expansao entre a normalizacao do texto e a busca de alias:

```python
# Abreviacoes comuns de hospitais
_ABREVIACOES_HOSPITAL = {
    "h": "hospital",
    "h.": "hospital",
    "hm": "hospital municipal",
    "hm.": "hospital municipal",
    "hr": "hospital regional",
    "hr.": "hospital regional",
    "he": "hospital estadual",
    "he.": "hospital estadual",
    "hge": "hospital geral estadual",
    "upa": "upa",  # UPA ja e nome proprio
    "ps": "pronto socorro",
    "ps.": "pronto socorro",
    "sta": "santa",
    "sta.": "santa",
    "sto": "santo",
    "sto.": "santo",
    "s.": "sao",
    "n.s.": "nossa senhora",
    "dr": "doutor",
    "dr.": "doutor",
    "dra": "doutora",
    "dra.": "doutora",
    "prof": "professor",
    "prof.": "professor",
}

def expandir_abreviacoes_hospital(texto: str) -> str:
    """Expande abreviacoes comuns em nomes de hospitais."""
    palavras = texto.split()
    resultado = []
    for palavra in palavras:
        expandida = _ABREVIACOES_HOSPITAL.get(palavra.lower(), palavra)
        resultado.append(expandida)
    return " ".join(resultado)
```

Chamar `expandir_abreviacoes_hospital` ANTES de `normalizar_para_busca` em `buscar_hospital_por_alias`.

### Testes Obrigatorios

**Unitarios:**
- [ ] "H. BENEDICTO MONTENEGRO" → "hospital benedicto montenegro"
- [ ] "HM Dr. Jose Silva" → "hospital municipal doutor jose silva"
- [ ] "UPA VERGUEIRO" → "upa vergueiro" (sem alteracao)
- [ ] "Santa Casa" → "santa casa" (sem alteracao, "santa" nao abreviado)
- [ ] "STA. CASA DE SAO PAULO" → "santa casa de sao paulo"
- [ ] Texto sem abreviacoes nao muda

### Definition of Done

- [ ] Funcao expandir_abreviacoes_hospital implementada
- [ ] Integrada no fluxo de busca de hospital
- [ ] Testes unitarios passando
- [ ] Testes de regressao (hospitais que ja funcionavam continuam)

### Estimativa

2 pontos

---

## Tarefa 2: Preservar conteudo de parenteses para contexto

### Objetivo

Avaliar se o conteudo entre parenteses deve ser preservado como campo separado em vez de descartado. Ex: "(IVA)" pode ser util para desambiguacao de unidades hospitalares.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/normalizador.py` |

### Implementacao

Opcao A (recomendada): Extrair conteudo dos parenteses ANTES de remover, usar como campo auxiliar na busca:

```python
def normalizar_para_busca(texto: str) -> str:
    # ... existente ...

def extrair_qualificador(texto: str) -> str | None:
    """Extrai texto entre parenteses como qualificador (ex: IVA, SEDE)."""
    match = re.search(r"\(([^)]+)\)", texto)
    return match.group(1).strip().lower() if match else None
```

Opcao B (minima): Manter strip de parenteses mas expandir abreviacoes ANTES do strip.

**Decisao:** Implementar Opcao A, usar qualificador apenas como logging/tracking por enquanto. Nao mudar logica de match.

### Testes Obrigatorios

**Unitarios:**
- [ ] extrair_qualificador("H. BENEDICTO MONTENEGRO (IVA)") == "iva"
- [ ] extrair_qualificador("Hospital Sao Paulo") == None
- [ ] extrair_qualificador("UPA (24h)") == "24h"

### Definition of Done

- [ ] Funcao extrair_qualificador implementada
- [ ] Qualificador logado para analise futura
- [ ] Testes passando

### Estimativa

1 ponto

---

## Tarefa 3: Adicionar aliases via migration

### Objetivo

Adicionar aliases comuns para hospitais que usam abreviacoes no nome do grupo.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | Migration Supabase `add_hospital_abbreviation_aliases` |

### Implementacao

```sql
-- Adicionar aliases para abreviacoes comuns
-- Nao duplicar aliases existentes (ON CONFLICT DO NOTHING)
INSERT INTO hospital_aliases (hospital_id, alias)
SELECT h.id, lower(regexp_replace(h.nome, '^Hospital ', 'H. ', 'i'))
FROM hospitais h
WHERE h.nome ILIKE 'Hospital %'
  AND NOT EXISTS (
    SELECT 1 FROM hospital_aliases ha
    WHERE ha.hospital_id = h.id
      AND ha.alias = lower(regexp_replace(h.nome, '^Hospital ', 'H. ', 'i'))
  );
```

### Testes Obrigatorios

- [ ] Migration e idempotente (rodar 2x nao cria duplicatas)
- [ ] "H. Benedicto Montenegro" encontrado apos migration

### Definition of Done

- [ ] Migration aplicada
- [ ] Aliases verificados no banco
- [ ] Testes de busca passando

### Estimativa

1 ponto
