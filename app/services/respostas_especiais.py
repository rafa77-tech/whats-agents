"""
Respostas especiais para tipos de mensagem não-texto.
"""

import random

RESPOSTAS_AUDIO = [
    "Oi! Desculpa, to num lugar barulhento e não consigo ouvir áudio agora 😅 Pode mandar em texto?",
    "Ops, to no meio de uma reunião e não dá pra ouvir áudio. Me manda por escrito?",
    "Opa! To sem fone aqui, consegue digitar pra mim?",
    "Ei! Não consegui ouvir o áudio, pode escrever?",
    "Desculpa, não to conseguindo ouvir áudio agora. Pode mandar por texto?",
]

RESPOSTAS_IMAGEM = {
    "documento": [
        "Recebi! Vou dar uma olhada aqui 👀",
        "Beleza, chegou aqui! Deixa eu ver...",
        "Show, recebi o doc!",
        "Opa, recebi! Vou analisar",
    ],
    "generica": [
        "Recebi a imagem! O que precisa que eu veja?",
        "Opa, chegou aqui! Sobre o que é?",
        "Recebi! Me conta mais sobre isso?",
        "Show, recebi! O que é isso?",
    ],
}

RESPOSTAS_DOCUMENTO = [
    "Recebi o documento! Vou dar uma olhada",
    "Beleza, chegou aqui! Deixa eu ver o que é",
    "Show, recebi! Vou analisar",
]

RESPOSTAS_VIDEO = [
    "Recebi o vídeo! Mas não consigo assistir agora, pode me explicar o que é?",
    "Opa, recebi! Mas não to conseguindo ver vídeo, me conta o que é?",
]


def obter_resposta_audio() -> str:
    """Retorna resposta aleatória para áudio."""
    return random.choice(RESPOSTAS_AUDIO)


def obter_resposta_imagem(caption: str = None) -> str:
    """
    Retorna resposta para imagem.

    Se tem caption, provavelmente é documento.
    Se não tem, pede contexto.

    Args:
        caption: Legenda da imagem (opcional)

    Returns:
        Resposta apropriada
    """
    if caption and len(caption) > 10:
        # Tem contexto, provavelmente documento
        return random.choice(RESPOSTAS_IMAGEM["documento"])
    else:
        # Sem contexto, perguntar
        return random.choice(RESPOSTAS_IMAGEM["generica"])


def obter_resposta_documento() -> str:
    """Retorna resposta para documento."""
    return random.choice(RESPOSTAS_DOCUMENTO)


def obter_resposta_video() -> str:
    """Retorna resposta para vídeo."""
    return random.choice(RESPOSTAS_VIDEO)
