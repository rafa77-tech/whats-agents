"""
Conversation Generator - Gera conversas naturais para aquecimento.

Cria conteúdo variado e orgânico para troca entre chips durante
o processo de warmup, simulando conversas reais.
"""

import random
import logging
from collections import deque
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TipoConversa(str, Enum):
    """Tipos de conversa para warmup."""

    CASUAL = "casual"  # Papo do dia a dia
    TRABALHO = "trabalho"  # Assuntos profissionais genéricos
    COMBINADO = "combinado"  # Combinar algo (almoço, reunião)
    NOVIDADE = "novidade"  # Compartilhar algo novo
    PERGUNTA = "pergunta"  # Tirar dúvida
    CONFIRMACAO = "confirmacao"  # Confirmar algo
    AGRADECIMENTO = "agradecimento"  # Agradecer
    PIADA = "piada"  # Humor leve


class TipoMidia(str, Enum):
    """Tipos de mídia para variedade."""

    TEXTO = "texto"
    AUDIO = "audio"
    IMAGEM = "imagem"
    STICKER = "sticker"
    VIDEO = "video"
    DOCUMENTO = "documento"


@dataclass
class MensagemGerada:
    """Mensagem gerada para envio."""

    texto: str
    tipo_midia: TipoMidia
    sugestao_resposta: Optional[str] = None
    contexto: Optional[str] = None
    espera_resposta: bool = True


# Templates de conversas por tipo
TEMPLATES_CONVERSA = {
    TipoConversa.CASUAL: [
        # Clima
        ("E aí, como tá o dia aí?", "Tá tranquilo, e vc?"),
        ("Esse calor tá demais né", "Sim! Nem dá pra sair de casa"),
        ("Finalmente esfriou um pouco", "Até que enfim né"),
        ("Chove demais aqui hoje", "Aqui tá sol ainda"),
        # Fim de semana
        ("O que vc fez no fds?", "Descansei em casa, e vc?"),
        ("Bom dia! Conseguiu descansar?", "Consegui sim, precisava"),
        ("Fds passou voando né", "Nem me fala, já segunda de novo"),
        # Dia a dia
        ("Já almoçou?", "Tô indo agora, e vc?"),
        ("Vc viu o jogo ontem?", "Vi! Que jogo hein"),
        ("Tô precisando de férias", "Somos dois rsrs"),
        ("Que semana corrida", "Tá osso mesmo"),
        ("Bom dia!", "Bom dia! Tudo bem?"),
        ("Boa tarde!", "Boa tarde! Como tá o dia?"),
    ],
    TipoConversa.TRABALHO: [
        ("Conseguiu resolver aquilo lá?", "Ainda não, tô vendo aqui"),
        ("Deu certo o que vc tava fazendo?", "Deu sim, finalmente"),
        ("Tá muito corrido aí?", "Demais, nem parei ainda"),
        ("Reunião foi bem?", "Foi sim, tranquila"),
        ("Já mandou o email?", "Acabei de mandar"),
        ("Viu a mensagem que mandei?", "Vi sim, vou responder já"),
        ("Precisa de ajuda com algo?", "Por enquanto tá ok, valeu!"),
    ],
    TipoConversa.COMBINADO: [
        ("Vamos almoçar amanhã?", "Bora! Que horas?"),
        ("Podemos marcar uma call?", "Pode ser, quando vc pode?"),
        ("Quer um café depois?", "Quero! Me avisa quando sair"),
        ("Vamos resolver isso pessoalmente?", "Melhor mesmo, marca aí"),
        ("Tá livre pra uma ligação rápida?", "Tô sim, pode ligar"),
        ("Sexta vc tá livre?", "Acho que sim, por que?"),
    ],
    TipoConversa.NOVIDADE: [
        ("Vc viu isso aqui? [link]", "Ainda não, vou ver!"),
        ("Descobri um lugar novo pra almoçar", "Onde? Conta aí"),
        ("Mudaram o sistema aqui", "Sério? Como ficou?"),
        ("Trocaram o gerente lá", "Nossa, não sabia"),
        ("Abriu uma loja nova perto de casa", "Que tipo de loja?"),
    ],
    TipoConversa.PERGUNTA: [
        ("Vc sabe o telefone do fulano?", "Deixa eu ver aqui"),
        ("Lembra o nome daquele lugar?", "Qual lugar?"),
        ("Sabe se vai ter reunião hoje?", "Acho que sim, vou confirmar"),
        ("Vc tá no escritório?", "Tô sim, por que?"),
        ("Tem o contato do ciclano?", "Tenho, vou te mandar"),
    ],
    TipoConversa.CONFIRMACAO: [
        ("Tá confirmado pra amanhã?", "Tá sim, pode contar comigo"),
        ("Vc vem né?", "Vou sim!"),
        ("Me confirma se deu certo", "Deu certo sim"),
        ("Recebeu o que mandei?", "Recebi, valeu!"),
        ("Anotou o endereço?", "Anotei, tá salvo aqui"),
    ],
    TipoConversa.AGRADECIMENTO: [
        ("Muito obrigado pela ajuda!", "Imagina, precisando é só falar"),
        ("Valeu demais!", "De nada!"),
        ("Vc me salvou", "Que isso, foi nada"),
        ("Ajudou muito, obrigado", "Sempre às ordens"),
    ],
    TipoConversa.PIADA: [
        ("Kkkk olha isso", "Kkkkk boa"),
        ("Cara, muito bom isso", "Rsrs demais"),
        ("Vc viu o meme?", "Vi! Muito bom kkk"),
        ("Essa foi boa hein", "Kkkkk realmente"),
    ],
}

# Emojis por contexto
EMOJIS = {
    "positivo": ["👍", "😊", "✨", "🙌", "👏", "💪"],
    "risada": ["😂", "🤣", "😄", "😆"],
    "neutro": ["👌", "🤝", "✅"],
    "trabalho": ["💼", "📊", "📋", "✍️"],
    "comida": ["🍕", "🍔", "☕", "🍽️"],
}


class ConversationGenerator:
    """Gerador de conversas para warmup."""

    def __init__(self):
        self.historico_tipos: deque[TipoConversa] = deque(maxlen=50)
        self.ultimo_tipo: Optional[TipoConversa] = None

    def _escolher_tipo_conversa(self) -> TipoConversa:
        """
        Escolhe tipo de conversa garantindo variedade.

        Returns:
            Tipo de conversa selecionado
        """
        # Pesos por tipo (casual é mais comum)
        pesos = {
            TipoConversa.CASUAL: 30,
            TipoConversa.TRABALHO: 20,
            TipoConversa.COMBINADO: 15,
            TipoConversa.NOVIDADE: 10,
            TipoConversa.PERGUNTA: 10,
            TipoConversa.CONFIRMACAO: 5,
            TipoConversa.AGRADECIMENTO: 5,
            TipoConversa.PIADA: 5,
        }

        # Reduzir peso do último tipo para variedade
        if self.ultimo_tipo:
            pesos[self.ultimo_tipo] = max(1, pesos[self.ultimo_tipo] // 3)

        # Selecionar baseado nos pesos
        tipos = list(pesos.keys())
        weights = list(pesos.values())

        tipo = random.choices(tipos, weights=weights, k=1)[0]

        self.ultimo_tipo = tipo
        self.historico_tipos.append(tipo)

        return tipo

    def _escolher_tipo_midia(self, fase_warmup: str) -> TipoMidia:
        """
        Escolhe tipo de mídia baseado na fase de warmup.

        Args:
            fase_warmup: Fase atual do chip

        Returns:
            Tipo de mídia selecionado
        """
        # Fases iniciais: apenas texto
        if fase_warmup in ["repouso", "setup", "primeiros_contatos"]:
            return TipoMidia.TEXTO

        # Fases intermediárias: texto + audio + sticker
        if fase_warmup in ["expansao", "pre_operacao"]:
            opcoes = [
                (TipoMidia.TEXTO, 70),
                (TipoMidia.AUDIO, 15),
                (TipoMidia.STICKER, 15),
            ]
            tipos, pesos = zip(*opcoes)
            return random.choices(tipos, weights=pesos, k=1)[0]

        # Fases avançadas: todos os tipos
        opcoes = [
            (TipoMidia.TEXTO, 50),
            (TipoMidia.AUDIO, 20),
            (TipoMidia.STICKER, 15),
            (TipoMidia.IMAGEM, 10),
            (TipoMidia.VIDEO, 5),
        ]
        tipos, pesos = zip(*opcoes)
        return random.choices(tipos, weights=pesos, k=1)[0]

    def _adicionar_emoji_opcional(self, texto: str, contexto: str = "positivo") -> str:
        """
        Adiciona emoji opcional ao texto.

        Args:
            texto: Texto original
            contexto: Contexto para escolha do emoji

        Returns:
            Texto possivelmente com emoji
        """
        # 20% de chance de adicionar emoji
        if random.random() > 0.2:
            return texto

        emojis = EMOJIS.get(contexto, EMOJIS["positivo"])
        emoji = random.choice(emojis)

        # Adicionar no final
        return f"{texto} {emoji}"

    def gerar_abertura(
        self,
        fase_warmup: str = "operacao",
    ) -> MensagemGerada:
        """
        Gera mensagem de abertura de conversa.

        Args:
            fase_warmup: Fase atual do chip

        Returns:
            MensagemGerada com abertura
        """
        tipo = self._escolher_tipo_conversa()
        tipo_midia = self._escolher_tipo_midia(fase_warmup)

        templates = TEMPLATES_CONVERSA[tipo]
        abertura, sugestao = random.choice(templates)

        # Contexto para emoji
        contexto_emoji = "positivo"
        if tipo == TipoConversa.PIADA:
            contexto_emoji = "risada"
        elif tipo == TipoConversa.TRABALHO:
            contexto_emoji = "trabalho"
        elif tipo == TipoConversa.COMBINADO and "almoç" in abertura.lower():
            contexto_emoji = "comida"

        abertura = self._adicionar_emoji_opcional(abertura, contexto_emoji)

        logger.debug(f"[ConvGen] Abertura gerada: tipo={tipo.value}, midia={tipo_midia.value}")

        return MensagemGerada(
            texto=abertura,
            tipo_midia=tipo_midia,
            sugestao_resposta=sugestao,
            contexto=tipo.value,
            espera_resposta=True,
        )


# Instância global
conversation_generator = ConversationGenerator()


def gerar_mensagem_inicial(fase_warmup: str = "operacao") -> MensagemGerada:
    """
    Função de conveniência para gerar apenas abertura.

    Args:
        fase_warmup: Fase atual do chip

    Returns:
        Mensagem de abertura
    """
    return conversation_generator.gerar_abertura(fase_warmup)
