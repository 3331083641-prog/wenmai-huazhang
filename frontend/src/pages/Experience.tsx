import { Link, useParams } from 'react-router-dom';
import { Loader2, RotateCcw } from 'lucide-react';
import { useExperience } from '../hooks/useExperience';
import CultureExperienceViewer from '../features/culture-experience/components/CultureExperienceViewer';
import ExperienceErrorBoundary from '../features/culture-experience/components/ExperienceErrorBoundary';

/** /experience/:id —— 「画中有话」互动页；运行期作品按 caseId 拉取自己的体验。 */
export function Experience() {
  const { id } = useParams();
  const { experience, state, retry } = useExperience(id);

  if (state === 'loading') {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center px-6 text-center">
        <Loader2 className="mb-4 h-6 w-6 animate-spin text-[color:var(--color-primary)]" />
        <p className="text-[13px] text-[color:var(--color-ink)]/60">
          正在读取这件作品自己的文化热点与解读……
        </p>
      </div>
    );
  }

  if (!experience) {
    return (
      <div className="mx-auto max-w-xl px-6 py-28 text-center">
        <p className="mb-3 text-[11px] tracking-[0.3em] text-[color:var(--color-ink)]/45">
          {state === 'error' ? '读取失败' : '未找到这一卷'}
        </p>
        <h1 className="mb-4 font-serif text-2xl text-[color:var(--color-ink)]">
          展厅里暂时没有「{id}」这件作品的画中有话
        </h1>
        <p className="mb-6 text-[13px] leading-relaxed text-[color:var(--color-ink)]/60">
          如果它刚刚生成，互动内容可能仍在后台构建；回到作品展厅可以看到实时状态。
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/gallery"
            className="inline-flex items-center rounded border border-[color:var(--color-gold)] px-5 py-2 text-sm text-[color:var(--color-primary)] transition hover:bg-[color:var(--color-primary)] hover:text-white"
          >
            返回作品展厅
          </Link>
          {state === 'error' && (
            <button
              type="button"
              onClick={retry}
              className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-4 py-2 text-sm text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
            >
              <RotateCcw size={14} />
              重试
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <ExperienceErrorBoundary fallbackLabel={experience.title}>
      <CultureExperienceViewer experience={experience} />
    </ExperienceErrorBoundary>
  );
}

export default Experience;