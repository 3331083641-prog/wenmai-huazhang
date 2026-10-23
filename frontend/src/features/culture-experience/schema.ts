/**
 * CultureExperience 的运行时校验。
 *
 * 目的不是「让 JSON 能过」，而是把项目的内容纪律写成可执行约束：
 *   - 坐标必须归一化且在 0..1 内；
 *   - shape 必须与 geometry 的实际形态一致，避免热点画歪；
 *   - reviewStatus = confirmed 的热点必须有来源，否则文化解释是无源之水；
 *   - id 不得重复，章节 index 必须连续，否则导航会错位；
 *   - 章节的 focusHotspotIds 必须真实存在。
 *
 * 校验失败时返回可读问题清单，开发期直接抛错，生产期降级为警告（不白屏）。
 */

import { z } from 'zod';
import type { CultureExperienceDraft, HotspotGeometry } from './types';

const unit = z.number().min(0).max(1);

const rectSchema = z.object({
  x: unit,
  y: unit,
  width: z.number().min(0.01).max(1),
  height: z.number().min(0.01).max(1),
});

const circleSchema = z.object({
  cx: unit,
  cy: unit,
  r: z.number().min(0.01).max(0.5),
});

/** 归一化点：必须是 [x, y] 且都在 0..1 内，类型直接对齐 types.ts。 */
const pointSchema = z.custom<[number, number]>(
  (value) =>
    Array.isArray(value) &&
    value.length === 2 &&
    value.every((n) => typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 1),
  { message: '多边形点必须是 0..1 区间内的 [x, y]' }
);

const polygonSchema = z.object({
  points: z.array(pointSchema).min(3),
});

const geometrySchema = z.union([rectSchema, circleSchema, polygonSchema]);

/**
 * zod 的 union 推断会把 geometry 推成可选属性（三个分支同时出现在 union 里时
 * 可辨识性不足），这里显式钉住类型；校验仍然由 geometrySchema 完成。
 */
const geometryField = geometrySchema as unknown as z.ZodType<HotspotGeometry>;

const hotspotSchema = z
  .object({
    id: z.string().min(1).regex(/^[a-z0-9-]+$/, '热点 id 只允许小写字母、数字与连字符'),
    title: z.string().min(1).max(24),
    kicker: z.string().min(1).max(12),
    shape: z.enum(['rect', 'circle', 'polygon']),
    geometry: geometryField,
    shortDescription: z.string().min(1).max(60),
    visualObservation: z.string().min(10),
    culturalExplanation: z.string().min(20),
    sourceIds: z.array(z.string().min(1)),
    locationStatus: z.enum(['verified', 'approximate', 'unverified']),
    reviewStatus: z.enum(['confirmed', 'pending']),
    relatedChapterId: z.string().optional(),
  })
  .superRefine((hotspot, ctx) => {
    const isRect = 'width' in hotspot.geometry;
    const isCircle = 'r' in hotspot.geometry;
    const isPolygon = 'points' in hotspot.geometry;
    const actual = isRect ? 'rect' : isCircle ? 'circle' : isPolygon ? 'polygon' : 'unknown';
    if (hotspot.shape !== actual) {
      ctx.addIssue({
        code: 'custom',
        path: ['shape'],
        message: `shape=${hotspot.shape} 与 geometry 实际形态 ${actual} 不一致`,
      });
    }
    if (hotspot.reviewStatus === 'confirmed' && hotspot.sourceIds.length === 0) {
      ctx.addIssue({
        code: 'custom',
        path: ['sourceIds'],
        message: '已确认的热点必须至少引用一个文化来源',
      });
    }
    if (hotspot.reviewStatus === 'confirmed' && hotspot.locationStatus === 'unverified') {
      ctx.addIssue({
        code: 'custom',
        path: ['locationStatus'],
        message: 'reviewStatus=confirmed 的热点不应是 unverified 位置',
      });
    }
  });

const frameSchema = z.object({
  scale: z.number().min(1).max(4),
  focusX: unit,
  focusY: unit,
});

const chapterSchema = z.object({
  id: z.string().min(1).regex(/^[a-z0-9-]+$/),
  index: z.number().int().min(1),
  eyebrow: z.string().min(1).max(16),
  title: z.string().min(1).max(40),
  body: z.string().min(20),
  focusHotspotIds: z.array(z.string()),
  frame: frameSchema,
  sourceIds: z.array(z.string()),
});

const layerSchema = z.object({
  id: z.string().min(1),
  url: z.string().min(1),
  depth: z.number().min(0).max(1),
  maskFrom: unit,
  maskTo: unit,
  opacity: z.number().min(0).max(1).optional(),
});

const worldSchema = z.object({
  url: z.string().min(1),
  depthNote: z.string().optional(),
});

const animationSchema = z.object({
  mode: z.enum(['static', 'parallax', 'layered', 'world']),
  layers: z.array(layerSchema).optional(),
  world: worldSchema.optional(),
  capabilityNote: z.string().min(1),
  layerSource: z.string().optional(),
});

const themeSchema = z.object({
  accent: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  accentSoft: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  paper: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  ink: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  gold: z.string().regex(/^#[0-9a-fA-F]{6}$/),
});

const visualAnalysisSchema = z.object({
  source: z.string().min(1),
  model: z.string().optional(),
  observedSubjects: z.array(z.string()).min(1),
  visualFeatures: z.array(z.string()).min(1),
  dominantColors: z.array(z.string()).min(1),
});

const draftSchema = z
  .object({
    id: z.string().min(1).regex(/^[a-z0-9-]+$/),
    styleId: z.string().min(1),
    styleName: z.string().min(1),
    title: z.string().min(1).max(24),
    subtitle: z.string().min(1).max(40),
    lead: z.string().min(8),
    artworkSize: z.object({ width: z.number().int().positive(), height: z.number().int().positive() }),
    theme: themeSchema,
    visualAnalysis: visualAnalysisSchema,
    hotspots: z.array(hotspotSchema).min(3),
    chapters: z.array(chapterSchema).min(3),
    animation: animationSchema,
    provenance: z.object({
      sourceCaseId: z.string().optional(),
      knowledgeVersion: z.string().optional(),
      authoredAt: z.string().optional(),
      hotspotMethod: z.string().optional(),
      designNote: z.string().optional(),
    }),
  })
  .superRefine((draft, ctx) => {
    const hotspotIds = new Set<string>();
    draft.hotspots.forEach((hotspot, index) => {
      if (hotspotIds.has(hotspot.id)) {
        ctx.addIssue({ code: 'custom', path: ['hotspots', index, 'id'], message: `热点 id 重复：${hotspot.id}` });
      }
      hotspotIds.add(hotspot.id);
      if (hotspot.relatedChapterId && !draft.chapters.some((c) => c.id === hotspot.relatedChapterId)) {
        ctx.addIssue({
          code: 'custom',
          path: ['hotspots', index, 'relatedChapterId'],
          message: `关联章节不存在：${hotspot.relatedChapterId}`,
        });
      }
    });

    const chapterIds = new Set<string>();
    draft.chapters.forEach((chapter, index) => {
      if (chapterIds.has(chapter.id)) {
        ctx.addIssue({ code: 'custom', path: ['chapters', index, 'id'], message: `章节 id 重复：${chapter.id}` });
      }
      chapterIds.add(chapter.id);
      if (chapter.index !== index + 1) {
        ctx.addIssue({
          code: 'custom',
          path: ['chapters', index, 'index'],
          message: `章节 index 应为 ${index + 1}，实际为 ${chapter.index}`,
        });
      }
      chapter.focusHotspotIds.forEach((id) => {
        if (!draft.hotspots.some((h) => h.id === id)) {
          ctx.addIssue({
            code: 'custom',
            path: ['chapters', index, 'focusHotspotIds'],
            message: `章节引用了不存在的热点：${id}`,
          });
        }
      });
    });

    if (draft.animation.mode === 'world') {
      if (!draft.animation.world?.url) {
        ctx.addIssue({
          code: 'custom',
          path: ['animation', 'world', 'url'],
          message: '画境模式必须提供 world.url（深度资产清单）',
        });
      }
    } else if (draft.animation.mode !== 'static' && !draft.animation.layers?.length) {
      ctx.addIssue({
        code: 'custom',
        path: ['animation', 'layers'],
        message: '非静态模式必须提供分层素材',
      });
    }
  });

export interface ExperienceIssue {
  path: string;
  message: string;
}

export interface ValidationResult {
  ok: boolean;
  issues: ExperienceIssue[];
}

/** 校验单个体验草稿；返回可读问题清单。 */
export function validateExperienceDraft(input: unknown): ValidationResult {
  const result = draftSchema.safeParse(input);
  if (result.success) return { ok: true, issues: [] };
  return {
    ok: false,
    issues: result.error.issues.map((issue) => ({
      path: issue.path.join('.'),
      message: issue.message,
    })),
  };
}

/** 通过校验则返回强类型数据，否则抛错（开发期由 ErrorBoundary 兜底）。 */
export function parseExperienceDraft(input: unknown, label = 'experience'): CultureExperienceDraft {
  const result = validateExperienceDraft(input);
  if (!result.ok) {
    const detail = result.issues.map((issue) => `${issue.path}: ${issue.message}`).join('; ');
    throw new Error(`${label} 数据校验失败 → ${detail}`);
  }
  return input as CultureExperienceDraft;
}

/**
 * 编译期类型一致性检查：schema 的输出类型必须仍是 CultureExperienceDraft。
 * 若 types.ts 与 schema.ts 漂移，tsc 会在这里报错。
 */
type DraftSchemaOutput = z.infer<typeof draftSchema>;
type AssertAssignable<T extends U, U> = T;
export type SchemaMatchesTypes = AssertAssignable<DraftSchemaOutput, CultureExperienceDraft>;