"use client";

import { useState } from "react";
import { Clock } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPause: (duration: number, reason: string) => Promise<void>;
}

const PRESET_DURATIONS = [
  { label: "15 min", value: 15 },
  { label: "30 min", value: 30 },
  { label: "1 hora", value: 60 },
  { label: "2 horas", value: 120 },
];

export function JuliaPauseDialog({ open, onOpenChange, onPause }: Props) {
  const [duration, setDuration] = useState(30);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);

  const handlePause = async () => {
    setLoading(true);
    try {
      await onPause(duration, reason || "Pausa via dashboard");
      onOpenChange(false);
      setReason("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Pausar Julia
          </DialogTitle>
          <DialogDescription>
            Julia voltara automaticamente apos o tempo definido
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Presets */}
          <div className="space-y-2">
            <Label>Duracao rapida</Label>
            <div className="flex gap-2">
              {PRESET_DURATIONS.map((preset) => (
                <Button
                  key={preset.value}
                  variant={duration === preset.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDuration(preset.value)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Slider customizado */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <Label>Duracao customizada</Label>
              <span className="text-sm font-medium">{duration} min</span>
            </div>
            <Slider
              value={[duration]}
              onValueChange={(values) => setDuration(values[0] ?? 30)}
              min={5}
              max={240}
              step={5}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>5 min</span>
              <span>4 horas</span>
            </div>
          </div>

          {/* Motivo */}
          <div className="space-y-2">
            <Label htmlFor="reason">Motivo (opcional)</Label>
            <Input
              id="reason"
              placeholder="Ex: Reuniao de equipe"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handlePause} disabled={loading}>
            {loading ? "Pausando..." : `Pausar por ${duration} min`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
