# VPS Setup - Chip Activator

Documentacao do setup do VPS para o sistema de ativacao automatizada de chips WhatsApp.

## Servidor

| Atributo | Valor |
|----------|-------|
| Provider | DigitalOcean |
| IP | 165.227.76.85 |
| OS | Ubuntu 24.04.3 LTS |
| vCPUs | 4 |
| RAM | 8 GB |
| Disco | 48 GB |
| KVM | Habilitado |

## Acesso SSH

```bash
# Chave SSH local
~/.ssh/digitalocean

# Conectar
ssh -i ~/.ssh/digitalocean root@165.227.76.85
```

## Software Instalado

### Java

```
OpenJDK 17.0.17+10-1~24.04
```

### Android SDK

| Componente | Versao | Path |
|------------|--------|------|
| SDK Manager | 12.0 | /opt/android-sdk/cmdline-tools/latest |
| Platform Tools | Latest | /opt/android-sdk/platform-tools |
| Emulator | Latest | /opt/android-sdk/emulator |
| System Image | android-30;google_apis;x86_64 | /opt/android-sdk/system-images |

### Variaveis de Ambiente

```bash
# /etc/profile.d/android-sdk.sh
export ANDROID_HOME=/opt/android-sdk
export ANDROID_SDK_ROOT=/opt/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator
```

### AVD (Android Virtual Device)

```
Name: whatsapp-activator
Device: pixel_4 (Google)
Target: Google APIs (Android 11.0 "R")
ABI: google_apis/x86_64
SDCard: 512 MB
Path: /root/.android/avd/whatsapp-activator.avd
```

### Node.js e Appium

| Componente | Versao |
|------------|--------|
| Node.js | 20.19.6 |
| NPM | 10.8.2 |
| Appium | 3.1.2 |
| UiAutomator2 | 6.7.8 |

## Comandos Uteis

### Emulador

```bash
# Carregar variaveis de ambiente
source /etc/profile.d/android-sdk.sh

# Iniciar emulador (headless)
emulator -avd whatsapp-activator -no-window -no-audio -no-snapshot -gpu swiftshader_indirect &

# Verificar boot
adb shell getprop sys.boot_completed

# Listar dispositivos
adb devices

# Parar emulador
adb emu kill
```

### Appium

```bash
# Iniciar Appium server
appium --address 127.0.0.1 --port 4723

# Verificar drivers instalados
appium driver list --installed
```

### SDK Manager

```bash
# Listar pacotes instalados
sdkmanager --list_installed

# Atualizar pacotes
sdkmanager --update
```

## Teste de Validacao

```bash
# 1. Verificar KVM
kvm-ok
# Esperado: "KVM acceleration can be used"

# 2. Verificar Java
java -version
# Esperado: openjdk 17.x.x

# 3. Verificar SDK
sdkmanager --version
# Esperado: 12.0

# 4. Verificar AVD
avdmanager list avd
# Esperado: whatsapp-activator listado

# 5. Verificar Appium
appium --version
# Esperado: 3.x.x
```

## Observacoes

### Hostinger VPS (NAO funciona)

O VPS da Hostinger (31.97.170.230) **nao suporta nested virtualization**.
Tentativa de habilitar KVM falhou - Hostinger confirmou que nao e possivel em planos VPS KVM.

### Performance do Emulador

- Boot time: ~90-120 segundos (primeira vez)
- Com snapshot: ~30-40 segundos
- Recomendado: usar `-no-snapshot` para ativacoes para evitar estado corrompido

### Proximos Passos

1. E02: Criar script de automacao WhatsApp com Appium
2. E03: Criar API FastAPI para orquestrar ativacoes
3. E04: Configurar systemd, nginx, SSL

---

*Documentado em: 12/01/2026*
*Setup realizado por: Claude Code*
