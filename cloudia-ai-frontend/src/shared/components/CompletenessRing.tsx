import { scoreColor } from '@/lib/brand-dna-score'

interface Props {
  score: number
  size?: number
  strokeWidth?: number
  showLabel?: boolean
}

export function CompletenessRing({ score, size = 44, strokeWidth = 4, showLabel = true }: Props) {
  const r = (size - strokeWidth) / 2
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const color = scoreColor(score)

  return (
    <div className="relative inline-flex items-center justify-center flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      {showLabel && (
        <span className="absolute text-[10px] font-bold" style={{ color }}>
          {score}%
        </span>
      )}
    </div>
  )
}
