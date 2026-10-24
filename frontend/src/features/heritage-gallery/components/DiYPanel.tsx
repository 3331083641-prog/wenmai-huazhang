/**
 * 右侧「器物图库」抽屉 —— DIY 布展的选件面板。
 *
 * 三种选件方式同时可用：
 *  1. 直接拖卡片到画面上（HTML5 drag，桌面端最顺手）；
 *  2. 点卡片 -> 进入落位状态 -> 在场景里点一下放下；
 *  3. 已摆好的器物可再拖动，选中后用这里的按钮旋转 / 缩放 / 删除。
 */

import { useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import {
  Boxes,
  Flower2,
  Grid2X2,
  Sparkles,
  Lamp,
  LayoutGrid,
  Mountain,
  RotateCw,
  Trash2,
  Minus,
  Plus,
  Move,
  X,
} from 'lucide-react';
import * as THREE from 'three';

import {
  PROP_BY_ID,
  PROP_CATALOG,
  PROP_CATEGORY_LABEL,
  type PropCategory,
  type PropDef,
} from '../scene/props/catalog';
import { ROOF_TINTS, useDiyItems, useDiyStore, useRoofTint } from '../state/diyStore';
import { ALL_PROP_CATALOG, ASSET_GROUP_LABEL, getPropDef } from '../props/assets/assetProps';
import { ASSET_BY_ID } from '../props/assets/assetCatalog';

const CATEGORY_ICON: Record<PropCategory, typeof Boxes> = {
  greenery: Flower2,
  light: Lamp,
  stone: Mountain,
  exhibit: Boxes,
  furniture: LayoutGrid,
  wall: Grid2X2,
  asset: Sparkles,
};

const CATEGORY_ORDER: PropCategory[] = ['asset', 'exhibit', 'furniture', 'greenery', 'light', 'stone', 'wall'];

/** 面板顶部的小预览：一只旋转的器物，比图标直观 */
function Preview({ propId }: { propId: string | null }) {
  const def = propId ? getPropDef(propId) : undefined;
  return (
    <div className="relative h-[132px] w-full overflow-hidden rounded border border-[color:var(--color-gold)]/35 bg-[#F4ECDC]">
      {def ? (
        <>
          <Canvas
            shadows={false}
            dpr={1}
            camera={{ position: [2.1, 1.5, 2.4], fov: 30, near: 0.1, far: 40 }}
            gl={{ antialias: true, alpha: true, preserveDrawingBuffer: false }}
          >
            <ambientLight intensity={1.15} color="#fff2dd" />
            <directionalLight position={[3, 5, 2]} intensity={2.1} color="#fff0d6" />
            <directionalLight position={[-3, 2, -2]} intensity={0.5} color="#cfd8e6" />
            <Spinner def={def} />
          </Canvas>
          <div className="pointer-events-none absolute bottom-1 left-2 text-[10px] text-[color:var(--color-ink)]/50">
            {def.footprint[0].toFixed(2)} × {def.footprint[1].toFixed(2)} m · 高 {def.height.toFixed(2)} m
          </div>
        </>
      ) : (
        <p className="grid h-full place-items-center text-[11px] text-[color:var(--color-ink)]/40">
          选一件器物
        </p>
      )}
    </div>
  );
}

function Spinner({ def }: { def: PropDef }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.6;
  });
  // 让任意尺寸的器物都落在画面里
  const box = Math.max(def.footprint[0], def.footprint[1], def.height);
  const scale = 1.55 / Math.max(0.5, box);
  const center = useMemo(() => -def.height * 0.45, [def.height]);
  return (
    <group ref={ref} scale={scale} position={[0, center * scale, 0]}>
      <def.Component />
    </group>
  );
}

export function DiYPanel() {
  const open = useDiyStore((state) => state.panelOpen);
  const items = useDiyItems();
  const selectedKey = useDiyStore((state) => state.selectedKey);
  const pendingPropId = useDiyStore((state) => state.pendingPropId);
  const roofTint = useRoofTint();
  const setPanelOpen = useDiyStore((state) => state.setPanelOpen);
  const setPending = useDiyStore((state) => state.setPending);
  const updateItem = useDiyStore((state) => state.updateItem);
  const removeItem = useDiyStore((state) => state.removeItem);
  const selectItem = useDiyStore((state) => state.selectItem);
  const setRoofTint = useDiyStore((state) => state.setRoofTint);
  const clearItems = useDiyStore((state) => state.clearItems);
  const editMode = useDiyStore((state) => state.editMode);
  const setEditMode = useDiyStore((state) => state.setEditMode);

  const [category, setCategory] = useState<PropCategory>('asset');
  const [hovered, setHovered] = useState<string | null>(null);
  const [tab, setTab] = useState<'props' | 'roof'>('props');

  const selected = selectedKey ? items.find((item) => item.key === selectedKey) : undefined;
  const selectedDef = selected ? getPropDef(selected.propId) : undefined;

  const list = useMemo(
    () => ALL_PROP_CATALOG.filter((def) => def.category === category),
    [category],
  );
  const previewId = hovered ?? pendingPropId ?? selected?.propId ?? list[0]?.id ?? null;

  if (!open) return null;

  return (
    <aside
      aria-label="器物图库"
      className="pointer-events-auto absolute right-0 top-0 z-30 flex h-full w-[min(92vw,392px)] flex-col border-l border-[color:var(--color-gold)]/40 bg-[#FBF6EB]/94 shadow-[-12px_0_40px_rgba(63,43,31,0.14)] outline-none backdrop-blur-md"
    >
      <div className="flex items-start justify-between gap-3 border-b border-[color:var(--color-gold)]/30 px-4 pb-2.5 pt-3.5">
        <div>
          <p className="text-[10px] tracking-[0.28em] text-[color:var(--color-primary)]">DIY · 陈设</p>
          <h2 className="mt-0.5 font-serif text-[15px] text-[color:var(--color-ink)]">器物图库</h2>
          <p className="mt-0.5 text-[10.5px] text-[color:var(--color-ink)]/50">
            拖到画面落位 · 已摆 {items.length} 件
          </p>
        </div>
        <button
          type="button"
          onClick={() => setPanelOpen(false)}
          aria-label="收起器物图库"
          className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full text-[color:var(--color-ink)]/45 transition hover:bg-black/5 hover:text-[color:var(--color-ink)]"
        >
          <X size={15} />
        </button>
      </div>

      <div className="flex gap-1 border-b border-[color:var(--color-gold)]/25 px-3 py-2">
        {(
          [
            ['props', '器物'],
            ['roof', '屋顶与配色'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex-1 rounded px-2 py-1 text-[11.5px] transition ${
              tab === id
                ? 'bg-[color:var(--color-primary)] text-white'
                : 'text-[color:var(--color-ink)]/60 hover:bg-black/5'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'props' ? (
        <>
          <div className="px-3 pt-2.5">
            <Preview propId={previewId} />
          </div>

          <div className="flex flex-wrap gap-1 px-3 py-2">
            {CATEGORY_ORDER.map((id) => {
              const Icon = CATEGORY_ICON[id];
              const active = category === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setCategory(id)}
                  className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] transition ${
                    active
                      ? 'border-[color:var(--color-primary)] bg-[color:var(--color-primary)] text-white'
                      : 'border-[color:var(--color-gold)]/50 text-[color:var(--color-ink)]/60 hover:border-[color:var(--color-primary)]'
                  }`}
                >
                  <Icon size={10} />
                  {PROP_CATEGORY_LABEL[id]}
                </button>
              );
            })}
          </div>

          <div className="flex-1 overflow-y-auto px-2 pb-2">
            <ul className="grid grid-cols-2 gap-1.5">
              {list.map((def) => {
                const active = pendingPropId === def.id;
                return (
                  <li key={def.id}>
                    <button
                      type="button"
                      draggable
                      onDragStart={(event) => {
                        event.dataTransfer.setData('text/x-wenmai-prop', def.id);
                        event.dataTransfer.effectAllowed = 'copy';
                        setPending(def.id);
                      }}
                      onClick={() => setPending(active ? null : def.id)}
                      onMouseEnter={() => setHovered(def.id)}
                      onMouseLeave={() => setHovered((value) => (value === def.id ? null : value))}
                      className={`w-full rounded border px-2 py-2 text-left transition ${
                        active
                          ? 'border-[color:var(--color-primary)] bg-white/85 shadow-[inset_0_0_0_1px_rgba(158,36,27,0.35)]'
                          : 'border-[color:var(--color-gold)]/35 bg-white/45 hover:border-[color:var(--color-primary)]/60 hover:bg-white/75'
                      }`}
                    >
                      <span className="block font-serif text-[12px] text-[color:var(--color-ink)]">
                        {def.name}
                      </span>
                      <span className="mt-0.5 block truncate text-[10px] text-[color:var(--color-ink)]/45">
                        {def.note}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            {pendingPropId && (
              <p className="mt-2 rounded bg-[color:var(--color-primary)]/8 px-2 py-1.5 text-[10.5px] leading-relaxed text-[color:var(--color-primary)]">
                已取「{getPropDef(pendingPropId)?.name}」，在场景里点一下落位；再点一次取消。
              </p>
            )}
          </div>

          {selected && selectedDef && (
            <div className="border-t border-[color:var(--color-gold)]/30 px-3 py-2">
              <p className="mb-1.5 text-[10.5px] text-[color:var(--color-ink)]/55">
                已选中「{selectedDef.name}」
              </p>
              <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setEditMode(!editMode)}
                  data-testid="diy-edit-mode"
                  className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-[10.5px] transition ${
                    editMode
                      ? 'border-[color:var(--color-primary)] bg-[color:var(--color-primary)] text-white'
                      : 'border-[color:var(--color-gold)]/50 text-[color:var(--color-ink)]/65 hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]'
                  }`}
                >
                  <Move size={11} />
                  {editMode ? '完成调整' : '调整位置'}
                </button>
                {editMode && (
                  <span className="text-[10px] text-[color:var(--color-primary)]/70">
                    调整模式：点击只选中，不触发器物互动
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <ActionButton
                  icon={RotateCw}
                  label="左转 15°"
                  onClick={() => updateItem(selected.key, { rotY: selected.rotY - Math.PI / 12 })}
                />
                <ActionButton
                  icon={RotateCw}
                  label="右转 15°"
                  flip
                  onClick={() => updateItem(selected.key, { rotY: selected.rotY + Math.PI / 12 })}
                />
                <ActionButton
                  icon={Minus}
                  label="缩小"
                  onClick={() => updateItem(selected.key, { scale: Math.max(0.5, selected.scale - 0.1) })}
                />
                <ActionButton
                  icon={Plus}
                  label="放大"
                  onClick={() => updateItem(selected.key, { scale: Math.min(2.2, selected.scale + 0.1) })}
                />
                <ActionButton
                  icon={Trash2}
                  label="删除"
                  danger
                  onClick={() => removeItem(selected.key)}
                />
              </div>
            </div>
          )}

          <div className="flex items-center justify-between border-t border-[color:var(--color-gold)]/30 px-3 py-2">
            <button
              type="button"
              onClick={clearItems}
              className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 px-2 py-1 text-[11px] text-[color:var(--color-ink)]/65 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
            >
              <Trash2 size={11} />
              清空器物
            </button>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setEditMode(!editMode)}
                data-testid="diy-edit-entry"
                className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-[11px] transition ${
                  editMode
                    ? 'border-[color:var(--color-primary)] bg-[color:var(--color-primary)] text-white'
                    : 'border-[color:var(--color-gold)]/50 text-[color:var(--color-ink)]/65 hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]'
                }`}
                title={editMode ? '退出调整位置' : '进入调整位置：点击已摆器物只选中，不触发互动'}
              >
                <Move size={11} />
                {editMode ? '完成调整' : '调整位置'}
              </button>
              <button
                type="button"
                onClick={() => selectItem(null)}
                className="text-[10.5px] text-[color:var(--color-ink)]/45 transition hover:text-[color:var(--color-primary)]"
              >
                取消选中
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="flex-1 overflow-y-auto px-4 py-3">
          <p className="text-[11px] leading-relaxed text-[color:var(--color-ink)]/55">
            屋顶瓦色只影响瓦面与瓦垄，梁架、彩画、石作保持原样。
          </p>
          <div className="mt-3 grid grid-cols-5 gap-2">
            {ROOF_TINTS.map((tint) => (
              <button
                key={tint.id}
                type="button"
                title={tint.name}
                onClick={() => setRoofTint(tint.id)}
                className={`group flex flex-col items-center gap-1 rounded border p-1.5 transition ${
                  roofTint === tint.id
                    ? 'border-[color:var(--color-primary)] bg-white/70'
                    : 'border-[color:var(--color-gold)]/35 hover:border-[color:var(--color-primary)]/60'
                }`}
              >
                <span
                  className="h-7 w-full rounded-sm border border-black/10"
                  style={{ background: tint.color }}
                />
                <span className="text-[10px] text-[color:var(--color-ink)]/65">{tint.name}</span>
              </button>
            ))}
          </div>
          <p className="mt-4 text-[10.5px] leading-relaxed text-[color:var(--color-ink)]/45">
            提示：夜间模式下灯笼与窗纸会自然发光，瓦色深浅对夜景影响更明显。
          </p>
        </div>
      )}
    </aside>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  danger,
  flip,
}: {
  icon: typeof RotateCw;
  label: string;
  onClick: () => void;
  danger?: boolean;
  flip?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={`inline-flex h-6 items-center gap-1 rounded border px-1.5 text-[10.5px] transition ${
        danger
          ? 'border-[color:var(--color-primary)]/50 text-[color:var(--color-primary)] hover:bg-[color:var(--color-primary)] hover:text-white'
          : 'border-[color:var(--color-gold)]/50 text-[color:var(--color-ink)]/65 hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]'
      }`}
    >
      <Icon size={11} style={flip ? { transform: 'scaleX(-1)' } : undefined} />
    </button>
  );
}