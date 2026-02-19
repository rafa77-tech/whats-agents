# EPICO 07: Constantes e Enums

## Prioridade: P3 (Baixo)

## Contexto

O pipeline de grupos tem magic numbers espalhados e string literals onde deveria usar enums. Apos os epicos anteriores limparem a base, este epic consolida constantes.

## Escopo

- **Incluido**: Mover magic numbers para GruposConfig, substituir strings por enums
- **Excluido**: Criar novos enums de dominio, mudar logica de negocio

---

## Tarefa 1: Mover magic numbers para GruposConfig

### Objetivo

Centralizar constantes magicas em `GruposConfig`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/core/config.py` (GruposConfig) |
| Modificar | `app/services/grupos/importador.py` |
| Modificar | `app/services/grupos/pipeline_worker.py` |

### Implementacao

Constantes identificadas:
- `importador.py:99` — `100 <= valor <= 10000` (faixa de valor de plantao)
- `importador.py:181` — `timedelta(days=90)` (janela de data futura)
- `importador.py` — `timedelta(days=1)` (margem para data passada)

```python
# Em GruposConfig:
VALOR_PLANTAO_MIN: int = 100
VALOR_PLANTAO_MAX: int = 10000
JANELA_DATA_FUTURA_DIAS: int = 90
MARGEM_DATA_PASSADA_DIAS: int = 1
```

### Testes Obrigatorios

- [ ] Valores usados no importador vem de GruposConfig
- [ ] Testes existentes do importador continuam passando

### Definition of Done

- [ ] Zero magic numbers no importador
- [ ] Constantes em GruposConfig
- [ ] Testes passando

### Estimativa

1 ponto

---

## Tarefa 2: Substituir string literals no mapeamento de acoes

### Objetivo

`mapear_acao_para_estagio` em `pipeline_worker.py` usa strings ("classificar", "extrair", etc.) que deveriam ser um Enum.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/pipeline_worker.py` |

### Implementacao

```python
class AcaoPipeline(str, Enum):
    CLASSIFICAR = "classificar"
    EXTRAIR = "extrair"
    NORMALIZAR = "normalizar"
    DEDUPLICAR = "deduplicar"
    IMPORTAR = "importar"
    FINALIZAR = "finalizar"
    DESCARTAR = "descartar"
    ERRO = "erro"
```

Atualizar `ResultadoPipeline.acao` e `mapear_acao_para_estagio` para usar o enum.

### Testes Obrigatorios

- [ ] Mapeamento de acoes funciona com enum
- [ ] Testes existentes passando (enum tem mesmo .value)
- [ ] Comparacao de strings "classificar" == AcaoPipeline.CLASSIFICAR funciona (str Enum)

### Definition of Done

- [ ] Enum AcaoPipeline criado
- [ ] Zero strings magicas de acao no pipeline
- [ ] Testes passando
- [ ] Backward compatible (str Enum)

### Estimativa

2 pontos

---

## Tarefa 3: Criar helper generico de normalizacao por mapa

### Objetivo

`normalizador.py` tem 4 funcoes de normalizacao identicas (hospital, especialidade, periodo, tipo_vaga) que so diferem no mapa de alias. Extrair helper generico.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/normalizador.py` |

### Implementacao

```python
async def _normalizar_por_mapa(
    texto_raw: str,
    tabela: str,
    tabela_alias: str,
    campo_busca: str = "nome",
) -> ResultadoMatch:
    """Busca entidade no banco por alias ou match parcial."""
    normalizado = normalizar_para_busca(texto_raw)
    # ... logica generica de busca ...
```

Refatorar `buscar_hospital_por_alias`, `buscar_especialidade_por_alias`, etc. para usar o helper.

### Testes Obrigatorios

- [ ] Helper funciona para hospitais
- [ ] Helper funciona para especialidades
- [ ] Helper funciona para periodos
- [ ] Funcoes especificas sao wrappers finos

### Definition of Done

- [ ] Zero duplicacao de logica de busca
- [ ] Funcoes especificas delegam para helper
- [ ] Testes passando

### Estimativa

3 pontos
