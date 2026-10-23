/**
 * 画框悬停提示：鼠标移到画框上时，在光标旁提示「点击更换图画」。
 *
 * 画框不再允许自由拖动（用户要求只保留固定画框），所以这里只记录
 * 悬停的画框 id 与光标位置，供页面的浮层使用。
 */

import { create } from 'zustand';

interface FrameHoverState {
  frameId: string | null;
  x: number;
  y: number;
  title: string;
  setHover: (frameId: string, x: number, y: number, title?: string) => void;
  clear: () => void;
}

export const useFrameHoverStore = create<FrameHoverState>()((set) => ({
  frameId: null,
  x: 0,
  y: 0,
  title: '',
  setHover: (frameId, x, y, title = '') => set({ frameId, x, y, title }),
  clear: () => set({ frameId: null }),
}));