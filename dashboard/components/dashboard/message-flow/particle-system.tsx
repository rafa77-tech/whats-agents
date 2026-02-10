'use client'

import type { Particle } from './use-particles'

interface ParticleSystemProps {
  particles: Particle[]
  chipPositions: Map<string, { x: number; y: number }>
  centerX: number
  centerY: number
}

export function ParticleSystem({
  particles,
  chipPositions,
  centerX,
  centerY,
}: ParticleSystemProps) {
  if (particles.length === 0) return null

  return (
    <g className="mf-particles">
      {particles.map((particle) => {
        const chipPos = chipPositions.get(particle.chipId)
        if (!chipPos) return null

        // Outbound: Julia (center) → Chip
        // Inbound: Chip → Julia (center)
        const isOutbound = particle.direction === 'outbound'
        const startX = isOutbound ? centerX : chipPos.x
        const startY = isOutbound ? centerY : chipPos.y
        const endX = isOutbound ? chipPos.x : centerX
        const endY = isOutbound ? chipPos.y : centerY

        const dx = endX - startX
        const dy = endY - startY

        return (
          <circle
            key={particle.id}
            cx={startX}
            cy={startY}
            r={3}
            className={`mf-particle ${
              isOutbound ? 'mf-particle-outbound' : 'mf-particle-inbound'
            }`}
            style={
              {
                '--mf-dx': `${dx}px`,
                '--mf-dy': `${dy}px`,
              } as React.CSSProperties
            }
          />
        )
      })}
    </g>
  )
}
