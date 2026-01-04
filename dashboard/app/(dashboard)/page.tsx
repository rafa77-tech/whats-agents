import { Suspense } from "react";
import { StatusCards } from "@/components/dashboard/status-cards";
import { FunnelCard } from "@/components/dashboard/funnel-card";
import { ActiveConversations } from "@/components/dashboard/active-conversations";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { AlertsList } from "@/components/dashboard/alerts-list";
import { Skeleton } from "@/components/ui/skeleton";

function StatusCardsSkeleton() {
  return (
    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <Skeleton key={i} className="h-24" />
      ))}
    </div>
  );
}

function CardSkeleton({ className }: { className?: string }) {
  return <Skeleton className={className} />;
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Visao geral das operacoes de hoje
          </p>
        </div>
      </div>

      {/* Status Cards */}
      <Suspense fallback={<StatusCardsSkeleton />}>
        <StatusCards />
      </Suspense>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Funnel */}
        <Suspense fallback={<CardSkeleton className="h-[300px]" />}>
          <FunnelCard />
        </Suspense>

        {/* Active Conversations */}
        <Suspense fallback={<CardSkeleton className="h-[300px]" />}>
          <ActiveConversations />
        </Suspense>
      </div>

      {/* Alerts & Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Alerts */}
        <Suspense fallback={<CardSkeleton className="h-[200px]" />}>
          <AlertsList />
        </Suspense>

        {/* Activity Feed */}
        <Suspense fallback={<CardSkeleton className="h-[200px]" />}>
          <ActivityFeed />
        </Suspense>
      </div>
    </div>
  );
}
