# Epic 01: Setup VPS

**Status:** Pendente
**Estimativa:** 4 horas
**Prioridade:** Alta
**Dependencia:** E00 (KVM validado)
**Responsavel:** Dev Junior

---

## Objetivo

Preparar o VPS com todas as ferramentas necessarias para rodar o emulador Android:
- Android SDK
- Android Emulator
- AVD (Android Virtual Device)
- Java (necessario para SDK)

---

## Pre-requisitos

- [ ] E00 concluido (KVM validado)
- [ ] Acesso SSH ao VPS
- [ ] Pelo menos 20GB de espaco livre
- [ ] Pelo menos 4GB de RAM

### Verificar Espaco

```bash
df -h /
# Deve ter pelo menos 20GB livres na coluna "Avail"
```

### Verificar RAM

```bash
free -h
# Deve ter pelo menos 4GB na linha "Mem" coluna "total"
```

---

## Story 1.1: Instalar Dependencias Base

### Objetivo
Instalar pacotes necessarios para o Android SDK.

### Passo a Passo

**1. Atualizar sistema**

```bash
sudo apt update
sudo apt upgrade -y
```

**2. Instalar dependencias**

```bash
sudo apt install -y \
    openjdk-17-jdk \
    unzip \
    wget \
    curl \
    git \
    libpulse0 \
    libgl1-mesa-glx \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxext6 \
    libxfixes3 \
    libxrender1 \
    libxtst6 \
    libxrandr2 \
    libnss3 \
    libxcomposite1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxkbcommon0 \
    libxshmfence1
```

**3. Verificar Java**

```bash
java -version
# Deve mostrar: openjdk version "17.x.x"
```

**4. Configurar JAVA_HOME**

```bash
# Adicionar ao ~/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$PATH:$JAVA_HOME/bin' >> ~/.bashrc

# Aplicar
source ~/.bashrc

# Verificar
echo $JAVA_HOME
# Deve mostrar: /usr/lib/jvm/java-17-openjdk-amd64
```

### DoD

- [ ] Sistema atualizado
- [ ] Java 17 instalado
- [ ] JAVA_HOME configurado
- [ ] Dependencias instaladas

---

## Story 1.2: Instalar Android SDK (Command Line Tools)

### Objetivo
Baixar e configurar o Android SDK.

### Passo a Passo

**1. Criar diretorio**

```bash
sudo mkdir -p /opt/android-sdk
sudo chown $USER:$USER /opt/android-sdk
```

**2. Baixar Command Line Tools**

```bash
cd /tmp

# Baixar (versao mais recente de Jan/2025)
# Verificar versao atual em: https://developer.android.com/studio#command-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip

# Descompactar
unzip commandlinetools-linux-*.zip -d /opt/android-sdk/

# Reorganizar estrutura (necessario para sdkmanager funcionar)
mkdir -p /opt/android-sdk/cmdline-tools/latest
mv /opt/android-sdk/cmdline-tools/* /opt/android-sdk/cmdline-tools/latest/ 2>/dev/null || true
```

**3. Configurar variaveis de ambiente**

```bash
# Adicionar ao ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# Android SDK
export ANDROID_SDK_ROOT=/opt/android-sdk
export ANDROID_HOME=/opt/android-sdk
export PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools
export PATH=$PATH:$ANDROID_SDK_ROOT/emulator
EOF

# Aplicar
source ~/.bashrc
```

**4. Verificar sdkmanager**

```bash
sdkmanager --version
# Deve mostrar: X.X (versao do sdkmanager)
```

**5. Aceitar licencas**

```bash
yes | sdkmanager --licenses
# Aceita todas as licencas automaticamente
```

### DoD

- [ ] Android SDK em /opt/android-sdk
- [ ] Variaveis de ambiente configuradas
- [ ] sdkmanager funciona
- [ ] Licencas aceitas

### Troubleshooting

| Problema | Solucao |
|----------|---------|
| sdkmanager: command not found | Verificar PATH, fazer `source ~/.bashrc` |
| Could not find or load main class | Verificar estrutura de pastas, deve ter cmdline-tools/latest/bin |
| Java version error | Verificar JAVA_HOME aponta para Java 17 |

---

## Story 1.3: Instalar Componentes do SDK

### Objetivo
Baixar emulador, platform-tools e imagem do sistema.

### Passo a Passo

**1. Instalar platform-tools**

```bash
sdkmanager "platform-tools"
```

**2. Instalar emulador**

```bash
sdkmanager "emulator"
```

**3. Instalar imagem do sistema Android 11 (API 30)**

```bash
# Imagem x86_64 com Google APIs (necessario para WhatsApp)
sdkmanager "system-images;android-30;google_apis;x86_64"
```

**NOTA:** Este download e grande (~1.5GB). Pode demorar.

**4. Instalar build-tools e platform**

```bash
sdkmanager "build-tools;30.0.3"
sdkmanager "platforms;android-30"
```

**5. Verificar instalacao**

```bash
sdkmanager --list | grep installed
# Deve mostrar:
#   emulator
#   platform-tools
#   system-images;android-30;google_apis;x86_64
#   build-tools;30.0.3
#   platforms;android-30
```

**6. Verificar ADB**

```bash
adb version
# Deve mostrar: Android Debug Bridge version X.X.X
```

**7. Verificar emulador**

```bash
emulator -version
# Deve mostrar: Android emulator version X.X.X
```

### DoD

- [ ] platform-tools instalado
- [ ] emulator instalado
- [ ] system-image android-30 instalada
- [ ] adb funciona
- [ ] emulator funciona

---

## Story 1.4: Criar AVD (Android Virtual Device)

### Objetivo
Criar e configurar o dispositivo virtual Android.

### Passo a Passo

**1. Criar AVD**

```bash
# Criar AVD chamado "chip-activator"
avdmanager create avd \
    --name chip-activator \
    --package "system-images;android-30;google_apis;x86_64" \
    --device "pixel_4" \
    --force
```

Quando perguntar "Do you wish to create a custom hardware profile?", responder `no`.

**2. Configurar AVD para melhor performance**

```bash
# Editar config do AVD
cat >> ~/.android/avd/chip-activator.avd/config.ini << 'EOF'
hw.ramSize=2048
hw.cpu.ncore=2
disk.dataPartition.size=4G
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader_indirect
EOF
```

**3. Verificar AVD criado**

```bash
avdmanager list avd
# Deve mostrar:
#   Name: chip-activator
#   Device: pixel_4
#   Path: /home/usuario/.android/avd/chip-activator.avd
#   Target: Google APIs (Google Inc.)
#   Based on: Android 11.0 (R)
```

### DoD

- [ ] AVD "chip-activator" criado
- [ ] Config de performance aplicada
- [ ] avdmanager lista o AVD

---

## Story 1.5: Testar Emulador

### Objetivo
Iniciar o emulador e verificar que funciona.

### Passo a Passo

**1. Iniciar emulador em modo headless**

```bash
# Iniciar sem interface grafica (headless)
emulator -avd chip-activator \
    -no-window \
    -no-audio \
    -no-boot-anim \
    -gpu swiftshader_indirect \
    -accel on \
    &

# O & no final coloca em background
```

**2. Aguardar boot (pode demorar 1-2 minutos)**

```bash
# Verificar se emulador esta rodando
adb devices
# Deve mostrar:
#   List of devices attached
#   emulator-5554    device

# Se mostrar "offline" ou nao aparecer, aguardar mais
```

**3. Verificar boot completo**

```bash
# Aguardar boot completar
adb wait-for-device
adb shell getprop sys.boot_completed
# Deve retornar: 1
```

**4. Testar comandos ADB**

```bash
# Listar apps instalados
adb shell pm list packages | head -5

# Ver versao Android
adb shell getprop ro.build.version.release
# Deve mostrar: 11
```

**5. Desligar emulador**

```bash
# Desligar via ADB
adb emu kill

# OU matar processo
pkill -f emulator
```

**6. Verificar que desligou**

```bash
adb devices
# Deve mostrar:
#   List of devices attached
#   (vazio)
```

### DoD

- [ ] Emulador inicia em modo headless
- [ ] ADB conecta ao emulador
- [ ] Boot completa (sys.boot_completed = 1)
- [ ] Emulador desliga corretamente

### Troubleshooting

| Problema | Solucao |
|----------|---------|
| PANIC: Missing emulator engine | Verificar PATH inclui $ANDROID_SDK_ROOT/emulator |
| KVM permission denied | Verificar usuario no grupo kvm, fazer logout/login |
| emulator-5554 offline | Aguardar mais, boot pode demorar |
| Cannot connect to adb | Reiniciar adb: `adb kill-server && adb start-server` |
| Segmentation fault | Trocar `-gpu` para `off` ou `auto` |

---

## Story 1.6: Criar Script de Controle

### Objetivo
Criar scripts para ligar/desligar emulador facilmente.

### Passo a Passo

**1. Criar diretorio do projeto**

```bash
sudo mkdir -p /opt/chip-activator
sudo chown $USER:$USER /opt/chip-activator
```

**2. Criar script de start**

```bash
cat > /opt/chip-activator/start_emulator.sh << 'EOF'
#!/bin/bash
# Script para iniciar emulador Android

AVD_NAME="chip-activator"
LOG_FILE="/var/log/chip-activator/emulator.log"

# Criar diretorio de log se nao existir
sudo mkdir -p /var/log/chip-activator
sudo chown $USER:$USER /var/log/chip-activator

# Verificar se ja esta rodando
if adb devices | grep -q "emulator"; then
    echo "Emulador ja esta rodando"
    exit 0
fi

echo "Iniciando emulador..."

# Iniciar emulador
nohup emulator -avd $AVD_NAME \
    -no-window \
    -no-audio \
    -no-boot-anim \
    -gpu swiftshader_indirect \
    -accel on \
    > $LOG_FILE 2>&1 &

# Aguardar dispositivo
echo "Aguardando boot..."
adb wait-for-device

# Aguardar boot completo (max 120 segundos)
TIMEOUT=120
ELAPSED=0
while [ "$(adb shell getprop sys.boot_completed 2>/dev/null)" != "1" ]; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "ERRO: Timeout aguardando boot"
        exit 1
    fi
    echo "Aguardando boot... ${ELAPSED}s"
done

echo "Emulador pronto!"
exit 0
EOF

chmod +x /opt/chip-activator/start_emulator.sh
```

**3. Criar script de stop**

```bash
cat > /opt/chip-activator/stop_emulator.sh << 'EOF'
#!/bin/bash
# Script para parar emulador Android

echo "Parando emulador..."

# Tentar parar via ADB
adb emu kill 2>/dev/null

# Aguardar 5 segundos
sleep 5

# Se ainda estiver rodando, matar processo
if pgrep -f "emulator" > /dev/null; then
    echo "Forcando parada..."
    pkill -9 -f "emulator"
fi

# Verificar
if adb devices | grep -q "emulator"; then
    echo "ERRO: Emulador ainda rodando"
    exit 1
fi

echo "Emulador parado!"
exit 0
EOF

chmod +x /opt/chip-activator/stop_emulator.sh
```

**4. Criar script de status**

```bash
cat > /opt/chip-activator/status_emulator.sh << 'EOF'
#!/bin/bash
# Script para verificar status do emulador

if adb devices | grep -q "emulator"; then
    BOOT=$(adb shell getprop sys.boot_completed 2>/dev/null)
    if [ "$BOOT" == "1" ]; then
        echo "running"
    else
        echo "booting"
    fi
else
    echo "stopped"
fi
EOF

chmod +x /opt/chip-activator/status_emulator.sh
```

**5. Testar scripts**

```bash
# Iniciar
/opt/chip-activator/start_emulator.sh

# Verificar status
/opt/chip-activator/status_emulator.sh
# Deve mostrar: running

# Parar
/opt/chip-activator/stop_emulator.sh

# Verificar status
/opt/chip-activator/status_emulator.sh
# Deve mostrar: stopped
```

### DoD

- [ ] Scripts criados em /opt/chip-activator/
- [ ] start_emulator.sh funciona
- [ ] stop_emulator.sh funciona
- [ ] status_emulator.sh funciona

---

## Checklist Final E01

- [ ] **Story 1.1** - Dependencias instaladas (Java 17, libs)
- [ ] **Story 1.2** - Android SDK instalado e configurado
- [ ] **Story 1.3** - Componentes do SDK (emulator, platform-tools, image)
- [ ] **Story 1.4** - AVD "chip-activator" criado
- [ ] **Story 1.5** - Emulador testado (liga/desliga)
- [ ] **Story 1.6** - Scripts de controle funcionando

---

## Estrutura Final

```
/opt/android-sdk/
├── cmdline-tools/latest/bin/
│   ├── avdmanager
│   └── sdkmanager
├── emulator/
│   └── emulator
├── platform-tools/
│   └── adb
├── platforms/android-30/
├── system-images/android-30/google_apis/x86_64/
└── build-tools/30.0.3/

/opt/chip-activator/
├── start_emulator.sh
├── stop_emulator.sh
└── status_emulator.sh

~/.android/avd/
└── chip-activator.avd/
    └── config.ini
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 1.1 Dependencias | 30 min |
| 1.2 Android SDK | 30 min |
| 1.3 Componentes | 45 min (download grande) |
| 1.4 AVD | 15 min |
| 1.5 Testar | 30 min |
| 1.6 Scripts | 30 min |
| **Total** | ~3-4 horas |

---

## Proximo Epic

[E02: Automacao WhatsApp](./epic-02-automacao-whatsapp.md)
