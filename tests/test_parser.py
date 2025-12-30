"""
Testes do parser de mensagens.
"""
import pytest
from app.services.parser import (
    extrair_telefone,
    is_grupo,
    is_status,
    is_lid_format,
    extrair_texto,
    identificar_tipo,
    parsear_mensagem,
    deve_processar,
)


class TestExtrairTelefone:
    def test_numero_normal(self):
        assert extrair_telefone("5511999999999@s.whatsapp.net") == "5511999999999"

    def test_grupo(self):
        assert extrair_telefone("5511999999999-123456@g.us") == "5511999999999"

    def test_vazio(self):
        assert extrair_telefone("") == ""
        assert extrair_telefone(None) == ""

    def test_lid_format_retorna_vazio(self):
        """LID format não contém telefone real, deve retornar vazio."""
        assert extrair_telefone("211484206436558@lid") == ""
        assert extrair_telefone("154417159582282@lid") == ""


class TestIsLidFormat:
    def test_lid_verdadeiro(self):
        assert is_lid_format("211484206436558@lid") == True
        assert is_lid_format("154417159582282@lid") == True

    def test_lid_falso_whatsapp_normal(self):
        assert is_lid_format("5511999999999@s.whatsapp.net") == False

    def test_lid_falso_grupo(self):
        assert is_lid_format("5511999999999-123456@g.us") == False

    def test_lid_vazio(self):
        assert is_lid_format("") == False
        assert is_lid_format(None) == False


class TestIsGrupo:
    def test_grupo(self):
        assert is_grupo("123@g.us") == True

    def test_individual(self):
        assert is_grupo("123@s.whatsapp.net") == False

    def test_vazio(self):
        assert is_grupo("") == False
        assert is_grupo(None) == False


class TestIsStatus:
    def test_status(self):
        assert is_status("status@broadcast") == True

    def test_normal(self):
        assert is_status("123@s.whatsapp.net") == False

    def test_vazio(self):
        assert is_status("") == False
        assert is_status(None) == False


class TestExtrairTexto:
    def test_conversation(self):
        msg = {"conversation": "Oi, tudo bem?"}
        assert extrair_texto(msg) == "Oi, tudo bem?"

    def test_extended(self):
        msg = {"extendedTextMessage": {"text": "Link: http://..."}}
        assert extrair_texto(msg) == "Link: http://..."

    def test_imagem_com_caption(self):
        msg = {"imageMessage": {"caption": "Foto do hospital"}}
        assert extrair_texto(msg) == "Foto do hospital"

    def test_documento_com_caption(self):
        msg = {"documentMessage": {"caption": "Contrato assinado"}}
        assert extrair_texto(msg) == "Contrato assinado"

    def test_video_com_caption(self):
        msg = {"videoMessage": {"caption": "Video do plantao"}}
        assert extrair_texto(msg) == "Video do plantao"

    def test_sem_texto(self):
        msg = {"audioMessage": {}}
        assert extrair_texto(msg) == None

    def test_vazio(self):
        assert extrair_texto({}) == None
        assert extrair_texto(None) == None


class TestIdentificarTipo:
    def test_texto_conversation(self):
        assert identificar_tipo({"conversation": "oi"}) == "texto"

    def test_texto_extended(self):
        assert identificar_tipo({"extendedTextMessage": {"text": "oi"}}) == "texto"

    def test_audio(self):
        assert identificar_tipo({"audioMessage": {}}) == "audio"

    def test_imagem(self):
        assert identificar_tipo({"imageMessage": {}}) == "imagem"

    def test_documento(self):
        assert identificar_tipo({"documentMessage": {}}) == "documento"

    def test_video(self):
        assert identificar_tipo({"videoMessage": {}}) == "video"

    def test_sticker(self):
        assert identificar_tipo({"stickerMessage": {}}) == "sticker"

    def test_outro(self):
        assert identificar_tipo({"reactionMessage": {}}) == "outro"

    def test_vazio(self):
        assert identificar_tipo({}) == "outro"
        assert identificar_tipo(None) == "outro"


class TestParsearMensagem:
    def test_mensagem_completa(self):
        data = {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {
                "conversation": "Oi, tenho interesse em plantão"
            },
            "messageTimestamp": 1701888000,
            "pushName": "Dr. Carlos"
        }

        msg = parsear_mensagem(data)

        assert msg is not None
        assert msg.telefone == "5511999999999"
        assert msg.tipo == "texto"
        assert msg.texto == "Oi, tenho interesse em plantão"
        assert msg.from_me == False
        assert msg.nome_contato == "Dr. Carlos"
        assert msg.is_grupo == False
        assert msg.is_status == False

    def test_mensagem_de_grupo(self):
        data = {
            "key": {
                "remoteJid": "5511999999999-123456@g.us",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {"conversation": "Mensagem no grupo"},
            "messageTimestamp": 1701888000,
        }

        msg = parsear_mensagem(data)

        assert msg is not None
        assert msg.is_grupo == True

    def test_mensagem_propria(self):
        data = {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": True,
                "id": "ABC123"
            },
            "message": {"conversation": "Minha mensagem"},
            "messageTimestamp": 1701888000,
        }

        msg = parsear_mensagem(data)

        assert msg is not None
        assert msg.from_me == True

    def test_mensagem_sem_jid(self):
        data = {
            "key": {
                "remoteJid": "",
                "fromMe": False,
                "id": "ABC123"
            },
        }

        msg = parsear_mensagem(data)
        assert msg is None

    def test_mensagem_sem_id(self):
        data = {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": ""
            },
        }

        msg = parsear_mensagem(data)
        assert msg is None

    def test_mensagem_lid_com_remote_jid_alt(self):
        """LID com remoteJidAlt deve extrair telefone do alt."""
        data = {
            "key": {
                "remoteJid": "211484206436558@lid",
                "remoteJidAlt": "5511981677736@s.whatsapp.net",
                "fromMe": False,
                "id": "3A287F9E01CFA289E153"
            },
            "message": {"conversation": "Oi, tenho interesse"},
            "messageTimestamp": 1701888000,
            "pushName": "Rafael Pivovar"
        }

        msg = parsear_mensagem(data)

        assert msg is not None
        assert msg.telefone == "5511981677736"  # Extraído do remoteJidAlt
        assert msg.is_lid == True
        assert msg.remote_jid == "211484206436558@lid"
        assert msg.remote_jid_alt == "5511981677736@s.whatsapp.net"
        assert msg.nome_contato == "Rafael Pivovar"

    def test_mensagem_lid_sem_remote_jid_alt(self):
        """LID sem remoteJidAlt não tem telefone."""
        data = {
            "key": {
                "remoteJid": "211484206436558@lid",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {"conversation": "Oi"},
            "messageTimestamp": 1701888000,
            "pushName": "Usuario"
        }

        msg = parsear_mensagem(data)

        assert msg is not None
        assert msg.telefone == ""  # Não tem telefone
        assert msg.is_lid == True
        assert msg.remote_jid == "211484206436558@lid"
        assert msg.remote_jid_alt is None


class TestDeveProcessar:
    def test_mensagem_valida(self):
        data = {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {"conversation": "Oi"},
            "messageTimestamp": 1701888000,
        }
        msg = parsear_mensagem(data)
        assert deve_processar(msg) == True

    def test_mensagem_propria(self):
        data = {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": True,
                "id": "ABC123"
            },
            "message": {"conversation": "Oi"},
            "messageTimestamp": 1701888000,
        }
        msg = parsear_mensagem(data)
        assert deve_processar(msg) == False

    def test_mensagem_grupo(self):
        data = {
            "key": {
                "remoteJid": "5511999999999-123456@g.us",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {"conversation": "Oi"},
            "messageTimestamp": 1701888000,
        }
        msg = parsear_mensagem(data)
        assert deve_processar(msg) == False

    def test_mensagem_status(self):
        data = {
            "key": {
                "remoteJid": "status@broadcast",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {},
            "messageTimestamp": 1701888000,
        }
        msg = parsear_mensagem(data)
        assert deve_processar(msg) == False

    def test_mensagem_lid_com_telefone_deve_processar(self):
        """LID com telefone (via remoteJidAlt) deve ser processada."""
        data = {
            "key": {
                "remoteJid": "211484206436558@lid",
                "remoteJidAlt": "5511981677736@s.whatsapp.net",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {"conversation": "Oi"},
            "messageTimestamp": 1701888000,
            "pushName": "Usuario"
        }
        msg = parsear_mensagem(data)
        assert deve_processar(msg) == True

    def test_mensagem_lid_sem_telefone_nao_processa(self):
        """LID sem telefone (sem remoteJidAlt) não deve ser processada."""
        data = {
            "key": {
                "remoteJid": "211484206436558@lid",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {"conversation": "Oi"},
            "messageTimestamp": 1701888000,
            "pushName": "Usuario"
        }
        msg = parsear_mensagem(data)
        assert deve_processar(msg) == False
