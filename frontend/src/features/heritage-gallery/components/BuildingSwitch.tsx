/**
 * 建筑风格切换面板。
 *
 * 交互取舍：
 *  - 常驻只占一个图标按钮，和「环境 / 帮助 / 沉浸」同级，不抢主入口；
 *  - 展开后是两张卡片，每张用「天空底色 + 建筑剪影」自绘缩略图，
 *    不额外加载图片资源，也不会因为截图过期而与实际建筑不符；
 *  - 切换中显示进度，卡片进入 loading 态；切换完成由页面统一收起遮罩。
 */

import type { JSX } from 'react';
import { Check, Landmark } from 'lucide-react';
import type { BuildingDef } from '../buildings';

interface BuildingSwitchProps {
  buildings: BuildingDef[];
  activeId: string;
  /** 正在切换的目标建筑 id（null 表示没有切换在途） */
  pendingId: string | null;
  /** 下载进度 0..1 */
  progress: number;
  onSelect: (id: string) => void;
  onHover?: (id: string) => void;
}

/** 一张建筑的缩略卡：渐变天空 + 简笔屋顶剪影 */
function BuildingThumb({ building, active }: { building: BuildingDef; active: boolean }): JSX.Element {
  const { sky, from, to, ink } = building.preview;
  return (
    <span
      className="relative block h-[52px] w-[76px] shrink-0 overflow-hidden rounded-[5px] ring-1 ring-black/10"
      style={{ background: `linear-gradient(180deg, ${sky} 0%, ${to} 100%)` }}
      aria-hidden
    >
      {/* 屋脊与屋檐：用两层三角/梯形拼出「重檐」轮廓 */}
      <svg viewBox="0 0 76 52" className="absolute inset-0 h-full w-full">
        <path d="M6 33 L38 19 L70 33 L66 36 L38 25 L10 36 Z" fill={ink} opacity="0.78" />
        <path d="M12 40 L38 29 L64 40 L60 43 L38 34 L16 43 Z" fill={ink} opacity="0.92" />
        <rect x="16" y="40" width="44" height="10" fill={from} opacity="0.95" />
        <rect x="34" y="35" width="8" height="15" fill={ink} opacity="0.55" />
      </svg>
      {active && (
        <span className="absolute right-1 top-1 grid h-4 w-4 place-items-center rounded-full bg-[color:var(--color-primary)] text-white shadow">
          <Check size={10} strokeWidth={3} />
        </span>
      )}
    </span>
  );
}

export function BuildingSwitch({
  buildings,
  activeId,
  pendingId,
  progress,
  onSelect,
  onHover,
}: BuildingSwitchProps): JSX.Element {
  return (
    <div className="w-full">
      <p className="mb-1.5 px-1 text-[9.5px] tracking-[0.22em] text-[color:var(--color-ink)]/40">
        建筑风格
      </p>
      <div className="space-y-1">
        {buildings.map((item) => {
          const active = item.id === activeId;
          const pending = item.id === pendingId;
          return (
            <button
              key={item.id}
              type="button"
              data-testid={`building-option-${item.id}`}
              aria-pressed={active}
              onMouseEnter={() => onHover?.(item.id)}
              onClick={() => onSelect(item.id)}
              className={`flex w-full items-center gap-2.5 rounded-lg border p-1.5 text-left transition ${
                active
                  ? 'border-[color:var(--color-primary)]/55 bg-[color:var(--color-primary)]/8'
                  : 'border-transparent hover:border-[color:var(--color-gold)]/45 hover:bg-black/[0.03]'
              }`}
            >
              <BuildingThumb building={item} active={active} />
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline gap-1.5">
                  <span
                    className={`text-[12.5px] font-medium ${
                      active ? 'text-[color:var(--color-primary)]' : 'text-[color:var(--color-ink)]/85'
                    }`}
                  >
                    {item.name}
                  </span>
                  {active && (
                    <span className="text-[9.5px] tracking-wide text-[color:var(--color-primary)]/70">当前</span>
                  )}
                </span>
                <span className="mt-0.5 block text-[10px] leading-snug text-[color:var(--color-ink)]/50">
                  {item.tagline}
                </span>
                {pending && (
                  <span className="mt-1 block h-[3px] w-full overflow-hidden rounded-full bg-black/10">
                    <span
                      className="block h-full rounded-full bg-[color:var(--color-primary)] transition-[width] duration-200"
                      style={{ width: `${Math.round(Math.max(0.06, progress) * 100)}%` }}
                    />
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>
      <p className="mt-2 border-t border-[color:var(--color-gold)]/25 px-1 pt-1.5 text-[10px] leading-snug text-[color:var(--color-ink)]/45">
        两座展馆是独立场景：画框与器物布展各自保存，来回切换不会互相覆盖。
      </p>
    </div>
  );
}

/** 右上角工具栏里的入口按钮图标，供页面复用，避免样式漂移 */
export const BUILDING_ICON = Landmark;