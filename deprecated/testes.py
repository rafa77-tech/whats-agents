import requests
import os
from dotenv import load_dotenv
import io
from PIL import Image
import base64

load_dotenv()


BASE_URL = "http://localhost:8080"
API_KEY = os.getenv("AUTHENTICATION_API_KEY")

payload = {
    "instanceName": "Revoluna",
    "integration": "WHATSAPP-BAILEYS"
}

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(f"{BASE_URL}/instance/create", json=payload, headers=headers)
print(response.json())

#### Gerando QR Code
payload = {
    "instanceName": "Revoluna",
    "integration": "WHATSAPP-BAILEYS"
}

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

response = requests.get(f"{BASE_URL}/instance/connect/Revoluna", json=payload, headers=headers)
print(response.json())

# Gerando imagem do QR Code
# O uso do IPython.display só faz sentido em ambiente notebook/Jupyter;
# em ambiente script/python puro, este display não exibirá a imagem.

try:
    import IPython.display as display
except ImportError:
    display = None

data = response.json()
qr_base64 = data.get("base64")

if qr_base64:
    # Remove prefixo se houver e decodifica corretamente
    if "," in qr_base64:
        img_bytes = base64.b64decode(qr_base64.split(",")[1])
    else:
        img_bytes = base64.b64decode(qr_base64)
    img = Image.open(io.BytesIO(img_bytes))

    if display:
        display.display(img)
    else:
        # Em ambiente python script, só salva localmente ou exibe com img.show()
        img.show()
else:
    print("QR code base64 não encontrado na resposta.")



########################################################


import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")  # http://localhost:8080
API_KEY = os.getenv("AUTHENTICATION_API_KEY")

payload = {
    "enabled": True,
    "accountId": "3",  
    "token": "mWX8rVVqDrnRGdYWiTNHuQaG", 
    "url": "http://rails:3000",  # ← corrigido aqui
    "signMsg": True,
    "reopenConversation": True,
    "conversationPending": False,
    "nameInbox": "WhatsApp",
    "mergeBrazilContacts": True,
    "importContacts": True,
    "importMessages": True,
    "daysLimitImportMessages": 7,
    "autoCreate": True
}

response = requests.post(
    f"{BASE_URL}/chatwoot/set/Revoluna",
    headers={
        "apikey": API_KEY,
        "Content-Type": "application/json"
    },
    json=payload
)

print(response.json())


########################################################



payload = {
    "enabled": True,
    "accountId": "3",  
    "token": "mWX8rVVqDrnRGdYWiTNHuQaG", 
    "url": "http://rails:3000",
    "signMsg": True,
    "reopenConversation": True,
    "conversationPending": False,
    "nameInbox": "WhatsApp",
    "mergeBrazilContacts": True,
    "importContacts": True,
    "importMessages": True,
    "daysLimitImportMessages": 7,
    "autoCreate": True
}

response = requests.post(
    f"{BASE_URL}/chatwoot/set/Revoluna",
    headers={
        "apikey": API_KEY,
        "Content-Type": "application/json"
    },
    json=payload
)

print(response.json())



########################################################
payload = {
    "webhook": {
        "enabled": True,
        "url": "http://n8n:5678/webhook-test/whatsapp",
        "webhookByEvents": False,
        "events": [
            "MESSAGES_UPSERT"
        ]
    }
}

response = requests.post(
    f"{BASE_URL}/webhook/set/Revoluna",
    headers={
        "apikey": API_KEY,
        "Content-Type": "application/json"
    },
    json=payload
)

print(response.json())


########################################################



import requests

response = requests.post(
    "https://api.deepseek.com/v1/chat/completions",
    headers={
        "Authorization": "Bearer sk-6b8cf8914801446380bf4e94d2a95e13",
        "Content-Type": "application/json"
    },
    json={
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Olá, tudo bem?"}
        ]
    }
)

print(response.json())


########################################################



payload = {
    "webhook": {
        "enabled": True,
        "url": "http://n8n:5678/webhook/whatsapp",  # ← sem o "-test"
        "webhookByEvents": False,
        "events": ["MESSAGES_UPSERT"]
    }
}

response = requests.post(
    f"{BASE_URL}/webhook/set/Revoluna",
    headers={
        "apikey": API_KEY,
        "Content-Type": "application/json"
    },
    json=payload
)

print(response.json())

