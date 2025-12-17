"""
Detector de perfil de médico.

Identifica perfil para adaptar abordagem e buscar conhecimento específico.
"""
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class PerfilMedico(str, Enum):
    """6 perfis de médico do guia de adaptação."""

    RECEM_FORMADO = "recem_formado"  # 0-2 anos
    EM_DESENVOLVIMENTO = "em_desenvolvimento"  # 2-7 anos
    EXPERIENTE = "experiente"  # 7-15 anos
    SENIOR = "senior"  # 15+ anos
    ESPECIALISTA = "especialista"  # Subespecialista
    EM_TRANSICAO = "em_transicao"  # Mudando de carreira
    DESCONHECIDO = "desconhecido"


@dataclass
class ResultadoPerfil:
    """Resultado da detecção de perfil."""

    perfil: PerfilMedico
    confianca: float
    anos_experiencia: Optional[int] = None
    indicadores: list[str] = None  # Sinais que indicaram o perfil
    recomendacao_abordagem: Optional[str] = None


class DetectorPerfil:
    """Detecta perfil do médico baseado em dados e comportamento."""

    # Indicadores por perfil (inferidos do comportamento)
    INDICADORES = {
        PerfilMedico.RECEM_FORMADO: {
            "keywords": [
                "residência",
                "residencia",
                "recém formado",
                "recem formado",
                "r1",
                "r2",
                "r3",
                "acabei de formar",
                "formei esse ano",
                "primeiro emprego",
                "começando",
                "comecando",
            ],
            "comportamento": [
                "pergunta_muito",  # Faz muitas perguntas
                "responde_rapido",  # Responde rápido
                "aceita_qualquer_vaga",  # Menos seletivo
            ],
        },
        PerfilMedico.EM_DESENVOLVIMENTO: {
            "keywords": [
                "alguns anos",
                "já trabalho há",
                "ja trabalho ha",
                "experiência",
                "experiencia",
                "rotina",
                "estabilidade",
            ],
            "comportamento": [
                "seletivo_hospital",  # Prefere alguns hospitais
                "negocia_valor",  # Negocia
            ],
        },
        PerfilMedico.EXPERIENTE: {
            "keywords": [
                "muitos anos",
                "bastante tempo",
                "longa experiência",
                "longa experiencia",
                "já vi de tudo",
                "ja vi de tudo",
            ],
            "comportamento": [
                "muito_seletivo",
                "exige_valor_alto",
                "responde_devagar",
            ],
        },
        PerfilMedico.SENIOR: {
            "keywords": [
                "décadas",
                "decadas",
                "aposentando",
                "final de carreira",
                "professor",
                "preceptor",
                "legado",
                "contribuição",
                "contribuicao",
            ],
            "comportamento": [
                "responde_muito_devagar",
                "exige_respeito",
                "nao_aceita_pressao",
            ],
        },
        PerfilMedico.ESPECIALISTA: {
            "keywords": [
                "subespecialidade",
                "fellowship",
                "certificação",
                "certificacao",
                "título",
                "titulo",
                "área específica",
                "area especifica",
                "nicho",
            ],
            "comportamento": [
                "muito_seletivo_especialidade",
                "valor_premium",
            ],
        },
        PerfilMedico.EM_TRANSICAO: {
            "keywords": [
                "mudando",
                "transição",
                "transicao",
                "nova área",
                "nova area",
                "recomeçando",
                "recomecando",
                "saindo de",
                "deixando",
            ],
            "comportamento": [
                "muitas_duvidas",
                "compara_com_anterior",
            ],
        },
    }

    # Abordagem recomendada por perfil
    ABORDAGENS = {
        PerfilMedico.RECEM_FORMADO: "Apoio e orientação. Ofereça segurança e mostre oportunidades de crescimento.",
        PerfilMedico.EM_DESENVOLVIMENTO: "Foco em carreira e desenvolvimento. Mostre como as vagas ajudam no crescimento profissional.",
        PerfilMedico.EXPERIENTE: "Eficiência e soluções. Seja direto, respeite o tempo, ofereça vagas de qualidade.",
        PerfilMedico.SENIOR: "Parceria e respeito. NUNCA pressione. Foque em legado e contribuição, não em dinheiro.",
        PerfilMedico.ESPECIALISTA: "Personalização total. Mostre vagas que combinam com a subespecialidade.",
        PerfilMedico.EM_TRANSICAO: "Suporte na mudança. Ajude a encontrar vagas que facilitem a transição.",
        PerfilMedico.DESCONHECIDO: "Abordagem neutra. Faça perguntas para descobrir o perfil.",
    }

    def detectar_por_dados(
        self,
        anos_experiencia: Optional[int] = None,
        especialidade: Optional[str] = None,
        subespecialidade: Optional[str] = None,
        titulo: Optional[str] = None,
    ) -> ResultadoPerfil:
        """
        Detecta perfil baseado em dados estruturados.

        Args:
            anos_experiencia: Anos desde formatura
            especialidade: Especialidade principal
            subespecialidade: Se tem subespecialidade
            titulo: Títulos acadêmicos (professor, etc)

        Returns:
            ResultadoPerfil com perfil detectado
        """
        indicadores = []

        # Prioridade 1: Subespecialidade indica ESPECIALISTA
        if subespecialidade:
            indicadores.append("tem_subespecialidade")
            return ResultadoPerfil(
                perfil=PerfilMedico.ESPECIALISTA,
                confianca=0.9,
                anos_experiencia=anos_experiencia,
                indicadores=indicadores,
                recomendacao_abordagem=self.ABORDAGENS[PerfilMedico.ESPECIALISTA],
            )

        # Prioridade 2: Título acadêmico indica SENIOR
        if titulo and any(
            t in titulo.lower() for t in ["professor", "doutor", "dr.", "preceptor"]
        ):
            indicadores.append("titulo_academico")
            return ResultadoPerfil(
                perfil=PerfilMedico.SENIOR,
                confianca=0.85,
                anos_experiencia=anos_experiencia,
                indicadores=indicadores,
                recomendacao_abordagem=self.ABORDAGENS[PerfilMedico.SENIOR],
            )

        # Prioridade 3: Anos de experiência
        if anos_experiencia is not None:
            indicadores.append(f"anos_experiencia_{anos_experiencia}")

            if anos_experiencia <= 2:
                perfil = PerfilMedico.RECEM_FORMADO
                confianca = 0.9
            elif anos_experiencia <= 7:
                perfil = PerfilMedico.EM_DESENVOLVIMENTO
                confianca = 0.85
            elif anos_experiencia <= 15:
                perfil = PerfilMedico.EXPERIENTE
                confianca = 0.85
            else:
                perfil = PerfilMedico.SENIOR
                confianca = 0.9

            return ResultadoPerfil(
                perfil=perfil,
                confianca=confianca,
                anos_experiencia=anos_experiencia,
                indicadores=indicadores,
                recomendacao_abordagem=self.ABORDAGENS[perfil],
            )

        # Sem dados suficientes
        return ResultadoPerfil(
            perfil=PerfilMedico.DESCONHECIDO,
            confianca=0.3,
            indicadores=["dados_insuficientes"],
            recomendacao_abordagem=self.ABORDAGENS[PerfilMedico.DESCONHECIDO],
        )

    def detectar_por_mensagem(self, mensagem: str) -> ResultadoPerfil:
        """
        Detecta perfil baseado em keywords na mensagem.

        Args:
            mensagem: Texto da mensagem do médico

        Returns:
            ResultadoPerfil inferido
        """
        mensagem_lower = mensagem.lower()
        indicadores = []
        melhor_perfil = PerfilMedico.DESCONHECIDO
        maior_score = 0

        for perfil, dados in self.INDICADORES.items():
            score = 0
            for kw in dados["keywords"]:
                if kw in mensagem_lower:
                    score += 1
                    indicadores.append(f"keyword:{kw}")

            if score > maior_score:
                maior_score = score
                melhor_perfil = perfil

        # Confiança baseada em quantidade de matches
        confianca = min(0.5 + (maior_score * 0.15), 0.9) if maior_score > 0 else 0.3

        return ResultadoPerfil(
            perfil=melhor_perfil,
            confianca=confianca,
            indicadores=indicadores if indicadores else ["nenhum_indicador"],
            recomendacao_abordagem=self.ABORDAGENS[melhor_perfil],
        )

    def detectar_por_historico(
        self, historico: list[dict], dados_cliente: Optional[dict] = None
    ) -> ResultadoPerfil:
        """
        Detecta perfil analisando histórico de conversas.

        Args:
            historico: Lista de mensagens anteriores
            dados_cliente: Dados do cliente do banco

        Returns:
            ResultadoPerfil com análise completa
        """
        indicadores = []

        # 1. Se tem dados estruturados, usa como base
        if dados_cliente:
            # Calcular anos de experiência se tiver CRM
            anos_exp = None
            if dados_cliente.get("crm"):
                # Assumir que médico com CRM tem pelo menos 6 anos (faculdade)
                # Se tiver data de registro, calcular
                pass

            resultado_dados = self.detectar_por_dados(
                anos_experiencia=anos_exp,
                especialidade=dados_cliente.get("especialidade"),
                subespecialidade=dados_cliente.get("subespecialidade"),
                titulo=dados_cliente.get("titulo"),
            )

            if resultado_dados.confianca >= 0.8:
                return resultado_dados

            indicadores.extend(resultado_dados.indicadores or [])

        # 2. Analisar mensagens do histórico
        if historico:
            texto_completo = " ".join(
                [m.get("conteudo", "") for m in historico if m.get("tipo") == "recebida"]
            )
            resultado_msg = self.detectar_por_mensagem(texto_completo)
            indicadores.extend(resultado_msg.indicadores or [])

            if resultado_msg.confianca > 0.6:
                return ResultadoPerfil(
                    perfil=resultado_msg.perfil,
                    confianca=resultado_msg.confianca,
                    indicadores=list(set(indicadores)),
                    recomendacao_abordagem=self.ABORDAGENS[resultado_msg.perfil],
                )

        # 3. Perfil desconhecido
        return ResultadoPerfil(
            perfil=PerfilMedico.DESCONHECIDO,
            confianca=0.3,
            indicadores=indicadores if indicadores else ["sem_dados"],
            recomendacao_abordagem=self.ABORDAGENS[PerfilMedico.DESCONHECIDO],
        )

    async def detectar_com_llm(
        self, mensagens: list[str], dados_cliente: Optional[dict] = None
    ) -> ResultadoPerfil:
        """
        Detecta perfil usando LLM para análise mais profunda.

        Args:
            mensagens: Últimas mensagens da conversa
            dados_cliente: Dados do cliente

        Returns:
            ResultadoPerfil com análise do LLM
        """
        from app.services.llm import gerar_resposta_llm

        contexto = ""
        if dados_cliente:
            contexto = f"\nDados conhecidos: Especialidade: {dados_cliente.get('especialidade', 'N/A')}"

        historico = "\n".join([f"- {m}" for m in mensagens[-5:]])

        prompt = f"""Analise as mensagens do médico e identifique o PERFIL profissional.

Mensagens do médico:
{historico}{contexto}

Perfis possíveis:
- recem_formado: 0-2 anos, busca oportunidades, aceita várias vagas
- em_desenvolvimento: 2-7 anos, quer crescer na carreira
- experiente: 7-15 anos, seletivo, valoriza tempo
- senior: 15+ anos, foco em legado, não aceita pressão
- especialista: Subespecialidade, vagas específicas
- em_transicao: Mudando de área/carreira
- desconhecido: Não dá para identificar

Responda APENAS com o perfil (uma palavra)."""

        try:
            resposta = await gerar_resposta_llm(
                mensagem=prompt,
                historico=[],
                system_prompt="Você é um classificador de perfis médicos. Responda apenas com uma palavra.",
                modelo="haiku",
            )

            perfil_str = resposta.strip().lower()

            perfil_map = {
                "recem_formado": PerfilMedico.RECEM_FORMADO,
                "em_desenvolvimento": PerfilMedico.EM_DESENVOLVIMENTO,
                "experiente": PerfilMedico.EXPERIENTE,
                "senior": PerfilMedico.SENIOR,
                "especialista": PerfilMedico.ESPECIALISTA,
                "em_transicao": PerfilMedico.EM_TRANSICAO,
                "desconhecido": PerfilMedico.DESCONHECIDO,
            }

            perfil = perfil_map.get(perfil_str, PerfilMedico.DESCONHECIDO)

            return ResultadoPerfil(
                perfil=perfil,
                confianca=0.8,
                indicadores=["analise_llm"],
                recomendacao_abordagem=self.ABORDAGENS[perfil],
            )

        except Exception as e:
            logger.warning(f"Erro ao usar LLM para perfil: {e}")
            return ResultadoPerfil(
                perfil=PerfilMedico.DESCONHECIDO,
                confianca=0.3,
                indicadores=["erro_llm"],
                recomendacao_abordagem=self.ABORDAGENS[PerfilMedico.DESCONHECIDO],
            )
