'use client'

import { useMemo, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import type { ChipNode, ChipNodeStatus, RecentMessage } from '@/types/dashboard'
import { ParticleSystem } from './particle-system'
import { useParticles } from './use-particles'
import { FlowLegend } from './flow-legend'

interface RadialGraphProps {
  chips: ChipNode[]
  recentMessages: RecentMessage[]
  messagesPerMinute: number
}

const VIEW_WIDTH = 600
const VIEW_HEIGHT = 200

/** Julia node: left side */
const JULIA_X = 80
const JULIA_RADIUS = 24

/** Chips column: right side */
const CHIPS_X = VIEW_WIDTH - 80
const CHIP_RADIUS = 9
const CHIP_VERTICAL_GAP = 18
const CHIP_HIT_RADIUS = 16 // larger invisible hit area for easier interaction

const STATUS_COLORS: Record<ChipNodeStatus, string> = {
  active: 'hsl(142, 71%, 45%)',
  warming: 'hsl(45, 93%, 47%)',
  degraded: 'hsl(0, 72%, 51%)',
  paused: 'hsl(220, 9%, 60%)',
  offline: 'hsl(220, 9%, 43%)',
}

const STATUS_LABELS: Record<ChipNodeStatus, string> = {
  active: 'Ativo',
  warming: 'Aquecendo',
  degraded: 'Degradado',
  paused: 'Pausado',
  offline: 'Offline',
}

function getChipY(index: number, total: number, viewHeight: number): number {
  if (total === 1) return viewHeight / 2
  const itemHeight = CHIP_RADIUS * 2 + CHIP_VERTICAL_GAP
  const totalHeight = total * itemHeight - CHIP_VERTICAL_GAP
  const startY = (viewHeight - totalHeight) / 2 + CHIP_RADIUS
  return startY + index * itemHeight
}

function truncateName(name: string, maxLen = 12): string {
  return name.length > maxLen ? name.slice(0, maxLen) : name
}

/** Tooltip dimensions */
const TT_WIDTH = 150
const TT_HEIGHT = 62
const TT_PADDING = 8
const TT_LINE_HEIGHT = 13

export function RadialGraph({
  chips,
  recentMessages,
  messagesPerMinute,
}: RadialGraphProps) {
  const router = useRouter()
  const [hoveredChipId, setHoveredChipId] = useState<string | null>(null)
  const [juliaHovered, setJuliaHovered] = useState(false)

  const viewHeight = Math.max(VIEW_HEIGHT, chips.length * (CHIP_RADIUS * 2 + CHIP_VERTICAL_GAP) + 40)

  const chipPositions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>()
    chips.forEach((chip, i) => {
      map.set(chip.id, { x: CHIPS_X, y: getChipY(i, chips.length, viewHeight) })
    })
    return map
  }, [chips, viewHeight])

  const particles = useParticles({
    messages: recentMessages,
    maxParticles: 20,
    animationDuration: Math.max(1000, 2000 - messagesPerMinute * 50),
  })

  const isIdle = messagesPerMinute === 0
  const juliaY = viewHeight / 2

  const handleChipClick = useCallback(
    (chipId: string) => {
      router.push(`/chips?highlight=${chipId}`)
    },
    [router]
  )

  const hoveredChip = hoveredChipId ? chips.find((c) => c.id === hoveredChipId) : null
  const hoveredPos = hoveredChipId ? chipPositions.get(hoveredChipId) : null

  return (
    <div className="flex h-full flex-col">
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${viewHeight}`}
        preserveAspectRatio="xMidYMid meet"
        className="flex-1"
        role="img"
        aria-label={`Fluxo de mensagens: ${chips.length} chips, ${messagesPerMinute} mensagens por minuto`}
      >

        {/* Layer 1: Connection lines */}
        <g className="mf-connections">
          {chips.map((chip) => {
            const pos = chipPositions.get(chip.id)
            if (!pos) return null
            const activity = chip.recentOutbound + chip.recentInbound
            const isHovered = chip.id === hoveredChipId
            const opacity = isHovered
              ? 0.5
              : chip.isActive
                ? Math.min(0.2 + activity * 0.05, 0.6)
                : 0.1
            return (
              <line
                key={`conn-${chip.id}`}
                x1={JULIA_X}
                y1={juliaY}
                x2={pos.x}
                y2={pos.y}
                stroke="currentColor"
                strokeOpacity={opacity}
                strokeWidth={isHovered ? 1.5 : 1}
                strokeDasharray={chip.isActive ? 'none' : '4 3'}
                className={`text-muted-foreground transition-opacity duration-150`}
              />
            )
          })}
        </g>

        {/* Layer 2: Chip nodes (right side) */}
        <g className="mf-chip-nodes">
          {chips.map((chip) => {
            const pos = chipPositions.get(chip.id)
            if (!pos) return null
            const color = STATUS_COLORS[chip.status]
            const isHovered = chip.id === hoveredChipId
            return (
              <g
                key={`chip-${chip.id}`}
                onMouseEnter={() => setHoveredChipId(chip.id)}
                onMouseLeave={() => setHoveredChipId(null)}
                onClick={() => handleChipClick(chip.id)}
                className="cursor-pointer"
              >
                {/* Invisible larger hit area */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={CHIP_HIT_RADIUS}
                  fill="transparent"
                />
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={isHovered ? CHIP_RADIUS + 2 : CHIP_RADIUS}
                  fill={color}
                  fillOpacity={isHovered ? 1 : 0.85}
                  stroke={color}
                  strokeWidth={1.5}
                  strokeOpacity={Math.max(0.3, (chip.trustScore ?? 0) / 100)}
                  className={`${chip.isActive ? 'mf-chip-pulse' : ''} transition-all duration-150`}
                  style={{ color }}
                />
                <text
                  x={pos.x - CHIP_RADIUS - 6}
                  y={pos.y + 3.5}
                  textAnchor="end"
                  fontSize="9"
                  fontWeight={isHovered ? '600' : '400'}
                  className="fill-muted-foreground"
                >
                  {truncateName(chip.name)}
                </text>
              </g>
            )
          })}
        </g>

        {/* Layer 3: Julia node (left side) */}
        <g
          className={`${isIdle && !juliaHovered ? 'mf-breathe' : ''} cursor-pointer`}
          onMouseEnter={() => setJuliaHovered(true)}
          onMouseLeave={() => setJuliaHovered(false)}
        >
          <circle
            cx={JULIA_X}
            cy={juliaY}
            r={juliaHovered ? JULIA_RADIUS + 3 : JULIA_RADIUS}
            fill="hsl(262, 83%, 55%)"
            stroke="hsl(262, 83%, 55%)"
            strokeWidth={2}
            className="transition-all duration-150"
          />
          <text
            x={JULIA_X}
            y={juliaY + 4}
            textAnchor="middle"
            fontSize="11"
            fontWeight="600"
            className="fill-white"
          >
            Jull.ia
          </text>
        </g>

        {/* Layer 4: Particles */}
        <ParticleSystem
          particles={particles}
          chipPositions={chipPositions}
          centerX={JULIA_X}
          centerY={juliaY}
        />

        {/* Layer 5: Tooltips (rendered last so they're on top) */}
        {juliaHovered && (
          <g
            className="pointer-events-none"
            transform={`translate(${JULIA_X + JULIA_RADIUS + 10}, ${juliaY - TT_HEIGHT / 2})`}
          >
            <rect
              width={TT_WIDTH}
              height={TT_HEIGHT}
              rx={6}
              className="fill-popover stroke-border"
              strokeWidth={0.5}
              filter="drop-shadow(0 2px 4px rgba(0,0,0,0.1))"
            />
            <text x={TT_PADDING} y={TT_PADDING + TT_LINE_HEIGHT} fontSize="10" fontWeight="600" className="fill-foreground">
              Jull.ia · Agente IA
            </text>
            <text x={TT_PADDING} y={TT_PADDING + TT_LINE_HEIGHT * 2 + 2} fontSize="9" className="fill-muted-foreground">
              {chips.length} chips conectados
            </text>
            <text x={TT_PADDING} y={TT_PADDING + TT_LINE_HEIGHT * 3 + 4} fontSize="9" className="fill-muted-foreground">
              {messagesPerMinute} msg/min · {isIdle ? 'Idle' : 'Ativa'}
            </text>
          </g>
        )}
        {hoveredChip && hoveredPos && (
          <g
            className="pointer-events-none"
            transform={`translate(${hoveredPos.x - TT_WIDTH - CHIP_HIT_RADIUS - 8}, ${hoveredPos.y - TT_HEIGHT / 2})`}
          >
            <rect
              width={TT_WIDTH}
              height={TT_HEIGHT}
              rx={6}
              className="fill-popover stroke-border"
              strokeWidth={0.5}
              filter="drop-shadow(0 2px 4px rgba(0,0,0,0.1))"
            />
            <text x={TT_PADDING} y={TT_PADDING + TT_LINE_HEIGHT} fontSize="10" fontWeight="600" className="fill-foreground">
              {hoveredChip.name}
            </text>
            <text x={TT_PADDING} y={TT_PADDING + TT_LINE_HEIGHT * 2 + 2} fontSize="9" className="fill-muted-foreground">
              {STATUS_LABELS[hoveredChip.status]} · Trust {hoveredChip.trustScore}%
            </text>
            <text x={TT_PADDING} y={TT_PADDING + TT_LINE_HEIGHT * 3 + 4} fontSize="9" className="fill-muted-foreground">
              ↑ {hoveredChip.recentOutbound} enviadas · ↓ {hoveredChip.recentInbound} recebidas
            </text>
          </g>
        )}
      </svg>

      <FlowLegend />
    </div>
  )
}
