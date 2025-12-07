# Medicos do Piloto - MVP Julia

## Data da Selecao
2025-12-07

## Criterios de Selecao
1. Especialidade: Anestesiologia
2. Opt-out: false
3. Telefone valido (12+ digitos)
4. Priorizados por completude dos dados (CRM, nome, email)

## Perfil do Grupo Selecionado

| Metrica | Valor | Percentual |
|---------|-------|------------|
| Total selecionados | 100 | 100% |
| Com CRM | 100 | 100% |
| Com primeiro nome | 100 | 100% |
| Com sobrenome | 100 | 100% |
| Com email | 100 | 100% |

## Base Total de Anestesistas

| Metrica | Valor |
|---------|-------|
| Total anestesistas | 1.660 |
| Com CRM | 1.345 (81%) |
| Elegiveis para piloto | 1.345 |
| Selecionados | 100 (7.4% dos elegiveis) |

## Query de Selecao

```sql
UPDATE clientes
SET grupo_piloto = true
WHERE id IN (
    SELECT id
    FROM clientes
    WHERE especialidade = 'Anestesiologia'
      AND opt_out = false
      AND telefone IS NOT NULL
      AND LENGTH(telefone) >= 12
    ORDER BY
        (CASE WHEN crm IS NOT NULL THEN 4 ELSE 0 END) +
        (CASE WHEN primeiro_nome IS NOT NULL THEN 2 ELSE 0 END) +
        (CASE WHEN sobrenome IS NOT NULL THEN 2 ELSE 0 END) +
        (CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) DESC,
        created_at DESC
    LIMIT 100
);
```

## Como Consultar

```sql
-- Listar medicos do piloto
SELECT id, primeiro_nome, sobrenome, crm, telefone, email
FROM clientes
WHERE grupo_piloto = true
ORDER BY primeiro_nome;

-- Contar total
SELECT COUNT(*) FROM clientes WHERE grupo_piloto = true;
```

## Proximos Passos
1. Gestor revisa lista (opcional)
2. Iniciar Sprint 1 - MVP
3. Primeira campanha de teste com grupo piloto
