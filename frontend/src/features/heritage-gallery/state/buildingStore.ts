/**
 * 当前建筑皮肤：全局唯一来源。
 *
 * 为什么单独开一个 store：
 *  建筑选择是「整个展馆的上下文」，curationStore（画框布展）和 diyStore（器物布展）
 *  都要按它分桶。放在这里，两边都只依赖这一个值，不会出现两个 store 各自记一套。
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { BUILDINGS, DEFAULT_BUILDING_ID, getBuilding, isKnownBuilding, type BuildingDef, type BuildingId } from '../buildings';

interface BuildingState {
  active: BuildingId;
  setActive: (id: BuildingId) => void;
}

export const useBuildingStore = create<BuildingState>()(
  persist(
    (set) => ({
      active: DEFAULT_BUILDING_ID,
      setActive: (id) => set({ active: isKnownBuilding(id) ? id : DEFAULT_BUILDING_ID }),
    }),
    {
      name: 'wenmai-gallery-building-v1',
      storage: createJSONStorage(() => localStorage),
      // 以后删掉某个建筑皮肤时，旧持久化数据不能把页面卡在一个不存在的 id 上
      merge: (persisted, current) => {
        const next = persisted as Partial<BuildingState> | undefined;
        return {
          ...current,
          active: isKnownBuilding(next?.active) ? (next?.active as string) : current.active,
        };
      },
    },
  ),
);

/** 非 React 环境（store / 事件回调 / 射线回调）里取当前建筑 */
export function activeBuildingId(): string {
  return useBuildingStore.getState().active;
}

export function activeBuilding(): BuildingDef {
  return getBuilding(activeBuildingId());
}

/** 给面板做「有哪些馆可切」的列表 */
export function buildingChoices(): BuildingDef[] {
  return BUILDINGS;
}