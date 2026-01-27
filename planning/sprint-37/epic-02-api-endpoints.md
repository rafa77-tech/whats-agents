# Epic 02 - API Endpoints

**Sprint:** 37
**Estimativa:** 0.5 dia
**Prioridade:** P0 (Bloqueador)
**Depende de:** Epic 01

---

## Objetivo

Adicionar endpoints REST para gerenciamento de instâncias no router do dashboard.

---

## Arquivo

`app/api/routes/chips_dashboard.py`

---

## Endpoints

### 1. Criar Instância

```python
@router.post("/instances/create")
async def create_instance(request: CreateInstanceRequest):
    """
    Cria nova instância Evolution API e chip no banco.
    Retorna QR code para autenticação.
    """
```

**Request:**
```json
{
  "telefone": "5511999999999",
  "instance_name": "julia-99999999"  // opcional
}
```

**Response:**
```json
{
  "sucesso": true,
  "chip_id": "uuid",
  "instance_name": "julia-99999999",
  "qr_code": "data:image/png;base64,..."
}
```

---

### 2. Obter QR Code

```python
@router.get("/instances/{instance_name}/qr-code")
async def get_qr_code(instance_name: str):
    """
    Obtém QR code para autenticação da instância.
    """
```

**Response:**
```json
{
  "qr_code": "data:image/png;base64,...",
  "code": "ABC-123-XYZ",
  "connected": false,
  "instance_name": "julia-99999999"
}
```

---

### 3. Status de Conexão

```python
@router.get("/instances/{instance_name}/connection-state")
async def get_connection_state(instance_name: str):
    """
    Verifica estado atual da conexão.
    """
```

**Response:**
```json
{
  "state": "open",  // "open" | "close" | "connecting"
  "connected": true,
  "instance_name": "julia-99999999"
}
```

---

### 4. Desconectar

```python
@router.post("/{chip_id}/disconnect")
async def disconnect_chip(chip_id: str):
    """
    Desconecta chip (logout do WhatsApp).
    Mantém registro no banco, apenas desconecta sessão.
    """
```

**Response:**
```json
{
  "sucesso": true,
  "message": "Instância desconectada com sucesso"
}
```

---

### 5. Excluir Instância

```python
@router.delete("/{chip_id}/instance")
async def delete_chip_instance(chip_id: str):
    """
    Deleta instância e marca chip como cancelado.
    Operação irreversível na Evolution API.
    """
```

**Response:**
```json
{
  "sucesso": true,
  "message": "Instância excluída com sucesso"
}
```

---

### 6. Reconectar

```python
@router.post("/{chip_id}/reconnect")
async def reconnect_chip(chip_id: str):
    """
    Reconecta chip desconectado.
    Gera novo QR code para autenticação.
    """
```

**Response:**
```json
{
  "sucesso": true,
  "qr_code": "data:image/png;base64,...",
  "code": "ABC-123-XYZ",
  "instance_name": "julia-99999999"
}
```

---

## Schemas Pydantic

```python
from pydantic import BaseModel
from typing import Optional, Literal

class CreateInstanceRequest(BaseModel):
    telefone: str
    instance_name: Optional[str] = None

class CreateInstanceResponse(BaseModel):
    sucesso: bool
    chip_id: Optional[str] = None
    instance_name: Optional[str] = None
    qr_code: Optional[str] = None
    error: Optional[str] = None

class QRCodeResponse(BaseModel):
    qr_code: str
    code: str
    connected: bool
    instance_name: str

class ConnectionStateResponse(BaseModel):
    state: Literal["open", "close", "connecting"]
    connected: bool
    instance_name: str

class InstanceActionResponse(BaseModel):
    sucesso: bool
    message: Optional[str] = None
    error: Optional[str] = None
```

---

## Validação

- [ ] POST /instances/create cria instância e retorna QR
- [ ] GET /instances/{name}/qr-code retorna QR válido
- [ ] GET /instances/{name}/connection-state retorna estado
- [ ] POST /{id}/disconnect desconecta e atualiza banco
- [ ] DELETE /{id}/instance deleta e marca como cancelled
- [ ] POST /{id}/reconnect gera novo QR
- [ ] Erros retornam mensagens claras
