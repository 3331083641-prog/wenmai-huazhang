/**
 * 门的交互状态：悬停提示 + 开关状态。
 *
 * 放在独立小 store 里，是为了让「左侧 UI 浮层」和 Canvas 内的射线检测解耦：
 * 场景里只负责判定鼠标是否落在门扇上并更新坐标，页面只负责把提示画出来。
 */

import { create } from 'zustand';

interface DoorState {
  hover: boolean;
  open: boolean;
  /** 提示文字的屏幕坐标（相对画布左上角） */
  x: number;
  y: number;
  setHover: (hover: boolean, x?: number, y?: number) => void;
  toggle: () => void;
  reset: () => void;
}

export const useDoorStore = create<DoorState>()((set) => ({
  hover: false,
  open: false,
  x: 0,
  y: 0,
  setHover: (hover, x, y) =>
    set((state) => ({
      hover,
      x: x ?? state.x,
      y: y ?? state.y,
    })),
  toggle: () => set((state) => ({ open: !state.open })),
  reset: () => set({ hover: false, open: false }),
}));