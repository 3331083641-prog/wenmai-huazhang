import { resolveSources } from '../../../data/experiences';

interface SourceChipsProps {
  sourceIds: string[];
  /** compact 用于面板，full 用于章节页底部。 */
  variant?: 'compact' | 'full';
}

/**
 * 来源标注：每个文化解释都要能点回机构页面。
 * 只渲染已核验来源；未核验的明确标注，绝不伪装成可靠出处。
 */
export function SourceChips({ sourceIds, variant = 'compact' }: SourceChipsProps) {
  const sources = resolveSources(sourceIds);
  if (sources.length === 0) return null;

  return (
    <ul className={variant === 'compact' ? 'flex flex-wrap gap-1.5' : 'space-y-2'}>
      {sources.map((source) => (
        <li key={source.id}>
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer noopener"
            className="group inline-flex max-w-full items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/50 px-2.5 py-1 text-[11px] leading-tight text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
            title={`${source.publisher}：${source.title}`}
          >
            <span className="h-1 w-1 shrink-0 rounded-full bg-[color:var(--color-gold)]" aria-hidden="true" />
            <span className="truncate">{source.publisher}</span>
            {source.verification === 'unverified' && (
              <span className="rounded bg-amber-100 px-1 text-[10px] text-amber-800">未核验</span>
            )}
            <span className="text-[10px] opacity-60 group-hover:opacity-100" aria-hidden="true">
              ↗
            </span>
          </a>
        </li>
      ))}
    </ul>
  );
}

export default SourceChips;