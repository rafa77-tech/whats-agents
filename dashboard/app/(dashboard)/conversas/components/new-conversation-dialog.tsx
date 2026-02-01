'use client'

import { useCallback, useEffect, useState } from 'react'
import { Search, Phone, User, Loader2, MessageSquarePlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

interface Doctor {
  id: string
  nome: string
  telefone: string
  especialidade?: string
  crm?: string
}

interface Props {
  onStart: (phone: string, doctorId?: string) => Promise<void>
  trigger?: React.ReactNode
}

function formatPhone(phone: string): string {
  const cleaned = phone.replace(/\D/g, '').slice(-11)
  if (cleaned.length === 11) {
    return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`
  }
  return phone
}

export function NewConversationDialog({ onStart, trigger }: Props) {
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState<'search' | 'manual'>('search')
  const [search, setSearch] = useState('')
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [doctors, setDoctors] = useState<Doctor[]>([])

  const searchDoctors = useCallback(async (query: string) => {
    if (!query || query.length < 2) {
      setDoctors([])
      return
    }

    setSearching(true)
    try {
      const response = await fetch(`/api/medicos?search=${encodeURIComponent(query)}&limit=20`)
      if (response.ok) {
        const result = await response.json()
        setDoctors(result.data || [])
      }
    } catch (err) {
      console.error('Failed to search doctors:', err)
    } finally {
      setSearching(false)
    }
  }, [])

  useEffect(() => {
    const timeout = setTimeout(() => {
      searchDoctors(search)
    }, 300)
    return () => clearTimeout(timeout)
  }, [search, searchDoctors])

  const handleStartWithDoctor = async (doctor: Doctor) => {
    setLoading(true)
    try {
      await onStart(doctor.telefone, doctor.id)
      setOpen(false)
      setSearch('')
      setDoctors([])
    } finally {
      setLoading(false)
    }
  }

  const handleStartWithPhone = async () => {
    const cleanPhone = phone.replace(/\D/g, '')
    if (cleanPhone.length < 10) return

    setLoading(true)
    try {
      await onStart(cleanPhone)
      setOpen(false)
      setPhone('')
    } finally {
      setLoading(false)
    }
  }

  const handlePhoneInput = (value: string) => {
    // Only allow numbers, spaces, dashes, and parentheses
    const cleaned = value.replace(/[^\d\s\-()]/g, '')
    setPhone(cleaned)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button size="sm" className="gap-2 bg-emerald-600 hover:bg-emerald-700">
            <MessageSquarePlus className="h-4 w-4" />
            <span className="hidden sm:inline">Nova Conversa</span>
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Nova Conversa</DialogTitle>
          <DialogDescription>
            Busque um medico ou digite um numero de telefone
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => setTab(v as 'search' | 'manual')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="search" className="gap-2">
              <Search className="h-4 w-4" />
              Buscar Medico
            </TabsTrigger>
            <TabsTrigger value="manual" className="gap-2">
              <Phone className="h-4 w-4" />
              Numero Manual
            </TabsTrigger>
          </TabsList>

          <TabsContent value="search" className="mt-4 space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Nome, telefone ou CRM..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            <ScrollArea className="h-[300px]">
              {searching ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : doctors.length > 0 ? (
                <div className="space-y-1">
                  {doctors.map((doctor) => (
                    <button
                      key={doctor.id}
                      onClick={() => handleStartWithDoctor(doctor)}
                      disabled={loading}
                      className={cn(
                        'flex w-full items-center gap-3 rounded-lg p-3 text-left transition-colors',
                        'hover:bg-muted/50',
                        loading && 'opacity-50'
                      )}
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                        <User className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{doctor.nome}</span>
                          {doctor.especialidade && (
                            <span className="text-xs text-muted-foreground">
                              {doctor.especialidade}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Phone className="h-3 w-3" />
                          {formatPhone(doctor.telefone)}
                          {doctor.crm && (
                            <>
                              <span className="text-muted-foreground/50">|</span>
                              <span>CRM {doctor.crm}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              ) : search.length >= 2 ? (
                <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-muted-foreground">
                  <User className="h-8 w-8 opacity-50" />
                  <p>Nenhum medico encontrado</p>
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() => {
                      setPhone(search)
                      setTab('manual')
                    }}
                  >
                    Usar como numero
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-muted-foreground">
                  <Search className="h-8 w-8 opacity-50" />
                  <p>Digite para buscar</p>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="manual" className="mt-4 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="phone">Numero de telefone</Label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="phone"
                  placeholder="(11) 99999-9999"
                  value={phone}
                  onChange={(e) => handlePhoneInput(e.target.value)}
                  className="pl-9"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Digite o numero com DDD
              </p>
            </div>

            <Button
              onClick={handleStartWithPhone}
              disabled={loading || phone.replace(/\D/g, '').length < 10}
              className="w-full gap-2 bg-emerald-600 hover:bg-emerald-700"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <MessageSquarePlus className="h-4 w-4" />
              )}
              Iniciar Conversa
            </Button>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
