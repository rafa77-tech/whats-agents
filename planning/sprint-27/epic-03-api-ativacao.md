# Epic 03: API de Ativacao

**Status:** Pendente
**Estimativa:** 3 horas
**Prioridade:** Alta
**Dependencia:** E02 (Automacao WhatsApp)
**Responsavel:** Dev Junior

---

## Objetivo

Criar API REST (FastAPI) que expoe o servico de ativacao de chips para o backend Railway.

---

## Endpoints

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | /activate | Ativa um chip |
| GET | /queue | Status da fila |
| GET | /health | Health check |
| GET | /metrics | Metricas basicas |

---

## Story 3.1: Estrutura do Projeto FastAPI

### Objetivo
Criar estrutura de arquivos da API.

### Passo a Passo

**1. Criar estrutura de diretorios**

```bash
cd /opt/chip-activator

# Criar estrutura
mkdir -p api
touch api/__init__.py
touch api/main.py
touch api/models.py
touch api/queue.py
touch api/auth.py
```

**2. Criar arquivo de configuracao**

```bash
cat > /opt/chip-activator/config.py << 'EOF'
"""
Configuracoes do Chip Activator.
"""
import os
from pathlib import Path

# Diretorios
BASE_DIR = Path("/opt/chip-activator")
LOG_DIR = Path("/var/log/chip-activator")
SCREENSHOT_DIR = LOG_DIR / "screenshots"

# Criar diretorios se nao existirem
LOG_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")

# Appium
APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")

# Emulador
AVD_NAME = os.getenv("AVD_NAME", "chip-activator")
EMULATOR_BOOT_TIMEOUT = int(os.getenv("EMULATOR_BOOT_TIMEOUT", "120"))  # 2 min boot max

# Ativacao - Timeouts escalonados
AUTOMATION_TIMEOUT = int(os.getenv("AUTOMATION_TIMEOUT", "300"))  # 5 min automacao
ACTIVATION_TIMEOUT = int(os.getenv("ACTIVATION_TIMEOUT", "480"))  # 8 min total (2+5+1 buffer)
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "10"))
QUEUE_TIMEOUT = int(os.getenv("QUEUE_TIMEOUT", "600"))  # 10 minutos
EOF
```

**3. Criar modelos Pydantic**

```bash
cat > /opt/chip-activator/api/models.py << 'EOF'
"""
Modelos Pydantic para a API.
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ActivationStatus(str, Enum):
    """Status de uma ativacao."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ActivationRequest(BaseModel):
    """Request para ativar um chip."""
    numero: str = Field(..., description="Numero de telefone (sem +55)", example="11999990001")
    codigo_sms: str = Field(..., description="Codigo SMS de verificacao", example="123456")
    evolution_qr_url: str = Field(..., description="URL do QR code da Evolution API")

    class Config:
        json_schema_extra = {
            "example": {
                "numero": "11999990001",
                "codigo_sms": "123456",
                "evolution_qr_url": "https://evolution.example.com/qr/julia-001"
            }
        }


class ActivationResponse(BaseModel):
    """Response de uma ativacao."""
    status: ActivationStatus
    message: str
    activation_id: Optional[str] = None
    tempo_segundos: Optional[int] = None
    step: Optional[str] = None
    screenshot_path: Optional[str] = None


class QueueItem(BaseModel):
    """Item na fila de ativacao."""
    id: str
    numero: str
    status: ActivationStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QueueStatus(BaseModel):
    """Status da fila."""
    size: int
    items: list[QueueItem]
    current: Optional[QueueItem] = None


class HealthResponse(BaseModel):
    """Response do health check."""
    status: str  # healthy, degraded, unhealthy
    emulator: str  # running, stopped, error
    appium: str  # running, stopped
    queue_size: int
    last_activation: Optional[datetime] = None
    uptime_seconds: int


class MetricsResponse(BaseModel):
    """Metricas do servico."""
    total_activations: int
    successful_activations: int
    failed_activations: int
    success_rate: float
    average_time_seconds: float
    last_24h_activations: int
EOF
```

### DoD

- [ ] Estrutura de pastas criada
- [ ] config.py criado
- [ ] models.py criado

---

## Story 3.2: Sistema de Fila

### Objetivo
Implementar fila sequencial de ativacoes.

### Passo a Passo

**1. Criar modulo de fila**

```bash
cat > /opt/chip-activator/api/queue.py << 'EOF'
"""
Sistema de fila para ativacoes.
Apenas uma ativacao por vez.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict
from uuid import uuid4
from collections import deque

from api.models import ActivationStatus, QueueItem

logger = logging.getLogger(__name__)


class ActivationQueue:
    """Fila de ativacoes (singleton)."""

    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.queue: deque[QueueItem] = deque()
        self.current: Optional[QueueItem] = None
        self.lock = asyncio.Lock()
        self.results: Dict[str, dict] = {}  # id -> resultado

    async def add(self, numero: str, codigo_sms: str, qr_url: str) -> Optional[QueueItem]:
        """
        Adiciona item a fila.

        Returns:
            QueueItem se adicionado, None se fila cheia
        """
        async with self.lock:
            if len(self.queue) >= self.max_size:
                logger.warning(f"Fila cheia ({self.max_size})")
                return None

            item = QueueItem(
                id=str(uuid4()),
                numero=numero,
                status=ActivationStatus.QUEUED,
                created_at=datetime.utcnow()
            )

            # Armazenar dados completos no results
            self.results[item.id] = {
                "numero": numero,
                "codigo_sms": codigo_sms,
                "qr_url": qr_url,
                "item": item
            }

            self.queue.append(item)
            logger.info(f"Item adicionado a fila: {item.id} (posicao {len(self.queue)})")

            return item

    async def get_next(self) -> Optional[tuple]:
        """
        Pega proximo item da fila para processar.

        Returns:
            (item, numero, codigo_sms, qr_url) ou None
        """
        async with self.lock:
            if self.current is not None:
                return None  # Ja tem um em processamento

            if not self.queue:
                return None

            item = self.queue.popleft()
            item.status = ActivationStatus.RUNNING
            item.started_at = datetime.utcnow()
            self.current = item

            data = self.results.get(item.id, {})

            logger.info(f"Processando: {item.id}")
            return (item, data.get("numero"), data.get("codigo_sms"), data.get("qr_url"))

    async def complete(self, item_id: str, success: bool, result: dict):
        """
        Marca item como completo.

        Args:
            item_id: ID do item
            success: Se foi sucesso
            result: Resultado da ativacao
        """
        async with self.lock:
            if self.current and self.current.id == item_id:
                self.current.status = ActivationStatus.SUCCESS if success else ActivationStatus.FAILED
                self.current.completed_at = datetime.utcnow()

                # Atualizar resultado
                if item_id in self.results:
                    self.results[item_id]["result"] = result

                logger.info(f"Completado: {item_id} - {'sucesso' if success else 'falha'}")
                self.current = None

    async def get_status(self) -> dict:
        """Retorna status da fila."""
        return {
            "size": len(self.queue),
            "items": list(self.queue),
            "current": self.current
        }

    async def get_result(self, item_id: str) -> Optional[dict]:
        """Retorna resultado de uma ativacao."""
        return self.results.get(item_id)

    async def cleanup_old(self, max_age_seconds: int = 3600):
        """Remove resultados antigos."""
        now = datetime.utcnow()
        to_remove = []

        for item_id, data in self.results.items():
            item = data.get("item")
            if item and item.completed_at:
                age = (now - item.completed_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(item_id)

        for item_id in to_remove:
            del self.results[item_id]

        if to_remove:
            logger.info(f"Limpeza: removidos {len(to_remove)} resultados antigos")


# Singleton
activation_queue = ActivationQueue()
EOF
```

### DoD

- [ ] queue.py criado
- [ ] Fila thread-safe com asyncio.Lock
- [ ] Maximo de items configuravel

---

## Story 3.3: Autenticacao

### Objetivo
Implementar autenticacao via API Key.

### Passo a Passo

**1. Criar modulo de autenticacao**

```bash
cat > /opt/chip-activator/api/auth.py << 'EOF'
"""
Autenticacao da API via API Key.
"""
import logging
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from config import API_KEY

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verifica API Key no header.

    Raises:
        HTTPException 401 se invalida
        HTTPException 403 se ausente

    Returns:
        API Key validada
    """
    if not api_key:
        logger.warning("Requisicao sem API Key")
        raise HTTPException(
            status_code=403,
            detail="API Key ausente. Use header X-API-Key."
        )

    if api_key != API_KEY:
        logger.warning(f"API Key invalida: {api_key[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="API Key invalida"
        )

    return api_key
EOF
```

### DoD

- [ ] auth.py criado
- [ ] Verifica header X-API-Key

---

## Story 3.4: Endpoint POST /activate

### Objetivo
Implementar endpoint principal de ativacao.

### Passo a Passo

**1. Criar main.py com endpoint**

```bash
cat > /opt/chip-activator/api/main.py << 'EOF'
"""
API de Ativacao de Chips WhatsApp.
"""
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from config import API_HOST, API_PORT
from api.models import (
    ActivationRequest, ActivationResponse, ActivationStatus,
    QueueStatus, HealthResponse, MetricsResponse
)
from api.queue import activation_queue
from api.auth import verify_api_key

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Metricas globais
metrics = {
    "total_activations": 0,
    "successful_activations": 0,
    "failed_activations": 0,
    "total_time_seconds": 0,
    "start_time": datetime.utcnow(),
    "last_activation": None
}

# Worker de processamento
worker_task = None


async def process_queue():
    """Worker que processa a fila de ativacoes."""
    from whatsapp_automation import ativar_chip

    logger.info("Worker de ativacao iniciado")

    while True:
        try:
            # Pegar proximo da fila
            next_item = await activation_queue.get_next()

            if next_item:
                item, numero, codigo_sms, qr_url = next_item
                logger.info(f"Processando ativacao: {item.id}")

                try:
                    # Executar ativacao
                    resultado = ativar_chip(numero, codigo_sms, qr_url)

                    # Atualizar metricas
                    metrics["total_activations"] += 1
                    metrics["last_activation"] = datetime.utcnow()
                    metrics["total_time_seconds"] += resultado.get("tempo_segundos", 0)

                    if resultado.get("success"):
                        metrics["successful_activations"] += 1
                    else:
                        metrics["failed_activations"] += 1

                    # Marcar como completo
                    await activation_queue.complete(
                        item.id,
                        resultado.get("success", False),
                        resultado
                    )

                except Exception as e:
                    logger.error(f"Erro ao processar {item.id}: {e}")
                    await activation_queue.complete(item.id, False, {"error": str(e)})
                    metrics["total_activations"] += 1
                    metrics["failed_activations"] += 1

            # Aguardar antes de verificar novamente
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Erro no worker: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicacao."""
    global worker_task

    # Startup
    logger.info("Iniciando API de Ativacao...")
    worker_task = asyncio.create_task(process_queue())

    yield

    # Shutdown
    logger.info("Encerrando API...")
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


# Criar app
app = FastAPI(
    title="Chip Activator API",
    description="API para ativacao automatizada de chips WhatsApp",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/activate", response_model=ActivationResponse)
async def activate_chip(
    request: ActivationRequest,
    api_key: str = Depends(verify_api_key)
) -> ActivationResponse:
    """
    Adiciona chip a fila de ativacao.

    O chip sera processado assim que possivel (fila FIFO).
    Use GET /queue/{id} para verificar o status.
    """
    logger.info(f"Requisicao de ativacao: {request.numero}")

    # Validar numero
    if not request.numero.isdigit() or len(request.numero) < 10:
        raise HTTPException(400, "Numero invalido")

    # Validar codigo SMS
    if not request.codigo_sms.isdigit() or len(request.codigo_sms) != 6:
        raise HTTPException(400, "Codigo SMS deve ter 6 digitos")

    # Adicionar a fila
    item = await activation_queue.add(
        request.numero,
        request.codigo_sms,
        request.evolution_qr_url
    )

    if not item:
        raise HTTPException(503, "Fila cheia. Tente novamente em alguns minutos.")

    return ActivationResponse(
        status=ActivationStatus.QUEUED,
        message=f"Chip adicionado a fila (posicao {await activation_queue.get_status()['size']})",
        activation_id=item.id
    )


@app.get("/activate/{activation_id}", response_model=ActivationResponse)
async def get_activation_status(
    activation_id: str,
    api_key: str = Depends(verify_api_key)
) -> ActivationResponse:
    """
    Consulta status de uma ativacao.
    """
    result = await activation_queue.get_result(activation_id)

    if not result:
        raise HTTPException(404, "Ativacao nao encontrada")

    item = result.get("item")
    activation_result = result.get("result", {})

    return ActivationResponse(
        status=item.status,
        message=activation_result.get("message", "Em processamento"),
        activation_id=activation_id,
        tempo_segundos=activation_result.get("tempo_segundos"),
        step=activation_result.get("step"),
        screenshot_path=activation_result.get("screenshot")
    )


@app.get("/queue", response_model=QueueStatus)
async def get_queue_status(
    api_key: str = Depends(verify_api_key)
) -> QueueStatus:
    """
    Retorna status da fila de ativacoes.
    """
    status = await activation_queue.get_status()
    return QueueStatus(**status)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check do servico (sem autenticacao).
    """
    import subprocess
    import requests

    # Verificar emulador
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        emulator_status = "running" if "emulator" in result.stdout else "stopped"
    except Exception:
        emulator_status = "error"

    # Verificar Appium
    try:
        response = requests.get("http://127.0.0.1:4723/status", timeout=5)
        appium_status = "running" if response.ok else "error"
    except Exception:
        appium_status = "stopped"

    # Calcular uptime
    uptime = (datetime.utcnow() - metrics["start_time"]).total_seconds()

    # Determinar status geral
    if emulator_status == "error" or appium_status == "error":
        overall_status = "unhealthy"
    elif emulator_status == "stopped":
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    queue_status = await activation_queue.get_status()

    return HealthResponse(
        status=overall_status,
        emulator=emulator_status,
        appium=appium_status,
        queue_size=queue_status["size"],
        last_activation=metrics["last_activation"],
        uptime_seconds=int(uptime)
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    api_key: str = Depends(verify_api_key)
) -> MetricsResponse:
    """
    Retorna metricas do servico.
    """
    total = metrics["total_activations"]
    successful = metrics["successful_activations"]
    failed = metrics["failed_activations"]

    success_rate = (successful / total * 100) if total > 0 else 0
    avg_time = (metrics["total_time_seconds"] / total) if total > 0 else 0

    return MetricsResponse(
        total_activations=total,
        successful_activations=successful,
        failed_activations=failed,
        success_rate=round(success_rate, 2),
        average_time_seconds=round(avg_time, 2),
        last_24h_activations=total  # TODO: filtrar por tempo
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
EOF
```

### DoD

- [ ] main.py criado
- [ ] POST /activate funciona
- [ ] GET /activate/{id} funciona
- [ ] Worker processa fila

---

## Story 3.5: Testar API Localmente

### Objetivo
Testar todos os endpoints da API.

### Passo a Passo

**1. Iniciar servicos**

```bash
cd /opt/chip-activator
source venv/bin/activate

# Iniciar emulador
./start_emulator.sh

# Iniciar Appium
./start_appium.sh

# Iniciar API
python -m api.main
```

**2. Testar health check (sem auth)**

```bash
# Em outro terminal
curl http://localhost:8000/health
# Deve retornar JSON com status
```

**3. Testar POST /activate (com auth)**

```bash
# Sem API Key (deve falhar)
curl -X POST http://localhost:8000/activate \
  -H "Content-Type: application/json" \
  -d '{"numero": "11999990001", "codigo_sms": "123456", "evolution_qr_url": "http://example.com/qr"}'
# Deve retornar 403

# Com API Key
curl -X POST http://localhost:8000/activate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{"numero": "11999990001", "codigo_sms": "123456", "evolution_qr_url": "http://example.com/qr"}'
# Deve retornar activation_id
```

**4. Consultar status**

```bash
curl http://localhost:8000/activate/SEU_ACTIVATION_ID \
  -H "X-API-Key: dev-key-change-in-production"
```

**5. Ver fila**

```bash
curl http://localhost:8000/queue \
  -H "X-API-Key: dev-key-change-in-production"
```

**6. Ver metricas**

```bash
curl http://localhost:8000/metrics \
  -H "X-API-Key: dev-key-change-in-production"
```

### DoD

- [ ] Health check funciona
- [ ] POST /activate adiciona a fila
- [ ] GET /activate/{id} retorna status
- [ ] GET /queue mostra fila
- [ ] GET /metrics mostra metricas
- [ ] Auth bloqueia sem API Key

---

## Checklist Final E03

- [ ] **Story 3.1** - Estrutura do projeto criada
- [ ] **Story 3.2** - Sistema de fila implementado
- [ ] **Story 3.3** - Autenticacao via API Key
- [ ] **Story 3.4** - Endpoints implementados
- [ ] **Story 3.5** - Testes locais passando

---

## Estrutura Final

```
/opt/chip-activator/
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── models.py        # Pydantic models
│   ├── queue.py         # Sistema de fila
│   └── auth.py          # Autenticacao
├── config.py            # Configuracoes
├── whatsapp_automation.py  # Script de automacao
├── venv/                # Ambiente virtual
└── requirements.txt
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 3.1 Estrutura | 30min |
| 3.2 Fila | 45min |
| 3.3 Auth | 15min |
| 3.4 Endpoints | 1h |
| 3.5 Testes | 30min |
| **Total** | ~3 horas |

---

## Proximo Epic

[E04: Deploy e Monitoramento](./epic-04-deploy-monitoramento.md)
