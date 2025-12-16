# Epic 01: Preparacao da VPS

## Objetivo

Preparar a VPS com todas as configuracoes de seguranca e dependencias necessarias para rodar os containers Docker em producao.

---

## Stories

| ID | Story | Status |
|----|-------|--------|
| S12.E1.1 | Provisionar e acessar VPS | 🔴 |
| S12.E1.2 | Hardening de seguranca | 🔴 |
| S12.E1.3 | Instalar Docker e Docker Compose | 🔴 |
| S12.E1.4 | Configurar firewall (UFW) | 🔴 |
| S12.E1.5 | Clonar repositorio e configurar | 🔴 |

---

## S12.E1.1 - Provisionar e Acessar VPS

### Objetivo
Contratar VPS com especificacoes adequadas e configurar acesso SSH seguro.

### Contexto
Escolha um provedor com boa relacao custo-beneficio. Recomendamos Ubuntu 22.04 LTS pela estabilidade e suporte longo.

### Pre-requisitos
- Cartao de credito para provedor de VPS
- Par de chaves SSH gerado localmente

### Tarefas

1. **Gerar chave SSH local (se nao tiver)**
```bash
# No seu computador local
ssh-keygen -t ed25519 -C "julia-deploy" -f ~/.ssh/julia_vps
```

2. **Contratar VPS** (exemplo DigitalOcean)
   - Acessar digitalocean.com/droplets
   - Escolher Ubuntu 22.04 LTS
   - Selecionar plano (4GB RAM, 2 vCPUs minimo)
   - Regiao: Sao Paulo (melhor latencia)
   - Adicionar chave SSH publica
   - Nome: `julia-production`

3. **Configurar SSH local**
```bash
# Adicionar ao ~/.ssh/config
cat >> ~/.ssh/config << 'EOF'
Host julia-vps
    HostName SEU_IP_AQUI
    User root
    IdentityFile ~/.ssh/julia_vps
    ServerAliveInterval 60
EOF
```

4. **Testar conexao**
```bash
ssh julia-vps
```

### Como Testar
```bash
# Deve conectar sem pedir senha
ssh julia-vps "echo 'Conexao OK' && uname -a"
```

### DoD
- [ ] VPS contratada e rodando
- [ ] IP publico anotado
- [ ] Conexao SSH funcionando sem senha
- [ ] Arquivo ~/.ssh/config configurado
- [ ] Console web do provedor acessivel (backup)

---

## S12.E1.2 - Hardening de Seguranca

### Objetivo
Aplicar configuracoes basicas de seguranca na VPS.

### Contexto
Servidores expostos a internet sao alvos constantes. Estas configuracoes reduzem significativamente a superficie de ataque.

### Pre-requisitos
- S12.E1.1 completo

### Tarefas

1. **Atualizar sistema**
```bash
apt update && apt upgrade -y
```

2. **Criar usuario nao-root**
```bash
# Criar usuario 'deploy'
adduser deploy --disabled-password --gecos ""

# Adicionar ao grupo sudo
usermod -aG sudo deploy

# Permitir sudo sem senha para deploy
echo "deploy ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/deploy
```

3. **Configurar SSH para usuario deploy**
```bash
# Copiar chave SSH
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

4. **Endurecer SSH**
```bash
# Backup do sshd_config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Aplicar configuracoes seguras
cat > /etc/ssh/sshd_config.d/hardening.conf << 'EOF'
# Desabilitar login root
PermitRootLogin no

# Desabilitar login por senha
PasswordAuthentication no

# Desabilitar autenticacao por challenge-response
ChallengeResponseAuthentication no

# Usar apenas protocolo 2
Protocol 2

# Timeout de sessao ociosa (10 min)
ClientAliveInterval 300
ClientAliveCountMax 2

# Limitar tentativas de login
MaxAuthTries 3

# Apenas usuarios especificos
AllowUsers deploy
EOF

# Reiniciar SSH
systemctl restart sshd
```

5. **Instalar Fail2ban**
```bash
apt install fail2ban -y

# Configurar jail para SSH
cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
EOF

systemctl enable fail2ban
systemctl start fail2ban
```

6. **Atualizar ~/.ssh/config local**
```bash
# No seu computador local, mudar User para deploy
sed -i 's/User root/User deploy/' ~/.ssh/config
```

### Como Testar
```bash
# Testar novo usuario
ssh julia-vps "whoami && sudo whoami"

# Verificar fail2ban
ssh julia-vps "sudo fail2ban-client status sshd"

# Tentar login root (deve falhar)
ssh root@SEU_IP  # Deve ser negado
```

### DoD
- [ ] Usuario 'deploy' criado e funcionando
- [ ] Login root desabilitado
- [ ] Login por senha desabilitado
- [ ] Fail2ban instalado e ativo
- [ ] SSH funcionando com usuario deploy
- [ ] Sistema atualizado

---

## S12.E1.3 - Instalar Docker e Docker Compose

### Objetivo
Instalar Docker e Docker Compose no servidor.

### Contexto
Usamos Docker Compose v2 (integrado ao Docker CLI) - nao precisa instalar separadamente.

### Pre-requisitos
- S12.E1.2 completo

### Tarefas

1. **Remover versoes antigas (se houver)**
```bash
sudo apt remove docker docker-engine docker.io containerd runc -y 2>/dev/null || true
```

2. **Instalar dependencias**
```bash
sudo apt update
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```

3. **Adicionar repositorio Docker**
```bash
# Adicionar chave GPG oficial
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Adicionar repositorio
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

4. **Instalar Docker**
```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

5. **Configurar usuario no grupo docker**
```bash
sudo usermod -aG docker deploy
```

6. **Configurar Docker para iniciar no boot**
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

7. **Configurar logging do Docker**
```bash
sudo mkdir -p /etc/docker
sudo cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true
}
EOF

sudo systemctl restart docker
```

### Como Testar
```bash
# Sair e entrar para aplicar grupo docker
exit
ssh julia-vps

# Verificar Docker
docker --version
docker compose version

# Testar container
docker run --rm hello-world
```

### DoD
- [ ] Docker instalado (versao 24+)
- [ ] Docker Compose instalado (v2+)
- [ ] Usuario deploy pode rodar docker sem sudo
- [ ] Container hello-world executou com sucesso
- [ ] Docker configurado para iniciar no boot
- [ ] Logging limitado a 10m/3 arquivos

---

## S12.E1.4 - Configurar Firewall (UFW)

### Objetivo
Configurar firewall para permitir apenas portas necessarias.

### Contexto
UFW (Uncomplicated Firewall) e o firewall padrao do Ubuntu. Vamos permitir apenas SSH (22), HTTP (80) e HTTPS (443).

### Pre-requisitos
- S12.E1.3 completo

### Tarefas

1. **Instalar UFW (geralmente ja vem)**
```bash
sudo apt install ufw -y
```

2. **Configurar regras padrao**
```bash
# Bloquear tudo por padrao
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

3. **Permitir portas necessarias**
```bash
# SSH (CRITICO: fazer primeiro!)
sudo ufw allow ssh

# HTTP e HTTPS
sudo ufw allow http
sudo ufw allow https

# Opcional: porta para Evolution API webhook durante debug
# sudo ufw allow 8080/tcp comment 'Evolution API'
```

4. **Ativar firewall**
```bash
# IMPORTANTE: Certifique-se que SSH esta permitido!
sudo ufw enable
```

5. **Verificar status**
```bash
sudo ufw status verbose
```

### Como Testar
```bash
# Verificar portas abertas
sudo ufw status numbered

# Output esperado:
# [ 1] 22/tcp                     ALLOW IN    Anywhere
# [ 2] 80/tcp                     ALLOW IN    Anywhere
# [ 3] 443/tcp                    ALLOW IN    Anywhere

# Testar de fora (no seu computador)
nc -zv SEU_IP 22    # Deve conectar
nc -zv SEU_IP 80    # Deve conectar
nc -zv SEU_IP 8080  # Deve recusar (timeout)
```

### DoD
- [ ] UFW instalado e ativo
- [ ] Porta 22 (SSH) permitida
- [ ] Porta 80 (HTTP) permitida
- [ ] Porta 443 (HTTPS) permitida
- [ ] Outras portas bloqueadas
- [ ] SSH continua funcionando apos ativar firewall

---

## S12.E1.5 - Clonar Repositorio e Configurar

### Objetivo
Clonar o codigo do projeto na VPS e preparar configuracoes iniciais.

### Contexto
O codigo sera clonado em `/opt/julia` - diretorio padrao para aplicacoes de terceiros no Linux.

### Pre-requisitos
- S12.E1.4 completo
- Repositorio Git acessivel (GitHub/GitLab)

### Tarefas

1. **Instalar Git**
```bash
sudo apt install git -y
```

2. **Criar diretorio do projeto**
```bash
sudo mkdir -p /opt/julia
sudo chown deploy:deploy /opt/julia
```

3. **Configurar Git (opcional - para commits)**
```bash
git config --global user.name "Deploy Julia"
git config --global user.email "deploy@suaempresa.com"
```

4. **Clonar repositorio**
```bash
cd /opt/julia

# Via HTTPS (mais simples)
git clone https://github.com/SEU_USUARIO/whatsapp-api.git .

# OU via SSH (se tiver deploy key configurada)
# git clone git@github.com:SEU_USUARIO/whatsapp-api.git .
```

5. **Criar arquivo .env de producao**
```bash
# Copiar template
cp .env.example .env

# Editar com valores de producao
nano .env
```

6. **Valores criticos para ajustar no .env**
```bash
# Mudar para production
ENVIRONMENT=production
DEBUG=false

# URLs internas do Docker
REDIS_URL=redis://redis:6379/0
EVOLUTION_API_URL=http://evolution-api:8080
CHATWOOT_URL=http://chatwoot:3000
JULIA_API_URL=http://julia-api:8000

# Adicionar todas as API keys reais
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
# etc...
```

7. **Proteger arquivo .env**
```bash
chmod 600 .env
```

8. **Criar diretorio de credentials**
```bash
mkdir -p credentials
chmod 700 credentials

# Copiar google-sa.json (via scp do seu computador)
# scp ./credentials/google-sa.json julia-vps:/opt/julia/credentials/
```

### Como Testar
```bash
# Verificar arquivos
ls -la /opt/julia/

# Verificar .env existe e esta protegido
ls -la /opt/julia/.env
# -rw------- 1 deploy deploy ... .env

# Verificar docker-compose.yml existe
cat /opt/julia/docker-compose.yml | head -20
```

### DoD
- [ ] Git instalado
- [ ] Repositorio clonado em /opt/julia
- [ ] Arquivo .env criado e configurado
- [ ] Arquivo .env com permissao 600
- [ ] Credenciais Google copiadas (se usar briefing)
- [ ] docker-compose.yml presente no diretorio

---

## Resumo do Epic

| Story | Tempo Estimado | Complexidade |
|-------|----------------|--------------|
| S12.E1.1 | 30 min | Baixa |
| S12.E1.2 | 45 min | Media |
| S12.E1.3 | 30 min | Baixa |
| S12.E1.4 | 15 min | Baixa |
| S12.E1.5 | 30 min | Baixa |
| **Total** | **~2.5h** | |

## Proximo Epic

Apos completar este epic, prossiga para [Epic 02: Docker Producao](./epic-02-docker-producao.md)
