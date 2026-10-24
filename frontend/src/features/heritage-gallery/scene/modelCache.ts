/**
 * 建筑模型缓存：两座展馆各自一个 GLB，切换时不允许白屏。
 *
 * 为什么不用 drei 的 useGLTF：
 *  1. 切换建筑时 useGLTF 会把整棵场景挂起（Suspense），旧建筑已经卸载、新建筑还没好，
 *     中间那一两秒就是白屏/空场地——正是需求里明确禁止的；
 *  2. 我们需要「先加载完、再切换」的顺序控制，以及真实的进度回调；
 *  3. 两个 10 MB 级模型要能各自缓存、按需加载，切换回来的第二次必须瞬时。
 *
 * 做法：用 GLTFLoader 手动加载 + Map 缓存 + useState 订阅。
 * 页面在切换前先 `await preloadBuildingModel(next)`，完成后再改 activeBuilding，
 * 因此渲染阶段永远是同步命中缓存，不会出现半成品镜头。
 */

import { useEffect, useState } from 'react';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';

export type ModelProgress = (ratio: number, loaded: number, total: number) => void;

const loader = new GLTFLoader();
const models = new Map<string, GLTF>();
const pending = new Map<string, Promise<GLTF>>();
/** 每个 URL 的下载进度，供加载遮罩显示 */
const progressMap = new Map<string, number>();

export function getCachedModel(url: string): GLTF | null {
  return models.get(url) ?? null;
}

export function getModelProgress(url: string): number {
  return progressMap.get(url) ?? 0;
}

export function isModelLoading(url: string): boolean {
  return pending.has(url) && !models.has(url);
}

/** 加载（或复用缓存）一座建筑模型 */
export function preloadBuildingModel(url: string, onProgress?: ModelProgress): Promise<GLTF> {
  const cached = models.get(url);
  if (cached) {
    progressMap.set(url, 1);
    return Promise.resolve(cached);
  }
  const inflight = pending.get(url);
  if (inflight) return inflight;

  const promise = loader
    .loadAsync(url, (event) => {
      const total = event.total || 0;
      const loaded = event.loaded || 0;
      const ratio = total > 0 ? Math.min(1, loaded / total) : 0;
      progressMap.set(url, ratio);
      onProgress?.(ratio, loaded, total);
    })
    .then((gltf) => {
      models.set(url, gltf);
      progressMap.set(url, 1);
      pending.delete(url);
      return gltf;
    })
    .catch((error: unknown) => {
      pending.delete(url);
      progressMap.delete(url);
      throw error;
    });

  pending.set(url, promise);
  return promise;
}

/**
 * React 侧读取模型：命中缓存时同步返回，未命中时返回 null 并后台加载。
 *
 * 组件不会挂起，所以切换过程中旧建筑可以继续显示，直到页面显式切走。
 */
export function useBuildingModel(url: string): GLTF | null {
  const [model, setModel] = useState<GLTF | null>(() => getCachedModel(url));

  useEffect(() => {
    const cached = getCachedModel(url);
    if (cached) {
      setModel(cached);
      return undefined;
    }
    setModel(null);
    let alive = true;
    preloadBuildingModel(url)
      .then((gltf) => {
        if (alive) setModel(gltf);
      })
      .catch(() => {
        if (alive) setModel(null);
      });
    return () => {
      alive = false;
    };
  }, [url]);

  return model;
}

/** 预加载但不解析：给「悬停在建筑风格按钮上」做暖场 */
export function warmupBuildingModel(url: string): void {
  if (getCachedModel(url) || pending.has(url)) return;
  void preloadBuildingModel(url).catch(() => undefined);
}