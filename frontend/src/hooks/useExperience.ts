/**
 * 统一的体验读取入口：
 *  - 内置五件：同步命中，离线可用；
 *  - 运行期新作品：异步向 Case Service 取这件作品自己的 experience.json；
 *  - 加载中 / 不存在 / 数据损坏 三种状态分开返回，页面不白屏。
 */
import { useEffect, useState } from 'react';
import { getExperience } from '../data/experiences';
import { getRuntimeExperience, loadRuntimeExperience } from '../data/runtimeExperiences';
import type { CultureExperience } from '../features/culture-experience/types';

export type ExperienceLoadState = 'ready' | 'loading' | 'missing' | 'error';

export interface ExperienceLoadResult {
  experience: CultureExperience | undefined;
  state: ExperienceLoadState;
  retry: () => void;
}

export function useExperience(id: string | undefined): ExperienceLoadResult {
  const builtin = id ? getExperience(id) : undefined;
  const [experience, setExperience] = useState<CultureExperience | undefined>(
    builtin ?? getRuntimeExperience(id),
  );
  const [state, setState] = useState<ExperienceLoadState>(
    builtin || getRuntimeExperience(id) ? 'ready' : id ? 'loading' : 'missing',
  );
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!id) {
      setExperience(undefined);
      setState('missing');
      return;
    }
    const local = getExperience(id) ?? getRuntimeExperience(id);
    if (local) {
      setExperience(local);
      setState('ready');
      return;
    }

    let alive = true;
    setState('loading');
    loadRuntimeExperience(id).then((loaded) => {
      if (!alive) return;
      if (loaded) {
        setExperience(loaded);
        setState('ready');
      } else {
        setState('missing');
      }
    });
    return () => {
      alive = false;
    };
  }, [id, attempt]);

  return {
    experience,
    state,
    retry: () => setAttempt((value) => value + 1),
  };
}