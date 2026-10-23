import { Link } from 'react-router-dom';
import { BookOpen, Compass, Image as ImageIcon } from 'lucide-react';
import type { CultureExperience } from '../types';

/**
 * 「互动画境 / 一图一境 / 画境漫游」三入口切换条。
 *
 * 为什么要有它：这三条路讲的是同一件作品，之前只有「互动画境 ↔ 一图一境」互链，
 * 进了画境就只能退回首页；用户进来以后没法在原作线索、三折叙事、画中漫游之间来回换。
 * 现在三个页面顶部都挂同一条，任何一页都能一键切到另外两页，当前页高亮。
 */
export type ExperienceMode = 'experience' | 'story' | 'wander';

const MODES = [
  {
    key: 'experience' as const,
    label: '互动画境',
    hint: '在原作上逐处读线索',
    Icon: ImageIcon,
  },
  {
    key: 'story' as const,
    label: '一图一境',
    hint: '三折叙事，滚动换镜头',
    Icon: BookOpen,
  },
  {
    key: 'wander' as const,
    label: '画境漫游',
    hint: '走进画里，拖拽观察',
    Icon: Compass,
  },
];

export function hasWanderMode(animation: CultureExperience['animation']): boolean {
  return animation.mode === 'world' && Boolean(animation.world?.url);
}

type ExperienceModeSwitchProps = {
  experienceId: string;
  current: ExperienceMode;
  hasWorld?: boolean;
  /** inline 用于纸面页面；overlay 用于画境里的深色浮层 */
  variant?: 'inline' | 'overlay';
  className?: string;
};

export function ExperienceModeSwitch({
  experienceId,
  current,
  hasWorld = true,
  variant = 'inline',
  className = '',
}: ExperienceModeSwitchProps) {
  const overlay = variant === 'overlay';
  return (
    <nav
      aria-label="换一种看法"
      className={[
        'flex items-center gap-0.5 rounded-full border p-0.5',
        overlay
          ? 'border-white/25 bg-black/35 backdrop-blur-md'
          : 'border-[color:var(--color-gold)]/45 bg-white/55',
        className,
      ].join(' ')}
    >
      {MODES.map(({ key, label, hint, Icon }) => {
        const active = key === current;
        const available = key !== 'wander' || hasWorld;
        const base =
          'inline-flex items-center gap-1 rounded-full px-2.5 py-1.5 text-[12px] transition';

        if (!available) {
          return (
            <span
              key={key}
              title="这件作品还没有画境资产"
              aria-disabled="true"
              className={[
                base,
                'cursor-not-allowed',
                overlay ? 'text-white/30' : 'text-[color:var(--color-ink)]/28',
              ].join(' ')}
            >
              <Icon size={13} />
              {label}
            </span>
          );
        }

        if (active) {
          return (
            <span
              key={key}
              aria-current="page"
              title={hint}
              className={[
                base,
                overlay
                  ? 'bg-white/92 font-medium text-[color:var(--color-ink)]'
                  : 'bg-[color:var(--color-primary)] font-medium text-white',
              ].join(' ')}
            >
              <Icon size={13} />
              {label}
            </span>
          );
        }

        return (
          <Link
            key={key}
            to={`/${key}/${experienceId}`}
            title={hint}
            className={[
              base,
              overlay
                ? 'text-white/80 hover:bg-white/15 hover:text-white'
                : 'text-[color:var(--color-ink)]/65 hover:bg-white hover:text-[color:var(--color-primary)]',
            ].join(' ')}
          >
            <Icon size={13} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export default ExperienceModeSwitch;