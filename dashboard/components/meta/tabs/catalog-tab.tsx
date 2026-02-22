'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import type { MetaCatalogProduct, MetaMMLiteMetrics } from '@/types/meta'
import { ShoppingBag, Package, Zap, TrendingUp, Eye } from 'lucide-react'

export default function CatalogTab() {
  const { toast } = useToast()
  const [products, setProducts] = useState<MetaCatalogProduct[]>([])
  const [mmLite, setMmLite] = useState<MetaMMLiteMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [p, m] = await Promise.all([metaApi.getCatalogProducts(), metaApi.getMMLiteMetrics()])
      setProducts(p)
      setMmLite(m)
    } catch (err) {
      toast({
        title: 'Erro ao carregar catalogo',
        description: err instanceof Error ? err.message : 'Erro desconhecido',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  if (loading) {
    return <div className="text-sm text-muted-foreground">Carregando catalogo...</div>
  }

  return (
    <div className="space-y-6">
      {/* MM Lite metrics */}
      {mmLite && (
        <>
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            <h3 className="text-sm font-medium">Marketing Messages Lite</h3>
            <Badge variant={mmLite.enabled ? 'default' : 'secondary'}>
              {mmLite.enabled ? 'Ativo' : 'Inativo'}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Enviados (7d)</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">{mmLite.total_sent}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Entregues</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">{mmLite.delivered}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-1">
                  <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Delivery Rate</p>
                </div>
                <p className="mt-1 text-2xl font-bold tabular-nums">
                  {(mmLite.delivery_rate * 100).toFixed(1)}%
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-1">
                  <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Read Rate</p>
                </div>
                <p className="mt-1 text-2xl font-bold tabular-nums">
                  {(mmLite.read_rate * 100).toFixed(1)}%
                </p>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {/* Catalog products */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShoppingBag className="h-4 w-4" />
            Catalogo de Produtos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {products.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum produto no catalogo.</p>
          ) : (
            <div className="space-y-2">
              {products.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div className="flex items-center gap-3">
                    <Package className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{p.name}</p>
                      {p.description && (
                        <p className="line-clamp-1 text-xs text-muted-foreground">
                          {p.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {p.price && (
                      <span className="text-sm tabular-nums">
                        {p.currency ?? 'BRL'} {p.price}
                      </span>
                    )}
                    <Badge
                      variant={p.availability === 'in stock' ? 'default' : 'secondary'}
                      className="text-[10px]"
                    >
                      {p.availability}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
