# E12 - Hospitais Bloqueados

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 4 - Arquitetura de Dados
**Dependências:** Nenhuma
**Estimativa:** 4h

---

## Objetivo

Implementar sistema de **hospitais bloqueados** onde o gestor pode temporariamente bloquear um hospital, fazendo Julia **não ver** suas vagas automaticamente.

---

## Problema

Situações que exigem bloqueio:
- Hospital com problema temporário (reforma, mudança de gestão)
- Conflito ou situação delicada com hospital
- Hospital não pagando médicos corretamente
- Pausa estratégica no relacionamento

**Problema atual:** Julia oferece todas as vagas da tabela `vagas`, sem filtro. Se gestor quer parar de ofertar Hospital X, precisa deletar todas as vagas manualmente.

---

## Solução

Arquitetura por **separação de dados**. Julia consulta apenas `vagas`. Quando hospital é bloqueado, vagas são **movidas** para `vagas_hospitais_bloqueados`.

```
ANTES (hospital ativo):
┌─────────────────────────────────────┐
│ vagas                               │
│ - Vaga 1 (Hospital X) ← Julia vê    │
│ - Vaga 2 (Hospital X) ← Julia vê    │
│ - Vaga 3 (Hospital Y) ← Julia vê    │
└─────────────────────────────────────┘

DEPOIS (Hospital X bloqueado):
┌─────────────────────────────────────┐
│ vagas                               │
│ - Vaga 3 (Hospital Y) ← Julia vê    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ vagas_hospitais_bloqueados          │
│ - Vaga 1 (Hospital X) ← Julia NÃO vê│
│ - Vaga 2 (Hospital X) ← Julia NÃO vê│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ hospitais_bloqueados                │
│ - Hospital X (motivo, data, quem)   │
└─────────────────────────────────────┘
```

**Vantagem:** Julia não precisa de filtro especial. Ela continua consultando `vagas` normalmente.

---

## Tasks

### T1: Criar tabela hospitais_bloqueados (30min)

**Migration:** `criar_hospitais_bloqueados`

```sql
-- Migration: criar_hospitais_bloqueados
-- Registra hospitais temporariamente bloqueados

CREATE TABLE hospitais_bloqueados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitais(id) UNIQUE,
    motivo TEXT NOT NULL,
    bloqueado_por TEXT NOT NULL,  -- ID do gestor
    bloqueado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    desbloqueado_em TIMESTAMPTZ,
    desbloqueado_por TEXT,
    status TEXT NOT NULL DEFAULT 'bloqueado' CHECK (status IN ('bloqueado', 'desbloqueado')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX idx_hospitais_bloqueados_hospital ON hospitais_bloqueados(hospital_id);
CREATE INDEX idx_hospitais_bloqueados_status ON hospitais_bloqueados(status);

-- Comentários
COMMENT ON TABLE hospitais_bloqueados IS 'Hospitais temporariamente bloqueados para oferta';
COMMENT ON COLUMN hospitais_bloqueados.motivo IS 'Motivo do bloqueio em texto livre';
COMMENT ON COLUMN hospitais_bloqueados.status IS 'bloqueado ou desbloqueado (histórico)';

-- RLS
ALTER TABLE hospitais_bloqueados ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Leitura para service role"
ON hospitais_bloqueados FOR SELECT
TO service_role
USING (true);

CREATE POLICY "Escrita para service role"
ON hospitais_bloqueados FOR ALL
TO service_role
USING (true);
```

---

### T2: Criar tabela vagas_hospitais_bloqueados (30min)

**Migration:** `criar_vagas_hospitais_bloqueados`

```sql
-- Migration: criar_vagas_hospitais_bloqueados
-- Armazena vagas de hospitais bloqueados (não visíveis para Julia)

CREATE TABLE vagas_hospitais_bloqueados (
    -- Mesma estrutura da tabela vagas
    id UUID PRIMARY KEY,
    hospital_id UUID NOT NULL REFERENCES hospitais(id),
    especialidade_id UUID REFERENCES especialidades(id),
    data DATE NOT NULL,
    hora_inicio TIME,
    hora_fim TIME,
    valor DECIMAL(10, 2),
    status TEXT,
    medico_confirmado_id UUID REFERENCES clientes(id),
    observacoes TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    -- Metadados do bloqueio
    movido_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    movido_por TEXT NOT NULL,
    bloqueio_id UUID NOT NULL REFERENCES hospitais_bloqueados(id)
);

-- Índices
CREATE INDEX idx_vagas_bloqueadas_hospital ON vagas_hospitais_bloqueados(hospital_id);
CREATE INDEX idx_vagas_bloqueadas_bloqueio ON vagas_hospitais_bloqueados(bloqueio_id);
CREATE INDEX idx_vagas_bloqueadas_data ON vagas_hospitais_bloqueados(data);

-- Comentários
COMMENT ON TABLE vagas_hospitais_bloqueados IS 'Vagas movidas de hospitais bloqueados';
COMMENT ON COLUMN vagas_hospitais_bloqueados.movido_em IS 'Quando a vaga foi movida';
COMMENT ON COLUMN vagas_hospitais_bloqueados.movido_por IS 'Quem bloqueou o hospital';

-- RLS
ALTER TABLE vagas_hospitais_bloqueados ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Leitura para service role"
ON vagas_hospitais_bloqueados FOR SELECT
TO service_role
USING (true);

CREATE POLICY "Escrita para service role"
ON vagas_hospitais_bloqueados FOR ALL
TO service_role
USING (true);
```

---

### T3: Criar serviço de bloqueio (1h)

**Arquivo:** `app/services/hospitais/bloqueio.py`

```python
"""
Serviço para bloquear/desbloquear hospitais.
"""
from datetime import datetime
from app.services.supabase import supabase
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ValidationError

logger = get_logger(__name__)


async def bloquear_hospital(
    hospital_id: str,
    motivo: str,
    bloqueado_por: str
) -> dict:
    """
    Bloqueia um hospital e move suas vagas para tabela separada.

    Args:
        hospital_id: ID do hospital
        motivo: Motivo do bloqueio
        bloqueado_por: ID do gestor

    Returns:
        Registro do bloqueio criado

    Raises:
        NotFoundError: Hospital não existe
        ValidationError: Hospital já está bloqueado
    """
    # 1. Verificar se hospital existe
    hospital = supabase.table("hospitais").select("id, nome").eq(
        "id", hospital_id
    ).single().execute()

    if not hospital.data:
        raise NotFoundError(f"Hospital {hospital_id} não encontrado")

    # 2. Verificar se já está bloqueado
    bloqueio_existente = supabase.table("hospitais_bloqueados").select("id").eq(
        "hospital_id", hospital_id
    ).eq("status", "bloqueado").execute()

    if bloqueio_existente.data:
        raise ValidationError(f"Hospital {hospital.data['nome']} já está bloqueado")

    # 3. Criar registro de bloqueio
    bloqueio = supabase.table("hospitais_bloqueados").insert({
        "hospital_id": hospital_id,
        "motivo": motivo,
        "bloqueado_por": bloqueado_por,
        "status": "bloqueado"
    }).execute()

    bloqueio_id = bloqueio.data[0]["id"]

    # 4. Mover vagas para tabela de bloqueados
    vagas_movidas = await _mover_vagas_para_bloqueados(
        hospital_id=hospital_id,
        bloqueio_id=bloqueio_id,
        movido_por=bloqueado_por
    )

    logger.info(
        f"Hospital bloqueado: {hospital.data['nome']} ({hospital_id}). "
        f"Motivo: {motivo}. Vagas movidas: {vagas_movidas}"
    )

    return {
        "bloqueio_id": bloqueio_id,
        "hospital_id": hospital_id,
        "hospital_nome": hospital.data["nome"],
        "motivo": motivo,
        "vagas_movidas": vagas_movidas
    }


async def desbloquear_hospital(
    hospital_id: str,
    desbloqueado_por: str
) -> dict:
    """
    Desbloqueia um hospital e restaura suas vagas.

    Args:
        hospital_id: ID do hospital
        desbloqueado_por: ID do gestor

    Returns:
        Resultado do desbloqueio

    Raises:
        NotFoundError: Hospital não está bloqueado
    """
    # 1. Buscar bloqueio ativo
    bloqueio = supabase.table("hospitais_bloqueados").select("*").eq(
        "hospital_id", hospital_id
    ).eq("status", "bloqueado").single().execute()

    if not bloqueio.data:
        raise NotFoundError(f"Hospital {hospital_id} não está bloqueado")

    bloqueio_id = bloqueio.data["id"]

    # 2. Restaurar vagas para tabela principal
    vagas_restauradas = await _restaurar_vagas_de_bloqueados(
        hospital_id=hospital_id,
        bloqueio_id=bloqueio_id
    )

    # 3. Atualizar status do bloqueio
    supabase.table("hospitais_bloqueados").update({
        "status": "desbloqueado",
        "desbloqueado_em": datetime.utcnow().isoformat(),
        "desbloqueado_por": desbloqueado_por,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", bloqueio_id).execute()

    logger.info(
        f"Hospital desbloqueado: {hospital_id}. "
        f"Vagas restauradas: {vagas_restauradas}"
    )

    return {
        "hospital_id": hospital_id,
        "vagas_restauradas": vagas_restauradas
    }


async def _mover_vagas_para_bloqueados(
    hospital_id: str,
    bloqueio_id: str,
    movido_por: str
) -> int:
    """
    Move vagas do hospital para tabela de bloqueados.

    Returns:
        Quantidade de vagas movidas
    """
    # Buscar vagas do hospital
    vagas = supabase.table("vagas").select("*").eq(
        "hospital_id", hospital_id
    ).execute()

    if not vagas.data:
        return 0

    # Inserir na tabela de bloqueados
    for vaga in vagas.data:
        vaga_bloqueada = {
            **vaga,
            "movido_em": datetime.utcnow().isoformat(),
            "movido_por": movido_por,
            "bloqueio_id": bloqueio_id
        }
        supabase.table("vagas_hospitais_bloqueados").insert(vaga_bloqueada).execute()

    # Deletar da tabela principal
    supabase.table("vagas").delete().eq("hospital_id", hospital_id).execute()

    return len(vagas.data)


async def _restaurar_vagas_de_bloqueados(
    hospital_id: str,
    bloqueio_id: str
) -> int:
    """
    Restaura vagas da tabela de bloqueados para principal.

    Apenas restaura vagas ainda válidas (data >= hoje).

    Returns:
        Quantidade de vagas restauradas
    """
    hoje = datetime.utcnow().date().isoformat()

    # Buscar vagas bloqueadas ainda válidas
    vagas_bloqueadas = supabase.table("vagas_hospitais_bloqueados").select("*").eq(
        "bloqueio_id", bloqueio_id
    ).gte("data", hoje).execute()

    if not vagas_bloqueadas.data:
        return 0

    # Restaurar para tabela principal
    for vaga in vagas_bloqueadas.data:
        # Remover campos de metadados de bloqueio
        vaga_restaurada = {k: v for k, v in vaga.items()
                          if k not in ("movido_em", "movido_por", "bloqueio_id")}
        vaga_restaurada["updated_at"] = datetime.utcnow().isoformat()

        supabase.table("vagas").insert(vaga_restaurada).execute()

    # Deletar da tabela de bloqueados
    supabase.table("vagas_hospitais_bloqueados").delete().eq(
        "bloqueio_id", bloqueio_id
    ).execute()

    return len(vagas_bloqueadas.data)


async def listar_hospitais_bloqueados() -> list[dict]:
    """
    Lista todos os hospitais atualmente bloqueados.

    Returns:
        Lista de hospitais bloqueados com detalhes
    """
    resultado = supabase.table("hospitais_bloqueados").select(
        "*, hospitais(nome, cidade)"
    ).eq("status", "bloqueado").order("bloqueado_em", desc=True).execute()

    return resultado.data or []


async def esta_bloqueado(hospital_id: str) -> bool:
    """
    Verifica se hospital está bloqueado.

    Args:
        hospital_id: ID do hospital

    Returns:
        True se bloqueado, False caso contrário
    """
    resultado = supabase.table("hospitais_bloqueados").select("id").eq(
        "hospital_id", hospital_id
    ).eq("status", "bloqueado").execute()

    return len(resultado.data or []) > 0
```

---

### T4: Criar endpoints de API (45min)

**Arquivo:** `app/api/routes/hospitais.py` (adicionar)

```python
"""
Endpoints para gestão de hospitais bloqueados.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.hospitais.bloqueio import (
    bloquear_hospital,
    desbloquear_hospital,
    listar_hospitais_bloqueados,
    esta_bloqueado
)
from app.core.exceptions import NotFoundError, ValidationError
from app.api.deps import get_current_user

router = APIRouter(prefix="/hospitais", tags=["hospitais"])


class BloquearHospitalRequest(BaseModel):
    hospital_id: str
    motivo: str


class BloquearHospitalResponse(BaseModel):
    bloqueio_id: str
    hospital_id: str
    hospital_nome: str
    motivo: str
    vagas_movidas: int


class DesbloquearHospitalRequest(BaseModel):
    hospital_id: str


@router.post("/bloquear", response_model=BloquearHospitalResponse)
async def api_bloquear_hospital(
    request: BloquearHospitalRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Bloqueia um hospital e move suas vagas.

    - Requer autenticação de gestor
    - Vagas são movidas para tabela separada
    - Julia deixa de ver as vagas automaticamente
    """
    try:
        resultado = await bloquear_hospital(
            hospital_id=request.hospital_id,
            motivo=request.motivo,
            bloqueado_por=current_user["id"]
        )
        return resultado

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/desbloquear")
async def api_desbloquear_hospital(
    request: DesbloquearHospitalRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Desbloqueia um hospital e restaura vagas válidas.

    - Apenas vagas com data >= hoje são restauradas
    - Vagas passadas permanecem no histórico
    """
    try:
        resultado = await desbloquear_hospital(
            hospital_id=request.hospital_id,
            desbloqueado_por=current_user["id"]
        )
        return resultado

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/bloqueados")
async def api_listar_bloqueados():
    """
    Lista todos os hospitais bloqueados.
    """
    return await listar_hospitais_bloqueados()


@router.get("/{hospital_id}/status")
async def api_verificar_status(hospital_id: str):
    """
    Verifica se um hospital está bloqueado.
    """
    bloqueado = await esta_bloqueado(hospital_id)
    return {"hospital_id": hospital_id, "bloqueado": bloqueado}
```

---

### T5: Integrar com Slack (45min)

Gestor deve poder bloquear/desbloquear via Slack.

**Arquivo:** `app/services/slack/comandos_hospital.py`

```python
"""
Comandos Slack para gestão de hospitais bloqueados.
"""
from app.services.hospitais.bloqueio import (
    bloquear_hospital,
    desbloquear_hospital,
    listar_hospitais_bloqueados
)
from app.services.slack.client import enviar_mensagem_slack
from app.core.logging import get_logger

logger = get_logger(__name__)


async def processar_comando_bloquear_hospital(
    texto: str,
    usuario_slack: str,
    canal: str
) -> None:
    """
    Processa comando para bloquear hospital.

    Formato: "bloquear hospital [nome] motivo: [motivo]"

    Args:
        texto: Texto do comando
        usuario_slack: ID do usuário Slack
        canal: Canal onde foi enviado
    """
    # Extrair nome do hospital e motivo
    # Formato esperado: "bloquear hospital São Luiz motivo: problemas de pagamento"

    try:
        # Parse simples - em produção usar NLP
        partes = texto.lower().replace("bloquear hospital", "").strip()
        if "motivo:" in partes:
            hospital_nome, motivo = partes.split("motivo:")
            hospital_nome = hospital_nome.strip()
            motivo = motivo.strip()
        else:
            hospital_nome = partes
            motivo = "Não especificado"

        # Buscar hospital pelo nome
        hospital = await _buscar_hospital_por_nome(hospital_nome)

        if not hospital:
            await enviar_mensagem_slack(
                canal=canal,
                texto=f"Não encontrei hospital com nome '{hospital_nome}'. "
                      f"Verifique o nome e tente novamente."
            )
            return

        # Bloquear
        resultado = await bloquear_hospital(
            hospital_id=hospital["id"],
            motivo=motivo,
            bloqueado_por=usuario_slack
        )

        await enviar_mensagem_slack(
            canal=canal,
            texto=f"✅ Hospital **{resultado['hospital_nome']}** bloqueado.\n"
                  f"Motivo: {motivo}\n"
                  f"Vagas movidas: {resultado['vagas_movidas']}\n\n"
                  f"Julia não oferecerá mais vagas deste hospital."
        )

    except Exception as e:
        logger.error(f"Erro ao bloquear hospital: {e}")
        await enviar_mensagem_slack(
            canal=canal,
            texto=f"Erro ao bloquear hospital: {e}"
        )


async def processar_comando_desbloquear_hospital(
    texto: str,
    usuario_slack: str,
    canal: str
) -> None:
    """
    Processa comando para desbloquear hospital.

    Formato: "desbloquear hospital [nome]"
    """
    try:
        hospital_nome = texto.lower().replace("desbloquear hospital", "").strip()

        hospital = await _buscar_hospital_por_nome(hospital_nome)

        if not hospital:
            await enviar_mensagem_slack(
                canal=canal,
                texto=f"Não encontrei hospital com nome '{hospital_nome}'."
            )
            return

        resultado = await desbloquear_hospital(
            hospital_id=hospital["id"],
            desbloqueado_por=usuario_slack
        )

        await enviar_mensagem_slack(
            canal=canal,
            texto=f"✅ Hospital **{hospital_nome}** desbloqueado.\n"
                  f"Vagas restauradas: {resultado['vagas_restauradas']}\n\n"
                  f"Julia voltará a ofertar vagas deste hospital."
        )

    except Exception as e:
        logger.error(f"Erro ao desbloquear hospital: {e}")
        await enviar_mensagem_slack(
            canal=canal,
            texto=f"Erro ao desbloquear hospital: {e}"
        )


async def processar_comando_listar_bloqueados(canal: str) -> None:
    """
    Lista hospitais bloqueados.

    Formato: "hospitais bloqueados" ou "listar bloqueados"
    """
    bloqueados = await listar_hospitais_bloqueados()

    if not bloqueados:
        await enviar_mensagem_slack(
            canal=canal,
            texto="Nenhum hospital bloqueado no momento."
        )
        return

    linhas = ["**Hospitais Bloqueados:**\n"]
    for h in bloqueados:
        hospital_nome = h.get("hospitais", {}).get("nome", "Desconhecido")
        linhas.append(
            f"• {hospital_nome}\n"
            f"  Motivo: {h['motivo']}\n"
            f"  Bloqueado em: {h['bloqueado_em'][:10]}"
        )

    await enviar_mensagem_slack(
        canal=canal,
        texto="\n".join(linhas)
    )


async def _buscar_hospital_por_nome(nome: str) -> dict | None:
    """Busca hospital pelo nome (fuzzy match)."""
    from app.services.supabase import supabase

    # Busca exata primeiro
    resultado = supabase.table("hospitais").select("id, nome").ilike(
        "nome", f"%{nome}%"
    ).limit(1).execute()

    if resultado.data:
        return resultado.data[0]

    return None
```

---

### T6: Criar testes (30min)

**Arquivo:** `tests/hospitais/test_bloqueio.py`

```python
"""
Testes para bloqueio de hospitais.
"""
import pytest
from app.services.hospitais.bloqueio import (
    bloquear_hospital,
    desbloquear_hospital,
    listar_hospitais_bloqueados,
    esta_bloqueado
)
from app.core.exceptions import NotFoundError, ValidationError


class TestBloquearHospital:
    """Testes para bloqueio de hospital."""

    @pytest.mark.asyncio
    async def test_bloquear_hospital_sucesso(self, supabase_mock, hospital_fixture):
        """Bloqueia hospital e move vagas."""
        resultado = await bloquear_hospital(
            hospital_id=hospital_fixture["id"],
            motivo="Reforma em andamento",
            bloqueado_por="gestor-123"
        )

        assert resultado["hospital_id"] == hospital_fixture["id"]
        assert resultado["motivo"] == "Reforma em andamento"
        assert resultado["vagas_movidas"] >= 0

    @pytest.mark.asyncio
    async def test_bloquear_hospital_inexistente(self, supabase_mock):
        """Erro ao bloquear hospital que não existe."""
        with pytest.raises(NotFoundError):
            await bloquear_hospital(
                hospital_id="hospital-inexistente",
                motivo="Teste",
                bloqueado_por="gestor-123"
            )

    @pytest.mark.asyncio
    async def test_bloquear_hospital_ja_bloqueado(self, supabase_mock, hospital_bloqueado_fixture):
        """Erro ao bloquear hospital já bloqueado."""
        with pytest.raises(ValidationError):
            await bloquear_hospital(
                hospital_id=hospital_bloqueado_fixture["id"],
                motivo="Tentativa duplicada",
                bloqueado_por="gestor-123"
            )


class TestDesbloquearHospital:
    """Testes para desbloqueio de hospital."""

    @pytest.mark.asyncio
    async def test_desbloquear_hospital_sucesso(self, supabase_mock, hospital_bloqueado_fixture):
        """Desbloqueia hospital e restaura vagas."""
        resultado = await desbloquear_hospital(
            hospital_id=hospital_bloqueado_fixture["id"],
            desbloqueado_por="gestor-123"
        )

        assert resultado["hospital_id"] == hospital_bloqueado_fixture["id"]
        assert resultado["vagas_restauradas"] >= 0

    @pytest.mark.asyncio
    async def test_desbloquear_hospital_nao_bloqueado(self, supabase_mock, hospital_fixture):
        """Erro ao desbloquear hospital que não está bloqueado."""
        with pytest.raises(NotFoundError):
            await desbloquear_hospital(
                hospital_id=hospital_fixture["id"],
                desbloqueado_por="gestor-123"
            )


class TestEstaBloqueado:
    """Testes para verificação de status."""

    @pytest.mark.asyncio
    async def test_esta_bloqueado_true(self, supabase_mock, hospital_bloqueado_fixture):
        """Retorna True para hospital bloqueado."""
        resultado = await esta_bloqueado(hospital_bloqueado_fixture["id"])
        assert resultado is True

    @pytest.mark.asyncio
    async def test_esta_bloqueado_false(self, supabase_mock, hospital_fixture):
        """Retorna False para hospital ativo."""
        resultado = await esta_bloqueado(hospital_fixture["id"])
        assert resultado is False


class TestVagasMovidas:
    """Testes para movimentação de vagas."""

    @pytest.mark.asyncio
    async def test_vagas_movidas_ao_bloquear(self, supabase_mock, hospital_com_vagas_fixture):
        """Vagas são movidas para tabela de bloqueados."""
        hospital_id = hospital_com_vagas_fixture["id"]
        vagas_antes = hospital_com_vagas_fixture["vagas_count"]

        resultado = await bloquear_hospital(
            hospital_id=hospital_id,
            motivo="Teste",
            bloqueado_por="gestor-123"
        )

        assert resultado["vagas_movidas"] == vagas_antes

        # Verificar que vagas não estão mais na tabela principal
        from app.services.supabase import supabase
        vagas_principal = supabase.table("vagas").select("id").eq(
            "hospital_id", hospital_id
        ).execute()

        assert len(vagas_principal.data) == 0

    @pytest.mark.asyncio
    async def test_vagas_passadas_nao_restauradas(self, supabase_mock, hospital_bloqueado_com_vagas_passadas):
        """Vagas com data passada não são restauradas."""
        resultado = await desbloquear_hospital(
            hospital_id=hospital_bloqueado_com_vagas_passadas["id"],
            desbloqueado_por="gestor-123"
        )

        # Vagas passadas não devem ser restauradas
        assert resultado["vagas_restauradas"] == 0
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Tabela `hospitais_bloqueados` criada
- [ ] Tabela `vagas_hospitais_bloqueados` criada
- [ ] Endpoint POST `/hospitais/bloquear` funcionando
- [ ] Endpoint POST `/hospitais/desbloquear` funcionando
- [ ] Endpoint GET `/hospitais/bloqueados` funcionando
- [ ] Vagas são movidas ao bloquear
- [ ] Vagas válidas são restauradas ao desbloquear
- [ ] Vagas passadas permanecem no histórico

### Slack
- [ ] Comando "bloquear hospital X motivo: Y" funciona
- [ ] Comando "desbloquear hospital X" funciona
- [ ] Comando "listar bloqueados" funciona

### Testes
- [ ] Testes de bloqueio/desbloqueio
- [ ] Testes de movimentação de vagas
- [ ] Testes de erro (hospital inexistente, já bloqueado)

### Qualidade
- [ ] Log de auditoria em todas as operações
- [ ] RLS configurado nas tabelas
- [ ] Índices criados

### Verificação Manual

1. **Via API - Bloquear:**
   ```bash
   curl -X POST http://localhost:8000/hospitais/bloquear \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"hospital_id": "UUID", "motivo": "Reforma"}'
   ```

2. **Verificar que vagas sumiram:**
   ```sql
   -- Não deve retornar nada
   SELECT * FROM vagas WHERE hospital_id = 'UUID';

   -- Deve mostrar as vagas movidas
   SELECT * FROM vagas_hospitais_bloqueados WHERE hospital_id = 'UUID';
   ```

3. **Julia não vê vagas (testar buscar_vagas):**
   ```python
   vagas = await buscar_vagas(hospital_id="UUID")
   assert len(vagas) == 0
   ```

4. **Via Slack:**
   ```
   Usuário: "Julia, bloquear hospital São Luiz motivo: reforma"
   Julia: "✅ Hospital São Luiz bloqueado. Vagas movidas: 5"
   ```

---

## Notas para Dev

1. **Integridade referencial:** Vagas em `vagas_hospitais_bloqueados` mantêm referência ao hospital original
2. **Histórico:** Manter bloqueios antigos com status "desbloqueado" para auditoria
3. **Performance:** Operação de mover vagas deve ser transacional (tudo ou nada)
4. **Vagas futuras:** Se novas vagas forem criadas para hospital bloqueado, precisam de validação
5. **Dashboard:** Tela de hospitais bloqueados será implementada no E17

---

## Métricas de Sucesso

| Métrica | Expectativa |
|---------|-------------|
| Tempo de bloqueio | < 2s para até 100 vagas |
| Tempo de desbloqueio | < 2s para até 100 vagas |
| Disponibilidade | 99.9% |
