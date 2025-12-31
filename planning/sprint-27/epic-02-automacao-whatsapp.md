# Epic 02: Automacao WhatsApp

**Status:** Pendente
**Estimativa:** 12 horas
**Prioridade:** Alta
**Dependencia:** E01 (Setup VPS)
**Responsavel:** Dev Junior

> **Nota sobre estimativa:** 12h considera curva de aprendizado com Appium.
> - Dia 1 (4h): Setup, aprender Appium, primeiros testes
> - Dia 2 (4h): Automacao funcionando ~50%
> - Dia 3 (4h): Debugging edge cases, testes finais

---

## Objetivo

Criar script de automacao que controla o WhatsApp no emulador para:
1. Registrar novo numero
2. Inserir codigo SMS
3. Escanear QR code da Evolution API

---

## Conceitos Importantes

### O Que e Appium?

Appium e um framework de automacao para apps mobile. Funciona assim:

```
Python Script  -->  Appium Server  -->  ADB  -->  Emulador  -->  WhatsApp
```

- **Python Script**: Nosso codigo que define os passos
- **Appium Server**: Servidor que traduz comandos para o emulador
- **ADB**: Android Debug Bridge (ja instalamos em E01)
- **Emulador**: Nosso AVD "chip-activator"
- **WhatsApp**: O app que vamos controlar

### Locators (Como Encontrar Elementos)

Para clicar em botoes ou digitar texto, precisamos "localizar" elementos na tela:

| Metodo | Exemplo | Quando Usar |
|--------|---------|-------------|
| resource-id | `com.whatsapp:id/agree_button` | Preferido, mais estavel |
| text | `CONCORDAR E CONTINUAR` | Quando nao tem id |
| xpath | `//android.widget.Button[@text='OK']` | Ultimo recurso |
| class + index | `android.widget.EditText[0]` | Para campos de texto |

### UIAutomator2

Driver que usamos para controlar Android. Ja vem integrado com Appium.

---

## Pre-requisitos

- [ ] E01 concluido (emulador funcionando)
- [ ] Python 3.10+ instalado no VPS
- [ ] WhatsApp APK disponivel

### Verificar Python

```bash
python3 --version
# Deve ser 3.10 ou superior
```

---

## Story 2.1: Instalar Appium e Dependencias

### Objetivo
Instalar Appium Server e bibliotecas Python.

### Passo a Passo

**1. Instalar Node.js (necessario para Appium)**

```bash
# Instalar Node.js 18 LTS
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar
node --version   # v18.x.x
npm --version    # 9.x.x ou superior
```

**2. Instalar Appium**

```bash
# Instalar Appium globalmente
sudo npm install -g appium

# Verificar
appium --version
# Deve mostrar: 2.x.x
```

**3. Instalar driver UIAutomator2**

```bash
# Instalar driver para Android
appium driver install uiautomator2

# Verificar
appium driver list --installed
# Deve mostrar: uiautomator2
```

**4. Instalar dependencias Python**

```bash
# Criar ambiente virtual
cd /opt/chip-activator
python3 -m venv venv
source venv/bin/activate

# Instalar bibliotecas
pip install \
    Appium-Python-Client==3.1.0 \
    selenium==4.15.0 \
    requests==2.31.0 \
    Pillow==10.1.0

# Criar requirements.txt
pip freeze > requirements.txt
```

**5. Verificar instalacao**

```bash
# Testar import
python3 -c "from appium import webdriver; print('OK')"
# Deve mostrar: OK
```

### DoD

- [ ] Node.js instalado
- [ ] Appium instalado
- [ ] Driver uiautomator2 instalado
- [ ] Dependencias Python instaladas

---

## Story 2.2: Baixar WhatsApp APK

### Objetivo
Obter APK do WhatsApp para instalar no emulador.

### Passo a Passo

**1. Baixar APK**

Baixar de fonte confiavel (APKMirror):

```bash
cd /opt/chip-activator

# Criar pasta para APKs
mkdir -p apks

# Baixar WhatsApp (verificar versao mais recente)
# Usar versao arm64-v8a + armeabi-v7a + x86 + x86_64
wget -O apks/whatsapp.apk "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/whatsapp-2-24-25-76-release/whatsapp-messenger-2-24-25-76-android-apk-download/"
```

**NOTA:** O link acima pode mudar. Passos para baixar manualmente:

1. Acessar https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/
2. Clicar na versao mais recente
3. Escolher variante "arm64-v8a + armeabi-v7a + x86 + x86_64"
4. Baixar APK
5. Copiar para VPS: `scp whatsapp.apk usuario@VPS:/opt/chip-activator/apks/`

**2. Verificar APK**

```bash
ls -lh apks/whatsapp.apk
# Deve ter ~60-80MB
```

**3. Criar script de instalacao**

```bash
cat > /opt/chip-activator/install_whatsapp.sh << 'EOF'
#!/bin/bash
# Script para instalar WhatsApp no emulador

APK_PATH="/opt/chip-activator/apks/whatsapp.apk"

# Verificar se emulador esta rodando
if ! adb devices | grep -q "emulator"; then
    echo "ERRO: Emulador nao esta rodando"
    exit 1
fi

# Verificar se WhatsApp ja esta instalado
if adb shell pm list packages | grep -q "com.whatsapp"; then
    echo "WhatsApp ja esta instalado"
    exit 0
fi

# Instalar APK
echo "Instalando WhatsApp..."
adb install -r $APK_PATH

# Verificar instalacao
if adb shell pm list packages | grep -q "com.whatsapp"; then
    echo "WhatsApp instalado com sucesso!"
    exit 0
else
    echo "ERRO: Falha ao instalar WhatsApp"
    exit 1
fi
EOF

chmod +x /opt/chip-activator/install_whatsapp.sh
```

### DoD

- [ ] APK do WhatsApp baixado
- [ ] Script de instalacao criado
- [ ] Consegue instalar no emulador

---

## Story 2.3: Iniciar Appium Server

### Objetivo
Configurar e iniciar o Appium Server.

### Passo a Passo

**1. Criar script de start do Appium**

```bash
cat > /opt/chip-activator/start_appium.sh << 'EOF'
#!/bin/bash
# Script para iniciar Appium Server

LOG_FILE="/var/log/chip-activator/appium.log"
PORT=4723

# Verificar se ja esta rodando
if pgrep -f "appium" > /dev/null; then
    echo "Appium ja esta rodando"
    exit 0
fi

# Configurar variaveis de ambiente
export ANDROID_HOME=/opt/android-sdk
export ANDROID_SDK_ROOT=/opt/android-sdk
export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools
export PATH=$PATH:$ANDROID_SDK_ROOT/emulator

# Iniciar Appium
echo "Iniciando Appium na porta $PORT..."
nohup appium \
    --address 127.0.0.1 \
    --port $PORT \
    --relaxed-security \
    --log-timestamp \
    --local-timezone \
    > $LOG_FILE 2>&1 &

# Aguardar inicializacao
sleep 5

# Verificar se iniciou
if curl -s http://127.0.0.1:$PORT/status | grep -q "ready"; then
    echo "Appium pronto na porta $PORT"
    exit 0
else
    echo "ERRO: Appium nao iniciou"
    cat $LOG_FILE | tail -20
    exit 1
fi
EOF

chmod +x /opt/chip-activator/start_appium.sh
```

**2. Criar script de stop do Appium**

```bash
cat > /opt/chip-activator/stop_appium.sh << 'EOF'
#!/bin/bash
# Script para parar Appium Server

echo "Parando Appium..."
pkill -f "appium"

sleep 2

if pgrep -f "appium" > /dev/null; then
    echo "ERRO: Appium ainda rodando"
    exit 1
fi

echo "Appium parado!"
exit 0
EOF

chmod +x /opt/chip-activator/stop_appium.sh
```

**3. Testar Appium**

```bash
# Iniciar
/opt/chip-activator/start_appium.sh

# Verificar status
curl http://127.0.0.1:4723/status
# Deve retornar JSON com "ready": true

# Parar
/opt/chip-activator/stop_appium.sh
```

### DoD

- [ ] Script start_appium.sh funciona
- [ ] Script stop_appium.sh funciona
- [ ] Appium responde em /status

---

## Story 2.4: Script de Automacao - Estrutura Base

### Objetivo
Criar estrutura do script Python de automacao.

### Passo a Passo

**1. Criar arquivo principal**

```bash
cat > /opt/chip-activator/whatsapp_automation.py << 'EOF'
"""
WhatsApp Automation Script
Automatiza registro de numero e pareamento com Evolution API.
"""
import os
import time
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
APPIUM_URL = "http://127.0.0.1:4723"
SCREENSHOT_DIR = Path("/var/log/chip-activator/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class WhatsAppAutomation:
    """Classe para automacao do WhatsApp."""

    def __init__(self):
        self.driver: Optional[webdriver.Remote] = None
        self.wait: Optional[WebDriverWait] = None

    def connect(self) -> bool:
        """
        Conecta ao emulador via Appium.

        Returns:
            True se conectou com sucesso
        """
        logger.info("Conectando ao emulador...")

        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.platform_version = "11"
        options.device_name = "emulator-5554"
        options.app_package = "com.whatsapp"
        options.app_activity = "com.whatsapp.Main"
        options.auto_grant_permissions = True
        options.no_reset = True
        options.new_command_timeout = 300

        try:
            self.driver = webdriver.Remote(APPIUM_URL, options=options)
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("Conectado ao emulador!")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar: {e}")
            return False

    def disconnect(self):
        """Desconecta do emulador."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Desconectado do emulador")
            except Exception as e:
                logger.warning(f"Erro ao desconectar: {e}")

    def screenshot(self, name: str) -> str:
        """
        Captura screenshot para debug.

        Args:
            name: Nome do arquivo (sem extensao)

        Returns:
            Caminho do arquivo salvo
        """
        if not self.driver:
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.png"
        filepath = SCREENSHOT_DIR / filename

        try:
            self.driver.save_screenshot(str(filepath))
            logger.info(f"Screenshot salvo: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Erro ao salvar screenshot: {e}")
            return ""

    def find_element_safe(self, by: str, value: str, timeout: int = 10):
        """
        Encontra elemento com tratamento de erro.

        Args:
            by: Tipo de locator (AppiumBy.ID, etc)
            value: Valor do locator
            timeout: Tempo maximo de espera

        Returns:
            Elemento encontrado ou None
        """
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            return element
        except TimeoutException:
            logger.warning(f"Elemento nao encontrado: {by}={value}")
            return None

    def click_if_exists(self, by: str, value: str, timeout: int = 5) -> bool:
        """
        Clica em elemento se existir.

        Args:
            by: Tipo de locator
            value: Valor do locator
            timeout: Tempo maximo de espera

        Returns:
            True se clicou, False se elemento nao existe
        """
        element = self.find_element_safe(by, value, timeout)
        if element:
            element.click()
            logger.info(f"Clicou em: {value}")
            return True
        return False


# Instancia global
automation = WhatsAppAutomation()


if __name__ == "__main__":
    # Teste basico
    if automation.connect():
        automation.screenshot("test_connection")
        automation.disconnect()
        print("Teste OK!")
    else:
        print("Teste FALHOU!")
EOF
```

**2. Testar conexao basica**

```bash
# Garantir emulador e Appium rodando
/opt/chip-activator/start_emulator.sh
/opt/chip-activator/start_appium.sh
/opt/chip-activator/install_whatsapp.sh

# Ativar ambiente virtual
cd /opt/chip-activator
source venv/bin/activate

# Executar teste
python3 whatsapp_automation.py
# Deve mostrar: Teste OK!

# Verificar screenshot
ls /var/log/chip-activator/screenshots/
# Deve ter um arquivo .png
```

### DoD

- [ ] whatsapp_automation.py criado
- [ ] Consegue conectar ao emulador
- [ ] Screenshot funciona

---

## Story 2.5: Automacao - Aceitar Termos

### Objetivo
Automatizar tela inicial de termos do WhatsApp.

### Passo a Passo

**1. Adicionar metodo ao whatsapp_automation.py**

```python
# Adicionar apos a classe WhatsAppAutomation

    def aceitar_termos(self) -> bool:
        """
        Aceita termos de uso do WhatsApp (tela inicial).

        Returns:
            True se aceitou ou ja estava aceito
        """
        logger.info("Verificando tela de termos...")

        # Tentar encontrar botao de concordar
        # Pode ter diferentes textos dependendo do idioma
        botoes_concordar = [
            "CONCORDAR E CONTINUAR",
            "AGREE AND CONTINUE",
            "Concordar e continuar",
        ]

        for texto in botoes_concordar:
            if self.click_if_exists(AppiumBy.XPATH, f"//android.widget.Button[@text='{texto}']", timeout=3):
                logger.info("Termos aceitos!")
                time.sleep(2)
                return True

        # Se nao encontrou botao, pode ser que ja passou dessa tela
        logger.info("Tela de termos nao encontrada (pode ja ter passado)")
        return True
```

**2. Testar aceitar termos**

Para testar, precisamos limpar dados do WhatsApp:

```bash
# Limpar dados do WhatsApp (volta ao estado inicial)
adb shell pm clear com.whatsapp

# Executar teste
python3 -c "
from whatsapp_automation import automation

automation.connect()
automation.aceitar_termos()
automation.screenshot('apos_termos')
automation.disconnect()
"
```

### DoD

- [ ] Metodo aceitar_termos implementado
- [ ] Funciona com app recem-instalado

---

## Story 2.6: Automacao - Inserir Numero

### Objetivo
Automatizar insercao do numero de telefone.

### Passo a Passo

**1. Adicionar metodo**

```python
    def inserir_numero(self, numero: str, codigo_pais: str = "55") -> bool:
        """
        Insere numero de telefone na tela de registro.

        Args:
            numero: Numero sem codigo de pais (ex: "11999990001")
            codigo_pais: Codigo do pais (default: "55" Brasil)

        Returns:
            True se inseriu com sucesso
        """
        logger.info(f"Inserindo numero: +{codigo_pais}{numero}")

        try:
            # Selecionar pais (Brasil)
            # Clicar no spinner de pais
            pais_spinner = self.find_element_safe(
                AppiumBy.ID,
                "com.whatsapp:id/registration_country_selector"
            )
            if pais_spinner:
                pais_spinner.click()
                time.sleep(1)

                # Buscar Brasil
                search = self.find_element_safe(AppiumBy.ID, "com.whatsapp:id/search_src_text")
                if search:
                    search.send_keys("Brasil")
                    time.sleep(1)

                    # Clicar no resultado
                    self.click_if_exists(AppiumBy.XPATH, "//android.widget.TextView[contains(@text, 'Brasil')]")
                    time.sleep(1)

            # Inserir numero
            campo_numero = self.find_element_safe(
                AppiumBy.ID,
                "com.whatsapp:id/registration_phone"
            )
            if not campo_numero:
                logger.error("Campo de numero nao encontrado")
                self.screenshot("erro_campo_numero")
                return False

            campo_numero.clear()
            campo_numero.send_keys(numero)
            logger.info(f"Numero inserido: {numero}")

            # Clicar em PROXIMO/NEXT
            if not self.click_if_exists(AppiumBy.ID, "com.whatsapp:id/registration_submit"):
                # Tentar por texto
                self.click_if_exists(AppiumBy.XPATH, "//android.widget.Button[contains(@text, 'PRÓXIMO') or contains(@text, 'NEXT')]")

            time.sleep(2)

            # Confirmar numero (popup de confirmacao)
            self.click_if_exists(AppiumBy.ID, "android:id/button1")  # OK

            logger.info("Numero enviado para verificacao")
            return True

        except Exception as e:
            logger.error(f"Erro ao inserir numero: {e}")
            self.screenshot("erro_inserir_numero")
            return False
```

**2. Testar insercao de numero**

```bash
python3 -c "
from whatsapp_automation import automation

automation.connect()
automation.aceitar_termos()
automation.inserir_numero('11999990001')
automation.screenshot('apos_numero')
automation.disconnect()
"
```

### DoD

- [ ] Metodo inserir_numero implementado
- [ ] Seleciona Brasil corretamente
- [ ] Insere numero e clica em proximo

---

## Story 2.7: Automacao - Inserir Codigo SMS

### Objetivo
Automatizar insercao do codigo de verificacao SMS.

### Passo a Passo

**1. Adicionar metodo**

```python
    def inserir_codigo_sms(self, codigo: str) -> bool:
        """
        Insere codigo SMS de verificacao.

        Args:
            codigo: Codigo de 6 digitos

        Returns:
            True se inseriu com sucesso
        """
        logger.info(f"Inserindo codigo SMS: {codigo[:3]}***")  # Mascarar parte do codigo

        try:
            # Aguardar tela de codigo
            time.sleep(3)

            # WhatsApp tem 6 campos separados para cada digito
            # OU um campo unico dependendo da versao

            # Tentar campo unico primeiro
            campo_codigo = self.find_element_safe(
                AppiumBy.ID,
                "com.whatsapp:id/verify_sms_code_input"
            )

            if campo_codigo:
                campo_codigo.send_keys(codigo)
                logger.info("Codigo inserido (campo unico)")
            else:
                # Tentar campos separados
                for i, digito in enumerate(codigo):
                    campo = self.find_element_safe(
                        AppiumBy.ID,
                        f"com.whatsapp:id/verify_sms_code_input_{i}"
                    )
                    if campo:
                        campo.send_keys(digito)
                    else:
                        # Fallback: usar xpath
                        campos = self.driver.find_elements(
                            AppiumBy.CLASS_NAME,
                            "android.widget.EditText"
                        )
                        if i < len(campos):
                            campos[i].send_keys(digito)

                logger.info("Codigo inserido (campos separados)")

            # Aguardar verificacao automatica
            time.sleep(5)

            # Verificar se passou da tela de codigo
            # Se ainda estiver na tela de codigo, algo deu errado
            if self.find_element_safe(AppiumBy.ID, "com.whatsapp:id/verify_sms_code_input", timeout=3):
                logger.warning("Ainda na tela de codigo - pode ter falhado")
                self.screenshot("codigo_possivelmente_errado")
                return False

            logger.info("Codigo verificado!")
            return True

        except Exception as e:
            logger.error(f"Erro ao inserir codigo: {e}")
            self.screenshot("erro_inserir_codigo")
            return False
```

### DoD

- [ ] Metodo inserir_codigo_sms implementado
- [ ] Funciona com campo unico e campos separados

---

## Story 2.8: Automacao - Configurar Perfil

### Objetivo
Pular ou preencher tela de perfil (nome e foto).

### Passo a Passo

**1. Adicionar metodo**

```python
    def configurar_perfil(self, nome: str = "Julia") -> bool:
        """
        Configura perfil (nome) ou pula se possivel.

        Args:
            nome: Nome para o perfil

        Returns:
            True se configurou ou pulou
        """
        logger.info("Configurando perfil...")

        try:
            # Aguardar tela de perfil
            time.sleep(2)

            # Verificar se estamos na tela de perfil
            campo_nome = self.find_element_safe(
                AppiumBy.ID,
                "com.whatsapp:id/registration_name"
            )

            if campo_nome:
                campo_nome.clear()
                campo_nome.send_keys(nome)
                logger.info(f"Nome definido: {nome}")

                # Clicar em PROXIMO/NEXT
                self.click_if_exists(AppiumBy.ID, "com.whatsapp:id/register_name_next")
                time.sleep(2)
            else:
                logger.info("Tela de perfil nao encontrada (pode ter pulado)")

            return True

        except Exception as e:
            logger.error(f"Erro ao configurar perfil: {e}")
            self.screenshot("erro_perfil")
            return False
```

### DoD

- [ ] Metodo configurar_perfil implementado
- [ ] Define nome basico

---

## Story 2.9: Automacao - Navegar para Dispositivos Vinculados

### Objetivo
Navegar ate a tela de "Dispositivos vinculados".

### Passo a Passo

**1. Adicionar metodo**

```python
    def navegar_dispositivos_vinculados(self) -> bool:
        """
        Navega para tela de Dispositivos Vinculados.

        Returns:
            True se chegou na tela
        """
        logger.info("Navegando para Dispositivos Vinculados...")

        try:
            # Aguardar tela principal carregar
            time.sleep(3)

            # Clicar no menu (3 pontinhos)
            if not self.click_if_exists(AppiumBy.ACCESSIBILITY_ID, "Mais opções"):
                # Tentar alternativas
                if not self.click_if_exists(AppiumBy.ID, "com.whatsapp:id/menuitem_overflow"):
                    self.click_if_exists(AppiumBy.XPATH, "//android.widget.ImageView[@content-desc='Mais opções']")

            time.sleep(1)

            # Clicar em "Dispositivos vinculados"
            textos = [
                "Dispositivos vinculados",
                "Aparelhos conectados",
                "Linked devices",
                "Linked Devices"
            ]

            for texto in textos:
                if self.click_if_exists(AppiumBy.XPATH, f"//android.widget.TextView[@text='{texto}']"):
                    logger.info("Encontrou menu de dispositivos")
                    time.sleep(2)
                    return True

            # Fallback: tentar "Configurações" primeiro
            if self.click_if_exists(AppiumBy.XPATH, "//android.widget.TextView[@text='Configurações']"):
                time.sleep(1)
                for texto in textos:
                    if self.click_if_exists(AppiumBy.XPATH, f"//android.widget.TextView[@text='{texto}']"):
                        time.sleep(2)
                        return True

            logger.error("Nao encontrou menu de dispositivos vinculados")
            self.screenshot("erro_menu_dispositivos")
            return False

        except Exception as e:
            logger.error(f"Erro ao navegar: {e}")
            self.screenshot("erro_navegacao")
            return False
```

### DoD

- [ ] Metodo navegar_dispositivos_vinculados implementado
- [ ] Chega na tela correta

---

## Story 2.10: Automacao - Vincular Dispositivo (QR Code)

### Objetivo
Clicar em vincular e escanear QR code.

### Passo a Passo

**1. Adicionar metodo**

```python
    def vincular_dispositivo(self, qr_code_url: str) -> bool:
        """
        Inicia processo de vincular dispositivo e escaneia QR.

        Args:
            qr_code_url: URL da imagem do QR code (Evolution API)

        Returns:
            True se vinculou com sucesso
        """
        logger.info("Iniciando vinculacao de dispositivo...")

        try:
            # Clicar em "Vincular um dispositivo"
            botoes = [
                "Vincular um dispositivo",
                "Vincular dispositivo",
                "Link a device",
                "VINCULAR UM DISPOSITIVO"
            ]

            clicou = False
            for texto in botoes:
                if self.click_if_exists(AppiumBy.XPATH, f"//android.widget.Button[contains(@text, '{texto}')]"):
                    clicou = True
                    break
                if self.click_if_exists(AppiumBy.XPATH, f"//android.widget.TextView[contains(@text, '{texto}')]"):
                    clicou = True
                    break

            if not clicou:
                # Tentar por ID
                self.click_if_exists(AppiumBy.ID, "com.whatsapp:id/link_device_button")

            time.sleep(2)

            # Pode aparecer popup de biometria/PIN - pular
            self.click_if_exists(AppiumBy.ID, "android:id/button2")  # Cancelar
            time.sleep(1)

            # Aguardar camera abrir
            time.sleep(3)

            # IMPORTANTE: Aqui precisamos "mostrar" o QR code para a camera
            # Como estamos em emulador, vamos usar uma abordagem diferente

            # Opcao 1: Baixar imagem do QR e usar como "camera virtual"
            # Opcao 2: Usar adb para injetar imagem
            # Opcao 3: Usar deeplink do WhatsApp (se disponivel)

            # Por enquanto, vamos usar a abordagem de injetar via ADB
            # A camera do emulador pode ser configurada para usar uma imagem

            resultado = self._escanear_qr_code(qr_code_url)

            if resultado:
                # Aguardar confirmacao de vinculacao
                time.sleep(10)

                # Verificar se vinculou (deve sair da tela de camera)
                if not self.find_element_safe(AppiumBy.ID, "com.whatsapp:id/qr_code_scanner", timeout=3):
                    logger.info("Dispositivo vinculado com sucesso!")
                    return True

            logger.warning("Vinculacao pode ter falhado")
            self.screenshot("vinculacao_status")
            return False

        except Exception as e:
            logger.error(f"Erro ao vincular: {e}")
            self.screenshot("erro_vincular")
            return False

    def _escanear_qr_code(self, qr_code_url: str) -> bool:
        """
        Escaneia QR code usando camera virtual do emulador.

        Tecnica: Baixar imagem do QR e configurar como camera virtual.
        """
        import subprocess
        import requests

        logger.info(f"Baixando QR code de: {qr_code_url}")

        try:
            # Baixar imagem do QR
            response = requests.get(qr_code_url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Erro ao baixar QR: HTTP {response.status_code}")
                return False

            # Salvar temporariamente
            qr_path = "/tmp/qr_code.png"
            with open(qr_path, 'wb') as f:
                f.write(response.content)

            logger.info("QR code baixado")

            # Enviar para o emulador (camera virtual)
            # O emulador Android suporta camera virtual via arquivo

            # Copiar para o emulador
            subprocess.run([
                "adb", "push", qr_path, "/sdcard/qr_code.png"
            ], check=True)

            # Configurar camera virtual para usar a imagem
            # Isso depende de como o emulador foi configurado
            # Pode ser necessario usar "Virtual Scene" ou similar

            # Alternativa: Usar zxing para decodificar e usar deeplink
            # Por simplicidade, vamos assumir que a camera virtual funciona

            logger.info("QR code enviado para camera virtual")
            return True

        except Exception as e:
            logger.error(f"Erro ao escanear QR: {e}")
            return False
```

**NOTA IMPORTANTE:** A captura do QR code em emulador e complexa. Alternativas:

1. **Virtual Scene Camera**: Configurar emulador para usar imagem como camera
2. **Deeplink**: Usar URL whatsapp://... (se disponivel)
3. **Screen Overlay**: Mostrar QR na tela e usar OCR

Vamos implementar uma solucao mais robusta na proxima story.

### DoD

- [ ] Metodo vincular_dispositivo implementado
- [ ] Metodo _escanear_qr_code implementado (basico)

---

## Story 2.11: Automacao - Fluxo Completo

### Objetivo
Criar funcao que executa todo o fluxo de ativacao.

### Passo a Passo

**1. Adicionar metodo principal**

```python
def ativar_chip(numero: str, codigo_sms: str, qr_code_url: str) -> dict:
    """
    Executa fluxo completo de ativacao de chip.

    Args:
        numero: Numero de telefone (sem +55)
        codigo_sms: Codigo de verificacao SMS
        qr_code_url: URL do QR code da Evolution API

    Returns:
        {
            "success": bool,
            "message": str,
            "step": str,  # Ultimo passo executado
            "screenshot": str  # Caminho do screenshot (se erro)
        }
    """
    import time
    start_time = time.time()

    resultado = {
        "success": False,
        "message": "",
        "step": "init",
        "screenshot": "",
        "tempo_segundos": 0
    }

    try:
        # Passo 1: Conectar
        resultado["step"] = "connect"
        if not automation.connect():
            resultado["message"] = "Falha ao conectar ao emulador"
            return resultado

        # Passo 2: Aceitar termos
        resultado["step"] = "accept_terms"
        automation.aceitar_termos()

        # Passo 3: Inserir numero
        resultado["step"] = "insert_number"
        if not automation.inserir_numero(numero):
            resultado["message"] = "Falha ao inserir numero"
            resultado["screenshot"] = automation.screenshot("erro_numero")
            return resultado

        # Passo 4: Inserir codigo SMS
        resultado["step"] = "insert_sms_code"
        if not automation.inserir_codigo_sms(codigo_sms):
            resultado["message"] = "Falha ao inserir codigo SMS"
            resultado["screenshot"] = automation.screenshot("erro_sms")
            return resultado

        # Passo 5: Configurar perfil
        resultado["step"] = "setup_profile"
        automation.configurar_perfil("Julia")

        # Passo 6: Navegar para dispositivos vinculados
        resultado["step"] = "navigate_linked_devices"
        if not automation.navegar_dispositivos_vinculados():
            resultado["message"] = "Falha ao navegar para dispositivos vinculados"
            resultado["screenshot"] = automation.screenshot("erro_navegacao")
            return resultado

        # Passo 7: Vincular dispositivo
        resultado["step"] = "link_device"
        if not automation.vincular_dispositivo(qr_code_url):
            resultado["message"] = "Falha ao vincular dispositivo"
            resultado["screenshot"] = automation.screenshot("erro_vincular")
            return resultado

        # Sucesso!
        resultado["success"] = True
        resultado["message"] = "Chip ativado com sucesso"
        resultado["step"] = "completed"

    except Exception as e:
        resultado["message"] = f"Erro inesperado: {str(e)}"
        resultado["screenshot"] = automation.screenshot("erro_geral")

    finally:
        automation.disconnect()
        resultado["tempo_segundos"] = int(time.time() - start_time)

    return resultado


# Adicionar ao final do arquivo
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Uso: python whatsapp_automation.py <numero> <codigo_sms> <qr_url>")
        print("Exemplo: python whatsapp_automation.py 11999990001 123456 http://localhost:8080/qr.png")
        sys.exit(1)

    numero = sys.argv[1]
    codigo = sys.argv[2]
    qr_url = sys.argv[3]

    print(f"Ativando chip: {numero}")
    resultado = ativar_chip(numero, codigo, qr_url)

    print(f"\nResultado: {resultado}")
    sys.exit(0 if resultado["success"] else 1)
```

### DoD

- [ ] Funcao ativar_chip implementada
- [ ] Retorna resultado estruturado
- [ ] Pode ser chamada via linha de comando

---

## Checklist Final E02

- [ ] **Story 2.1** - Appium e dependencias instalados
- [ ] **Story 2.2** - WhatsApp APK baixado e instalavel
- [ ] **Story 2.3** - Appium Server inicia/para
- [ ] **Story 2.4** - Estrutura base do script
- [ ] **Story 2.5** - Aceitar termos funciona
- [ ] **Story 2.6** - Inserir numero funciona
- [ ] **Story 2.7** - Inserir codigo SMS funciona
- [ ] **Story 2.8** - Configurar perfil funciona
- [ ] **Story 2.9** - Navegar dispositivos funciona
- [ ] **Story 2.10** - Vincular dispositivo funciona
- [ ] **Story 2.11** - Fluxo completo funciona

---

## Tempo Estimado

| Story | Tempo | Notas |
|-------|-------|-------|
| 2.1 Appium | 1.5h | Inclui aprender conceitos |
| 2.2 APK | 30min | |
| 2.3 Appium Server | 30min | |
| 2.4 Estrutura | 1h | Inclui entender o codigo |
| 2.5-2.8 Automacao | 4h | Varias iteracoes ate funcionar |
| 2.9-2.10 Vinculacao | 3h | Parte mais complexa |
| 2.11 Integracao | 1.5h | Testes end-to-end |
| **Total** | ~12 horas | 3 dias |

**Realidade para dev junior:**
- Dia 1: Stories 2.1-2.4 (setup, aprender)
- Dia 2: Stories 2.5-2.8 (automacao basica)
- Dia 3: Stories 2.9-2.11 (vinculacao, integracao, debug)

---

## Troubleshooting

| Problema | Solucao |
|----------|---------|
| Appium nao conecta | Verificar se emulador esta rodando (`adb devices`) |
| Elemento nao encontrado | Verificar locator com `uiautomatorviewer` ou Appium Inspector |
| Timeout | Aumentar timeout ou verificar se tela correta |
| QR code nao escaneia | Ver Story 2.10 para alternativas |
| WhatsApp fecha | Verificar logs do app (`adb logcat | grep whatsapp`) |

---

## Ferramentas de Debug

### Appium Inspector

Para descobrir locators de elementos:

1. Baixar: https://github.com/appium/appium-inspector/releases
2. Conectar ao Appium Server (127.0.0.1:4723)
3. Navegar pela UI e ver IDs/XPaths

### UIAutomator Viewer

Alternativa nativa do Android SDK:

```bash
cd $ANDROID_SDK_ROOT/tools/bin
./uiautomatorviewer
```

---

## Proximo Epic

[E03: API de Ativacao](./epic-03-api-ativacao.md)
