# Epic 01 - Instance Manager Service

**Sprint:** 37
**Estimativa:** 0.5 dia
**Prioridade:** P0 (Bloqueador)

---

## Objetivo

Criar serviço Python para gerenciar ciclo de vida de instâncias Evolution API.

---

## Escopo

### Arquivo
`app/services/chips/instance_manager.py`

### Métodos

```python
class InstanceManager:
    """Gerenciador de instâncias Evolution API."""

    async def criar_instancia(
        self,
        instance_name: str,
        telefone: str,
        chip_id: Optional[str] = None,
    ) -> dict:
        """
        Cria nova instância na Evolution API e registra no banco.

        Returns:
            {"sucesso": bool, "chip_id": str, "instance_name": str, "qr_code": str}
        """

    async def obter_qr_code(self, instance_name: str) -> dict:
        """
        Obtém QR Code para autenticação.

        Returns:
            {"qr_code": str (base64), "code": str, "connected": bool}
        """

    async def verificar_conexao(self, instance_name: str) -> dict:
        """
        Verifica estado da conexão.

        Returns:
            {"state": "open"|"close"|"connecting", "connected": bool}
        """

    async def desconectar_instancia(self, instance_name: str, chip_id: str) -> dict:
        """
        Desconecta instância (logout) sem deletar.

        Returns:
            {"sucesso": bool, "message": str}
        """

    async def deletar_instancia(self, instance_name: str, chip_id: str) -> dict:
        """
        Deleta instância da Evolution API e atualiza banco.

        Returns:
            {"sucesso": bool, "message": str}
        """

    async def reconectar_instancia(self, instance_name: str, chip_id: str) -> dict:
        """
        Reinicia instância e retorna novo QR code.

        Returns:
            {"sucesso": bool, "qr_code": str}
        """
```

---

## Endpoints Evolution API

| Operação | Método | Endpoint |
|----------|--------|----------|
| Criar | POST | `/instance/create` |
| QR Code | GET | `/instance/connect/{instance}` |
| Status | GET | `/instance/connectionState/{instance}` |
| Logout | DELETE | `/instance/logout/{instance}` |
| Delete | DELETE | `/instance/delete/{instance}` |

---

## Mapeamento de Estados

```
Evolution State → Chip Status     → Ação no Banco
───────────────────────────────────────────────────
"open"          → active/warming  → evolution_connected=true
"close"         → pending         → evolution_connected=false
"connecting"    → warming         → evolution_connected=false
```

---

## Implementação

### criar_instancia

```python
async def criar_instancia(self, instance_name: str, telefone: str):
    # 1. Validar nome único
    existing = supabase.table("chips").select("id").eq("instance_name", instance_name).execute()
    if existing.data:
        return {"sucesso": False, "error": "Nome de instância já existe"}

    # 2. Criar na Evolution API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.base_url}/instance/create",
            headers=self.headers,
            json={
                "instanceName": instance_name,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True
            }
        )
        data = response.json()

    # 3. Inserir chip no banco
    chip = supabase.table("chips").insert({
        "telefone": telefone,
        "instance_name": instance_name,
        "status": "pending",
        "evolution_connected": False,
        "evolution_qr_code": data.get("qrcode", {}).get("base64")
    }).execute()

    # 4. Retornar QR code
    return {
        "sucesso": True,
        "chip_id": chip.data[0]["id"],
        "instance_name": instance_name,
        "qr_code": data.get("qrcode", {}).get("base64")
    }
```

---

## Testes de Validação

- [ ] Criar instância com nome único
- [ ] Criar instância com nome duplicado (deve falhar)
- [ ] Obter QR code de instância existente
- [ ] Verificar conexão retorna estado correto
- [ ] Desconectar atualiza banco corretamente
- [ ] Deletar remove da Evolution e atualiza banco
- [ ] Reconectar gera novo QR code

---

## Dependências

- `httpx` para requests async
- `app.services.supabase` para acesso ao banco
- `app.core.config.settings` para variáveis de ambiente
