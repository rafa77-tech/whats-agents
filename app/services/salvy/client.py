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


class SalvyError(Exception):
    """Erro da API Salvy."""
    def __init__(self, message: str, status_code: int = 0):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SalvyClient:
    """Cliente para API Salvy."""

    def __init__(self):
        self.token = getattr(settings, 'SALVY_API_TOKEN', None)
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
        }

    def _check_token(self):
        """Verifica se token esta configurado."""
        if not self.token:
            raise SalvyError("SALVY_API_TOKEN nao configurado", 401)

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
        """
        self._check_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/virtual-phone-accounts",
                headers=self.headers,
                json={
                    "areaCode": ddd,
                    "name": nome or f"julia-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                },
                timeout=30,
            )

            if response.status_code >= 400:
                logger.error(f"[Salvy] Erro ao criar numero: {response.text}")
                raise SalvyError(response.text, response.status_code)

            data = response.json()

            logger.info(f"[Salvy] Numero criado: {data['phoneNumber']}")

            return SalvyNumber(
                id=data["id"],
                name=data.get("name"),
                phone_number=data["phoneNumber"],
                status=data["status"],
                created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
                canceled_at=None,
            )

    async def cancelar_numero(self, salvy_id: str) -> bool:
        """
        Cancela numero virtual (para de pagar).

        Args:
            salvy_id: ID do numero na Salvy

        Returns:
            True se cancelado com sucesso
        """
        self._check_token()

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{BASE_URL}/virtual-phone-accounts/{salvy_id}",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 204:
                logger.info(f"[Salvy] Numero cancelado: {salvy_id}")
                return True

            logger.error(f"[Salvy] Erro ao cancelar: {response.text}")
            return False

    async def buscar_numero(self, salvy_id: str) -> Optional[SalvyNumber]:
        """Busca numero por ID."""
        self._check_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/virtual-phone-accounts/{salvy_id}",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 404:
                return None

            if response.status_code >= 400:
                raise SalvyError(response.text, response.status_code)

            data = response.json()

            return SalvyNumber(
                id=data["id"],
                name=data.get("name"),
                phone_number=data["phoneNumber"],
                status=data["status"],
                created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
                canceled_at=datetime.fromisoformat(data["canceledAt"].replace("Z", "+00:00")) if data.get("canceledAt") else None,
            )

    async def listar_numeros(self) -> List[SalvyNumber]:
        """Lista todos os numeros."""
        self._check_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/virtual-phone-accounts",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code >= 400:
                raise SalvyError(response.text, response.status_code)

            return [
                SalvyNumber(
                    id=d["id"],
                    name=d.get("name"),
                    phone_number=d["phoneNumber"],
                    status=d["status"],
                    created_at=datetime.fromisoformat(d["createdAt"].replace("Z", "+00:00")),
                    canceled_at=datetime.fromisoformat(d["canceledAt"].replace("Z", "+00:00")) if d.get("canceledAt") else None,
                )
                for d in response.json()
            ]

    async def listar_ddds_disponiveis(self) -> List[int]:
        """Lista DDDs com numeros disponiveis."""
        self._check_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/virtual-phone-accounts/area-codes",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code >= 400:
                raise SalvyError(response.text, response.status_code)

            return response.json()


# Singleton
salvy_client = SalvyClient()
