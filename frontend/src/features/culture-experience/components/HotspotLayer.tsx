import type { CSSProperties } from 'react';
import type { CultureHotspot, HotspotGeometry } from '../types';

interface HotspotLayerProps {
  hotspots: CultureHotspot[];
  activeId: string | null;
  hoveredId: string | null;
  showRegions: boolean;
  accent: string;
  gold: string;
  /** 当前缩放倍数：编号按钮反向缩放，避免放大后盖住画面。 */
  zoom: number;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  registerRef: (id: string, element: HTMLButtonElement | null) => void;
}

function centreOf(geometry: HotspotGeometry): { x: number; y: number } {
  if ('points' in geometry) {
    const sum = geometry.points.reduce((acc, point) => ({ x: acc.x + point[0], y: acc.y + point[1] }), { x: 0, y: 0 });
    return { x: sum.x / geometry.points.length, y: sum.y / geometry.points.length };
  }
  if ('r' in geometry) return { x: geometry.cx, y: geometry.cy };
  return { x: geometry.x + geometry.width / 2, y: geometry.y + geometry.height / 2 };
}

/**
 * 热点层：几何在归一化坐标里画，因此与任何容器尺寸、任何缩放都严格对齐。
 * 默认只显示编号，不直接在画面上涂红圈——需要时（提示模式）才显形。
 */
export function HotspotLayer({
  hotspots,
  activeId,
  hoveredId,
  showRegions,
  accent,
  gold,
  zoom,
  onSelect,
  onHover,
  registerRef,
}: HotspotLayerProps) {
  const chipScale = 1 / Math.max(zoom, 1);

  return (
    <div className="absolute inset-0">
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        viewBox="0 0 1 1"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {hotspots.map((hotspot) => {
          const isActive = hotspot.id === activeId;
          const isHovered = hotspot.id === hoveredId;
          const highlighted = isActive || isHovered;
          const opacity = highlighted ? 0.95 : showRegions ? 0.34 : 0;
          if (opacity === 0) return null;
          const common = {
            fill: isActive ? accent : 'transparent',
            fillOpacity: isActive ? 0.12 : 0,
            stroke: isActive ? accent : gold,
            strokeWidth: highlighted ? 1.6 : 1,
            strokeDasharray: highlighted ? undefined : '4 4',
            vectorEffect: 'non-scaling-stroke' as const,
            style: { transition: 'opacity 200ms ease, stroke-width 200ms ease' },
          };
          const g = hotspot.geometry;
          if ('points' in g) {
            return (
              <polygon
                key={hotspot.id}
                points={g.points.map((point) => `${point[0]},${point[1]}`).join(' ')}
                {...common}
                opacity={opacity}
              />
            );
          }
          if ('r' in g) {
            return (
              <ellipse
                key={hotspot.id}
                cx={g.cx}
                cy={g.cy}
                rx={g.r}
                ry={g.r}
                {...common}
                opacity={opacity}
              />
            );
          }
          return (
            <rect
              key={hotspot.id}
              x={g.x}
              y={g.y}
              width={g.width}
              height={g.height}
              rx={0.008}
              {...common}
              opacity={opacity}
            />
          );
        })}
      </svg>

      {hotspots.map((hotspot, index) => {
        const centre = centreOf(hotspot.geometry);
        const isActive = hotspot.id === activeId;
        const style: CSSProperties = {
          left: `${centre.x * 100}%`,
          top: `${centre.y * 100}%`,
          transform: `translate(-50%, -50%) scale(${chipScale})`,
          borderColor: isActive ? accent : 'rgba(255,255,255,0.85)',
          backgroundColor: isActive ? accent : 'rgba(28,22,18,0.55)',
          color: '#fff',
          boxShadow: isActive ? `0 0 0 4px ${accent}26` : '0 2px 8px rgba(0,0,0,0.28)',
        };
        return (
          <button
            key={hotspot.id}
            ref={(element) => registerRef(hotspot.id, element)}
            type="button"
            className="hotspot-chip absolute flex h-8 w-8 items-center justify-center rounded-full border text-[13px] font-medium outline-none transition-[background-color,box-shadow,transform] duration-200 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-white/60"
            style={style}
            aria-label={`第 ${index + 1} 处：${hotspot.title}`}
            aria-pressed={isActive}
            onPointerEnter={() => onHover(hotspot.id)}
            onPointerLeave={() => onHover(null)}
            onFocus={() => onHover(hotspot.id)}
            onBlur={() => onHover(null)}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(hotspot.id);
            }}
          >
            {index + 1}
          </button>
        );
      })}
    </div>
  );
}

export default HotspotLayer;