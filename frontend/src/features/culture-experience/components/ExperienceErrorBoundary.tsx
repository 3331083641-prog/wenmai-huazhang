import { Link } from 'react-router-dom';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  /** 出错时回退到的路径，默认回到展厅。 */
  fallbackHref?: string;
  fallbackLabel?: string;
}

interface State {
  error: Error | null;
}

/**
 * 体验页的数据/渲染兜底。
 * 校验失败时不要把整站打白屏，而是明确告诉用户「这一件暂时打不开」。
 */
export class ExperienceErrorBoundary extends Component<Props, State> {
  /** 仓库未安装 @types/react，这里显式声明 props 以获得类型提示。 */
  declare props: Props;

  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[culture-experience] 渲染失败', error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="mx-auto max-w-2xl px-6 py-24 text-center">
        <p className="mb-3 text-sm tracking-[0.3em] text-[color:var(--color-primary)]">体验暂时不可用</p>
        <h1 className="mb-4 font-serif text-2xl text-[color:var(--color-ink)]">
          这一卷《{this.props.fallbackLabel ?? '画境'}》未能加载
        </h1>
        <p className="mb-8 text-sm leading-relaxed text-[color:var(--color-ink)]/70">
          页面数据没有通过完整性校验，为避免展示错误的热点位置，这里主动停止渲染。
          你仍然可以回到展厅浏览其他作品。
        </p>
        <pre className="mb-8 max-h-40 overflow-auto rounded border border-[color:var(--color-gold)]/40 bg-white/60 p-3 text-left text-xs text-[color:var(--color-ink)]/60">
          {error.message}
        </pre>
        <Link
          to={this.props.fallbackHref ?? '/gallery'}
          className="inline-flex items-center gap-2 rounded border border-[color:var(--color-gold)] px-5 py-2 text-sm text-[color:var(--color-primary)] transition hover:bg-[color:var(--color-primary)] hover:text-white"
        >
          返回文化作品展厅
        </Link>
      </div>
    );
  }
}

export default ExperienceErrorBoundary;