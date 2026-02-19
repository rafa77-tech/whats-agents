# EPICO 06: Refatorar hospital_web.py

## Prioridade: P2 (Medio)

## Contexto

`normalizar_ou_criar_hospital` em `hospital_web.py:465` e uma god function de ~212 linhas com 7 responsabilidades:
1. Buscar hospital por alias
2. Buscar hospital por nome parcial
3. Buscar via Google Places API
4. Buscar via CNES (DataSUS)
5. Criar hospital novo
6. Criar aliases
7. Tracking de hospital_web_busca

Tem 5 blocos try/except aninhados, o que torna debugging e testes muito dificeis. O modulo inteiro tem 739 linhas com zero testes.

## Escopo

- **Incluido**: Quebrar god function em funcoes menores com responsabilidade unica
- **Excluido**: Mudar logica de negocio, adicionar novas fontes de busca

---

## Tarefa 1: Extrair funcoes de busca

### Objetivo

Separar cada estrategia de busca em funcao propria.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/hospital_web.py` |

### Implementacao

```python
async def _buscar_por_alias(nome_normalizado: str) -> UUID | None:
    """Busca hospital por alias exato."""
    ...

async def _buscar_por_nome_parcial(nome_normalizado: str) -> UUID | None:
    """Busca hospital por match parcial no nome."""
    ...

async def _buscar_via_google_places(nome_raw: str, cidade: str | None) -> dict | None:
    """Busca hospital via Google Places API."""
    ...

async def _buscar_via_cnes(nome_raw: str) -> dict | None:
    """Busca hospital via CNES/DataSUS."""
    ...

async def _criar_hospital(dados: dict) -> UUID:
    """Cria hospital novo no banco."""
    ...

async def normalizar_ou_criar_hospital(nome_raw: str, ...) -> UUID | None:
    """Orquestrador: tenta cada estrategia em cascata."""
    # 1. Alias
    hospital_id = await _buscar_por_alias(normalizar_para_busca(nome_raw))
    if hospital_id:
        return hospital_id

    # 2. Nome parcial
    hospital_id = await _buscar_por_nome_parcial(...)
    if hospital_id:
        return hospital_id

    # 3. Google Places
    dados = await _buscar_via_google_places(nome_raw, cidade)
    if dados:
        return await _criar_hospital(dados)

    # 4. CNES
    dados = await _buscar_via_cnes(nome_raw)
    if dados:
        return await _criar_hospital(dados)

    # 5. Criar com dados minimos
    return await _criar_hospital({"nome": nome_raw})
```

### Testes Obrigatorios

**Unitarios:**
- [ ] _buscar_por_alias encontra hospital existente
- [ ] _buscar_por_alias retorna None quando nao existe
- [ ] _buscar_por_nome_parcial faz match parcial
- [ ] _buscar_via_google_places retorna dados formatados
- [ ] _criar_hospital cria e retorna UUID
- [ ] normalizar_ou_criar_hospital tenta estrategias em cascata
- [ ] Falha em Google Places nao impede CNES

**Integracao:**
- [ ] Fluxo completo com hospital novo
- [ ] Fluxo completo com hospital existente

### Definition of Done

- [ ] God function < 30 linhas (orquestrador)
- [ ] Cada funcao < 50 linhas
- [ ] Zero try/except aninhados
- [ ] Testes unitarios para cada funcao
- [ ] Testes de integracao para fluxo completo

### Estimativa

5 pontos
