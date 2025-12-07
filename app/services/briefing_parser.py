"""
Parser de documentos de briefing.

Extrai secoes estruturadas de um documento de briefing
para configurar comportamento da Julia.

Formato esperado do documento:
```
# Briefing Julia - Semana XX/XX

## Foco da Semana
- Item 1
- Item 2

## Vagas Prioritarias
- Hospital X - Data - ate R$ Y

## Medicos VIP
- Dr. Nome (CRM XXXXX) - observacao

## Medicos Bloqueados
- Dr. Nome (CRM XXXXX) - motivo

## Tom da Semana
- Mais urgente
- Pode oferecer ate X% a mais

## Observacoes
- Nota importante
```
"""
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def parsear_briefing(conteudo: str) -> dict:
    """
    Parseia documento de briefing e extrai secoes.

    Args:
        conteudo: Texto completo do documento

    Returns:
        dict com secoes parseadas
    """
    secoes = {
        "foco_semana": [],
        "vagas_prioritarias": [],
        "medicos_vip": [],
        "medicos_bloqueados": [],
        "tom_semana": [],
        "observacoes": [],
        "margem_negociacao": None,
        "titulo": None,
        "raw": conteudo
    }

    if not conteudo:
        return secoes

    # Extrair titulo (# Titulo)
    titulo_match = re.search(r'^#\s+(.+?)$', conteudo, re.MULTILINE)
    if titulo_match:
        secoes["titulo"] = titulo_match.group(1).strip()

    # Dividir por secoes (## Titulo)
    partes = re.split(r'\n##\s+', conteudo)

    for parte in partes:
        linhas = parte.strip().split('\n')
        if not linhas:
            continue

        titulo = linhas[0].lower().strip()

        # Extrair itens (linhas que comecam com -)
        itens = []
        for linha in linhas[1:]:
            linha_limpa = linha.strip()
            if linha_limpa.startswith('-'):
                itens.append(linha_limpa.lstrip('- ').strip())
            elif linha_limpa.startswith('*'):
                itens.append(linha_limpa.lstrip('* ').strip())

        # Classificar secao
        if 'foco' in titulo:
            secoes["foco_semana"] = itens
        elif 'vaga' in titulo and 'priorit' in titulo:
            secoes["vagas_prioritarias"] = _parsear_vagas(itens)
        elif 'vip' in titulo or ('medico' in titulo and 'vip' in titulo):
            secoes["medicos_vip"] = _parsear_medicos(itens)
        elif 'bloqueado' in titulo or 'block' in titulo:
            secoes["medicos_bloqueados"] = _parsear_medicos(itens)
        elif 'tom' in titulo:
            secoes["tom_semana"] = itens
            # Extrair margem de negociacao se mencionada
            for item in itens:
                match = re.search(r'(\d+)%', item)
                if match and ('mais' in item.lower() or 'negoci' in item.lower()):
                    secoes["margem_negociacao"] = int(match.group(1))
        elif 'observa' in titulo or 'nota' in titulo:
            secoes["observacoes"] = itens

    logger.info(f"Briefing parseado: {len(secoes['foco_semana'])} focos, "
                f"{len(secoes['vagas_prioritarias'])} vagas prioritarias, "
                f"{len(secoes['medicos_vip'])} VIPs, "
                f"{len(secoes['medicos_bloqueados'])} bloqueados")

    return secoes


def _parsear_vagas(itens: List[str]) -> List[Dict]:
    """
    Extrai informacoes de vagas prioritarias.

    Formato esperado: "Hospital X - Data - ate R$ Y"
    """
    vagas = []
    for item in itens:
        # Formato esperado: "Hospital X - Data - ate R$ Y"
        match = re.search(
            r'(.+?)\s*-\s*(.+?)\s*-\s*(?:at[eé]\s*)?R\$\s*([\d.,]+)',
            item
        )
        if match:
            valor_str = match.group(3).replace('.', '').replace(',', '.')
            try:
                valor = float(valor_str)
            except ValueError:
                valor = 0

            vagas.append({
                "hospital": match.group(1).strip(),
                "data": match.group(2).strip(),
                "valor_max": valor
            })
        else:
            # Se nao conseguiu parsear, salva como raw
            vagas.append({"raw": item})

    return vagas


def _parsear_medicos(itens: List[str]) -> List[Dict]:
    """
    Extrai informacoes de medicos (VIP ou bloqueados).

    Formato esperado: "Dr. Nome (CRM XXXXX) - observacao"
    """
    medicos = []
    for item in itens:
        # Formato esperado: "Dr. Nome (CRM XXXXX) - observacao"
        match = re.search(
            r'(?:Dr\.?a?\.?\s*)?(.+?)\s*\(CRM\s*(\d+)\)',
            item,
            re.IGNORECASE
        )
        if match:
            # Extrair observacao (texto apos o ultimo -)
            obs = ""
            if '-' in item:
                partes = item.split('-')
                if len(partes) > 1:
                    obs = partes[-1].strip()

            medicos.append({
                "nome": match.group(1).strip(),
                "crm": match.group(2),
                "observacao": obs
            })
        else:
            # Se nao conseguiu parsear, salva como raw
            medicos.append({"raw": item})

    return medicos


def validar_briefing(secoes: dict) -> dict:
    """
    Valida estrutura do briefing parseado.

    Args:
        secoes: Dict retornado por parsear_briefing()

    Returns:
        dict com resultado da validacao
    """
    erros = []
    avisos = []

    # Verificar campos obrigatorios
    if not secoes.get("foco_semana"):
        avisos.append("Secao 'Foco da Semana' esta vazia")

    # Verificar vagas prioritarias tem estrutura correta
    for i, vaga in enumerate(secoes.get("vagas_prioritarias", [])):
        if "raw" in vaga:
            avisos.append(f"Vaga {i+1} nao pôde ser parseada: {vaga['raw'][:50]}")

    # Verificar medicos VIP tem CRM
    for i, med in enumerate(secoes.get("medicos_vip", [])):
        if "raw" in med:
            avisos.append(f"Medico VIP {i+1} nao pôde ser parseado: {med['raw'][:50]}")

    # Verificar medicos bloqueados tem CRM
    for i, med in enumerate(secoes.get("medicos_bloqueados", [])):
        if "raw" in med:
            avisos.append(f"Medico bloqueado {i+1} nao pôde ser parseado: {med['raw'][:50]}")

    return {
        "valido": len(erros) == 0,
        "erros": erros,
        "avisos": avisos,
        "secoes_encontradas": [
            k for k, v in secoes.items()
            if v and k not in ["raw", "titulo", "margem_negociacao"]
        ]
    }
