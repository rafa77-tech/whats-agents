"""
Carousel Message Builder.

Sprint 70+ — Chunk 25.

Horizontal scrollable cards with image + CTA button.
Up to 10 cards per carousel.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CarouselCard:
    """Um card do carousel."""

    header_image_url: str
    body_text: str
    button_text: str = "Ver mais"
    button_url: Optional[str] = None
    button_payload: Optional[str] = None


class CarouselBuilder:
    """
    Construtor de mensagens carousel para WhatsApp.

    Carousel: até 10 cards horizontais com imagem + CTA.
    """

    MAX_CARDS = 10

    def construir_carousel(
        self,
        header_text: str,
        cards: List[CarouselCard],
    ) -> dict:
        """
        Constrói payload de carousel message.

        Args:
            header_text: Texto do header do carousel
            cards: Lista de CarouselCard (max 10)

        Returns:
            Dict com payload para send_interactive
        """
        if not cards:
            raise ValueError("Carousel precisa de pelo menos 1 card")

        if len(cards) > self.MAX_CARDS:
            cards = cards[: self.MAX_CARDS]
            logger.warning(
                "[Carousel] Truncado para %d cards (máximo)",
                self.MAX_CARDS,
            )

        carousel_cards = []
        for i, card in enumerate(cards):
            carousel_card = {
                "card_index": i,
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "image",
                                "image": {"link": card.header_image_url},
                            }
                        ],
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": card.body_text},
                        ],
                    },
                    {
                        "type": "button",
                        "sub_type": "url" if card.button_url else "quick_reply",
                        "index": "0",
                        "parameters": [
                            {
                                "type": "text",
                                "text": card.button_url or card.button_payload or "",
                            }
                        ],
                    },
                ],
            }
            carousel_cards.append(carousel_card)

        return {
            "type": "template",
            "template": {
                "name": "carousel_template",
                "language": {"code": "pt_BR"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": header_text}],
                    },
                    {
                        "type": "carousel",
                        "cards": carousel_cards,
                    },
                ],
            },
        }

    def construir_carousel_vagas(
        self,
        vagas: List[dict],
        header_text: str = "Vagas disponíveis para você",
    ) -> dict:
        """
        Constrói carousel de vagas.

        Args:
            vagas: Lista de dicts com dados de vagas
            header_text: Texto do header

        Returns:
            Dict com payload do carousel
        """
        cards = []
        for vaga in vagas[: self.MAX_CARDS]:
            hospital = vaga.get("hospital_nome", "Hospital")
            esp = vaga.get("especialidade_nome", "")
            valor = vaga.get("valor", "")
            data = vaga.get("data", "")

            body = f"{hospital}"
            if data:
                body += f"\n📅 {data}"
            if valor:
                body += f"\n💰 R$ {valor}"

            cards.append(
                CarouselCard(
                    header_image_url=vaga.get("imagem_url", "https://via.placeholder.com/300"),
                    body_text=body,
                    button_text="Tenho interesse",
                    button_payload=f"vaga_{vaga.get('id', '')}",
                )
            )

        return self.construir_carousel(header_text, cards)


# Singleton
carousel_builder = CarouselBuilder()
