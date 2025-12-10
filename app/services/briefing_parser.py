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

    IMPORTANTE: O documento DEVE usar formato Markdown com # e ##
    para marcar secoes. Isso evita interpretar texto livre como input.

    Formato esperado:
    ```
    # Briefing Julia - Semana DD/MM

    ## Foco da Semana
    - Item 1
    - Item 2

    ## Vagas Prioritarias
    - Hospital X - Data - ate R$ Y

    ## Tom da Semana
    - Instrucao 1

    ## Observacoes
    - Nota 1
    ```

    Args:
        conteudo: Texto completo do documento

    Returns:
        dict com secoes parseadas
    """
    secoes = {
        "foco_semana": [],
        "vagas_prioritarias": [],
        "tom_semana": [],
        "observacoes": [],
        "margem_negociacao": None,
        "titulo": None,
        "raw": conteudo
    }

    if not conteudo:
        return secoes

    # Extrair titulo (# Titulo) - permite espacos no inicio da linha
    titulo_match = re.search(r'^\s*#\s+(.+?)$', conteudo, re.MULTILINE)
    if titulo_match:
        secoes["titulo"] = titulo_match.group(1).strip()

    # Dividir por secoes (## Titulo) - EXIGE marcador Markdown
    # Permite espacos antes do ## (Google Docs adiciona espacos)
    partes = re.split(r'\n\s*##\s+', conteudo)

    for parte in partes:
        linhas = parte.strip().split('\n')
        if not linhas:
            continue

        titulo = linhas[0].lower().strip()

        # Extrair itens (linhas que comecam com - ou *)
        # strip() remove espacos que Google Docs adiciona
        itens = []
        for linha in linhas[1:]:
            linha_limpa = linha.strip()
            if linha_limpa.startswith('-'):
                itens.append(linha_limpa[1:].strip())
            elif linha_limpa.startswith('*'):
                itens.append(linha_limpa[1:].strip())

        # Classificar secao
        if 'foco' in titulo:
            secoes["foco_semana"] = itens
        elif 'vaga' in titulo and 'priorit' in titulo:
            secoes["vagas_prioritarias"] = _parsear_vagas(itens)
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
                f"{len(secoes['tom_semana'])} instrucoes de tom")

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
        avisos.append("Secao '## Foco da Semana' esta vazia ou ausente")

    # Verificar vagas prioritarias tem estrutura correta
    for i, vaga in enumerate(secoes.get("vagas_prioritarias", [])):
        if "raw" in vaga:
            avisos.append(f"Vaga {i+1} nao pode ser parseada: {vaga['raw'][:50]}")

    return {
        "valido": len(erros) == 0,
        "erros": erros,
        "avisos": avisos,
        "secoes_encontradas": [
            k for k, v in secoes.items()
            if v and k not in ["raw", "titulo", "margem_negociacao"]
        ]
    }
