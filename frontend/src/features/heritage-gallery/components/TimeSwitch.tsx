/**
 * 纹脉展馆 · 时段切换条（纯展示组件）
 *
 * 只接 value / onChange，不读任何全局状态——时段存哪儿由页面决定。
 * 视觉与站内左侧按钮组同款：宣纸底 + 1px 金边 + 圆角，
 * 横排三个等宽项，整条最宽 360px，可以直接摞在「模式 / 机位 / 工具」下面。
 */

import type { JSX } from 'react';
import { Moon, Sun, Sunset } from 'lucide-react';
import type { TimeOfDay } from '../scene/DayNightRig';

const TIME_OPTIONS: {
  id: TimeOfDay;
  label: string;
  hint: string;
  icon: typeof Sun;
}[] = [
  { id: 'day', label: '白天', hint: '中性日照，天光通透', icon: Sun },
  { id: 'dusk', label: '黄昏', hint: '低角度暖光，长影', icon: Sunset },
  { id: 'night', label: '夜晚', hint: '冷月光 + 暖色窗灯', icon: Moon },
];

export function TimeSwitch({
  value,
  onChange,
}: {
  value: TimeOfDay;
  onChange: (t: TimeOfDay) => void;
}): JSX.Element {
  return (
    <div
      role="group"
      aria-label="时段切换"
      className="pointer-events-auto inline-flex w-full max-w-[360px] items-center gap-1 rounded-lg border border-[rgba(190,150,90,0.45)] bg-[rgba(251,246,235,0.92)] p-1 backdrop-blur-md"
    >
      {TIME_OPTIONS.map((option) => {
        const Icon = option.icon;
        const active = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            title={option.hint}
            aria-label={`${option.label}（${option.hint}）`}
            aria-pressed={active}
            onClick={() => onChange(option.id)}
            className={`inline-flex min-w-0 flex-1 items-center justify-center gap-1 rounded px-2 py-1 text-[11.5px] transition ${
              active
                ? 'bg-[#9E241B] text-white'
                : 'text-[#3F2B1F]/65 hover:bg-black/5 hover:text-[#3F2B1F]'
            }`}
          >
            <Icon size={11} className="shrink-0" aria-hidden />
            <span className="truncate">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}