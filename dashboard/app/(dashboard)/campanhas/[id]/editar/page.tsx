'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import {
  ArrowLeft,
  Save,
  Loader2,
  Settings,
  Users,
  MessageSquare,
  AlertTriangle,
  Calendar,
  Clock,
} from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'

const TIPOS_CAMPANHA = [
  { value: 'oferta_plantao', label: 'Oferta de Plantao' },
  { value: 'reativacao', label: 'Reativacao' },
  { value: 'followup', label: 'Follow-up' },
  { value: 'descoberta', label: 'Descoberta' },
]

const CATEGORIAS = [
  { value: 'marketing', label: 'Marketing' },
  { value: 'operacional', label: 'Operacional' },
  { value: 'relacionamento', label: 'Relacionamento' },
]

const TONS = [
  { value: 'amigavel', label: 'Amigavel' },
  { value: 'profissional', label: 'Profissional' },
  { value: 'urgente', label: 'Urgente' },
  { value: 'casual', label: 'Casual' },
]

interface FiltroOption {
  value: string
  label: string
  count: number
}

export default function EditarCampanhaPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filtros dinamicos do banco
  const [especialidadesOptions, setEspecialidadesOptions] = useState<FiltroOption[]>([])
  const [estadosOptions, setEstadosOptions] = useState<FiltroOption[]>([])
  const [loadingFiltros, setLoadingFiltros] = useState(true)

  // Form state
  const [nomeTemplate, setNomeTemplate] = useState('')
  const [tipoCampanha, setTipoCampanha] = useState('oferta_plantao')
  const [categoria, setCategoria] = useState('marketing')
  const [objetivo, setObjetivo] = useState('')
  const [corpo, setCorpo] = useState('')
  const [tom, setTom] = useState('amigavel')
  const [especialidades, setEspecialidades] = useState<string[]>([])
  const [regioes, setRegioes] = useState<string[]>([])
  const [quantidadeAlvo, setQuantidadeAlvo] = useState(50)
  const [agendarPara, setAgendarPara] = useState<string>('')
  const [horaAgendamento, setHoraAgendamento] = useState<string>('09:00')
  // Preservar IDs selecionados/excluidos manualmente
  const [selectedClienteIds, setSelectedClienteIds] = useState<string[] | undefined>(undefined)
  const [excludedClienteIds, setExcludedClienteIds] = useState<string[] | undefined>(undefined)

  const carregarCampanha = useCallback(async () => {
    try {
      setError(null)
      const res = await fetch(`/api/campanhas/${params.id}`)
      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Erro ao carregar campanha')
        return
      }

      // Verificar se a campanha pode ser editada
      if (!['rascunho', 'agendada'].includes(data.status)) {
        setError('Apenas campanhas em rascunho ou agendadas podem ser editadas')
        return
      }

      // Preencher formulario com dados da campanha
      setNomeTemplate(data.nome_template || '')
      setTipoCampanha(data.tipo_campanha || 'oferta_plantao')
      setCategoria(data.categoria || 'marketing')
      setObjetivo(data.objetivo || '')
      setCorpo(data.corpo || '')
      setTom(data.tom || 'amigavel')

      if (data.audience_filters) {
        setEspecialidades(data.audience_filters.especialidades || [])
        setRegioes(data.audience_filters.regioes || [])
        setQuantidadeAlvo(data.audience_filters.quantidade_alvo || 50)
        // Preservar IDs selecionados/excluidos manualmente
        setSelectedClienteIds(data.audience_filters.selected_cliente_ids)
        setExcludedClienteIds(data.audience_filters.excluded_cliente_ids)
      }

      // Carregar agendamento se existir
      if (data.agendar_para) {
        const dataAgendamento = new Date(data.agendar_para)
        const dataParte = dataAgendamento.toISOString().split('T')[0]
        if (dataParte) {
          setAgendarPara(dataParte)
        }
        const horaParte = dataAgendamento.toLocaleTimeString('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        })
        setHoraAgendamento(horaParte)
      }
    } catch (err) {
      console.error('Erro ao carregar campanha:', err)
      setError('Erro de conexao com o servidor')
    } finally {
      setLoading(false)
    }
  }, [params.id])

  useEffect(() => {
    carregarCampanha()
  }, [carregarCampanha])

  // Carregar opcoes de filtros do banco
  useEffect(() => {
    const carregarFiltros = async () => {
      try {
        const res = await fetch('/api/filtros')
        const data = await res.json()

        if (res.ok) {
          setEspecialidadesOptions(data.especialidades || [])
          setEstadosOptions(data.estados || [])
        }
      } catch (err) {
        console.error('Erro ao carregar filtros:', err)
      } finally {
        setLoadingFiltros(false)
      }
    }

    carregarFiltros()
  }, [])

  const handleSave = async () => {
    if (!nomeTemplate.trim()) {
      toast({
        title: 'Erro',
        description: 'Nome da campanha e obrigatorio',
        variant: 'destructive',
      })
      return
    }

    setSaving(true)

    try {
      // Montar data de agendamento se informada
      let agendarParaISO: string | null = null
      if (agendarPara) {
        const parteData = agendarPara.split('-')
        const parteHora = horaAgendamento.split(':')
        const ano = parteData[0] ?? '2026'
        const mes = parteData[1] ?? '01'
        const dia = parteData[2] ?? '01'
        const hora = parteHora[0] ?? '09'
        const minuto = parteHora[1] ?? '00'
        const dataCompleta = new Date(
          parseInt(ano),
          parseInt(mes) - 1,
          parseInt(dia),
          parseInt(hora),
          parseInt(minuto)
        )
        agendarParaISO = dataCompleta.toISOString()
      }

      // Construir audience_filters preservando IDs manuais
      const audienceFilters: Record<string, unknown> = {
        especialidades,
        regioes,
        quantidade_alvo: quantidadeAlvo,
      }
      // Preservar IDs selecionados/excluidos manualmente
      if (selectedClienteIds && selectedClienteIds.length > 0) {
        audienceFilters.selected_cliente_ids = selectedClienteIds
      }
      if (excludedClienteIds && excludedClienteIds.length > 0) {
        audienceFilters.excluded_cliente_ids = excludedClienteIds
      }

      const payload = {
        nome_template: nomeTemplate,
        tipo_campanha: tipoCampanha,
        categoria,
        objetivo: objetivo || null,
        corpo,
        tom,
        agendar_para: agendarParaISO,
        audience_filters: audienceFilters,
      }

      const res = await fetch(`/api/campanhas/${params.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json()

      if (!res.ok) {
        toast({
          title: 'Erro',
          description: data.detail || 'Erro ao salvar campanha',
          variant: 'destructive',
        })
        return
      }

      toast({
        title: 'Sucesso',
        description: 'Campanha atualizada com sucesso',
      })

      router.push(`/campanhas/${params.id}`)
    } catch (err) {
      console.error('Erro ao salvar campanha:', err)
      toast({
        title: 'Erro',
        description: 'Erro de conexao com o servidor',
        variant: 'destructive',
      })
    } finally {
      setSaving(false)
    }
  }

  const toggleEspecialidade = (esp: string) => {
    setEspecialidades((prev) =>
      prev.includes(esp) ? prev.filter((e) => e !== esp) : [...prev, esp]
    )
  }

  const toggleRegiao = (reg: string) => {
    setRegioes((prev) => (prev.includes(reg) ? prev.filter((r) => r !== reg) : [...prev, reg]))
  }

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/campanhas/${params.id}`}>
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Erro</h1>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-yellow-500" />
            <p className="text-lg font-medium">{error}</p>
            <Button className="mt-4" asChild>
              <Link href={`/campanhas/${params.id}`}>Voltar</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/campanhas/${params.id}`}>
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Editar Campanha</h1>
            <p className="text-gray-500">{nomeTemplate || 'Nova Campanha'}</p>
          </div>
        </div>

        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Salvando...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Salvar Alteracoes
            </>
          )}
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Configuracao */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Configuracao
            </CardTitle>
            <CardDescription>Informacoes basicas da campanha</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="nome">Nome da Campanha *</Label>
              <Input
                id="nome"
                value={nomeTemplate}
                onChange={(e) => setNomeTemplate(e.target.value)}
                placeholder="Ex: Discovery Janeiro 2026"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Tipo</Label>
                <Select value={tipoCampanha} onValueChange={setTipoCampanha}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIPOS_CAMPANHA.map((tipo) => (
                      <SelectItem key={tipo.value} value={tipo.value}>
                        {tipo.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Categoria</Label>
                <Select value={categoria} onValueChange={setCategoria}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIAS.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="objetivo">Objetivo</Label>
              <Textarea
                id="objetivo"
                value={objetivo}
                onChange={(e) => setObjetivo(e.target.value)}
                placeholder="Descreva o objetivo desta campanha... (este texto e enviado para a Julia como instrucao)"
                rows={3}
              />
              <p className="mt-1 text-xs text-gray-500">
                Este texto e injetado no prompt da Julia como instrucao
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Agendamento */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Agendamento
            </CardTitle>
            <CardDescription>Defina quando a campanha deve iniciar</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="data-agendamento">Data</Label>
                <Input
                  id="data-agendamento"
                  type="date"
                  value={agendarPara}
                  onChange={(e) => setAgendarPara(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>
              <div>
                <Label htmlFor="hora-agendamento">Horario</Label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    id="hora-agendamento"
                    type="time"
                    value={horaAgendamento}
                    onChange={(e) => setHoraAgendamento(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
            </div>
            {agendarPara ? (
              <div className="rounded-lg bg-blue-50 p-3">
                <p className="text-sm text-blue-700">
                  <Calendar className="mr-1 inline h-4 w-4" />
                  Campanha agendada para{' '}
                  <strong>
                    {new Date(agendarPara + 'T' + horaAgendamento).toLocaleDateString('pt-BR', {
                      weekday: 'long',
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })}{' '}
                    as {horaAgendamento}
                  </strong>
                </p>
              </div>
            ) : (
              <p className="text-xs text-gray-500">Deixe em branco para iniciar manualmente</p>
            )}
          </CardContent>
        </Card>

        {/* Mensagem */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Mensagem
            </CardTitle>
            <CardDescription>
              Template da mensagem (variacoes sao geradas automaticamente)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Tom da Mensagem</Label>
              <Select value={tom} onValueChange={setTom}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TONS.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="corpo">Corpo da Mensagem</Label>
              <Textarea
                id="corpo"
                value={corpo}
                onChange={(e) => setCorpo(e.target.value)}
                placeholder="Digite a mensagem base..."
                rows={5}
              />
              <p className="mt-1 text-xs text-gray-500">
                Julia gera variacoes automaticamente para cada medico
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Audiencia */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Audiencia
            </CardTitle>
            <CardDescription>Filtre os medicos que receberao a campanha</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <Label htmlFor="quantidade">Quantidade Alvo</Label>
              <Input
                id="quantidade"
                type="number"
                min={1}
                max={500}
                value={quantidadeAlvo}
                onChange={(e) => setQuantidadeAlvo(parseInt(e.target.value) || 50)}
                className="w-32"
              />
              <p className="mt-1 text-xs text-gray-500">Maximo de medicos a serem selecionados</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <Label className="mb-3 block">Especialidades</Label>
                {loadingFiltros ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Carregando...
                  </div>
                ) : (
                  <div className="max-h-64 overflow-y-auto">
                    <div className="grid grid-cols-1 gap-2">
                      {especialidadesOptions.map((esp) => (
                        <label
                          key={esp.value}
                          className="flex cursor-pointer items-center gap-2 rounded border p-2 hover:bg-gray-50"
                        >
                          <Checkbox
                            checked={especialidades.includes(esp.value)}
                            onCheckedChange={() => toggleEspecialidade(esp.value)}
                          />
                          <span className="flex-1 text-sm">{esp.label}</span>
                          <span className="text-xs text-gray-400">
                            ({esp.count.toLocaleString()})
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
                {especialidades.length === 0 && (
                  <p className="mt-2 text-xs text-gray-500">
                    Nenhuma selecionada = todas as especialidades
                  </p>
                )}
              </div>

              <div>
                <Label className="mb-3 block">Estados</Label>
                {loadingFiltros ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Carregando...
                  </div>
                ) : (
                  <div className="max-h-64 overflow-y-auto">
                    <div className="grid grid-cols-2 gap-2">
                      {estadosOptions.map((est) => (
                        <label
                          key={est.value}
                          className="flex cursor-pointer items-center gap-2 rounded border p-2 hover:bg-gray-50"
                        >
                          <Checkbox
                            checked={regioes.includes(est.value)}
                            onCheckedChange={() => toggleRegiao(est.value)}
                          />
                          <span className="flex-1 text-sm">{est.value}</span>
                          <span className="text-xs text-gray-400">
                            ({est.count.toLocaleString()})
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
                {regioes.length === 0 && (
                  <p className="mt-2 text-xs text-gray-500">
                    Nenhum selecionado = todos os estados
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
