/**
 * 纹脉展馆 · 视角切换条（纯展示组件）
 *
 * 只接 value / onChange，机位怎么切（轨道 / 电影 / 第一人称）由场景与相机实现。
 * 与 TimeSwitch 同款外观：宣纸底、1px 金边、选中朱红，最宽 360px 可横排。
 */

import type { JSX } from 'react';
import { Clapperboard, Orbit, PersonStanding } from 'lucide-react';

export type ViewMode = 'third' | 'cinema' | 'first';

export interface ViewModeDef {
  id: ViewMode;
  label: string;
  hint: string;
}

export const VIEW_MODES: ViewModeDef[] = [
  { id: 'third', label: '第三人称', hint: '绕建筑自由环绕，可缩放' },
  { id: 'cinema', label: '电影', hint: '低机位长焦，缓慢推拉的叙事镜头' },
  { id: 'first', label: '第一人称', hint: '站在展厅内部平视漫游' },
];

const VIEW_ICONS: Record<ViewMode, typeof Orbit> = {
  third: Orbit,
  cinema: Clapperboard,
  first: PersonStanding,
};

export function ViewModeSwitch({
  value,
  onChange,
}: {
  value: ViewMode;
  onChange: (m: ViewMode) => void;
}): JSX.Element {
  return (
    <div
      role="group"
      aria-label="视角切换"
      className="pointer-events-auto inline-flex w-full max-w-[360px] items-center gap-1 rounded-lg border border-[rgba(190,150,90,0.45)] bg-[rgba(251,246,235,0.92)] p-1 backdrop-blur-md"
    >
      {VIEW_MODES.map((mode) => {
        const Icon = VIEW_ICONS[mode.id];
        const active = mode.id === value;
        return (
          <button
            key={mode.id}
            type="button"
            title={mode.hint}
            aria-label={`${mode.label}（${mode.hint}）`}
            aria-pressed={active}
            onClick={() => onChange(mode.id)}
            className={`inline-flex min-w-0 flex-1 items-center justify-center gap-1 rounded px-2 py-1 text-[11.5px] transition ${
              active
                ? 'bg-[#9E241B] text-white'
                : 'text-[#3F2B1F]/65 hover:bg-black/5 hover:text-[#3F2B1F]'
            }`}
          >
            <Icon size={11} className="shrink-0" aria-hidden />
            <span className="truncate">{mode.label}</span>
          </button>
        );
      })}
    </div>
  );
}