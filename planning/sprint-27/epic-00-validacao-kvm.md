# Epic 00: Validacao KVM

**Status:** Pendente
**Estimativa:** 1 hora
**Prioridade:** BLOQUEANTE
**Responsavel:** Dev Junior

---

## Objetivo

Validar se o VPS Hostinger suporta virtualizacao KVM, necessaria para rodar o emulador Android.

**IMPORTANTE:** Este epic e BLOQUEANTE. Se KVM nao funcionar, PARAR TUDO e comunicar imediatamente.

---

## O Que e KVM?

KVM (Kernel-based Virtual Machine) e uma tecnologia de virtualizacao do Linux que permite rodar maquinas virtuais com performance proxima ao hardware nativo.

**Por que precisamos?**
- O emulador Android precisa de virtualizacao de hardware
- Sem KVM, o emulador roda em modo de software (MUITO lento, ~10x mais devagar)
- Com KVM, o emulador roda rapido o suficiente para automacao

---

## Pre-requisitos

- [ ] Acesso SSH ao VPS Hostinger
- [ ] Usuario com permissoes sudo

### Dados de Acesso (Pedir ao Rafael)

```
Host: ???.hostinger.com (ou IP)
Usuario: ???
Senha: ???
Porta SSH: 22 (padrao)
```

---

## Story 0.1: Conectar ao VPS

### Objetivo
Estabelecer conexao SSH com o VPS.

### Passo a Passo

**1. Abrir terminal local**

```bash
# No seu computador (Mac/Linux)
ssh usuario@IP_DO_VPS

# Se pedir senha, digitar a senha fornecida
```

**2. Se usar chave SSH**

```bash
# Se tiver chave SSH configurada
ssh -i ~/.ssh/sua_chave usuario@IP_DO_VPS
```

**3. Verificar que conectou**

```bash
# Deve mostrar algo como:
# Welcome to Ubuntu 22.04.x LTS
# usuario@vps:~$

# Testar comandos basicos
whoami          # Deve mostrar seu usuario
pwd             # Deve mostrar /home/usuario
uname -a        # Mostra info do sistema
```

### DoD (Definition of Done)

- [ ] Conseguiu conectar via SSH
- [ ] Comandos basicos funcionam
- [ ] Tem acesso sudo (`sudo whoami` retorna "root")

### Troubleshooting

| Problema | Solucao |
|----------|---------|
| Connection refused | Verificar IP e porta. VPS pode estar desligado. |
| Permission denied | Senha incorreta ou usuario errado. |
| Host key verification failed | Executar `ssh-keygen -R IP_DO_VPS` e tentar novamente. |

---

## Story 0.2: Verificar Suporte KVM

### Objetivo
Confirmar que o VPS suporta virtualizacao KVM.

### Passo a Passo

**1. Verificar se /dev/kvm existe**

```bash
ls -la /dev/kvm
```

**Resultado esperado (BOM):**
```
crw-rw---- 1 root kvm 10, 232 Jan 15 10:00 /dev/kvm
```

**Resultado ruim (PROBLEMA):**
```
ls: cannot access '/dev/kvm': No such file or directory
```

**2. Verificar se CPU suporta virtualizacao**

```bash
# Verificar flags de virtualizacao
grep -E "(vmx|svm)" /proc/cpuinfo
```

**Resultado esperado (BOM):**
```
flags : ... vmx ...   # Intel
# ou
flags : ... svm ...   # AMD
```

**Resultado ruim:**
```
# Nenhuma saida = CPU nao suporta virtualizacao
```

**3. Executar kvm-ok (se disponivel)**

```bash
# Instalar cpu-checker se nao tiver
sudo apt update
sudo apt install -y cpu-checker

# Executar verificacao
kvm-ok
```

**Resultado esperado (BOM):**
```
INFO: /dev/kvm exists
KVM acceleration can be used
```

**Resultado ruim:**
```
INFO: Your CPU does not support KVM extensions
KVM acceleration can NOT be used
```

**4. Verificar modulos do kernel**

```bash
lsmod | grep kvm
```

**Resultado esperado (BOM):**
```
kvm_intel             294912  0
kvm                   851968  1 kvm_intel
```
ou
```
kvm_amd               294912  0
kvm                   851968  1 kvm_amd
```

### DoD

- [ ] `/dev/kvm` existe
- [ ] `kvm-ok` retorna "can be used"
- [ ] Modulos kvm carregados

---

## Story 0.3: Testar KVM com QEMU

### Objetivo
Confirmar que KVM funciona na pratica.

### Passo a Passo

**1. Instalar QEMU**

```bash
sudo apt update
sudo apt install -y qemu-kvm
```

**2. Testar KVM**

```bash
# Teste simples
sudo qemu-system-x86_64 -enable-kvm -version

# Deve mostrar versao do QEMU sem erros
```

**3. Verificar permissoes do usuario**

```bash
# Adicionar usuario ao grupo kvm
sudo usermod -aG kvm $USER

# Verificar grupos
groups $USER

# Deve incluir "kvm" na lista
```

**IMPORTANTE:** Apos adicionar ao grupo, fazer logout e login novamente:

```bash
exit
# Reconectar SSH
ssh usuario@IP_DO_VPS
```

**4. Testar sem sudo**

```bash
# Agora deve funcionar sem sudo
qemu-system-x86_64 -enable-kvm -version
```

### DoD

- [ ] QEMU instalado
- [ ] Usuario no grupo kvm
- [ ] `qemu-system-x86_64 -enable-kvm` funciona sem sudo

---

## Story 0.4: Documentar Resultado

### Objetivo
Registrar o resultado da validacao.

### Se KVM FUNCIONA

**1. Criar arquivo de confirmacao**

```bash
# No VPS
echo "KVM_VALIDATED=true" > /tmp/kvm_status.txt
echo "DATE=$(date)" >> /tmp/kvm_status.txt
cat /tmp/kvm_status.txt
```

**2. Comunicar equipe**

Enviar mensagem no Slack:
```
KVM validado com sucesso no VPS Hostinger!
- /dev/kvm existe
- kvm-ok: can be used
- Modulos kvm_intel/kvm_amd carregados
- Usuario tem acesso ao grupo kvm

Proximo: E01 - Setup VPS
```

**3. Prosseguir para E01**

### Se KVM NAO FUNCIONA

**1. Documentar o problema**

```bash
# Coletar informacoes de debug
echo "=== KVM Debug ===" > /tmp/kvm_debug.txt
echo "Date: $(date)" >> /tmp/kvm_debug.txt
echo "" >> /tmp/kvm_debug.txt
echo "=== /dev/kvm ===" >> /tmp/kvm_debug.txt
ls -la /dev/kvm 2>&1 >> /tmp/kvm_debug.txt
echo "" >> /tmp/kvm_debug.txt
echo "=== CPU Flags ===" >> /tmp/kvm_debug.txt
grep -E "(vmx|svm)" /proc/cpuinfo >> /tmp/kvm_debug.txt
echo "" >> /tmp/kvm_debug.txt
echo "=== kvm-ok ===" >> /tmp/kvm_debug.txt
kvm-ok 2>&1 >> /tmp/kvm_debug.txt
echo "" >> /tmp/kvm_debug.txt
echo "=== lsmod kvm ===" >> /tmp/kvm_debug.txt
lsmod | grep kvm >> /tmp/kvm_debug.txt
echo "" >> /tmp/kvm_debug.txt
echo "=== uname ===" >> /tmp/kvm_debug.txt
uname -a >> /tmp/kvm_debug.txt

# Mostrar conteudo
cat /tmp/kvm_debug.txt
```

**2. Comunicar IMEDIATAMENTE**

Enviar mensagem no Slack:
```
BLOQUEIO: KVM nao funciona no VPS Hostinger!

Debug:
[colar conteudo de /tmp/kvm_debug.txt]

Opcoes:
1. Contatar Hostinger para habilitar KVM
2. Migrar para Hetzner (R$ 100/mes)
3. Usar outro VPS com KVM

Aguardando decisao antes de continuar.
```

**3. PARAR e aguardar decisao**

NAO prosseguir para E01 ate resolver.

---

## Fallback: Hetzner

Se Hostinger nao suportar KVM, alternativa recomendada:

### Hetzner CX21

| Spec | Valor |
|------|-------|
| vCPU | 2 |
| RAM | 4 GB |
| Disco | 40 GB SSD |
| Preco | ~R$ 100/mes (EUR 5.09/mes) |
| KVM | Garantido |

### Como Criar

1. Acessar https://www.hetzner.com/cloud
2. Criar conta
3. Novo projeto > Novo servidor
4. Escolher:
   - Location: Nuremberg (mais barato)
   - Image: Ubuntu 22.04
   - Type: CX21
5. Adicionar chave SSH
6. Criar

### Depois de Criar

1. Copiar IP do servidor
2. Testar SSH: `ssh root@IP_HETZNER`
3. Refazer Story 0.2 e 0.3 (vai funcionar)

---

## Checklist Final E00

- [ ] **Story 0.1** - Conectou ao VPS via SSH
- [ ] **Story 0.2** - Verificou suporte KVM
- [ ] **Story 0.3** - Testou KVM com QEMU
- [ ] **Story 0.4** - Documentou resultado
- [ ] **Decisao** - KVM funciona OU fallback definido

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 0.1 Conectar SSH | 10 min |
| 0.2 Verificar KVM | 15 min |
| 0.3 Testar QEMU | 20 min |
| 0.4 Documentar | 15 min |
| **Total** | ~1 hora |

---

## Proximo Epic

Se KVM validado: [E01: Setup VPS](./epic-01-setup-vps.md)
