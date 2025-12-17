"""
Detector de objeções em mensagens de médicos.

Identifica tipo de objeção para buscar conhecimento relevante.
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TipoObjecao(str, Enum):
    """Categorias de objeção do catálogo."""

    PRECO = "preco"  # Valor baixo, pagamento
    TEMPO = "tempo"  # Agenda cheia, ocupado
    CONFIANCA = "confianca"  # Não conhece, desconfiança
    PROCESSO = "processo"  # Burocracia, documentos
    DISPONIBILIDADE = "disponibilidade"  # Região, especialidade
    QUALIDADE = "qualidade"  # Hospital ruim, condições
    LEALDADE = "lealdade"  # Usa outra plataforma
    RISCO = "risco"  # Medo de não receber
    MOTIVACAO = "motivacao"  # Não quer fazer plantão
    COMUNICACAO = "comunicacao"  # Não responde, ignora
    NENHUMA = "nenhuma"  # Não é objeção


@dataclass
class ResultadoDeteccao:
    """Resultado da detecção de objeção."""

    tem_objecao: bool
    tipo: TipoObjecao
    confianca: float  # 0.0 a 1.0
    trecho: Optional[str] = None  # Parte que indica objeção
    subtipo: Optional[str] = None  # Detalhe específico


class DetectorObjecao:
    """Detecta objeções em mensagens."""

    # Padrões por categoria (regex)
    PADROES = {
        TipoObjecao.PRECO: [
            r"\b(valor|preço|preco|paga|pagar|pagamento|remuneração|remuneracao)\b.*\b(baixo|pouco|ruim|mal)\b",
            r"\b(baixo|pouco)\b.*\b(valor|preço|preco)\b",
            r"\bpaga\s*(muito\s*)?(pouco|mal)\b",
            r"\b(n[aã]o\s+)?compens[ao]",
            r"\bdesvalorizad[oa]\b",
            r"\bquanto\s+paga\b",
            r"\b(muito\s+)?(caro|barato)\b",
        ],
        TipoObjecao.TEMPO: [
            r"\b(n[aã]o\s+)?t(enho|em)\s+(tempo|disponibilidade)\b",
            r"\b(agenda|hor[aá]rio)\b.{0,15}\b(chei[oa]|lotad[oa]|apertad[oa])\b",
            r"\b(muito\s+)?ocupad[oa]\b",
            r"\best(ou|á)\s+(muito\s+)?(ocupad|atarefad|corrid)\b",
            r"\bagora\s+n[aã]o\s+(d[aá]|consigo)\b",
            r"\bsem\s+tempo\b",
            r"\bn[aã]o\s+consigo\s+encaixar\b",
        ],
        TipoObjecao.CONFIANCA: [
            r"\b(n[aã]o\s+)?(conhe[cç]o|sei)\s+(a\s+)?(revoluna|plataforma|voc[eê]s)\b",
            r"\b(nunca\s+)?ouvi\s+falar\b",
            r"\b(n[aã]o\s+)?confi[oa]\b",
            r"\bdesconfi(o|ado|ada)\b",
            r"\bcomo\s+(funciona|[eé])\b",
            r"\b[eé]\s+segur[oa]\b",
            r"\bgolpe\b",
            r"\bfraude\b",
        ],
        TipoObjecao.PROCESSO: [
            r"\b(muita\s+)?burocracia\b",
            r"\b(muito\s+)?document[oa]\b",
            r"\bcomplicad[oa]\b",
            r"\btrabalhoso\b",
            r"\b(n[aã]o\s+)?quero\s+cadastr(o|ar)\b",
            r"\bmuita\s+coisa\b",
            r"\bdem(ora|orad[oa])\b",
        ],
        TipoObjecao.DISPONIBILIDADE: [
            r"\b(n[aã]o\s+)?t(em|êm)\s+vaga\b",
            r"\blong[ei]\b.*\b(distante|região|regiao)\b",
            r"\b(minha\s+)?(especialidade|área|area)\b.*\bn[aã]o\b",
            r"\bmuito\s+longe\b",
            r"\bn[aã]o\s+atende\s+(minha|a)\s+(região|cidade)\b",
            r"\bfora\s+da\s+(minha\s+)?(área|zona)\b",
        ],
        TipoObjecao.QUALIDADE: [
            r"\b(hospital|unidade)\s+(ruim|p[eé]ssim[oa]|problema)\b",
            r"\bcondições\s+(ruins|p[eé]ssimas|precárias)\b",
            r"\b(n[aã]o\s+)?gost(o|ei)\s+(desse|daquele)\s+hospital\b",
            r"\breputação\s+(ruim|negativa)\b",
            r"\b(mal|péssima)\s+estrutura\b",
        ],
        TipoObjecao.LEALDADE: [
            r"\bj[aá]\s+(uso|trabalho)\s+(com\s+)?(outr[oa]|diferente)\b",
            r"\b(outra\s+)?(plataforma|empresa|agência)\b",
            r"\bfidelidade\b",
            r"\bj[aá]\s+tenho\s+(parceria|contrato)\b",
            r"\bexclusividade\b",
        ],
        TipoObjecao.RISCO: [
            r"\b(medo|receio)\s+(de\s+)?n[aã]o\s+(receber|pagar)\b",
            r"\b(e\s+)?se\s+n[aã]o\s+(pagar|receber)\b",
            r"\bgarantia\b",
            r"\bcalot[ei]\b",
            r"\bn[aã]o\s+paga(r|m)?\b",
            r"\batrasa(r|m)?\s+(pagamento|salário)\b",
        ],
        TipoObjecao.MOTIVACAO: [
            r"\b(n[aã]o\s+)?quero\s+(mais\s+)?(fazer\s+)?plant[aã]o\b",
            r"\bcansei\s+de\s+plant[aã]o\b",
            r"\bparei\s+(de\s+fazer\s+)?plant[aã]o\b",
            r"\b(n[aã]o\s+)?tenho\s+interesse\b",
            r"\b(n[aã]o\s+)?preciso\b",
            r"\bn[aã]o\s+estou\s+(interessad|precisand)\b",
            r"\bno\s+momento\s+n[aã]o\b",
        ],
        TipoObjecao.COMUNICACAO: [
            r"\bdepoisi?\b",
            r"\bvou\s+pensar\b",
            r"\bdepois\s+(a\s+gente\s+)?(fala|conversa|v[eê])\b",
            r"\bagora\s+n[aã]o\s+(d[aá]|posso)\b",
            r"\bme\s+liga\s+depois\b",
        ],
    }

    # Palavras-chave de alta confiança (match direto = objeção certa)
    KEYWORDS_ALTA_CONFIANCA = {
        TipoObjecao.PRECO: ["muito barato", "paga pouco", "valor baixo"],
        TipoObjecao.TEMPO: ["sem tempo", "agenda cheia", "muito ocupado"],
        TipoObjecao.CONFIANCA: ["não conheço", "nunca ouvi falar", "é golpe"],
        TipoObjecao.PROCESSO: ["muita burocracia", "muito documento"],
        TipoObjecao.MOTIVACAO: ["não quero plantão", "parei de fazer plantão"],
    }

    def detectar(self, mensagem: str) -> ResultadoDeteccao:
        """
        Detecta se há objeção na mensagem.

        Args:
            mensagem: Texto da mensagem do médico

        Returns:
            ResultadoDeteccao com tipo e confiança
        """
        mensagem_lower = mensagem.lower().strip()

        # 1. Verificar keywords de alta confiança primeiro
        for tipo, keywords in self.KEYWORDS_ALTA_CONFIANCA.items():
            for kw in keywords:
                if kw in mensagem_lower:
                    return ResultadoDeteccao(
                        tem_objecao=True,
                        tipo=tipo,
                        confianca=0.95,
                        trecho=kw,
                        subtipo=self._detectar_subtipo(tipo, mensagem_lower),
                    )

        # 2. Verificar padrões regex
        for tipo, padroes in self.PADROES.items():
            for padrao in padroes:
                match = re.search(padrao, mensagem_lower, re.IGNORECASE)
                if match:
                    return ResultadoDeteccao(
                        tem_objecao=True,
                        tipo=tipo,
                        confianca=0.75,
                        trecho=match.group(),
                        subtipo=self._detectar_subtipo(tipo, mensagem_lower),
                    )

        # 3. Nenhuma objeção detectada
        return ResultadoDeteccao(
            tem_objecao=False,
            tipo=TipoObjecao.NENHUMA,
            confianca=0.6,  # Confiança moderada - pode ser falso negativo
        )

    def _detectar_subtipo(self, tipo: TipoObjecao, texto: str) -> Optional[str]:
        """Detecta subtipo específico da objeção."""
        subtipos = {
            TipoObjecao.PRECO: {
                "valor_baixo": ["baixo", "pouco"],
                "pagamento_atrasado": ["atrasa", "demora"],
                "forma_pagamento": ["pix", "transferência", "boleto"],
            },
            TipoObjecao.TEMPO: {
                "agenda_cheia": ["agenda", "horário"],
                "temporario": ["agora", "momento", "essa semana"],
                "permanente": ["parei", "não faço mais"],
            },
            TipoObjecao.CONFIANCA: {
                "desconhecimento": ["não conheço", "nunca ouvi"],
                "desconfianca": ["golpe", "fraude", "não confio"],
                "curiosidade": ["como funciona", "é seguro"],
            },
        }

        if tipo in subtipos:
            for subtipo, keywords in subtipos[tipo].items():
                if any(kw in texto for kw in keywords):
                    return subtipo

        return None

    async def detectar_com_llm(
        self, mensagem: str, historico: list[str] = None
    ) -> ResultadoDeteccao:
        """
        Detecta objeção usando LLM para casos ambíguos.

        Usa Claude Haiku para classificação rápida.

        Args:
            mensagem: Texto da mensagem
            historico: Últimas mensagens da conversa

        Returns:
            ResultadoDeteccao com análise do LLM
        """
        from app.services.llm import gerar_resposta_llm

        # Primeiro tenta detecção por padrões
        resultado_padrao = self.detectar(mensagem)

        # Se confiança alta, retorna direto
        if resultado_padrao.tem_objecao and resultado_padrao.confianca >= 0.9:
            return resultado_padrao

        # Se confiança baixa ou sem objeção, usa LLM
        contexto = ""
        if historico:
            contexto = f"\nContexto das últimas mensagens:\n" + "\n".join(
                historico[-3:]
            )

        prompt = f"""Analise a mensagem do médico e identifique se há uma OBJEÇÃO.

Mensagem: "{mensagem}"{contexto}

Tipos de objeção possíveis:
- preco: Reclama do valor/pagamento
- tempo: Diz que está ocupado/sem tempo
- confianca: Não conhece ou desconfia da plataforma
- processo: Reclama de burocracia/documentos
- disponibilidade: Região/especialidade não atendida
- qualidade: Reclama do hospital/condições
- lealdade: Já usa outra plataforma
- risco: Medo de não receber pagamento
- motivacao: Não quer fazer plantão
- comunicacao: Adia conversa/não responde claramente
- nenhuma: NÃO é objeção

Responda APENAS com o tipo (uma palavra). Se não for objeção, responda "nenhuma"."""

        try:
            resposta = await gerar_resposta_llm(
                mensagem=prompt,
                historico=[],
                system_prompt="Você é um classificador de objeções. Responda apenas com uma palavra.",
                modelo="haiku",
            )

            tipo_str = resposta.strip().lower()

            # Mapear resposta para enum
            tipo_map = {
                "preco": TipoObjecao.PRECO,
                "tempo": TipoObjecao.TEMPO,
                "confianca": TipoObjecao.CONFIANCA,
                "processo": TipoObjecao.PROCESSO,
                "disponibilidade": TipoObjecao.DISPONIBILIDADE,
                "qualidade": TipoObjecao.QUALIDADE,
                "lealdade": TipoObjecao.LEALDADE,
                "risco": TipoObjecao.RISCO,
                "motivacao": TipoObjecao.MOTIVACAO,
                "comunicacao": TipoObjecao.COMUNICACAO,
                "nenhuma": TipoObjecao.NENHUMA,
            }

            tipo = tipo_map.get(tipo_str, TipoObjecao.NENHUMA)

            return ResultadoDeteccao(
                tem_objecao=tipo != TipoObjecao.NENHUMA,
                tipo=tipo,
                confianca=0.85,  # LLM tem confiança alta
                subtipo=self._detectar_subtipo(tipo, mensagem.lower()),
            )

        except Exception as e:
            logger.warning(f"Erro ao usar LLM para detecção: {e}")
            # Fallback para detecção por padrões
            return resultado_padrao
