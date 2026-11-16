import { useEffect, useRef } from 'react';

export interface UseDialogFocusTrapOptions {
  isOpen: boolean;
  onClose: () => void;
  triggerRef?: React.RefObject<HTMLElement | null>;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
}

/**
 * 符合 WAI-ARIA 标准的模态弹窗焦点捕获与管理 Hook：
 * 1. 弹窗打开时锁定背景滚动 (body overflow: hidden)；
 * 2. 自动聚焦弹窗首个可聚焦控件或指定的初始控件；
 * 3. 约束 Tab / Shift+Tab 循环在弹窗内部，防止焦点逃逸至背景；
 * 4. 支持 Escape 键关闭；
 * 5. 弹窗关闭后无缝将焦点恢复至触发按钮。
 */
export function useDialogFocusTrap({
  isOpen,
  onClose,
  triggerRef,
  initialFocusRef,
}: UseDialogFocusTrapOptions) {
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    // 1. 锁定背景滚动
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // 2. 聚焦弹窗内部元素
    const dialogElement = dialogRef.current;
    const focusTimer = setTimeout(() => {
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus();
      } else if (dialogElement) {
        const focusable = dialogElement.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length > 0) {
          focusable[0].focus();
        } else {
          dialogElement.focus();
        }
      }
    }, 40);

    // 3. 焦点闭环与 Escape 监听
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onClose();
        return;
      }

      if (e.key === 'Tab' && dialogElement) {
        const focusables = Array.from(
          dialogElement.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          )
        ).filter((el) => el.offsetParent !== null); // 仅检索可见元素

        if (focusables.length === 0) {
          e.preventDefault();
          return;
        }

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first || !dialogElement.contains(document.activeElement)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last || !dialogElement.contains(document.activeElement)) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(focusTimer);
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
      // 恢复焦点至触发器
      if (triggerRef?.current) {
        triggerRef.current.focus();
      }
    };
  }, [isOpen, onClose, triggerRef, initialFocusRef]);

  return { dialogRef };
}
