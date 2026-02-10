"""
Chip Activator Service.

Sprint 27 - Cliente para API de ativacao automatizada de chips WhatsApp.
"""

from app.services.chip_activator.client import (
    ChipActivatorClient,
    ChipActivatorError,
    chip_activator_client,
)

__all__ = [
    "ChipActivatorClient",
    "ChipActivatorError",
    "chip_activator_client",
]
