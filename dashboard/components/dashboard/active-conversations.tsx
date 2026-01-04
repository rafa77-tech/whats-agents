"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { formatRelativeTime } from "@/lib/utils";

interface Conversation {
  id: string;
  cliente_id: string;
  cliente_nome: string;
  cliente_telefone: string;
  status: string;
  controlled_by: string;
  last_message?: string;
  last_message_at?: string;
  unread_count: number;
  created_at: string;
}

interface ConversationsResponse {
  data: Conversation[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

function ConversationsSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-8 w-20" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-start gap-3 p-3">
              <Skeleton className="h-2 w-2 rounded-full mt-1.5" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
              <Skeleton className="h-3 w-12" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function ActiveConversations() {
  const { session } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchConversations() {
      if (!session?.access_token) return;

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(
          `${apiUrl}/dashboard/conversations?status=active&per_page=5`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          }
        );

        if (response.ok) {
          const data: ConversationsResponse = await response.json();
          setConversations(data.data);
          setTotal(data.total);
        }
      } catch (err) {
        console.error("Failed to fetch conversations:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchConversations();
    // Refresh every 30 seconds
    const interval = setInterval(fetchConversations, 30000);
    return () => clearInterval(interval);
  }, [session?.access_token]);

  if (loading) {
    return <ConversationsSkeleton />;
  }

  const getStatusColor = (conv: Conversation) => {
    if (conv.controlled_by === "human") return "bg-red-500";
    if (conv.status === "waiting") return "bg-amber-500";
    return "bg-green-500";
  };

  const getStatusLabel = (conv: Conversation) => {
    if (conv.controlled_by === "human") return "HANDOFF";
    if (conv.status === "waiting") return "Aguardando";
    return "Ativa";
  };

  const getStatusTextColor = (conv: Conversation) => {
    if (conv.controlled_by === "human") return "text-red-500";
    if (conv.status === "waiting") return "text-amber-500";
    return "text-green-500";
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <span>Conversas Ativas</span>
          <Badge variant="secondary">{total}</Badge>
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/conversas">
            Ver todas
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[240px] pr-4">
          <div className="space-y-2">
            {conversations.map((conv) => (
              <Link key={conv.id} href={`/conversas/${conv.id}`} className="block">
                <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent transition-colors">
                  {/* Status indicator */}
                  <span
                    className={`mt-1.5 h-2 w-2 rounded-full ${getStatusColor(conv)}`}
                  />

                  <div className="flex-1 min-w-0">
                    {/* Header */}
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium truncate">{conv.cliente_nome}</p>
                      {conv.last_message_at && (
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {formatRelativeTime(conv.last_message_at)}
                        </span>
                      )}
                    </div>

                    {/* Status */}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className={getStatusTextColor(conv)}>
                        {getStatusLabel(conv)}
                      </span>
                      {conv.unread_count > 0 && (
                        <>
                          <span>|</span>
                          <span className="text-primary font-medium">
                            {conv.unread_count} novas
                          </span>
                        </>
                      )}
                    </div>

                    {/* Last message */}
                    {conv.last_message && (
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                        {conv.last_message}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            ))}

            {conversations.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                Nenhuma conversa ativa no momento
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
