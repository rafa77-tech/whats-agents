"""
Validação de payloads de mensagens interativas do WhatsApp.

Sprint 67 (R3) — Garante conformidade com limites da API Meta.

Limites WhatsApp:
- Buttons: max 3 botões, títulos até 20 chars
- List: max 10 itens, títulos até 24 chars, descrições até 72 chars
- CTA URL: URLs devem ser HTTPS
"""

import logging

logger = logging.getLogger(__name__)

# Limites da API WhatsApp
LIMITS = {
    "buttons": {
        "max_buttons": 3,
        "max_title_chars": 20,
    },
    "list": {
        "max_items": 10,
        "max_item_title_chars": 24,
        "max_item_description_chars": 72,
        "max_button_text_chars": 20,
    },
    "cta_url": {
        "max_display_text_chars": 20,
    },
}


def validar_payload_interactive(tipo: str, payload: dict) -> tuple[bool, str]:
    """
    Valida payload de mensagem interativa contra limites do WhatsApp.

    Args:
        tipo: Tipo de mensagem ('buttons', 'list', 'cta_url')
        payload: Payload da mensagem interativa

    Returns:
        Tuple (valido, mensagem_erro). Se válido, mensagem_erro é string vazia.
    """
    if tipo not in LIMITS:
        return False, f"Tipo '{tipo}' não suportado. Use: {list(LIMITS.keys())}"

    if not isinstance(payload, dict):
        return False, "Payload deve ser um dicionário"

    if tipo == "buttons":
        return _validar_buttons(payload)
    elif tipo == "list":
        return _validar_list(payload)
    elif tipo == "cta_url":
        return _validar_cta_url(payload)

    return False, f"Tipo '{tipo}' não implementado"


def _validar_buttons(payload: dict) -> tuple[bool, str]:
    """Valida payload de botões."""
    buttons = payload.get("buttons", [])

    if not buttons:
        return False, "Payload de buttons deve ter pelo menos 1 botão"

    max_b = LIMITS["buttons"]["max_buttons"]
    if len(buttons) > max_b:
        return False, f"Máximo de {max_b} botões, recebido {len(buttons)}"

    max_title = LIMITS["buttons"]["max_title_chars"]
    for i, btn in enumerate(buttons):
        title = btn.get("title", "")
        if not title:
            return False, f"Botão {i} sem título"
        if len(title) > max_title:
            return (
                False,
                f"Título do botão {i} excede {max_title} chars: '{title}' ({len(title)})",
            )

    return True, ""


def _validar_list(payload: dict) -> tuple[bool, str]:
    """Valida payload de lista."""
    sections = payload.get("sections", [])
    if not sections:
        return False, "Payload de list deve ter pelo menos 1 seção"

    button_text = payload.get("button", "")
    max_btn = LIMITS["list"]["max_button_text_chars"]
    if button_text and len(button_text) > max_btn:
        return (
            False,
            f"Texto do botão da lista excede {max_btn} chars: '{button_text}' ({len(button_text)})",
        )

    total_items = 0
    max_items = LIMITS["list"]["max_items"]
    max_title = LIMITS["list"]["max_item_title_chars"]
    max_desc = LIMITS["list"]["max_item_description_chars"]

    for s_idx, section in enumerate(sections):
        rows = section.get("rows", [])
        total_items += len(rows)

        if total_items > max_items:
            return (
                False,
                f"Total de itens excede {max_items}: {total_items}",
            )

        for r_idx, row in enumerate(rows):
            title = row.get("title", "")
            if not title:
                return False, f"Item seção {s_idx}, row {r_idx} sem título"
            if len(title) > max_title:
                return (
                    False,
                    f"Título do item seção {s_idx} row {r_idx} excede {max_title} chars: '{title}' ({len(title)})",
                )

            desc = row.get("description", "")
            if desc and len(desc) > max_desc:
                return (
                    False,
                    f"Descrição do item seção {s_idx} row {r_idx} excede {max_desc} chars ({len(desc)})",
                )

    return True, ""


def _validar_cta_url(payload: dict) -> tuple[bool, str]:
    """Valida payload de CTA URL."""
    url = payload.get("url", "")
    if not url:
        return False, "CTA URL deve ter uma URL"

    if not url.startswith("https://"):
        return False, f"URL deve ser HTTPS: '{url}'"

    display_text = payload.get("display_text", "")
    max_text = LIMITS["cta_url"]["max_display_text_chars"]
    if display_text and len(display_text) > max_text:
        return (
            False,
            f"Texto do CTA excede {max_text} chars: '{display_text}' ({len(display_text)})",
        )

    return True, ""


def sanitizar_payload_interactive(tipo: str, payload: dict) -> dict:
    """
    Sanitiza payload truncando valores que excedem limites.

    Em vez de rejeitar, trunca strings para caber nos limites.
    Útil quando dados vêm de fontes externas (nomes de hospitais, etc).

    Args:
        tipo: Tipo de mensagem ('buttons', 'list', 'cta_url')
        payload: Payload original

    Returns:
        Payload sanitizado (cópia, não modifica original).
    """
    if not isinstance(payload, dict):
        return payload

    import copy

    result = copy.deepcopy(payload)

    if tipo == "buttons":
        return _sanitizar_buttons(result)
    elif tipo == "list":
        return _sanitizar_list(result)
    elif tipo == "cta_url":
        return _sanitizar_cta_url(result)

    return result


def _truncar(text: str, max_len: int) -> str:
    """Trunca texto adicionando '…' se necessário."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _sanitizar_buttons(payload: dict) -> dict:
    """Sanitiza payload de botões."""
    max_b = LIMITS["buttons"]["max_buttons"]
    max_title = LIMITS["buttons"]["max_title_chars"]

    buttons = payload.get("buttons", [])[:max_b]
    for btn in buttons:
        if "title" in btn:
            btn["title"] = _truncar(btn["title"], max_title)

    payload["buttons"] = buttons
    return payload


def _sanitizar_list(payload: dict) -> dict:
    """Sanitiza payload de lista."""
    max_items = LIMITS["list"]["max_items"]
    max_title = LIMITS["list"]["max_item_title_chars"]
    max_desc = LIMITS["list"]["max_item_description_chars"]
    max_btn = LIMITS["list"]["max_button_text_chars"]

    if "button" in payload:
        payload["button"] = _truncar(payload["button"], max_btn)

    total = 0
    for section in payload.get("sections", []):
        rows = section.get("rows", [])
        remaining = max_items - total
        if remaining <= 0:
            section["rows"] = []
            continue

        rows = rows[:remaining]
        for row in rows:
            if "title" in row:
                row["title"] = _truncar(row["title"], max_title)
            if "description" in row:
                row["description"] = _truncar(row["description"], max_desc)

        section["rows"] = rows
        total += len(rows)

    return payload


def _sanitizar_cta_url(payload: dict) -> dict:
    """Sanitiza payload de CTA URL."""
    max_text = LIMITS["cta_url"]["max_display_text_chars"]

    if "display_text" in payload:
        payload["display_text"] = _truncar(payload["display_text"], max_text)

    return payload
