/**
 * DIY 布展状态（双馆分桶）：器物实例、选中态、屋顶瓦色。
 *
 * 只持久化「摆了哪些东西、摆在哪、什么颜色」，不存几何：
 * 器物定义在 scene/props/catalog，改器物样式后旧布展仍然有效。
 * 与 curationStore（画框布展）分开存 key，互不影响。
 *
 * 分桶：`byBuilding[buildingId] = { items, roofTint }`
 *  - 切换建筑时各馆器物互不影响，坐标也不会跨馆串用；
 *  - 旧版本（v1，顶层 items/roofTint）迁移后落进 classic 桶。
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { getPropDef } from '../props/assets/assetProps';
import { activeBuildingId, useBuildingStore } from './buildingStore';

export interface DiyItem {
  key: string;
  propId: string;
  x: number;
  y: number;
  z: number;
  rotY: number;
  scale: number;
  variant: number;
  mount: 'ground' | 'wall';
  /** 非遗器物的互动状态（灯亮/门开），随布展一起持久化 */
  interactionState?: { active?: boolean } | null;
  /** 承载物实例 key（放在博古架/展柜上时记录） */
  parentInstanceId?: string;
  /** 承载面来源：已摆器物 key / 模型网格名 / 梁架锚点 */
  carrier?: string;
  /** 摆放面：1F / 2F 地面、桌面、梁架悬挂 */
  surfaceId?: string;
  floor?: 1 | 2;
  schemaVersion?: number;
}

export interface RoofTintDef {
  id: string;
  name: string;
  color: string;
}

export interface BuildingDiy {
  items: DiyItem[];
  roofTint: string;
}

/** 屋顶瓦色：都是古建可用的几种，不做高饱和色 */
export const ROOF_TINTS: RoofTintDef[] = [
  { id: 'dai', name: '黛瓦', color: '#4A5A61' },
  { id: 'qing', name: '青灰', color: '#5E6C74' },
  { id: 'yuebai', name: '月白', color: '#A8B4B9' },
  { id: 'liuli', name: '琉璃', color: '#B08A46' },
  { id: 'shan', name: '赭石', color: '#7A4E3C' },
];

const DEFAULT_TINT = 'dai';

interface DiyState {
  /** buildingId -> 该馆的器物布展 */
  byBuilding: Record<string, BuildingDiy>;
  selectedKey: string | null;
  /** 面板里点中、等待落位的器物 id */
  pendingPropId: string | null;
  panelOpen: boolean;
  /** 从面板拖到画面后的一次性落位请求（屏幕坐标） */
  dropRequest: { propId: string; clientX: number; clientY: number } | null;

  /** 当前建筑的器物列表（非 React 环境读取用） */
  current: () => BuildingDiy;
  addItem: (item: DiyItem) => void;
  updateItem: (key: string, patch: Partial<DiyItem>) => void;
  removeItem: (key: string) => void;
  selectItem: (key: string | null) => void;
  setPending: (propId: string | null) => void;
  setPanelOpen: (open: boolean) => void;
  setRoofTint: (id: string) => void;
  setDropRequest: (request: { propId: string; clientX: number; clientY: number } | null) => void;
  clearItems: () => void;
  resetAll: () => void;
  /** 编辑模式：只有开编辑时才允许拖动/缩放已摆器物，平时点击=互动 */
  editMode: boolean;
  setEditMode: (on: boolean) => void;
  /** 悬停提示：鼠标停在已摆器物上时告诉页面「点击可互动」 */
  hoverAssetKey: string | null;
  hoverAssetName: string;
  setHoverAsset: (key: string | null, name?: string) => void;
  /** A09 展签架弹出的文化解读卡 */
  infoAssetId: string | null;
  setInfoAsset: (id: string | null) => void;
  /** 落位失败/降级的一句话提示（自动消失） */
  placeHint: string;
  setPlaceHint: (text: string) => void;
  /** 右键菜单：定位到某件已摆器物，可直接删除 */
  contextMenu: { key: string; name: string; x: number; y: number } | null;
  openContextMenu: (menu: { key: string; name: string; x: number; y: number }) => void;
  closeContextMenu: () => void;
}

let seq = 0;
function newKey(): string {
  seq += 1;
  return `diy-${Date.now().toString(36)}-${seq}`;
}

/** 取某座馆的布展桶（没有就建空的） */
function bucketOf(byBuilding: Record<string, BuildingDiy>, buildingId: string): BuildingDiy {
  return byBuilding[buildingId] ?? { items: [], roofTint: DEFAULT_TINT };
}

/** 写回某座馆的桶 */
function withBucket(
  byBuilding: Record<string, BuildingDiy>,
  buildingId: string,
  patch: Partial<BuildingDiy>,
): Record<string, BuildingDiy> {
  return { ...byBuilding, [buildingId]: { ...bucketOf(byBuilding, buildingId), ...patch } };
}

export function makeItem(
  propId: string,
  x: number,
  y: number,
  z: number,
  rotY = 0,
  variant = 0,
): DiyItem | null {
  const def = getPropDef(propId);
  if (!def) return null;
  return {
    key: newKey(),
    propId,
    x,
    y,
    z,
    rotY,
    scale: 1,
    variant,
    mount: def.mount,
  };
}

export const useDiyStore = create<DiyState>()(
  persist(
    (set, get) => ({
      byBuilding: {},
      selectedKey: null,
      pendingPropId: null,
      panelOpen: false,
      dropRequest: null,

      current: () => bucketOf(get().byBuilding, activeBuildingId()),

      addItem: (item) => {
        const buildingId = activeBuildingId();
        set((state) => {
          const bucket = bucketOf(state.byBuilding, buildingId);
          return {
            byBuilding: withBucket(state.byBuilding, buildingId, { items: [...bucket.items, item] }),
            selectedKey: item.key,
            pendingPropId: null,
          };
        });
      },

      updateItem: (key, patch) => {
        const buildingId = activeBuildingId();
        set((state) => {
          const bucket = bucketOf(state.byBuilding, buildingId);
          const target = bucket.items.find((item) => item.key === key);
          if (!target) return {};
          const next = { ...target, ...patch };
          const hasChild = bucket.items.some((item) => item.parentInstanceId === key);
          const dx = next.x - target.x;
          const dy = next.y - target.y;
          const dz = next.z - target.z;
          const drot = next.rotY - target.rotY;
          if (!hasChild || (!dx && !dy && !dz && !drot)) {
            return {
              byBuilding: withBucket(state.byBuilding, buildingId, {
                items: bucket.items.map((item) => (item.key === key ? next : item)),
              }),
            };
          }
          // 承载物移动/转动时，子物件保持相对位置一起走（吸附在顶面的器物不会掉在原地）
          const cos = Math.cos(drot);
          const sin = Math.sin(drot);
          const items = bucket.items.map((item) => {
            if (item.key === key) return next;
            if (item.parentInstanceId !== key) return item;
            const ox = item.x - target.x;
            const oz = item.z - target.z;
            return {
              ...item,
              x: next.x + ox * cos - oz * sin,
              y: item.y + dy,
              z: next.z + ox * sin + oz * cos,
              rotY: item.rotY + drot,
            };
          });
          return { byBuilding: withBucket(state.byBuilding, buildingId, { items }) };
        });
      },

      removeItem: (key) => {
        const buildingId = activeBuildingId();
        set((state) => {
          const bucket = bucketOf(state.byBuilding, buildingId);
          const doomed = new Set([key]);
          // 承载物被删掉时，摆在它上面的器物一并移除，避免留下悬空件
          let grew = true;
          while (grew) {
            grew = false;
            for (const item of bucket.items) {
              if (doomed.has(item.key)) continue;
              if (item.parentInstanceId && doomed.has(item.parentInstanceId)) {
                doomed.add(item.key);
                grew = true;
              }
            }
          }
          return {
            byBuilding: withBucket(state.byBuilding, buildingId, {
              items: bucket.items.filter((item) => !doomed.has(item.key)),
            }),
            selectedKey: state.selectedKey && doomed.has(state.selectedKey) ? null : state.selectedKey,
          };
        });
      },

      selectItem: (key) => set({ selectedKey: key, pendingPropId: null }),
      setPending: (propId) => set({ pendingPropId: propId, panelOpen: true }),
      setPanelOpen: (open) => set({ panelOpen: open }),

      setRoofTint: (id) => {
        const buildingId = activeBuildingId();
        set((state) => ({
          byBuilding: withBucket(state.byBuilding, buildingId, { roofTint: id }),
        }));
      },

      setDropRequest: (request) => set({ dropRequest: request }),

      /** 只清空当前建筑的器物 */
      clearItems: () => {
        const buildingId = activeBuildingId();
        set((state) => ({
          byBuilding: withBucket(state.byBuilding, buildingId, { items: [] }),
          selectedKey: null,
        }));
      },

      /** 只重置当前建筑（器物 + 瓦色），另一座馆原样保留 */
      resetAll: () => {
        const buildingId = activeBuildingId();
        set((state) => ({
          byBuilding: withBucket(state.byBuilding, buildingId, { items: [], roofTint: DEFAULT_TINT }),
          selectedKey: null,
          pendingPropId: null,
        }));
      },

      editMode: false,
      setEditMode: (on) => set({ editMode: on, pendingPropId: null }),
      hoverAssetKey: null,
      hoverAssetName: '',
      setHoverAsset: (key, name = '') => set({ hoverAssetKey: key, hoverAssetName: name }),
      infoAssetId: null,
      setInfoAsset: (id) => set({ infoAssetId: id }),
      contextMenu: null,
      openContextMenu: (menu) => set({ contextMenu: menu, selectedKey: menu.key, pendingPropId: null }),
      closeContextMenu: () => set({ contextMenu: null }),
      placeHint: '',
      setPlaceHint: (text) => set({ placeHint: text }),
    }),
    {
      name: 'wenmai-gallery-diy-v2',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ byBuilding: state.byBuilding }),
      version: 2,
      migrate: (persisted, version) => {
        const legacy = persisted as
          | { items?: DiyItem[]; roofTint?: string; byBuilding?: Record<string, BuildingDiy> }
          | undefined;
        if (version >= 2 && legacy?.byBuilding) return { byBuilding: legacy.byBuilding };
        // v1：单份器物表，属于经典馆
        if (legacy && Array.isArray(legacy.items)) {
          return {
            byBuilding: {
              classic: { items: legacy.items, roofTint: legacy.roofTint ?? DEFAULT_TINT },
            },
          };
        }
        return { byBuilding: {} };
      },
    },
  ),
);

/* ---------------------------------------------------------------- 订阅 hooks */

/** 当前建筑的器物列表 */
export function useDiyItems(): DiyItem[] {
  const byBuilding = useDiyStore((state) => state.byBuilding);
  const active = useBuildingStore((state) => state.active);
  return byBuilding[active]?.items ?? EMPTY_ITEMS;
}

/** 当前建筑的屋顶瓦色 */
export function useRoofTint(): string {
  const byBuilding = useDiyStore((state) => state.byBuilding);
  const active = useBuildingStore((state) => state.active);
  return byBuilding[active]?.roofTint ?? DEFAULT_TINT;
}

/** 当前建筑的器物数量 */
export function useDiyCount(): number {
  return useDiyItems().length;
}

const EMPTY_ITEMS: DiyItem[] = [];