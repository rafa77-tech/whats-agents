"""
Testes para CarouselBuilder.

Sprint 70+ — Chunk 25.
"""

import pytest


class TestCarouselBuilder:

    def test_construir_carousel_basico(self):
        from app.services.meta.carousel_builder import CarouselBuilder, CarouselCard

        builder = CarouselBuilder()
        cards = [
            CarouselCard(header_image_url="https://img.com/1.jpg", body_text="Card 1"),
            CarouselCard(header_image_url="https://img.com/2.jpg", body_text="Card 2"),
        ]
        result = builder.construir_carousel("Vagas", cards)
        assert result["type"] == "template"
        carousel_comp = result["template"]["components"][1]
        assert carousel_comp["type"] == "carousel"
        assert len(carousel_comp["cards"]) == 2

    def test_construir_carousel_max_10_cards(self):
        from app.services.meta.carousel_builder import CarouselBuilder, CarouselCard

        builder = CarouselBuilder()
        cards = [
            CarouselCard(header_image_url=f"https://img.com/{i}.jpg", body_text=f"Card {i}")
            for i in range(15)
        ]
        result = builder.construir_carousel("Muitas vagas", cards)
        carousel_cards = result["template"]["components"][1]["cards"]
        assert len(carousel_cards) == 10

    def test_construir_carousel_vazio_raises(self):
        from app.services.meta.carousel_builder import CarouselBuilder

        builder = CarouselBuilder()
        with pytest.raises(ValueError):
            builder.construir_carousel("Empty", [])

    def test_construir_carousel_vagas(self):
        from app.services.meta.carousel_builder import CarouselBuilder

        builder = CarouselBuilder()
        vagas = [
            {"id": "v1", "hospital_nome": "São Luiz", "valor": "2500", "data": "15/03"},
            {"id": "v2", "hospital_nome": "Einstein", "valor": "3000", "data": "16/03"},
        ]
        result = builder.construir_carousel_vagas(vagas)
        assert result["type"] == "template"

    def test_card_com_url_button(self):
        from app.services.meta.carousel_builder import CarouselBuilder, CarouselCard

        builder = CarouselBuilder()
        cards = [
            CarouselCard(
                header_image_url="https://img.com/1.jpg",
                body_text="Card",
                button_text="Ver",
                button_url="https://link.com",
            ),
        ]
        result = builder.construir_carousel("Test", cards)
        button = result["template"]["components"][1]["cards"][0]["components"][2]
        assert button["sub_type"] == "url"

    def test_card_com_quick_reply(self):
        from app.services.meta.carousel_builder import CarouselBuilder, CarouselCard

        builder = CarouselBuilder()
        cards = [
            CarouselCard(
                header_image_url="https://img.com/1.jpg",
                body_text="Card",
                button_payload="action_1",
            ),
        ]
        result = builder.construir_carousel("Test", cards)
        button = result["template"]["components"][1]["cards"][0]["components"][2]
        assert button["sub_type"] == "quick_reply"

    def test_card_index_incrementa(self):
        from app.services.meta.carousel_builder import CarouselBuilder, CarouselCard

        builder = CarouselBuilder()
        cards = [
            CarouselCard(header_image_url=f"https://img.com/{i}.jpg", body_text=f"C{i}")
            for i in range(3)
        ]
        result = builder.construir_carousel("Test", cards)
        carousel_cards = result["template"]["components"][1]["cards"]
        assert carousel_cards[0]["card_index"] == 0
        assert carousel_cards[1]["card_index"] == 1
        assert carousel_cards[2]["card_index"] == 2

    def test_carousel_vagas_com_imagem_padrao(self):
        from app.services.meta.carousel_builder import CarouselBuilder

        builder = CarouselBuilder()
        vagas = [{"id": "v1", "hospital_nome": "H1"}]
        result = builder.construir_carousel_vagas(vagas)
        card = result["template"]["components"][1]["cards"][0]
        header_param = card["components"][0]["parameters"][0]
        assert "placeholder" in header_param["image"]["link"]
