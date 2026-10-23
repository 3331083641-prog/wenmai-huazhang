import { useParams } from 'react-router-dom';
import { getExperience } from '../data/experiences';
import CultureExperienceViewer from '../features/culture-experience/components/CultureExperienceViewer';
import ExperienceErrorBoundary from '../features/culture-experience/components/ExperienceErrorBoundary';

/** /experience/:id —— 「画中有话」互动油画页。 */
export function Experience() {
  const { id } = useParams();
  const experience = getExperience(id);

  if (!experience) {
    return (
      <div className="mx-auto max-w-xl px-6 py-28 text-center">
        <p className="mb-3 text-[11px] tracking-[0.3em] text-[color:var(--color-ink)]/45">未找到这一卷</p>
        <h1 className="mb-5 font-serif text-2xl text-[color:var(--color-ink)]">
          展厅里暂时没有「{id}」这件作品
        </h1>
        <a
          href="/gallery"
          className="inline-flex items-center rounded border border-[color:var(--color-gold)] px-5 py-2 text-sm text-[color:var(--color-primary)] transition hover:bg-[color:var(--color-primary)] hover:text-white"
        >
          返回文化作品展厅
        </a>
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