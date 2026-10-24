/**
 * 布展方案持久化。
 *
 * 只存「画框挂了什么 + 画框被拖到哪」，不存场景几何：
 * 几何在配置里是常量，改配置后旧的布展方案仍然有效。
 *
 * 用 localStorage 而不是后端：布展是个人偏好，不需要跨设备，也不需要账号。
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { frameSlots, frameById, wallById, clampToWall } from '../../../data/heritageGalleryConfig';
import { findArtwork } from '../../../data/artworkRegistry';

export interface CurationStore {
  /** frameId -> artworkId */
  assignments: Record<string, string>;
  /** frameId -> 归一化位置 */
  positions: Record<string, { u: number; v: number }>;
  /** 当前选中的画框（打开图库面板） */
  selectedFrameId: string | null;
  /** 当前查看详情的作品 */
  detailArtworkId: string | null;

  selectFrame: (frameId: string | null) => void;
  assignArtwork: (frameId: string, artworkId: string) => void;
  clearFrame: (frameId: string) => void;
  moveFrame: (frameId: string, u: number, v: number) => void;
  resetFrame: (frameId: string) => void;
  resetAll: () => void;
  openDetail: (artworkId: string | null) => void;
}

/** 默认布展方案：来自配置里的 defaultArtworkId */
export function defaultAssignments(): Record<string, string> {
  const result: Record<string, string> = {};
  for (const frame of frameSlots) {
    result[frame.id] = frame.defaultArtworkId;
  }
  return result;
}

/** 默认位置 */
export function defaultPositions(): Record<string, { u: number; v: number }> {
  const result: Record<string, { u: number; v: number }> = {};
  for (const frame of frameSlots) {
    result[frame.id] = { u: frame.u, v: frame.v };
  }
  return result;
}

/**
 * 读取某个画框当前的挂画。
 * 显式清空（空字符串）与「从未设置」要区分：前者用户主动留白。
 */
export function resolveArtworkId(assignments: Record<string, string>, frameId: string): string {
  if (frameId in assignments) return assignments[frameId];
  return frameById.get(frameId)?.defaultArtworkId ?? '';
}

export const useCurationStore = create<CurationStore>()(
  persist(
    (set, get) => ({
      assignments: defaultAssignments(),
      positions: defaultPositions(),
      selectedFrameId: null,
      detailArtworkId: null,

      selectFrame: (frameId) => set({ selectedFrameId: frameId }),

      assignArtwork: (frameId, artworkId) => {
        // 只接受已注册的作品（精选 + 运行期 Case Service 拉取到的），
        // 防止持久化数据里塞入无效 id。
        if (artworkId && !findArtwork(artworkId)) return;
        set((state) => ({
          assignments: { ...state.assignments, [frameId]: artworkId },
        }));
      },

      clearFrame: (frameId) => {
        set((state) => ({
          assignments: { ...state.assignments, [frameId]: '' },
        }));
      },

      moveFrame: (frameId, u, v) => {
        const frame = frameById.get(frameId);
        if (!frame) return;
        const wall = wallById.get(frame.wallId);
        if (!wall) return;
        const clamped = clampToWall(wall, frame.size, u, v);
        set((state) => ({
          positions: { ...state.positions, [frameId]: clamped },
        }));
      },

      resetFrame: (frameId) => {
        const frame = frameById.get(frameId);
        if (!frame) return;
        set((state) => ({
          assignments: { ...state.assignments, [frameId]: frame.defaultArtworkId },
          positions: { ...state.positions, [frameId]: { u: frame.u, v: frame.v } },
        }));
      },

      resetAll: () =>
        set({
          assignments: defaultAssignments(),
          positions: defaultPositions(),
          selectedFrameId: null,
          detailArtworkId: null,
        }),

      openDetail: (artworkId) => set({ detailArtworkId: artworkId }),
    }),
    {
      name: 'wenmai-heritage-gallery-v1',
      storage: createJSONStorage(() => localStorage),
      // 只持久化布展数据；选中态是瞬时的，刷新后应清空
      partialize: (state) => ({
        assignments: state.assignments,
        positions: state.positions,
      }),
      version: 1,
      migrate: (persisted, version) => {
        // 版本升级时用默认方案兜底，避免旧结构把画框渲染到墙外
        if (version !== 1) {
          return { assignments: defaultAssignments(), positions: defaultPositions() };
        }
        return persisted as { assignments: Record<string, string>; positions: Record<string, { u: number; v: number }> };
      },
    },
  ),
);
