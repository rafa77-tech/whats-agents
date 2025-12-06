"""
Agente Julia - Core do processamento de mensagens
"""

import logging
from typing import Optional
import anthropic

from config import settings
from config.prompts import build_prompt
from app.database import db

logger = logging.getLogger(__name__)


class JuliaAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model
        self.model_complex = settings.llm_model_complex

    async def processar_mensagem(
        self,
        telefone: str,
        mensagem: str,
        message_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Processa mensagem recebida e retorna resposta.
        Retorna None se a conversa estiver sob controle humano.
        """
        # 1. Buscar/criar medico
        medico = await db.get_or_create_medico(telefone)
        cliente_id = medico["id"]

        # 2. Buscar/criar conversa
        conversa = await db.get_or_create_conversa(cliente_id)
        conversa_id = conversa["id"]

        # 3. Salvar mensagem recebida
        await db.save_interacao(
            conversa_id=conversa_id,
            cliente_id=cliente_id,
            direcao="entrada",
            conteudo=mensagem
        )

        # 4. Verificar se IA pode responder
        if conversa.get("controlled_by") == "human":
            logger.info(f"Conversa {conversa_id} sob controle humano, ignorando")
            return None

        # 5. Carregar contexto
        historico = await db.get_historico(conversa_id, limit=10)
        vagas = await db.get_vagas_disponiveis(
            especialidade_id=medico.get("especialidade_id"),
            limit=3
        )

        # 6. Construir prompt
        system_prompt = build_prompt(
            nome_empresa=settings.nome_empresa,
            memoria_medico=self._format_memoria(medico),
            diretrizes="Foco em prospeccao. Seja amigavel e direta.",
            vagas_disponiveis=self._format_vagas(vagas),
            historico=self._format_historico(historico)
        )

        # 7. Montar mensagens para o LLM
        messages = self._build_messages(historico, mensagem)

        # 8. Chamar Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=system_prompt,
                messages=messages
            )
            resposta = response.content[0].text
        except Exception as e:
            logger.error(f"Erro ao chamar Claude: {e}")
            return None

        # 9. Salvar resposta
        await db.save_interacao(
            conversa_id=conversa_id,
            cliente_id=cliente_id,
            direcao="saida",
            conteudo=resposta
        )

        # 10. Atualizar conversa
        await db.update_conversa(conversa_id, {
            "last_message_at": "now()"
        })

        logger.info(f"Resposta gerada para {telefone[:8]}...")
        return resposta

    def _format_memoria(self, medico: dict) -> str:
        """Formata memoria do medico para o prompt."""
        partes = []
        nome = medico.get("primeiro_nome")
        if nome:
            sobrenome = medico.get("sobrenome", "")
            partes.append(f"Nome: {nome} {sobrenome}".strip())
        if medico.get("especialidade"):
            partes.append(f"Especialidade: {medico['especialidade']}")
        if medico.get("crm"):
            partes.append(f"CRM: {medico['crm']}")
        if medico.get("cidade"):
            partes.append(f"Cidade: {medico['cidade']}")
        if medico.get("stage_jornada"):
            partes.append(f"Stage: {medico['stage_jornada']}")

        return "\n".join(partes) if partes else "Primeiro contato com este medico."

    def _format_vagas(self, vagas: list) -> str:
        """Formata vagas para o prompt."""
        if not vagas:
            return "Sem vagas disponiveis no momento."

        linhas = []
        for v in vagas:
            hospital = v.get("hospitais", {}).get("nome", "Hospital")
            esp = v.get("especialidades", {}).get("nome", "")
            data = v.get("data_plantao", "")
            valor = v.get("valor")
            valor_str = f"R$ {valor}" if valor else "a combinar"
            linhas.append(f"- {hospital}: {esp}, {data}, {valor_str}")

        return "\n".join(linhas)

    def _format_historico(self, historico: list) -> str:
        """Formata historico para o prompt."""
        if not historico:
            return ""

        linhas = []
        for msg in historico[-10:]:  # Ultimas 10 mensagens
            autor = "Medico" if msg.get("origem") == "medico" else "Julia"
            linhas.append(f"{autor}: {msg['conteudo']}")

        return "\n".join(linhas)

    def _build_messages(self, historico: list, mensagem_atual: str) -> list:
        """Constroi lista de mensagens para a API."""
        messages = []

        # Adiciona historico como contexto
        for msg in historico[-6:]:  # Ultimas 6 mensagens para contexto
            role = "user" if msg.get("origem") == "medico" else "assistant"
            messages.append({
                "role": role,
                "content": msg["conteudo"]
            })

        # Adiciona mensagem atual
        messages.append({
            "role": "user",
            "content": mensagem_atual
        })

        return messages


# Singleton
julia = JuliaAgent()
