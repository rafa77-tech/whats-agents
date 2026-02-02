"""
Servico de analise inteligente de briefings.

Sprint 11 - Epic 02: Analise Inteligente

Usa Claude Sonnet para interpretar briefings em linguagem natural
e criar planos de acao estruturados.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from anthropic import Anthropic

from app.core.config import settings
from app.core.timezone import agora_brasilia
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# =============================================================================
# TIPOS E ESTRUTURAS
# =============================================================================

class TipoDemanda(str, Enum):
    """Tipos de demanda que Julia pode receber."""
    OPERACIONAL = "operacional"  # Fechar escala, preencher vagas
    MAPEAMENTO = "mapeamento"    # Descobrir info sobre medicos/mercado
    EXPANSAO = "expansao"        # Conseguir novos contatos, indicacoes
    INTELIGENCIA = "inteligencia"  # Analisar dados, entender padroes
    NOVO_TERRITORIO = "novo_territorio"  # Regiao/segmento novo
    MISTO = "misto"  # Combinacao


@dataclass
class PassoPlano:
    """Um passo do plano de acao."""
    numero: int
    descricao: str
    prazo: Optional[str] = None
    requer_ajuda: bool = False
    tipo_ajuda: Optional[str] = None  # ferramenta, dados, decisao, humano


@dataclass
class NecessidadeIdentificada:
    """Necessidade de ferramenta/dados identificada."""
    tipo: str  # ferramenta, dados, campo_banco
    descricao: str
    caso_uso: str
    alternativa_temporaria: Optional[str] = None
    prioridade: str = "media"  # alta, media, baixa


@dataclass
class AnaliseResult:
    """Resultado completo da analise de um briefing."""
    # Identificacao
    doc_id: str
    doc_nome: str
    timestamp: str = field(default_factory=lambda: agora_brasilia().isoformat())

    # Entendimento
    resumo_demanda: str = ""
    tipo_demanda: TipoDemanda = TipoDemanda.OPERACIONAL
    deadline: Optional[str] = None
    urgencia: str = "media"  # alta, media, baixa

    # Avaliacao
    dados_disponiveis: list[str] = field(default_factory=list)
    dados_faltantes: list[str] = field(default_factory=list)
    ferramentas_necessarias: list[str] = field(default_factory=list)
    ferramentas_faltantes: list[str] = field(default_factory=list)

    # Perguntas
    perguntas_para_gestor: list[str] = field(default_factory=list)

    # Plano
    passos: list[PassoPlano] = field(default_factory=list)
    metricas_sucesso: list[str] = field(default_factory=list)
    riscos: list[str] = field(default_factory=list)

    # Necessidades
    necessidades: list[NecessidadeIdentificada] = field(default_factory=list)

    # Avaliacao final
    viavel: bool = True
    ressalvas: list[str] = field(default_factory=list)
    avaliacao_honesta: str = ""

    def to_dict(self) -> dict:
        """Converte para dicionario serializavel."""
        data = asdict(self)
        data["tipo_demanda"] = self.tipo_demanda.value
        return data


# =============================================================================
# PROMPT DE ANALISE
# =============================================================================

PROMPT_ANALISE = """Voce eh a Julia, escalista senior da Revoluna com 4 anos de experiencia em staffing medico. Voce conhece bem o mercado, sabe como medicos pensam, e entende as dificuldades de fechar escalas.

O gestor escreveu um briefing para voce. Seu trabalho eh analisar a demanda e criar um plano de acao realista.

## COMO VOCE DEVE PENSAR

### 1. ENTENDER A DEMANDA
- Qual o objetivo final do gestor?
- Eh uma tarefa de rotina ou algo novo?
- Tem deadline? Qual a urgencia?
- O que define "sucesso" nessa demanda?

### 2. CLASSIFICAR O TIPO
Identifique se eh:
- **operacional**: Fechar escala, preencher vagas, follow-ups
- **mapeamento**: Descobrir informacoes sobre medicos/mercado
- **expansao**: Conseguir novos contatos, indicacoes, "crawling"
- **inteligencia**: Analisar dados, entender padroes, responder perguntas
- **novo_territorio**: Regiao ou segmento que nao atuamos ainda
- **misto**: Combinacao de tipos

### 3. AVALIAR O QUE VOCE TEM
Considere:
- Dados da base: ~1600 anestesistas, com telefone, nome, CRM, especialidade, cidade
- Historico de conversas com cada medico
- Preferencias detectadas (turno, regiao, hospitais)
- Vagas dos hospitais parceiros
- Metricas de campanhas anteriores

### 4. IDENTIFICAR O QUE FALTA
- Precisa de dados que nao tem? Quais especificamente?
- Precisa de ferramenta que nao existe? Para que?
- Precisa de aprovacao ou decisao do gestor?
- O prazo eh realista?

### 5. CRIAR O PLANO
- Passos concretos e ordenados
- O que VOCE faz vs. o que PRECISA de ajuda
- Como vai medir se deu certo

### 6. SER HONESTA
- Se algo for impossivel, diga claramente
- Se precisar de ferramenta nova, especifique
- Se o prazo for irrealista, avise

---

## SUAS FERRAMENTAS ATUAIS

Voce pode:
- Enviar mensagem WhatsApp para medico
- Buscar medicos na base (por regiao, especialidade, status)
- Buscar vagas disponiveis
- Reservar vaga para medico
- Consultar historico de conversas
- Bloquear/desbloquear medico
- Consultar metricas

Voce NAO pode (ainda):
- Acessar bases externas
- Fazer ligacoes telefonicas
- Enviar emails
- Criar novos campos no banco

---

## DADOS ATUAIS

{dados_contexto}

---

## BRIEFING DO GESTOR

{briefing_content}

---

## FORMATO DA RESPOSTA

Responda APENAS com um JSON valido neste formato exato:

{{
  "resumo_demanda": "Resumo em 1-2 frases do que o gestor quer",
  "tipo_demanda": "operacional|mapeamento|expansao|inteligencia|novo_territorio|misto",
  "deadline": "data ou null se nao especificado",
  "urgencia": "alta|media|baixa",
  "dados_disponiveis": ["lista de dados relevantes que voce tem"],
  "dados_faltantes": ["lista de dados que precisaria mas nao tem"],
  "ferramentas_necessarias": ["lista de ferramentas que vai usar"],
  "ferramentas_faltantes": ["lista de ferramentas que precisaria mas nao existem"],
  "perguntas_para_gestor": ["perguntas que precisa fazer antes de comecar"],
  "passos": [
    {{
      "numero": 1,
      "descricao": "O que fazer",
      "prazo": "quando ou null",
      "requer_ajuda": false,
      "tipo_ajuda": null
    }}
  ],
  "metricas_sucesso": ["como saber se deu certo"],
  "riscos": ["o que pode dar errado"],
  "necessidades": [
    {{
      "tipo": "ferramenta|dados|campo_banco",
      "descricao": "O que precisa",
      "caso_uso": "Por que precisa",
      "alternativa_temporaria": "Como contornar por agora ou null",
      "prioridade": "alta|media|baixa"
    }}
  ],
  "viavel": true,
  "ressalvas": ["pontos de atencao"],
  "avaliacao_honesta": "Sua opiniao sincera sobre a viabilidade e o que pode dar certo/errado"
}}
"""


# =============================================================================
# FUNCOES DE CONTEXTO
# =============================================================================

async def _buscar_dados_contexto() -> str:
    """Busca dados atuais para enriquecer a analise."""
    contexto_partes = []

    try:
        # Total de medicos
        resp = supabase.table("clientes").select("id", count="exact").execute()
        total_medicos = resp.count or 0
        contexto_partes.append(f"- Total de medicos na base: {total_medicos}")

        # Por especialidade (top 5)
        resp = supabase.table("clientes").select("especialidade").execute()
        if resp.data:
            especialidades = {}
            for c in resp.data:
                esp = c.get("especialidade") or "Nao informada"
                especialidades[esp] = especialidades.get(esp, 0) + 1
            top_esp = sorted(especialidades.items(), key=lambda x: -x[1])[:5]
            contexto_partes.append(f"- Especialidades principais: {', '.join([f'{e[0]} ({e[1]})' for e in top_esp])}")

        # Vagas abertas
        resp = supabase.table("vagas").select("id", count="exact").eq("status", "aberta").execute()
        vagas_abertas = resp.count or 0
        contexto_partes.append(f"- Vagas abertas: {vagas_abertas}")

        # Conversas ativas
        resp = supabase.table("conversations").select("id", count="exact").eq("status", "ativa").execute()
        conversas_ativas = resp.count or 0
        contexto_partes.append(f"- Conversas ativas: {conversas_ativas}")

        # Taxa de resposta geral (ultimos 7 dias)
        from datetime import timedelta
        uma_semana = (agora_brasilia() - timedelta(days=7)).isoformat()
        resp = supabase.table("interacoes").select("id", count="exact").gte("created_at", uma_semana).execute()
        interacoes_semana = resp.count or 0
        contexto_partes.append(f"- Interacoes na ultima semana: {interacoes_semana}")

    except Exception as e:
        logger.warning(f"Erro ao buscar contexto: {e}")
        contexto_partes.append("- Erro ao buscar alguns dados de contexto")

    return "\n".join(contexto_partes) if contexto_partes else "Dados de contexto indisponiveis"


# =============================================================================
# ANALISADOR
# =============================================================================

class BriefingAnalyzer:
    """Analisador de briefings usando Claude Sonnet."""

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.LLM_MODEL_COMPLEX  # Sonnet

    async def analisar(self, doc_id: str, doc_nome: str, conteudo: str) -> AnaliseResult:
        """
        Analisa um briefing e retorna plano estruturado.

        Args:
            doc_id: ID do documento
            doc_nome: Nome do documento
            conteudo: Conteudo do briefing

        Returns:
            AnaliseResult com plano completo
        """
        logger.info(f"Iniciando analise do briefing: {doc_nome}")

        # Buscar dados de contexto
        dados_contexto = await _buscar_dados_contexto()

        # Montar prompt
        prompt = PROMPT_ANALISE.format(
            dados_contexto=dados_contexto,
            briefing_content=conteudo
        )

        try:
            # Chamar Sonnet
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extrair resposta
            resposta_texto = response.content[0].text

            # Parsear JSON
            analise_dict = self._parsear_resposta(resposta_texto)

            # Construir resultado
            resultado = self._construir_resultado(doc_id, doc_nome, analise_dict)

            logger.info(f"Analise concluida: {doc_nome} - Tipo: {resultado.tipo_demanda.value}")
            return resultado

        except Exception as e:
            logger.error(f"Erro na analise do briefing: {e}")
            # Retornar resultado de erro
            return AnaliseResult(
                doc_id=doc_id,
                doc_nome=doc_nome,
                resumo_demanda=f"Erro ao analisar: {str(e)}",
                viavel=False,
                avaliacao_honesta="Nao consegui analisar o briefing. Tenta de novo ou simplifica o texto."
            )

    def _parsear_resposta(self, texto: str) -> dict:
        """Parseia resposta JSON do LLM."""
        # Tentar extrair JSON do texto
        texto = texto.strip()

        # Se comecar com ```, remover
        if texto.startswith("```"):
            linhas = texto.split("\n")
            # Remover primeira e ultima linha se forem ```
            if linhas[0].startswith("```"):
                linhas = linhas[1:]
            if linhas and linhas[-1].startswith("```"):
                linhas = linhas[:-1]
            texto = "\n".join(linhas)

        try:
            return json.loads(texto)
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao parsear JSON: {e}")
            # Tentar encontrar JSON no texto
            import re
            match = re.search(r'\{.*\}', texto, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Resposta do LLM nao eh JSON valido: {texto[:200]}...")

    def _construir_resultado(self, doc_id: str, doc_nome: str, data: dict) -> AnaliseResult:
        """Constroi AnaliseResult a partir do dict parseado."""
        # Converter passos
        passos = []
        for p in data.get("passos", []):
            passos.append(PassoPlano(
                numero=p.get("numero", 0),
                descricao=p.get("descricao", ""),
                prazo=p.get("prazo"),
                requer_ajuda=p.get("requer_ajuda", False),
                tipo_ajuda=p.get("tipo_ajuda")
            ))

        # Converter necessidades
        necessidades = []
        for n in data.get("necessidades", []):
            necessidades.append(NecessidadeIdentificada(
                tipo=n.get("tipo", "dados"),
                descricao=n.get("descricao", ""),
                caso_uso=n.get("caso_uso", ""),
                alternativa_temporaria=n.get("alternativa_temporaria"),
                prioridade=n.get("prioridade", "media")
            ))

        # Converter tipo de demanda
        tipo_str = data.get("tipo_demanda", "operacional")
        try:
            tipo = TipoDemanda(tipo_str)
        except ValueError:
            tipo = TipoDemanda.OPERACIONAL

        return AnaliseResult(
            doc_id=doc_id,
            doc_nome=doc_nome,
            resumo_demanda=data.get("resumo_demanda", ""),
            tipo_demanda=tipo,
            deadline=data.get("deadline"),
            urgencia=data.get("urgencia", "media"),
            dados_disponiveis=data.get("dados_disponiveis", []),
            dados_faltantes=data.get("dados_faltantes", []),
            ferramentas_necessarias=data.get("ferramentas_necessarias", []),
            ferramentas_faltantes=data.get("ferramentas_faltantes", []),
            perguntas_para_gestor=data.get("perguntas_para_gestor", []),
            passos=passos,
            metricas_sucesso=data.get("metricas_sucesso", []),
            riscos=data.get("riscos", []),
            necessidades=necessidades,
            viavel=data.get("viavel", True),
            ressalvas=data.get("ressalvas", []),
            avaliacao_honesta=data.get("avaliacao_honesta", "")
        )


# =============================================================================
# FORMATADOR DE PLANO
# =============================================================================

def formatar_plano_para_documento(analise: AnaliseResult) -> str:
    """
    Formata a analise em Markdown para escrever no Google Docs.

    Args:
        analise: Resultado da analise

    Returns:
        Texto formatado em Markdown
    """
    linhas = []

    # Header
    linhas.append("## Plano da Julia")
    linhas.append(f"*Gerado em: {agora_brasilia().strftime('%d/%m/%Y %H:%M')}*")
    linhas.append("*Status: Aguardando aprovacao*")
    linhas.append("")

    # O que entendi
    linhas.append("### O que entendi")
    linhas.append(analise.resumo_demanda)
    linhas.append("")

    # Tipo e urgencia
    linhas.append("### Avaliacao")
    linhas.append(f"**Tipo de demanda:** {analise.tipo_demanda.value}")
    linhas.append(f"**Urgencia:** {analise.urgencia}")
    if analise.deadline:
        linhas.append(f"**Deadline:** {analise.deadline}")
    linhas.append("")

    # O que tenho vs nao tenho
    if analise.dados_disponiveis:
        linhas.append("**O que tenho:**")
        for item in analise.dados_disponiveis:
            linhas.append(f"- {item}")
        linhas.append("")

    if analise.dados_faltantes:
        linhas.append("**O que nao tenho:**")
        for item in analise.dados_faltantes:
            linhas.append(f"- {item}")
        linhas.append("")

    # Perguntas
    if analise.perguntas_para_gestor:
        linhas.append("### Perguntas para voce")
        for pergunta in analise.perguntas_para_gestor:
            linhas.append(f"- {pergunta}")
        linhas.append("")

    # Plano de acao
    linhas.append("### Plano de acao")
    for passo in analise.passos:
        status = "[ ]" if not passo.requer_ajuda else "[?]"
        prazo = f" *(ate {passo.prazo})*" if passo.prazo else ""
        ajuda = f" - *preciso de ajuda: {passo.tipo_ajuda}*" if passo.requer_ajuda else ""
        linhas.append(f"{passo.numero}. {status} {passo.descricao}{prazo}{ajuda}")
    linhas.append("")

    # Necessidades identificadas
    if analise.necessidades:
        linhas.append("### Necessidades identificadas")
        for nec in analise.necessidades:
            emoji = "!" if nec.prioridade == "alta" else "?" if nec.prioridade == "media" else "-"
            linhas.append(f"- [{emoji}] **{nec.tipo}:** {nec.descricao}")
            linhas.append(f"  - Caso de uso: {nec.caso_uso}")
            if nec.alternativa_temporaria:
                linhas.append(f"  - Alternativa: {nec.alternativa_temporaria}")
        linhas.append("")

    # Metricas de sucesso
    if analise.metricas_sucesso:
        linhas.append("### Metricas de sucesso")
        for metrica in analise.metricas_sucesso:
            linhas.append(f"- [ ] {metrica}")
        linhas.append("")

    # Riscos
    if analise.riscos:
        linhas.append("### Riscos")
        for risco in analise.riscos:
            linhas.append(f"- {risco}")
        linhas.append("")

    # Avaliacao honesta
    linhas.append("### Minha avaliacao")
    viavel_emoji = "Viavel" if analise.viavel else "Dificil/Impossivel"
    linhas.append(f"**Viabilidade:** {viavel_emoji}")
    if analise.ressalvas:
        linhas.append("**Ressalvas:**")
        for r in analise.ressalvas:
            linhas.append(f"- {r}")
    linhas.append("")
    linhas.append(analise.avaliacao_honesta)

    return "\n".join(linhas)


def formatar_plano_para_slack(analise: AnaliseResult, doc_url: str) -> str:
    """
    Formata resumo do plano para apresentar no Slack.

    Args:
        analise: Resultado da analise
        doc_url: URL do documento

    Returns:
        Texto formatado para Slack
    """
    linhas = []

    linhas.append(f"Li o briefing *{analise.doc_nome}*!")
    linhas.append("")

    linhas.append(f"*Entendi que:* {analise.resumo_demanda}")
    linhas.append("")

    # Resumo do plano (max 5 passos)
    linhas.append("*Meu plano:*")
    for passo in analise.passos[:5]:
        linhas.append(f"{passo.numero}. {passo.descricao}")
    if len(analise.passos) > 5:
        linhas.append(f"   _...e mais {len(analise.passos) - 5} passos_")
    linhas.append("")

    # Perguntas se houver
    if analise.perguntas_para_gestor:
        linhas.append("*Preciso confirmar com voce:*")
        for p in analise.perguntas_para_gestor[:3]:
            linhas.append(f"- {p}")
        linhas.append("")

    # Se nao viavel, avisar
    if not analise.viavel:
        linhas.append("*Atencao:* Tem alguns pontos que podem dificultar:")
        for r in analise.ressalvas[:2]:
            linhas.append(f"- {r}")
        linhas.append("")

    linhas.append(f"Posso executar? (plano completo: {doc_url})")

    return "\n".join(linhas)


# =============================================================================
# INSTANCIA SINGLETON
# =============================================================================

_analyzer: Optional[BriefingAnalyzer] = None


def get_analyzer() -> BriefingAnalyzer:
    """Retorna instancia singleton do analisador."""
    global _analyzer
    if _analyzer is None:
        _analyzer = BriefingAnalyzer()
    return _analyzer


async def analisar_briefing(doc_id: str, doc_nome: str, conteudo: str) -> AnaliseResult:
    """
    Funcao de conveniencia para analisar briefing.

    Args:
        doc_id: ID do documento
        doc_nome: Nome do documento
        conteudo: Conteudo do briefing

    Returns:
        AnaliseResult
    """
    analyzer = get_analyzer()
    return await analyzer.analisar(doc_id, doc_nome, conteudo)
