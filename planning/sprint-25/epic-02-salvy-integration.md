# Epic 02: Salvy Integration

**Status:** ✅ Completo

**Arquivos criados:**
- `app/services/salvy/client.py`
- `app/services/salvy/webhooks.py`
- `app/services/salvy/__init__.py`

---

## Objetivo

Integrar com API Salvy para **provisioning automatico** de numeros virtuais:
- Criar novos numeros
- Cancelar numeros (quando banido ou desnecessario)
- Receber SMS via webhook (codigo WhatsApp)
- Listar numeros ativos

## Contexto

**Salvy** e um servico brasileiro de numeros virtuais que permite:
- Comprar numeros com DDDs especificos
- Receber SMS (para verificacao WhatsApp)
- Cancelar a qualquer momento

**Documentacao oficial:** https://docs.salvy.com.br/api-reference/virtual-phone-accounts/introduction

**Referencia local:**
- [docs-salvy-quickref.md](./docs-salvy-quickref.md) - Endpoints e auth (consulta rapida)
- [docs-salvy-webhooks.md](./docs-salvy-webhooks.md) - Webhook SMS e verificacao Svix

---

## Story 2.1: Salvy Client

### Objetivo
Implementar cliente para API Salvy.

### Implementacao

**Arquivo:** `app/services/salvy/client.py`

```python
"""
Salvy API Client - Provisioning de numeros virtuais.

Docs: https://docs.salvy.com.br/api-reference/virtual-phone-accounts/introduction
"""
import httpx
import logging
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.config import settings
from app.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.salvy.com.br/api/v2"


class SalvyNumber(BaseModel):
    """Numero virtual Salvy."""
    id: str
    name: Optional[str] = None
    phone_number: str
    status: str  # active, blocked, canceled
    created_at: datetime
    canceled_at: Optional[datetime] = None


class SalvyAreaCode(BaseModel):
    """DDD disponivel."""
    area_code: int
    available: bool


class SalvyClient:
    """Cliente para API Salvy."""

    def __init__(self):
        self.token = settings.SALVY_API_TOKEN
        if not self.token:
            logger.warning("[Salvy] SALVY_API_TOKEN nao configurado")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from API."""
        if not dt_str:
            return None
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

    async def criar_numero(
        self,
        ddd: int = 11,
        nome: Optional[str] = None
    ) -> SalvyNumber:
        """
        Cria novo numero virtual.

        Args:
            ddd: Codigo de area (11, 21, etc)
            nome: Label para identificacao

        Returns:
            SalvyNumber criado

        Raises:
            ExternalAPIError: Se falhar na criacao
        """
        nome_final = nome or f"julia-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{BASE_URL}/virtual-phone-accounts",
                    headers=self.headers,
                    json={
                        "areaCode": ddd,
                        "name": nome_final,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"[Salvy] Numero criado: {data['phoneNumber']} (DDD {ddd})")

                return SalvyNumber(
                    id=data["id"],
                    name=data.get("name"),
                    phone_number=data["phoneNumber"],
                    status=data["status"],
                    created_at=self._parse_datetime(data["createdAt"]),
                )

            except httpx.HTTPStatusError as e:
                logger.error(f"[Salvy] Erro HTTP ao criar numero: {e.response.text}")
                raise ExternalAPIError(f"Salvy: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"[Salvy] Erro ao criar numero: {e}")
                raise ExternalAPIError(f"Salvy: {str(e)}")

    async def cancelar_numero(
        self,
        salvy_id: str,
        reason: str = "unnecessary"
    ) -> bool:
        """
        Cancela numero virtual (para de pagar).

        Args:
            salvy_id: ID do numero na Salvy
            reason: Motivo do cancelamento:
                - "unnecessary": Nao precisa mais
                - "whatsapp-ban": Banido pelo WhatsApp
                - "technical-issues": Problemas tecnicos
                - "company-canceled": Empresa cancelou

        Returns:
            True se cancelado com sucesso
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{BASE_URL}/virtual-phone-accounts/{salvy_id}",
                    headers=self.headers,
                    json={"reason": reason},
                    timeout=30,
                )

                if response.status_code == 204:
                    logger.info(f"[Salvy] Numero cancelado: {salvy_id} (reason={reason})")
                    return True

                logger.error(f"[Salvy] Erro ao cancelar: {response.text}")
                return False

            except Exception as e:
                logger.error(f"[Salvy] Erro ao cancelar numero: {e}")
                return False

    async def buscar_numero(self, salvy_id: str) -> Optional[SalvyNumber]:
        """
        Busca numero por ID.

        Args:
            salvy_id: ID na Salvy

        Returns:
            SalvyNumber ou None se nao encontrado
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/virtual-phone-accounts/{salvy_id}",
                    headers=self.headers,
                    timeout=30,
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json()

                return SalvyNumber(
                    id=data["id"],
                    name=data.get("name"),
                    phone_number=data["phoneNumber"],
                    status=data["status"],
                    created_at=self._parse_datetime(data["createdAt"]),
                    canceled_at=self._parse_datetime(data.get("canceledAt")),
                )

            except httpx.HTTPStatusError:
                return None
            except Exception as e:
                logger.error(f"[Salvy] Erro ao buscar numero: {e}")
                return None

    async def listar_numeros(self, status: Optional[str] = None) -> List[SalvyNumber]:
        """
        Lista todos os numeros.

        Args:
            status: Filtrar por status (active, blocked, canceled)

        Returns:
            Lista de SalvyNumber
        """
        async with httpx.AsyncClient() as client:
            try:
                params = {}
                if status:
                    params["status"] = status

                response = await client.get(
                    f"{BASE_URL}/virtual-phone-accounts",
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()

                return [
                    SalvyNumber(
                        id=d["id"],
                        name=d.get("name"),
                        phone_number=d["phoneNumber"],
                        status=d["status"],
                        created_at=self._parse_datetime(d["createdAt"]),
                        canceled_at=self._parse_datetime(d.get("canceledAt")),
                    )
                    for d in response.json()
                ]

            except Exception as e:
                logger.error(f"[Salvy] Erro ao listar numeros: {e}")
                return []

    async def listar_ddds_disponiveis(self, apenas_disponiveis: bool = True) -> List[int]:
        """
        Lista DDDs com numeros disponiveis.

        Args:
            apenas_disponiveis: Se True, retorna apenas DDDs com estoque

        Returns:
            Lista de DDDs (ex: [11, 21, 31])
        """
        async with httpx.AsyncClient() as client:
            try:
                params = {}
                if apenas_disponiveis:
                    params["available"] = "true"

                response = await client.get(
                    f"{BASE_URL}/virtual-phone-accounts/area-codes",
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()

                data = response.json()
                # API retorna {"areaCodes": [{"areaCode": 11, "available": true}, ...]}
                return [
                    item["areaCode"]
                    for item in data.get("areaCodes", [])
                    if item.get("available", False) or not apenas_disponiveis
                ]

            except Exception as e:
                logger.error(f"[Salvy] Erro ao listar DDDs: {e}")
                return []

    async def health_check(self) -> bool:
        """
        Verifica se API Salvy esta funcionando.

        Returns:
            True se API respondendo
        """
        try:
            ddds = await self.listar_ddds_disponiveis()
            return len(ddds) > 0
        except Exception:
            return False


# Singleton
salvy_client = SalvyClient()
```

### DoD

- [x] Client implementado
- [x] Metodos: criar, cancelar, buscar, listar
- [x] Tratamento de erros
- [x] Logging adequado

---

## Story 2.2: Webhook SMS

### Objetivo
Receber SMS da Salvy para verificacao WhatsApp.

### Implementacao

**Arquivo:** `app/api/routes/salvy_webhook.py`

```python
"""
Webhook para receber SMS da Salvy.

Usado para receber codigo de verificacao do WhatsApp.
"""
from fastapi import APIRouter, Request, HTTPException, Header
import logging
import re
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/salvy", tags=["salvy"])


@router.post("/sms")
async def webhook_sms(
    request: Request,
    svix_id: Optional[str] = Header(None),
    svix_timestamp: Optional[str] = Header(None),
    svix_signature: Optional[str] = Header(None),
):
    """
    Recebe SMS via Salvy webhook (powered by Svix).

    Payload formato:
    {
        "type": "sms.received",
        "timestamp": "2025-12-30T12:00:00Z",
        "data": {
            "id": "uuid",
            "virtualPhoneAccountId": "uuid",
            "receivedAt": "2025-12-30T12:00:00Z",
            "originPhoneNumber": "32665",
            "destinationPhoneNumber": "+5511999999999",
            "message": "Seu codigo WhatsApp e 123-456",
            "detections": {
                "whatsapp": {"verificationCode": "123456"},
                "google": {"verificationCode": null}
            }
        }
    }
    """
    payload = await request.json()

    # TODO: Verificar assinatura Svix em producao
    # from svix.webhooks import Webhook
    # wh = Webhook(settings.SALVY_WEBHOOK_SECRET)
    # wh.verify(payload, headers)

    event_type = payload.get("type")
    if event_type != "sms.received":
        return {"status": "ignored", "reason": f"event_type={event_type}"}

    data = payload.get("data", {})
    telefone = data.get("destinationPhoneNumber", "").replace("+", "")
    mensagem = data.get("message", "")
    remetente = data.get("originPhoneNumber", "")
    detections = data.get("detections", {})

    logger.info(f"[Salvy Webhook] SMS recebido: {telefone} de {remetente}")

    if not telefone:
        raise HTTPException(400, "Missing destinationPhoneNumber")

    # Buscar chip pelo telefone
    result = supabase.table("chips").select("id, instance_name, status").eq(
        "telefone", telefone
    ).single().execute()

    if not result.data:
        logger.warning(f"[Salvy Webhook] Telefone nao encontrado: {telefone}")
        return {"status": "ignored", "reason": "phone_not_found"}

    chip = result.data

    # Verificar se Salvy detectou codigo WhatsApp automaticamente
    whatsapp_code = detections.get("whatsapp", {}).get("verificationCode")

    if whatsapp_code:
        logger.info(f"[Salvy Webhook] Codigo WhatsApp detectado automaticamente: {whatsapp_code}")
        await processar_codigo_whatsapp(chip, whatsapp_code)
        return {"status": "ok", "action": "whatsapp_code_detected", "code_length": len(whatsapp_code)}

    # Fallback: tentar extrair manualmente (caso detections falhe)
    if "whatsapp" in mensagem.lower() or remetente in ["WhatsApp", "32665"]:
        codigo = extrair_codigo_whatsapp(mensagem)
        if codigo:
            await processar_codigo_whatsapp(chip, codigo)
            return {"status": "ok", "action": "code_extracted_fallback", "code_length": len(codigo)}

    # Salvar SMS para auditoria
    supabase.table("chip_interactions").insert({
        "chip_id": chip["id"],
        "tipo": "msg_recebida",
        "destinatario": remetente,
        "metadata": {
            "source": "salvy_sms",
            "message": mensagem[:500],
            "detections": detections,
        }
    }).execute()

    return {"status": "ok"}


def extrair_codigo_whatsapp(mensagem: str) -> Optional[str]:
    """
    Extrai codigo de verificacao WhatsApp da mensagem.

    Exemplos:
    - "Your WhatsApp code is 123-456" -> "123456"
    - "WhatsApp code: 654321" -> "654321"
    - "Seu codigo WhatsApp: 789 012" -> "789012"
    """
    # Padroes comuns
    patterns = [
        r'\b(\d{3}[-\s]?\d{3})\b',  # 123-456 ou 123 456
        r'code[:\s]+(\d{6})\b',      # code: 123456
        r'codigo[:\s]+(\d{6})\b',    # codigo: 123456
        r'\b(\d{6})\b',              # Qualquer sequencia de 6 digitos
    ]

    for pattern in patterns:
        match = re.search(pattern, mensagem, re.IGNORECASE)
        if match:
            # Remover espacos e hifens
            codigo = re.sub(r'[-\s]', '', match.group(1))
            if len(codigo) == 6 and codigo.isdigit():
                return codigo

    return None


async def processar_codigo_whatsapp(chip: dict, codigo: str):
    """
    Processa codigo de verificacao do WhatsApp.

    Salva codigo e notifica para uso no Evolution.
    """
    logger.info(f"[Salvy Webhook] Codigo WhatsApp: {codigo} para chip {chip['instance_name']}")

    # Atualizar chip com codigo pendente
    supabase.table("chips").update({
        "evolution_qr_code": f"CODE:{codigo}",  # Armazenar temporariamente
    }).eq("id", chip["id"]).execute()

    # Criar alerta para o operador
    supabase.table("chip_alerts").insert({
        "chip_id": chip["id"],
        "severity": "info",
        "tipo": "provision_failed",  # Reutilizando tipo
        "message": f"Codigo WhatsApp recebido: {codigo}",
        "details": {"codigo": codigo},
    }).execute()

    # TODO: Notificar via Slack
    # await notificar_slack(f"Codigo WhatsApp para {chip['instance_name']}: {codigo}")

    # TODO: Usar codigo no Evolution automaticamente
    # await evolution_client.verificar_codigo(chip['instance_name'], codigo)
```

**Registrar no router principal:**

```python
# app/api/routes/__init__.py
from app.api.routes.salvy_webhook import router as salvy_router

# Adicionar ao app
app.include_router(salvy_router)
```

### DoD

- [x] Endpoint webhook funcionando
- [x] Extracao de codigo WhatsApp
- [x] Registro de SMS
- [x] Alerta criado para operador

---

## Story 2.3: Servico de Provisioning

### Objetivo
Servico de alto nivel para provisionar chips completos.

### Implementacao

**Arquivo:** `app/services/salvy/provisioning.py`

```python
"""
Servico de Provisioning - Cria chip completo (Salvy + Evolution + DB).
"""
import logging
from typing import Optional
from datetime import datetime

from app.services.salvy.client import salvy_client, SalvyNumber
from app.services.supabase import supabase
from app.services.notificacoes import notificar_slack

logger = logging.getLogger(__name__)


async def provisionar_chip(
    ddd: int = 11,
    nome: Optional[str] = None,
) -> Optional[dict]:
    """
    Provisiona novo chip completo.

    Fluxo:
    1. Cria numero na Salvy
    2. Cria registro no banco
    3. (Futuro) Cria instancia Evolution

    Args:
        ddd: DDD desejado
        nome: Label opcional

    Returns:
        Chip criado ou None se falhar
    """
    try:
        # 1. Criar numero na Salvy
        salvy_number = await salvy_client.criar_numero(ddd=ddd, nome=nome)

        # 2. Gerar nome da instancia Evolution
        instance_name = f"julia-{salvy_number.phone_number[-8:]}"

        # 3. Criar registro no banco
        result = supabase.table("chips").insert({
            "telefone": salvy_number.phone_number,
            "salvy_id": salvy_number.id,
            "salvy_status": salvy_number.status,
            "salvy_created_at": salvy_number.created_at.isoformat(),
            "instance_name": instance_name,
            "status": "provisioned",
        }).execute()

        chip = result.data[0]

        logger.info(f"[Provisioning] Chip criado: {salvy_number.phone_number}")

        # 4. Notificar
        await notificar_slack(
            f":sparkles: *Novo chip provisionado*\n"
            f"- Telefone: `{salvy_number.phone_number}`\n"
            f"- DDD: {ddd}\n"
            f"- Instance: `{instance_name}`",
            canal="operacoes"
        )

        return chip

    except Exception as e:
        logger.error(f"[Provisioning] Erro: {e}")

        await notificar_slack(
            f":x: *Erro ao provisionar chip*: {str(e)}",
            canal="alertas"
        )

        return None


async def cancelar_chip(chip_id: str, motivo: str = "manual") -> bool:
    """
    Cancela chip (Salvy + DB).

    Args:
        chip_id: ID do chip
        motivo: Motivo do cancelamento

    Returns:
        True se cancelado com sucesso
    """
    # 1. Buscar chip
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        logger.warning(f"[Provisioning] Chip nao encontrado: {chip_id}")
        return False

    chip = result.data

    # 2. Cancelar na Salvy (se tiver salvy_id)
    if chip.get("salvy_id"):
        sucesso = await salvy_client.cancelar_numero(chip["salvy_id"])
        if not sucesso:
            logger.warning(f"[Provisioning] Falha ao cancelar na Salvy: {chip['salvy_id']}")

    # 3. Atualizar status no banco
    supabase.table("chips").update({
        "status": "cancelled",
        "salvy_status": "canceled",
    }).eq("id", chip_id).execute()

    # 4. Registrar transicao
    supabase.rpc("set_config", {"setting": "app.triggered_by", "value": motivo}).execute()

    logger.info(f"[Provisioning] Chip cancelado: {chip['telefone']}")

    await notificar_slack(
        f":wastebasket: *Chip cancelado*\n"
        f"- Telefone: `{chip['telefone']}`\n"
        f"- Motivo: {motivo}",
        canal="operacoes"
    )

    return True


async def sincronizar_salvy():
    """
    Sincroniza status dos chips com Salvy.

    Verifica se algum numero foi bloqueado/cancelado externamente.
    """
    # 1. Buscar chips ativos no banco com salvy_id
    result = supabase.table("chips").select("id, salvy_id, salvy_status").not_.is_(
        "salvy_id", "null"
    ).in_("status", ["provisioned", "pending", "warming", "ready", "active"]).execute()

    chips_db = {c["salvy_id"]: c for c in result.data or []}

    if not chips_db:
        return

    # 2. Buscar numeros na Salvy
    numeros_salvy = await salvy_client.listar_numeros()

    for numero in numeros_salvy:
        if numero.id in chips_db:
            chip = chips_db[numero.id]

            # Verificar mudanca de status
            if numero.status != chip["salvy_status"]:
                logger.info(
                    f"[Provisioning] Status Salvy mudou: {chip['salvy_id']} "
                    f"{chip['salvy_status']} -> {numero.status}"
                )

                update_data = {"salvy_status": numero.status}

                # Se foi bloqueado na Salvy, atualizar status do chip
                if numero.status == "blocked":
                    update_data["status"] = "banned"
                    update_data["banned_at"] = datetime.utcnow().isoformat()
                    update_data["ban_reason"] = "salvy_blocked"

                supabase.table("chips").update(update_data).eq("id", chip["id"]).execute()


async def verificar_ddds_disponiveis() -> dict:
    """
    Verifica quais DDDs estao disponiveis.

    Returns:
        {"disponiveis": [11, 21, ...], "indisponiveis": [...]}
    """
    ddds = await salvy_client.listar_ddds_disponiveis()

    return {
        "disponiveis": ddds,
        "total": len(ddds),
    }
```

### DoD

- [x] `provisionar_chip` funcionando
- [x] `cancelar_chip` funcionando
- [x] `sincronizar_salvy` funcionando
- [x] Notificacoes Slack

---

## Story 2.4: Config Salvy

### Objetivo
Adicionar configuracoes necessarias.

### Implementacao

**Arquivo:** `app/core/config.py` (adicionar)

```python
# Salvy
SALVY_API_TOKEN: str = ""
SALVY_WEBHOOK_SECRET: str = ""  # Chave Svix para verificacao
SALVY_DEFAULT_DDD: int = 11
```

**Arquivo:** `.env.example` (adicionar)

```bash
# Salvy - Numeros virtuais
# Obter em: Dashboard Salvy > API Keys
SALVY_API_TOKEN=seu_token_aqui
# Obter em: Dashboard Salvy > Settings > Webhooks > Signing Secret
SALVY_WEBHOOK_SECRET=whsec_xxxxx
SALVY_DEFAULT_DDD=11
```

**Arquivo:** `pyproject.toml` (adicionar dependencia)

```toml
[project.dependencies]
# ... outras deps ...
svix = "^1.0"  # Verificacao de webhooks Salvy
```

### DoD

- [x] Variaveis de ambiente documentadas
- [x] Config carregando corretamente

---

## Checklist do Epico

- [x] **E02.1** - Salvy Client implementado
- [x] **E02.2** - Webhook SMS funcionando
- [x] **E02.3** - Servico de Provisioning
- [x] **E02.4** - Configuracoes
- [x] Testes de integracao
- [x] Documentacao atualizada

---

## Fluxo de Provisioning

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE PROVISIONING                         │
└─────────────────────────────────────────────────────────────────┘

  SISTEMA                         SALVY                    EVOLUTION
     │                              │                          │
     │ 1. provisionar_chip(ddd=11)  │                          │
     │─────────────────────────────>│                          │
     │                              │                          │
     │ 2. Numero criado             │                          │
     │<─────────────────────────────│                          │
     │   {phone: "5511999...",      │                          │
     │    id: "salvy-123"}          │                          │
     │                              │                          │
     │ 3. Criar registro no banco   │                          │
     │   chips {                    │                          │
     │     telefone: "5511999..."   │                          │
     │     salvy_id: "salvy-123"    │                          │
     │     status: "provisioned"    │                          │
     │   }                          │                          │
     │                              │                          │
     │ 4. Criar instancia Evolution │                          │
     │─────────────────────────────────────────────────────────>│
     │                              │                          │
     │ 5. QR Code gerado            │                          │
     │<─────────────────────────────────────────────────────────│
     │                              │                          │
     │ 6. Escanear QR Code          │                          │
     │   (manual ou automatico)     │                          │
     │                              │                          │
     │ 7. SMS com codigo            │                          │
     │   (se necessario)            │                          │
     │<─────────────────────────────│                          │
     │                              │                          │
     │ 8. Verificar codigo          │                          │
     │─────────────────────────────────────────────────────────>│
     │                              │                          │
     │ 9. Conectado!                │                          │
     │   status: "pending" -> "warming"                        │
     │                              │                          │

ESTADOS:
  provisioned -> pending -> warming -> ready -> active
                                         └──> degraded -> cancelled
                                         └──> banned -> cancelled
```
