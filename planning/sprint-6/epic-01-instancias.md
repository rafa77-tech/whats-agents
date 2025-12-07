# Epic 1: Gerenciamento de Instâncias

## Objetivo do Epic

> **Gerenciar múltiplas instâncias WhatsApp na Evolution API.**

Este epic estabelece a infraestrutura para trabalhar com N instâncias.

---

## Stories

1. [S6.E1.1 - Modelo de Instâncias](#s6e11---modelo-de-instâncias)
2. [S6.E1.2 - Gerenciador de Instâncias](#s6e12---gerenciador-de-instâncias)
3. [S6.E1.3 - Health Check](#s6e13---health-check)
4. [S6.E1.4 - Criar Instância via API](#s6e14---criar-instância-via-api)

---

# S6.E1.1 - Modelo de Instâncias

## Objetivo

> **Definir estrutura de dados para múltiplas instâncias.**

---

## Tarefas

### 1. Usar tabela existente whatsapp_instances

```sql
-- Já existe no schema, verificar campos:
SELECT * FROM whatsapp_instances LIMIT 1;

-- Se precisar adicionar campos:
ALTER TABLE whatsapp_instances
ADD COLUMN IF NOT EXISTS capacidade_hora INT DEFAULT 20,
ADD COLUMN IF NOT EXISTS capacidade_dia INT DEFAULT 100,
ADD COLUMN IF NOT EXISTS msgs_enviadas_hora INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS msgs_enviadas_dia INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS prioridade INT DEFAULT 1,
ADD COLUMN IF NOT EXISTS ultima_msg_at TIMESTAMPTZ;
```

### 2. Adicionar instância preferida no cliente

```sql
ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS instancia_preferida VARCHAR(50);
```

### 3. Criar schema Pydantic

```python
# app/schemas/instancia.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InstanciaWhatsApp(BaseModel):
    """Instância WhatsApp na Evolution API."""
    nome: str
    numero_telefone: Optional[str] = None
    status: str = "disconnected"  # connected, disconnected, banned
    capacidade_hora: int = 20
    capacidade_dia: int = 100
    msgs_enviadas_hora: int = 0
    msgs_enviadas_dia: int = 0
    prioridade: int = 1
    ultima_msg_at: Optional[datetime] = None

    @property
    def disponivel(self) -> bool:
        """Verifica se instância está disponível para envio."""
        return (
            self.status == "connected" and
            self.msgs_enviadas_hora < self.capacidade_hora and
            self.msgs_enviadas_dia < self.capacidade_dia
        )

    @property
    def carga_percentual(self) -> float:
        """Retorna percentual de carga da instância."""
        return (self.msgs_enviadas_dia / self.capacidade_dia) * 100
```

---

## DoD

- [ ] Tabela whatsapp_instances tem campos necessários
- [ ] Coluna instancia_preferida existe em clientes
- [ ] Schema Pydantic criado
- [ ] Seed com instâncias iniciais

---

# S6.E1.2 - Gerenciador de Instâncias

## Objetivo

> **Criar serviço para gerenciar ciclo de vida das instâncias.**

---

## Tarefas

### 1. Criar Instance Manager

```python
# app/services/instance_manager.py

"""
Gerenciador de instâncias WhatsApp.
"""
import logging
from typing import List, Optional
from datetime import datetime

from app.services.supabase import supabase
from app.schemas.instancia import InstanciaWhatsApp

logger = logging.getLogger(__name__)


class InstanceManager:
    """Gerencia múltiplas instâncias WhatsApp."""

    def __init__(self):
        self._cache: dict[str, InstanciaWhatsApp] = {}
        self._ultimo_refresh: Optional[datetime] = None

    async def listar_instancias(self, apenas_ativas: bool = True) -> List[InstanciaWhatsApp]:
        """Lista todas as instâncias."""
        query = supabase.table("whatsapp_instances").select("*")

        if apenas_ativas:
            query = query.eq("status", "connected")

        response = query.execute()

        return [InstanciaWhatsApp(**row) for row in response.data]

    async def obter_instancia(self, nome: str) -> Optional[InstanciaWhatsApp]:
        """Obtém instância por nome."""
        response = (
            supabase.table("whatsapp_instances")
            .select("*")
            .eq("nome", nome)
            .execute()
        )

        if response.data:
            return InstanciaWhatsApp(**response.data[0])
        return None

    async def escolher_instancia(
        self,
        medico_id: Optional[str] = None,
        estrategia: str = "sticky"
    ) -> Optional[str]:
        """
        Escolhe melhor instância para envio.

        Estratégias:
        - sticky: Mantém mesma instância do médico
        - round_robin: Distribui igualmente
        - least_loaded: Escolhe menos carregada
        """
        # Se médico tem preferência, tentar usar
        if medico_id and estrategia == "sticky":
            preferida = await self._obter_preferencia(medico_id)
            if preferida:
                instancia = await self.obter_instancia(preferida)
                if instancia and instancia.disponivel:
                    return preferida
                # Se preferida não disponível, escolher outra

        # Buscar instâncias disponíveis
        instancias = await self.listar_instancias(apenas_ativas=True)
        disponiveis = [i for i in instancias if i.disponivel]

        if not disponiveis:
            logger.warning("Nenhuma instância disponível!")
            return None

        # Escolher menos carregada
        escolhida = min(disponiveis, key=lambda i: i.carga_percentual)

        # Atualizar preferência do médico
        if medico_id:
            await self._salvar_preferencia(medico_id, escolhida.nome)

        return escolhida.nome

    async def registrar_envio(self, nome_instancia: str) -> None:
        """Registra envio de mensagem na instância."""
        await supabase.rpc(
            "incrementar_contador_instancia",
            {"p_nome": nome_instancia}
        ).execute()

    async def atualizar_status(self, nome: str, status: str) -> None:
        """Atualiza status da instância."""
        (
            supabase.table("whatsapp_instances")
            .update({"status": status, "updated_at": "now()"})
            .eq("nome", nome)
            .execute()
        )
        logger.info(f"Instância {nome} status: {status}")

    async def _obter_preferencia(self, medico_id: str) -> Optional[str]:
        """Obtém instância preferida do médico."""
        response = (
            supabase.table("clientes")
            .select("instancia_preferida")
            .eq("id", medico_id)
            .execute()
        )
        if response.data:
            return response.data[0].get("instancia_preferida")
        return None

    async def _salvar_preferencia(self, medico_id: str, instancia: str) -> None:
        """Salva instância preferida do médico."""
        (
            supabase.table("clientes")
            .update({"instancia_preferida": instancia})
            .eq("id", medico_id)
            .execute()
        )


# Instância global
instance_manager = InstanceManager()
```

### 2. Criar função SQL para incrementar contador

```sql
CREATE OR REPLACE FUNCTION incrementar_contador_instancia(p_nome VARCHAR)
RETURNS VOID AS $$
BEGIN
    UPDATE whatsapp_instances
    SET
        msgs_enviadas_hora = msgs_enviadas_hora + 1,
        msgs_enviadas_dia = msgs_enviadas_dia + 1,
        ultima_msg_at = NOW()
    WHERE nome = p_nome;
END;
$$ LANGUAGE plpgsql;

-- Job para resetar contadores (executar via cron ou pg_cron)
-- Resetar hora: a cada hora
-- Resetar dia: à meia-noite
```

---

## DoD

- [ ] InstanceManager implementado
- [ ] Função SQL de incremento criada
- [ ] escolher_instancia() funciona com sticky
- [ ] escolher_instancia() faz fallback se instância down
- [ ] Testes unitários passando

---

# S6.E1.3 - Health Check

## Objetivo

> **Monitorar status das instâncias em tempo real.**

---

## Tarefas

### 1. Verificar status na Evolution API

```python
# Adicionar em instance_manager.py

async def verificar_saude(self, nome: str) -> dict:
    """Verifica saúde da instância na Evolution API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.EVOLUTION_API_URL}/instance/connectionState/{nome}",
                headers={"apikey": settings.EVOLUTION_API_KEY},
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get("state", "unknown")

                # Atualizar no banco
                await self.atualizar_status(nome, status)

                return {
                    "nome": nome,
                    "status": status,
                    "online": status == "open",
                }

            return {"nome": nome, "status": "error", "online": False}

    except Exception as e:
        logger.error(f"Erro ao verificar {nome}: {e}")
        return {"nome": nome, "status": "error", "online": False}

async def verificar_todas(self) -> List[dict]:
    """Verifica saúde de todas as instâncias."""
    instancias = await self.listar_instancias(apenas_ativas=False)
    resultados = []

    for inst in instancias:
        resultado = await self.verificar_saude(inst.nome)
        resultados.append(resultado)

    return resultados
```

### 2. Endpoint de health check

```python
# app/api/routes/health.py

@router.get("/health/instances")
async def instances_health():
    """Retorna status de todas as instâncias WhatsApp."""
    from app.services.instance_manager import instance_manager

    resultados = await instance_manager.verificar_todas()

    online = sum(1 for r in resultados if r["online"])
    total = len(resultados)

    return {
        "status": "healthy" if online > 0 else "degraded",
        "online": online,
        "total": total,
        "instances": resultados
    }
```

### 3. Background task para verificação periódica

```python
# Adicionar no startup da aplicação

async def health_check_loop():
    """Loop de verificação de saúde das instâncias."""
    while True:
        try:
            await instance_manager.verificar_todas()
        except Exception as e:
            logger.error(f"Erro no health check: {e}")

        await asyncio.sleep(60)  # Verificar a cada minuto
```

---

## DoD

- [ ] verificar_saude() consulta Evolution API
- [ ] Status é atualizado no banco
- [ ] Endpoint /health/instances funciona
- [ ] Background task verifica periodicamente
- [ ] Log quando instância muda de status

---

# S6.E1.4 - Criar Instância via API

## Objetivo

> **Permitir criar novas instâncias programaticamente.**

---

## Tarefas

### 1. Endpoint para criar instância

```python
# app/api/routes/admin.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

class CriarInstanciaRequest(BaseModel):
    nome: str
    numero_telefone: Optional[str] = None

@router.post("/instances")
async def criar_instancia(request: CriarInstanciaRequest):
    """Cria nova instância na Evolution API."""

    # 1. Criar na Evolution
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.EVOLUTION_API_URL}/instance/create",
            headers={"apikey": settings.EVOLUTION_API_KEY},
            json={
                "instanceName": request.nome,
                "qrcode": True,
            }
        )

        if response.status_code != 201:
            raise HTTPException(500, "Erro ao criar instância na Evolution")

        data = response.json()

    # 2. Salvar no banco
    supabase.table("whatsapp_instances").insert({
        "nome": request.nome,
        "numero_telefone": request.numero_telefone,
        "status": "disconnected",
    }).execute()

    return {
        "nome": request.nome,
        "qrcode": data.get("qrcode"),
        "message": "Escaneie o QR Code para conectar"
    }

@router.get("/instances/{nome}/qrcode")
async def obter_qrcode(nome: str):
    """Obtém QR Code para conectar instância."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.EVOLUTION_API_URL}/instance/connect/{nome}",
            headers={"apikey": settings.EVOLUTION_API_KEY},
        )

        if response.status_code != 200:
            raise HTTPException(404, "Instância não encontrada")

        return response.json()
```

---

## DoD

- [ ] POST /admin/instances cria instância
- [ ] QR Code é retornado para conexão
- [ ] Instância é salva no banco
- [ ] GET /admin/instances/{nome}/qrcode funciona
- [ ] Documentação de como adicionar nova instância
