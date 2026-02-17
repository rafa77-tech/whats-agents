# EPICO 3: Integracao no Pipeline

## Contexto

O pipeline atual em `normalizar_ou_criar_hospital()` (`app/services/grupos/hospital_web.py`) segue: alias -> similaridade -> validador -> LLM Haiku -> fallback. Os novos servicos CNES e Google Places devem ser inseridos entre o validador e o LLM, priorizando dados reais sobre conhecimento estatico.

**Objetivo:** Inserir CNES e Google Places no fluxo de `normalizar_ou_criar_hospital()` e atualizar `InfoHospitalWeb` e `criar_hospital()` para suportar os novos campos.

## Escopo

- **Incluido:**
  - Adicionar campos `cnes_codigo` e `google_place_id` ao dataclass `InfoHospitalWeb`
  - Inserir steps 4 (CNES) e 5 (Google) no fluxo
  - Helpers de conversao `cnes_to_info_web()` e `google_to_info_web()`
  - Atualizar `criar_hospital()` para salvar novos campos
  - Atualizar RPC `buscar_ou_criar_hospital` para aceitar novos campos

- **Excluido:**
  - Modificar logica de alias ou similaridade (steps 1-2)
  - Modificar validador (step 3)
  - Remover busca LLM (step 6 continua como fallback)

---

## Tarefa 3.1: Atualizar InfoHospitalWeb e criar_hospital()

### Objetivo

Adicionar campos de CNES e Google Places ao dataclass e garantir que `criar_hospital()` os persista.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/hospital_web.py` (~15 linhas) |

### Implementacao

**InfoHospitalWeb — adicionar campos:**

```python
@dataclass
class InfoHospitalWeb:
    nome_oficial: str
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    confianca: float = 0.0
    fonte: Optional[str] = None
    # Sprint 61
    cnes_codigo: Optional[str] = None
    google_place_id: Optional[str] = None
    telefone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
```

**criar_hospital() — atualizar para salvar novos campos:**

Apos a criacao via RPC, se `info.cnes_codigo` ou `info.google_place_id` nao for None, fazer UPDATE:

```python
# Apos criacao/reutilizacao
if row["out_foi_criado"] and (info.cnes_codigo or info.google_place_id or info.telefone):
    updates = {}
    if info.cnes_codigo:
        updates["cnes_codigo"] = info.cnes_codigo
    if info.google_place_id:
        updates["google_place_id"] = info.google_place_id
    if info.telefone:
        updates["telefone"] = info.telefone
    if info.latitude is not None:
        updates["latitude"] = info.latitude
    if info.longitude is not None:
        updates["longitude"] = info.longitude
    if updates:
        from datetime import datetime, UTC
        updates["enriched_at"] = datetime.now(UTC).isoformat()
        updates["enriched_by"] = info.fonte or "pipeline"
        supabase.table("hospitais").update(updates).eq("id", str(hospital_id)).execute()
```

### Definition of Done

- [ ] `InfoHospitalWeb` tem campos `cnes_codigo`, `google_place_id`, `telefone`, `latitude`, `longitude`
- [ ] `criar_hospital()` persiste novos campos quando presentes

---

## Tarefa 3.2: Helpers de Conversao

### Objetivo

Criar funcoes para converter `InfoCNES` e `InfoGooglePlaces` em `InfoHospitalWeb`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/hospital_web.py` (~30 linhas) |

### Implementacao

```python
def cnes_to_info_web(info: "InfoCNES") -> InfoHospitalWeb:
    """Converte dados CNES para InfoHospitalWeb."""
    return InfoHospitalWeb(
        nome_oficial=info.nome_oficial,
        logradouro=info.logradouro,
        numero=info.numero,
        bairro=info.bairro,
        cidade=info.cidade,
        estado=info.estado,
        cep=info.cep,
        confianca=min(info.score + 0.2, 1.0),
        fonte="cnes",
        cnes_codigo=info.cnes_codigo,
        telefone=info.telefone,
        latitude=info.latitude,
        longitude=info.longitude,
    )


def google_to_info_web(info: "InfoGooglePlaces") -> InfoHospitalWeb:
    """Converte dados Google Places para InfoHospitalWeb."""
    return InfoHospitalWeb(
        nome_oficial=info.nome,
        cidade=info.cidade,
        estado=info.estado,
        cep=info.cep,
        confianca=info.confianca,
        fonte="google_places",
        google_place_id=info.place_id,
        telefone=info.telefone,
        latitude=info.latitude,
        longitude=info.longitude,
    )
```

### Definition of Done

- [ ] Helpers criados e testados
- [ ] Conversao preserva todos os campos relevantes

---

## Tarefa 3.3: Inserir CNES + Google no Fluxo

### Objetivo

Modificar `normalizar_ou_criar_hospital()` para tentar CNES e Google Places antes do LLM.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/hospital_web.py` (~40 linhas) |

### Implementacao

Inserir entre o gate de validacao (step 3) e busca web LLM (step atual 3 -> novo step 6):

```python
    # 4. Buscar no CNES (gratis, local)
    from app.services.grupos.hospital_cnes import buscar_hospital_cnes

    info_cnes = await buscar_hospital_cnes(texto, cidade_hint, estado_hint)
    if info_cnes and info_cnes.score >= 0.6:
        info_web = cnes_to_info_web(info_cnes)
        hospital_id = await criar_hospital(info_web, texto)
        await _emitir_evento_hospital(
            EventType.HOSPITAL_CREATED,
            hospital_id=str(hospital_id),
            props={"fonte": "cnes", "nome": info_web.nome_oficial, "confianca": info_web.confianca, "cnes": info_cnes.cnes_codigo},
        )
        return ResultadoHospitalAuto(
            hospital_id=hospital_id,
            nome=info_web.nome_oficial,
            score=info_web.confianca,
            foi_criado=True,
            fonte="cnes",
        )

    # 5. Buscar no Google Places (pago, mas dados frescos)
    from app.services.grupos.hospital_google_places import buscar_hospital_google_places

    info_google = await buscar_hospital_google_places(texto, regiao_grupo)
    if info_google and info_google.confianca >= 0.7:
        info_web = google_to_info_web(info_google)
        hospital_id = await criar_hospital(info_web, texto)
        await _emitir_evento_hospital(
            EventType.HOSPITAL_CREATED,
            hospital_id=str(hospital_id),
            props={"fonte": "google_places", "nome": info_web.nome_oficial, "confianca": info_web.confianca, "place_id": info_google.place_id},
        )
        return ResultadoHospitalAuto(
            hospital_id=hospital_id,
            nome=info_web.nome_oficial,
            score=info_web.confianca,
            foi_criado=True,
            fonte="google_places",
        )

    # 6. Buscar na web (LLM - fallback)
    # ... (codigo existente permanece igual)
```

**Nota sobre `cidade_hint` e `estado_hint`:** Extrair da `regiao_grupo` usando `inferir_cidade_regiao()` ja existente:

```python
    cidade_hint, estado_hint = inferir_cidade_regiao(regiao_grupo)
```

### Fluxo final:

```
1. alias exato          -> return (fonte="alias_exato")
2. similaridade >= 0.7  -> return (fonte="similaridade")
3. validador            -> invalido: return None
4. CNES >= 0.6          -> criar + return (fonte="cnes")        [NOVO]
5. Google Places >= 0.7 -> criar + return (fonte="google_places") [NOVO]
6. LLM Haiku >= 0.6     -> criar + return (fonte="web")
7. fallback             -> criar + return (fonte="fallback")
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Pipeline tenta CNES antes de Google
- [ ] Pipeline tenta Google antes de LLM
- [ ] CNES com score < 0.6 eh ignorado e continua para Google
- [ ] Google com confianca < 0.7 eh ignorado e continua para LLM
- [ ] CNES indisponivel (erro) nao bloqueia pipeline

**Integracao:**
- [ ] Hospital novo criado via CNES tem cnes_codigo preenchido
- [ ] Hospital novo criado via Google tem google_place_id preenchido

### Definition of Done

- [ ] Steps 4 e 5 inseridos no fluxo
- [ ] Eventos HOSPITAL_CREATED com fonte correta
- [ ] Testes passando
- [ ] Pipeline existente nao quebra quando CNES vazio e Google key nao configurada

---

## Dependencias

Depende de Epicos 1 e 2 (servicos CNES e Google Places criados).

## Risco: MEDIO

Mudanca no fluxo principal de criacao de hospitais. Mitigacao: os novos steps sao aditivos — se ambos falharem, o fluxo cai no LLM e fallback existentes.
