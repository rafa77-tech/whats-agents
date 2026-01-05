"""
Salvy Integration - Provisioning de numeros virtuais.

Docs: https://docs.salvy.com.br/api-reference/virtual-phone-accounts/introduction
"""

from app.services.salvy.client import salvy_client, SalvyClient, SalvyNumber

__all__ = ["salvy_client", "SalvyClient", "SalvyNumber"]
