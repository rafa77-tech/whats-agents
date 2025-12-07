# Epic 2: Distribuição de Carga

## Objetivo do Epic

> **Distribuir mensagens entre instâncias de forma inteligente.**

Este epic implementa a lógica de escolha de instância e rate limit por instância.

---

## Stories

1. [S6.E2.1 - Estratégia Sticky](#s6e21---estratégia-sticky)
2. [S6.E2.2 - Fallback Automático](#s6e22---fallback-automático)
3. [S6.E2.3 - Rate Limit por Instância](#s6e23---rate-limit-por-instância)

---

# S6.E2.1 - Estratégia Sticky

## Objetivo

> **Médico sempre fala com o mesmo número WhatsApp.**

Isso evita confusão - o médico não vai estranhar receber mensagem de número diferente.

---

## Tarefas

### 1. Implementar lógica sticky

```python
# app/services/instance_manager.py

async def escolher_instancia_sticky(
    self,
    medico_id: str
) -> Optional[str]:
    """
    Escolhe instância usando estratégia sticky.

    1. Se médico já tem preferência, usa ela
    2. Se preferência não disponível, migra para outra
    3. Se novo médico, atribui menos carregada
    """
    # Buscar preferência atual
    preferida = await self._obter_preferencia(medico_id)

    if preferida:
        instancia = await self.obter_instancia(preferida)

        # Preferida disponível? Usa ela
        if instancia and instancia.disponivel:
            logger.debug(f"Médico {medico_id[:8]} usando instância preferida: {preferida}")
            return preferida

        # Preferida não disponível, migrar
        logger.info(f"Instância {preferida} indisponível, migrando médico {medico_id[:8]}")

    # Escolher nova instância (menos carregada)
    instancias = await self.listar_instancias(apenas_ativas=True)
    disponiveis = [i for i in instancias if i.disponivel]

    if not disponiveis:
        logger.error("Nenhuma instância disponível!")
        return None

    # Ordenar por carga (menos carregada primeiro)
    disponiveis.sort(key=lambda i: i.carga_percentual)
    escolhida = disponiveis[0]

    # Salvar preferência
    await self._salvar_preferencia(medico_id, escolhida.nome)
    logger.info(f"Médico {medico_id[:8]} atribuído à instância: {escolhida.nome}")

    return escolhida.nome
```

### 2. Integrar no envio de mensagens

```python
# app/services/whatsapp.py

from app.services.instance_manager import instance_manager

async def enviar_mensagem_multi(
    telefone: str,
    texto: str,
    medico_id: Optional[str] = None
) -> dict:
    """
    Envia mensagem usando multi-instância.
    """
    # Escolher instância
    instancia = await instance_manager.escolher_instancia_sticky(medico_id)

    if not instancia:
        raise Exception("Nenhuma instância disponível")

    # Criar client para instância específica
    client = EvolutionClient(instance=instancia)

    # Enviar
    resultado = await client.enviar_mensagem(telefone, texto)

    # Registrar envio
    await instance_manager.registrar_envio(instancia)

    return resultado
```

---

## DoD

- [ ] Médico novo é atribuído a instância menos carregada
- [ ] Médico existente usa mesma instância
- [ ] Preferência é salva no banco
- [ ] Log mostra qual instância foi usada
- [ ] Testes com 10 médicos distribuem corretamente

---

# S6.E2.2 - Fallback Automático

## Objetivo

> **Se instância preferida não está disponível, usar outra automaticamente.**

---

## Cenários de Fallback

| Cenário | Ação |
|---------|------|
| Instância offline | Usar próxima disponível |
| Rate limit atingido | Usar outra com capacidade |
| Instância banida | Migrar permanentemente |
| Todas offline | Enfileirar para retry |

---

## Tarefas

### 1. Implementar fallback

```python
# app/services/instance_manager.py

async def escolher_com_fallback(
    self,
    medico_id: str,
    tentativas_max: int = 3
) -> Optional[str]:
    """
    Escolhe instância com fallback automático.
    """
    preferida = await self._obter_preferencia(medico_id)
    tentativas = 0
    instancias_tentadas = set()

    while tentativas < tentativas_max:
        tentativas += 1

        # Primeira tentativa: preferida
        if tentativas == 1 and preferida:
            candidata = preferida
        else:
            # Próximas tentativas: menos carregada não tentada
            disponiveis = await self.listar_instancias(apenas_ativas=True)
            candidatas = [
                i for i in disponiveis
                if i.disponivel and i.nome not in instancias_tentadas
            ]

            if not candidatas:
                break

            candidatas.sort(key=lambda i: i.carga_percentual)
            candidata = candidatas[0].nome

        instancias_tentadas.add(candidata)

        # Verificar se realmente disponível
        instancia = await self.obter_instancia(candidata)

        if instancia and instancia.disponivel:
            # Atualizar preferência se diferente
            if candidata != preferida:
                await self._salvar_preferencia(medico_id, candidata)
                logger.info(f"Fallback: médico {medico_id[:8]} migrado para {candidata}")

            return candidata

        logger.warning(f"Instância {candidata} indisponível, tentando próxima...")

    logger.error(f"Todas as {tentativas} tentativas falharam!")
    return None
```

### 2. Tratar instância banida

```python
async def marcar_banida(self, nome: str) -> None:
    """Marca instância como banida e migra médicos."""

    # Atualizar status
    await self.atualizar_status(nome, "banned")

    # Buscar médicos que usam essa instância
    response = (
        supabase.table("clientes")
        .select("id")
        .eq("instancia_preferida", nome)
        .execute()
    )

    if response.data:
        logger.warning(f"{len(response.data)} médicos precisam migrar de {nome}")

        # Limpar preferência (serão reatribuídos no próximo envio)
        (
            supabase.table("clientes")
            .update({"instancia_preferida": None})
            .eq("instancia_preferida", nome)
            .execute()
        )

    # Notificar admin
    # await notificar_admin(f"Instância {nome} foi banida!")
```

---

## DoD

- [ ] Fallback funciona quando preferida offline
- [ ] Fallback funciona quando rate limit atingido
- [ ] Médicos são migrados quando instância banida
- [ ] Log mostra cada tentativa de fallback
- [ ] Notificação quando todas falham

---

# S6.E2.3 - Rate Limit por Instância

## Objetivo

> **Cada instância tem seu próprio rate limit.**

---

## Tarefas

### 1. Modificar rate limiter

```python
# app/services/rate_limiter.py

async def verificar_limite_hora_instancia(instancia: str) -> Tuple[bool, int]:
    """
    Verifica limite por hora para instância específica.
    """
    chave = f"rate:hora:{instancia}:{datetime.now().strftime('%Y%m%d%H')}"

    try:
        count = await redis_client.get(chave)
        count = int(count) if count else 0

        # Buscar capacidade da instância
        inst = await instance_manager.obter_instancia(instancia)
        limite = inst.capacidade_hora if inst else LIMITE_POR_HORA

        return count < limite, count

    except Exception as e:
        logger.error(f"Erro ao verificar limite: {e}")
        return True, 0


async def registrar_envio_instancia(instancia: str, telefone: str) -> None:
    """
    Registra envio para instância específica.
    """
    agora = datetime.now()

    # Contador por hora (instância)
    chave_hora = f"rate:hora:{instancia}:{agora.strftime('%Y%m%d%H')}"
    await redis_client.incr(chave_hora)
    await redis_client.expire(chave_hora, 7200)

    # Contador por dia (instância)
    chave_dia = f"rate:dia:{instancia}:{agora.strftime('%Y%m%d')}"
    await redis_client.incr(chave_dia)
    await redis_client.expire(chave_dia, 90000)

    # Último envio para telefone (global)
    chave_ultimo = f"rate:ultimo:{telefone}"
    await redis_client.set(chave_ultimo, str(agora.timestamp()))
    await redis_client.expire(chave_ultimo, 3600)

    # Atualizar contador no banco
    await instance_manager.registrar_envio(instancia)
```

### 2. Verificar capacidade antes de escolher

```python
# Adicionar em instance_manager.py

async def instancia_tem_capacidade(self, nome: str) -> bool:
    """Verifica se instância tem capacidade."""
    ok_hora, _ = await verificar_limite_hora_instancia(nome)
    ok_dia, _ = await verificar_limite_dia_instancia(nome)
    return ok_hora and ok_dia
```

### 3. Endpoint de estatísticas

```python
@router.get("/stats/instances")
async def estatisticas_instancias():
    """Retorna estatísticas de uso das instâncias."""
    instancias = await instance_manager.listar_instancias(apenas_ativas=False)

    stats = []
    for inst in instancias:
        stats.append({
            "nome": inst.nome,
            "status": inst.status,
            "msgs_hora": inst.msgs_enviadas_hora,
            "capacidade_hora": inst.capacidade_hora,
            "msgs_dia": inst.msgs_enviadas_dia,
            "capacidade_dia": inst.capacidade_dia,
            "carga": f"{inst.carga_percentual:.1f}%",
            "disponivel": inst.disponivel,
        })

    return {
        "total_instancias": len(instancias),
        "online": sum(1 for i in instancias if i.status == "connected"),
        "capacidade_total_dia": sum(i.capacidade_dia for i in instancias),
        "enviadas_hoje": sum(i.msgs_enviadas_dia for i in instancias),
        "instancias": stats
    }
```

---

## DoD

- [ ] Rate limit funciona por instância
- [ ] Contadores separados no Redis
- [ ] Instância sem capacidade não é escolhida
- [ ] Endpoint /stats/instances mostra uso
- [ ] Reset de contadores funciona (hora/dia)
