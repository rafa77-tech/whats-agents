# Epic 05: Integracao Railway

**Status:** Pendente
**Estimativa:** 2 horas
**Prioridade:** Alta
**Dependencia:** E04 (Deploy e Monitoramento)
**Responsavel:** Dev Junior

---

## Objetivo

Integrar o backend Julia (Railway) com a API de ativacao no VPS para que:
1. Ao provisionar chip via Salvy, chame automaticamente a API de ativacao
2. Apos ativacao bem-sucedida, atualize status do chip no banco

---

## Contexto

```
FLUXO COMPLETO DE ATIVACAO

1. Backend Railway
   ├─ Provisiona numero via Salvy API
   ├─ Recebe salvy_id e telefone
   └─ Cria instancia Evolution → Gera QR code

2. Backend Railway (apos webhook SMS Salvy)
   ├─ Recebe codigo SMS
   └─ Chama POST /activate no VPS
       {
         numero: "11999990001",
         codigo_sms: "123456",
         evolution_qr_url: "https://evolution.../qr/julia-001"
       }

3. VPS Hostinger
   ├─ Recebe requisicao
   ├─ Liga emulador
   ├─ Ativa WhatsApp
   └─ Retorna sucesso/falha

4. Backend Railway
   ├─ Recebe resposta
   ├─ Atualiza status do chip
   └─ Chip entra em warming!
```

---

## Story 5.1: Adicionar Variaveis de Ambiente

### Objetivo
Configurar URL e API Key do VPS no Railway.

### Passo a Passo

**1. Definir variaveis no Railway**

Via Dashboard Railway ou CLI:

```bash
# Via CLI
railway variables set CHIP_ACTIVATOR_URL="https://VPS_IP_OU_DOMINIO"
railway variables set CHIP_ACTIVATOR_API_KEY="sua-api-key-segura"
```

Via Dashboard:
1. Acessar projeto no Railway
2. Ir em Settings > Variables
3. Adicionar:
   - `CHIP_ACTIVATOR_URL`: URL do VPS (ex: https://activator.example.com)
   - `CHIP_ACTIVATOR_API_KEY`: API Key definida no VPS

**2. Adicionar ao settings da aplicacao**

Em `app/core/config.py`:

```python
# Chip Activator (VPS)
CHIP_ACTIVATOR_URL: str = ""
CHIP_ACTIVATOR_API_KEY: str = ""
```

### DoD

- [ ] Variaveis configuradas no Railway
- [ ] Settings da app atualizados

---

## Story 5.2: Criar Cliente HTTP para API de Ativacao

### Objetivo
Criar modulo que chama a API de ativacao no VPS.

### Passo a Passo

**1. Criar arquivo do cliente**

Criar `app/services/chip_activator/client.py`:

```python
"""
Cliente para API de Ativacao de Chips (VPS).

Este modulo permite chamar a API de ativacao automatizada
que roda no VPS Hostinger.
"""
import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChipActivatorError(Exception):
    """Erro ao ativar chip."""
    pass


class ChipActivatorClient:
    """Cliente para API de Ativacao."""

    def __init__(self):
        self.base_url = settings.CHIP_ACTIVATOR_URL.rstrip("/")
        self.api_key = settings.CHIP_ACTIVATOR_API_KEY
        self.timeout = 600  # 10 minutos (ativacao pode demorar)

    @property
    def headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def health_check(self) -> dict:
        """
        Verifica status da API de ativacao.

        Returns:
            Status da API (healthy, degraded, unhealthy)
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"[ChipActivator] Health check falhou: {e}")
            return {"status": "unreachable", "error": str(e)}

    async def ativar_chip(
        self,
        numero: str,
        codigo_sms: str,
        evolution_qr_url: str
    ) -> dict:
        """
        Solicita ativacao de um chip.

        Args:
            numero: Numero de telefone (sem +55)
            codigo_sms: Codigo de verificacao SMS
            evolution_qr_url: URL do QR code da Evolution API

        Returns:
            {
                "success": bool,
                "activation_id": str,
                "message": str,
                "tempo_segundos": int
            }

        Raises:
            ChipActivatorError: Se falhar ao chamar API
        """
        if not self.base_url or not self.api_key:
            raise ChipActivatorError("CHIP_ACTIVATOR_URL ou CHIP_ACTIVATOR_API_KEY nao configurado")

        logger.info(f"[ChipActivator] Solicitando ativacao: {numero[:6]}****")

        payload = {
            "numero": numero,
            "codigo_sms": codigo_sms,
            "evolution_qr_url": evolution_qr_url
        }

        try:
            async with httpx.AsyncClient() as client:
                # Adicionar a fila
                response = await client.post(
                    f"{self.base_url}/activate",
                    json=payload,
                    headers=self.headers,
                    timeout=30
                )

                if response.status_code == 503:
                    raise ChipActivatorError("Fila de ativacao cheia. Tentar novamente depois.")

                response.raise_for_status()
                data = response.json()

                activation_id = data.get("activation_id")
                logger.info(f"[ChipActivator] Chip adicionado a fila: {activation_id}")

                # Aguardar conclusao (polling)
                result = await self._aguardar_ativacao(activation_id)
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"[ChipActivator] HTTP Error: {e.response.status_code} - {e.response.text}")
            raise ChipActivatorError(f"Erro HTTP: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[ChipActivator] Request Error: {e}")
            raise ChipActivatorError(f"Erro de conexao: {e}")
        except Exception as e:
            logger.error(f"[ChipActivator] Erro inesperado: {e}")
            raise ChipActivatorError(str(e))

    async def _aguardar_ativacao(
        self,
        activation_id: str,
        timeout_seconds: int = 600,
        poll_interval: int = 10
    ) -> dict:
        """
        Aguarda conclusao da ativacao (polling).

        Args:
            activation_id: ID da ativacao
            timeout_seconds: Tempo maximo de espera
            poll_interval: Intervalo entre verificacoes

        Returns:
            Resultado da ativacao
        """
        import asyncio

        elapsed = 0

        while elapsed < timeout_seconds:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/activate/{activation_id}",
                        headers=self.headers,
                        timeout=30
                    )
                    response.raise_for_status()
                    data = response.json()

                    status = data.get("status")

                    if status == "success":
                        logger.info(f"[ChipActivator] Ativacao concluida: {activation_id}")
                        return {
                            "success": True,
                            "activation_id": activation_id,
                            "message": data.get("message", "Chip ativado com sucesso"),
                            "tempo_segundos": data.get("tempo_segundos", 0)
                        }

                    elif status == "failed":
                        logger.warning(f"[ChipActivator] Ativacao falhou: {activation_id}")
                        return {
                            "success": False,
                            "activation_id": activation_id,
                            "message": data.get("message", "Falha na ativacao"),
                            "step": data.get("step"),
                            "screenshot": data.get("screenshot_path")
                        }

                    elif status in ("queued", "running"):
                        logger.debug(f"[ChipActivator] Status: {status}, aguardando...")

                    else:
                        logger.warning(f"[ChipActivator] Status desconhecido: {status}")

            except Exception as e:
                logger.warning(f"[ChipActivator] Erro no polling: {e}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout
        logger.error(f"[ChipActivator] Timeout aguardando ativacao: {activation_id}")
        return {
            "success": False,
            "activation_id": activation_id,
            "message": "Timeout aguardando ativacao"
        }

    async def verificar_fila(self) -> dict:
        """
        Verifica status da fila de ativacao.

        Returns:
            Status da fila (size, items, current)
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/queue",
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"[ChipActivator] Erro ao verificar fila: {e}")
            return {"error": str(e)}


# Singleton
chip_activator_client = ChipActivatorClient()
```

**2. Criar __init__.py**

```bash
# Criar diretorio se nao existir
mkdir -p app/services/chip_activator
touch app/services/chip_activator/__init__.py

echo 'from app.services.chip_activator.client import chip_activator_client, ChipActivatorError' > app/services/chip_activator/__init__.py
```

### DoD

- [ ] Cliente criado em `app/services/chip_activator/`
- [ ] Metodos ativar_chip, health_check, verificar_fila
- [ ] Polling para aguardar conclusao

---

## Story 5.3: Integrar no Fluxo de Provisioning

### Objetivo
Chamar ativacao automaticamente apos receber codigo SMS.

### Contexto do Fluxo

O webhook da Salvy recebe SMS com codigo. Nesse momento, precisamos:
1. Extrair codigo
2. Buscar chip pelo telefone
3. Obter URL do QR code da Evolution
4. Chamar API de ativacao
5. Atualizar status do chip

### Passo a Passo

**1. Atualizar webhook Salvy**

Em `app/services/salvy/webhooks.py`, adicionar integracao:

```python
"""
Webhook para receber SMS da Salvy - COM ATIVACAO AUTOMATICA.
"""
import logging
from app.services.supabase import supabase
from app.services.chip_activator import chip_activator_client, ChipActivatorError
from app.services.evolution import evolution_client

logger = logging.getLogger(__name__)


async def processar_codigo_whatsapp(telefone: str, codigo: str):
    """
    Processa codigo de verificacao do WhatsApp.

    1. Busca chip pelo telefone
    2. Obtem QR code da Evolution
    3. Chama API de ativacao
    4. Atualiza status do chip
    """
    logger.info(f"[SalvyWebhook] Codigo WhatsApp recebido para {telefone[:6]}****")

    try:
        # 1. Buscar chip pelo telefone
        result = supabase.table("chips").select("*").eq("telefone", telefone).single().execute()
        chip = result.data

        if not chip:
            logger.error(f"[SalvyWebhook] Chip nao encontrado: {telefone}")
            return

        chip_id = chip["id"]
        instance_name = chip["instance_name"]

        logger.info(f"[SalvyWebhook] Chip encontrado: {chip_id}")

        # 2. Obter URL do QR code da Evolution
        # A Evolution API deve ter um endpoint para isso
        qr_url = await evolution_client.get_qr_code_url(instance_name)

        if not qr_url:
            logger.error(f"[SalvyWebhook] QR code nao disponivel para {instance_name}")
            # Atualizar status para erro
            supabase.table("chips").update({
                "status": "pending",
                "evolution_qr_code": None
            }).eq("id", chip_id).execute()
            return

        # 3. Chamar API de ativacao
        logger.info(f"[SalvyWebhook] Chamando API de ativacao...")

        resultado = await chip_activator_client.ativar_chip(
            numero=telefone,
            codigo_sms=codigo,
            evolution_qr_url=qr_url
        )

        # 4. Atualizar status do chip
        if resultado.get("success"):
            logger.info(f"[SalvyWebhook] Chip ativado com sucesso: {chip_id}")

            supabase.table("chips").update({
                "status": "warming",
                "evolution_connected": True,
                "warming_started_at": "now()",
                "fase_warmup": "repouso"
            }).eq("id", chip_id).execute()

            # Registrar transicao
            supabase.table("chip_transitions").insert({
                "chip_id": chip_id,
                "from_status": chip["status"],
                "to_status": "warming",
                "reason": "Ativacao automatica bem-sucedida",
                "triggered_by": "chip_activator"
            }).execute()

        else:
            logger.warning(f"[SalvyWebhook] Ativacao falhou: {chip_id}")

            supabase.table("chips").update({
                "status": "pending"
            }).eq("id", chip_id).execute()

            # Criar alerta
            supabase.table("chip_alerts").insert({
                "chip_id": chip_id,
                "severity": "warning",
                "tipo": "provision_failed",
                "message": resultado.get("message", "Falha na ativacao automatica"),
                "acao_tomada": "none"
            }).execute()

    except ChipActivatorError as e:
        logger.error(f"[SalvyWebhook] Erro no activator: {e}")
        # Criar alerta para intervencao manual

    except Exception as e:
        logger.error(f"[SalvyWebhook] Erro inesperado: {e}")
```

**2. Atualizar webhook de SMS (se ainda nao existe)**

Verificar se o endpoint `/webhooks/salvy/sms` chama `processar_codigo_whatsapp`.

### DoD

- [ ] Webhook Salvy chama ativacao automaticamente
- [ ] Status do chip atualizado apos ativacao
- [ ] Alertas criados em caso de falha

---

## Story 5.4: Adicionar Endpoint de Health Check

### Objetivo
Backend Julia poder verificar se VPS esta funcionando.

### Passo a Passo

**1. Adicionar rota de verificacao**

Em `app/api/routes/health.py` ou similar:

```python
from fastapi import APIRouter
from app.services.chip_activator import chip_activator_client

router = APIRouter()


@router.get("/health/chip-activator")
async def health_chip_activator():
    """
    Verifica status da API de ativacao de chips.
    """
    status = await chip_activator_client.health_check()
    return {
        "service": "chip-activator",
        "status": status.get("status", "unknown"),
        "details": status
    }
```

### DoD

- [ ] Endpoint de health check criado
- [ ] Retorna status do VPS

---

## Story 5.5: Testar Integracao End-to-End

### Objetivo
Validar fluxo completo de ativacao.

### Passo a Passo

**1. Teste manual via curl**

```bash
# No ambiente de desenvolvimento

# 1. Verificar health do VPS
curl https://VPS_URL/health

# 2. Verificar fila
curl https://VPS_URL/queue \
  -H "X-API-Key: SUA_API_KEY"

# 3. Simular ativacao
curl -X POST https://VPS_URL/activate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: SUA_API_KEY" \
  -d '{
    "numero": "11999990001",
    "codigo_sms": "123456",
    "evolution_qr_url": "https://evolution.example.com/qr/test"
  }'
```

**2. Teste via Python**

```python
import asyncio
from app.services.chip_activator import chip_activator_client

async def test():
    # Health
    health = await chip_activator_client.health_check()
    print(f"Health: {health}")

    # Fila
    queue = await chip_activator_client.verificar_fila()
    print(f"Fila: {queue}")

asyncio.run(test())
```

**3. Teste com chip real**

Usar um numero de teste da Salvy:
1. Provisionar numero
2. Criar instancia Evolution
3. Aguardar SMS com codigo
4. Verificar se ativacao foi chamada
5. Verificar status final do chip

### DoD

- [ ] Health check funciona
- [ ] Fila consultavel
- [ ] Ativacao testada com chip real

---

## Checklist Final E05

- [ ] **Story 5.1** - Variaveis de ambiente configuradas
- [ ] **Story 5.2** - Cliente HTTP criado
- [ ] **Story 5.3** - Integracao no webhook Salvy
- [ ] **Story 5.4** - Endpoint health check
- [ ] **Story 5.5** - Teste end-to-end

---

## Arquivos Criados/Modificados

```
app/
├── core/
│   └── config.py              # + CHIP_ACTIVATOR_URL, CHIP_ACTIVATOR_API_KEY
├── services/
│   └── chip_activator/
│       ├── __init__.py
│       └── client.py          # ChipActivatorClient
└── api/routes/
    └── health.py              # + /health/chip-activator
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 5.1 Variaveis | 15min |
| 5.2 Cliente | 45min |
| 5.3 Integracao | 30min |
| 5.4 Health | 15min |
| 5.5 Testes | 15min |
| **Total** | ~2 horas |

---

## Proximo Epic

[E06: Documentacao e Runbook](./epic-06-documentacao-runbook.md)
