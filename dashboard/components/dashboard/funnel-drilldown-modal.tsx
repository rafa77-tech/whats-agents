/**
 * Funnel Drilldown Modal - Sprint 33 E11
 *
 * Modal showing list of doctors at each funnel stage.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { type FunnelDrilldownData } from "@/types/dashboard";
import {
  Search,
  ExternalLink,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

interface FunnelDrilldownModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  stage: string | null;
  period: string;
}

export function FunnelDrilldownModal({
  open,
  onOpenChange,
  stage,
  period,
}: FunnelDrilldownModalProps) {
  const [data, setData] = useState<FunnelDrilldownData | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchData = useCallback(async () => {
    if (!stage) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        pageSize: "10",
        search: debouncedSearch,
        period,
      });

      const res = await fetch(`/api/dashboard/funnel/${stage}?${params}`);
      const json = await res.json();

      if (res.ok) {
        setData(json);
      }
    } catch (error) {
      console.error("Error fetching drilldown:", error);
    } finally {
      setLoading(false);
    }
  }, [stage, page, debouncedSearch, period]);

  useEffect(() => {
    if (open && stage) {
      fetchData();
    }
  }, [open, stage, fetchData]);

  // Reset state when closing
  useEffect(() => {
    if (!open) {
      setSearch("");
      setDebouncedSearch("");
      setPage(1);
      setData(null);
    }
  }, [open]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1); // Reset page on search
  };

  const totalPages = data ? Math.ceil(data.total / data.pageSize) : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            Medicos em &quot;{data?.stageLabel || stage}&quot; ({data?.total || 0})
          </DialogTitle>
        </DialogHeader>

        {/* Busca */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar por nome..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Tabela */}
        <div className="flex-1 overflow-auto border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Telefone</TableHead>
                <TableHead>Especialidade</TableHead>
                <TableHead>Ultimo Contato</TableHead>
                <TableHead>Chip</TableHead>
                <TableHead className="w-[80px]">Acao</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center py-8 text-gray-500"
                  >
                    Nenhum medico encontrado
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">{item.nome}</TableCell>
                    <TableCell className="text-gray-600">
                      {item.telefone || "-"}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {item.especialidade}
                    </TableCell>
                    <TableCell className="text-gray-500">
                      {formatDistanceToNow(new Date(item.ultimoContato), {
                        addSuffix: true,
                        locale: ptBR,
                      })}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {item.chipName}
                    </TableCell>
                    <TableCell>
                      {item.chatwootUrl ? (
                        <Button variant="ghost" size="sm" asChild>
                          <a
                            href={item.chatwootUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </Button>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Paginacao */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Anterior
            </Button>
            <span className="text-sm text-gray-500">
              Pagina {page} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading}
            >
              Proximo
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
