/**
 * 布展方案持久化（双馆分桶）。
 *
 * 只存「画框挂了什么 + 画框被拖到哪」，不存场景几何：
 * 几何在各自建筑的 layout 里是常量，改配置后旧的布展方案仍然有效。
 *
 * 分桶规则：
 *  - `plans[buildingId]` 一座建筑一份方案，切换建筑时互不影响；
 *  - 画框 id 在两馆里各自独立（经典 15 个、华章 24 个），每个 id 只在它所属
 *    建筑的 config 里解析，所以不会出现「切馆后画框跑到墙外」的错位；
 *  - 旧版本（v1，只有一份 assignments/positions）在迁移时整体落进 classic 桶，
 *    老用户升级后打开经典馆，布展原样还在。
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { findArtwork } from '../../../data/artworkRegistry';
import { getBuilding } from '../buildings';
import { activeBuildingId, useBuildingStore } from './buildingStore';

export interface CurationPlan {
  /** frameId -> artworkId */
  assignments: Record<string, string>;
  /** frameId -> 归一化位置 */
  positions: Record<string, { u: number; v: number }>;
}

export interface CurationStore {
  /** buildingId -> 该馆的布展方案 */
  plans: Record<string, CurationPlan>;
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

const EMPTY_PLAN: CurationPlan = { assignments: {}, positions: {} };

/** 取某个建筑的方案；没有就按它的 layout 生成默认方案 */
export function planFor(plans: Record<string, CurationPlan>, buildingId: string): CurationPlan {
  const existing = plans[buildingId];
  if (existing) return existing;
  const config = getBuilding(buildingId).config;
  return { assignments: config.defaultAssignments(), positions: config.defaultPositions() };
}

/** 默认布展方案（默认当前建筑，也可显式指定） */
export function defaultAssignments(buildingId = activeBuildingId()): Record<string, string> {
  return getBuilding(buildingId).config.defaultAssignments();
}

/** 默认位置（默认当前建筑，也可显式指定） */
export function defaultPositions(
  buildingId = activeBuildingId(),
): Record<string, { u: number; v: number }> {
  return getBuilding(buildingId).config.defaultPositions();
}

/**
 * 读取某个画框当前的挂画。
 * 显式清空（空字符串）与「从未设置」要区分：前者是用户主动留白。
 */
export function resolveArtworkId(
  assignments: Record<string, string>,
  frameId: string,
  buildingId = activeBuildingId(),
): string {
  if (frameId in assignments) return assignments[frameId];
  return getBuilding(buildingId).config.frameById.get(frameId)?.defaultArtworkId ?? '';
}

/** 当前建筑的布展方案（React 订阅） */
export function useActivePlan(): CurationPlan {
  const plans = useCurationStore((state) => state.plans);
  const active = useBuildingStore((state) => state.active);
  return plans[active] ?? EMPTY_PLAN;
}

export const useCurationStore = create<CurationStore>()(
  persist(
    (set) => ({
      plans: {},
      selectedFrameId: null,
      detailArtworkId: null,

      selectFrame: (frameId) => set({ selectedFrameId: frameId }),

      assignArtwork: (frameId, artworkId) => {
        // 只接受已注册的作品（精选 + 运行期 Case Service 拉取到的），
        // 防止持久化数据里塞入无效 id。
        if (artworkId && !findArtwork(artworkId)) return;
        const buildingId = activeBuildingId();
        if (!getBuilding(buildingId).config.frameById.has(frameId)) return;
        set((state) => {
          const plan = planFor(state.plans, buildingId);
          return {
            plans: {
              ...state.plans,
              [buildingId]: {
                ...plan,
                assignments: { ...plan.assignments, [frameId]: artworkId },
              },
            },
          };
        });
      },

      clearFrame: (frameId) => {
        const buildingId = activeBuildingId();
        if (!getBuilding(buildingId).config.frameById.has(frameId)) return;
        set((state) => {
          const plan = planFor(state.plans, buildingId);
          return {
            plans: {
              ...state.plans,
              [buildingId]: {
                ...plan,
                assignments: { ...plan.assignments, [frameId]: '' },
              },
            },
          };
        });
      },

      moveFrame: (frameId, u, v) => {
        const buildingId = activeBuildingId();
        const config = getBuilding(buildingId).config;
        const frame = config.frameById.get(frameId);
        if (!frame) return;
        const wall = config.wallById.get(frame.wallId);
        if (!wall) return;
        const clamped = config.clampToWall(wall, frame.size, u, v);
        set((state) => {
          const plan = planFor(state.plans, buildingId);
          return {
            plans: {
              ...state.plans,
              [buildingId]: {
                ...plan,
                positions: { ...plan.positions, [frameId]: clamped },
              },
            },
          };
        });
      },

      resetFrame: (frameId) => {
        const buildingId = activeBuildingId();
        const config = getBuilding(buildingId).config;
        const frame = config.frameById.get(frameId);
        if (!frame) return;
        set((state) => {
          const plan = planFor(state.plans, buildingId);
          return {
            plans: {
              ...state.plans,
              [buildingId]: {
                ...plan,
                assignments: { ...plan.assignments, [frameId]: frame.defaultArtworkId },
                positions: { ...plan.positions, [frameId]: { u: frame.u, v: frame.v } },
              },
            },
          };
        });
      },

      /** 只重置当前建筑，另一座馆的布展原样保留 */
      resetAll: () => {
        const buildingId = activeBuildingId();
        const config = getBuilding(buildingId).config;
        set((state) => ({
          plans: {
            ...state.plans,
            [buildingId]: {
              assignments: config.defaultAssignments(),
              positions: config.defaultPositions(),
            },
          },
          selectedFrameId: null,
          detailArtworkId: null,
        }));
      },

      openDetail: (artworkId) => set({ detailArtworkId: artworkId }),
    }),
    {
      name: 'wenmai-heritage-gallery-v2',
      storage: createJSONStorage(() => localStorage),
      // 只持久化布展数据；选中态是瞬时的，刷新后应清空
      partialize: (state) => ({ plans: state.plans }),
      version: 2,
      migrate: (persisted, version) => {
        const legacy = persisted as
          | {
              assignments?: Record<string, string>;
              positions?: Record<string, { u: number; v: number }>;
              plans?: Record<string, CurationPlan>;
            }
          | undefined;
        if (version >= 2 && legacy?.plans) {
          return { plans: legacy.plans };
        }
        // v1：单份方案，属于经典馆
        if (legacy?.assignments) {
          return {
            plans: {
              classic: {
                assignments: legacy.assignments,
                positions: legacy.positions ?? {},
              },
            },
          };
        }
        return { plans: {} };
      },
    },
  ),
);

/** 旧版 localStorage key：仅用于排查迁移问题，不参与运行时逻辑 */
export const LEGACY_CURATION_KEY = 'wenmai-heritage-gallery-v1';