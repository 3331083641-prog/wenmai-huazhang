/**
 * DIY 布展状态：器物实例、选中态、屋顶瓦色。
 *
 * 只持久化「摆了哪些东西、摆在哪、什么颜色」，不存几何：
 * 器物定义在 scene/props/catalog，改器物样式后旧布展仍然有效。
 * 与 curationStore（画框布展）分开存 key，互不影响。
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { getPropDef } from '../props/assets/assetProps';

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

/** 屋顶瓦色：都是古建可用的几种，不做高饱和色 */
export const ROOF_TINTS: RoofTintDef[] = [
  { id: 'dai', name: '黛瓦', color: '#4A5A61' },
  { id: 'qing', name: '青灰', color: '#5E6C74' },
  { id: 'yuebai', name: '月白', color: '#A8B4B9' },
  { id: 'liuli', name: '琉璃', color: '#B08A46' },
  { id: 'shan', name: '赭石', color: '#7A4E3C' },
];

interface DiyState {
  items: DiyItem[];
  selectedKey: string | null;
  /** 面板里点中、等待落位的器物 id */
  pendingPropId: string | null;
  panelOpen: boolean;
  roofTint: string;
  /** 从面板拖到画面后的一次性落位请求（屏幕坐标） */
  dropRequest: { propId: string; clientX: number; clientY: number } | null;

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
    (set) => ({
      items: [],
      selectedKey: null,
      pendingPropId: null,
      panelOpen: false,
      roofTint: 'dai',
      dropRequest: null,

      addItem: (item) => set((state) => ({ items: [...state.items, item], selectedKey: item.key, pendingPropId: null })),
      updateItem: (key, patch) =>
        set((state) => {
          const target = state.items.find((item) => item.key === key);
          if (!target) return {};
          const next = { ...target, ...patch };
          const hasChild = state.items.some((item) => item.parentInstanceId === key);
          const dx = next.x - target.x;
          const dy = next.y - target.y;
          const dz = next.z - target.z;
          const drot = next.rotY - target.rotY;
          if (!hasChild || (!dx && !dy && !dz && !drot)) {
            return { items: state.items.map((item) => (item.key === key ? next : item)) };
          }
          // 承载物移动/转动时，子物件保持相对位置一起走（吸附在顶面的器物不会掉在原地）
          const cos = Math.cos(drot);
          const sin = Math.sin(drot);
          return {
            items: state.items.map((item) => {
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
            }),
          };
        }),
      removeItem: (key) =>
        set((state) => {
          const doomed = new Set([key]);
          // 承载物被删掉时，摆在它上面的器物一并移除，避免留下悬空件
          let grew = true;
          while (grew) {
            grew = false;
            for (const item of state.items) {
              if (doomed.has(item.key)) continue;
              if (item.parentInstanceId && doomed.has(item.parentInstanceId)) {
                doomed.add(item.key);
                grew = true;
              }
            }
          }
          return {
            items: state.items.filter((item) => !doomed.has(item.key)),
            selectedKey: state.selectedKey && doomed.has(state.selectedKey) ? null : state.selectedKey,
          };
        }),
      selectItem: (key) => set({ selectedKey: key, pendingPropId: null }),
      setPending: (propId) => set({ pendingPropId: propId, panelOpen: true }),
      setPanelOpen: (open) => set({ panelOpen: open }),
      setRoofTint: (id) => set({ roofTint: id }),
      setDropRequest: (request) => set({ dropRequest: request }),
      clearItems: () => set({ items: [], selectedKey: null }),
      resetAll: () =>
        set({ items: [], selectedKey: null, pendingPropId: null, roofTint: 'dai' }),
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
      name: 'wenmai-gallery-diy-v1',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ items: state.items, roofTint: state.roofTint }),
      version: 1,
    },
  ),
);