import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { computeContainBox, type Box, type Size } from '../utils/geometry';

interface Result {
  containerRef: RefObject<HTMLDivElement | null>;
  imageBox: Box;
  containerSize: Size;
}

/**
 * 测量容器，并按 object-fit: contain 的规则算出图片真实绘制区域。
 * 热点层只用这个 box 做定位，因此任何视口尺寸下都不会漂移。
 */
export function useContainedImage(imageSize: Size): Result {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerSize, setContainerSize] = useState<Size>({ width: 0, height: 0 });
  const [imageBox, setImageBox] = useState<Box>({ x: 0, y: 0, width: 0, height: 0 });

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const measure = () => {
      const rect = element.getBoundingClientRect();
      const size = { width: rect.width, height: rect.height };
      setContainerSize(size);
      setImageBox(computeContainBox(size, imageSize));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    window.addEventListener('resize', measure);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [imageSize.width, imageSize.height]);

  return { containerRef, imageBox, containerSize };
}