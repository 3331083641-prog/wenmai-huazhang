# Registration report — wenmai-3d-reconstruction

- generated: `2026-10-22T10:33:09+08:00`
- plugin root: `D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction`
- plugin export: `wenmai-3d-reconstruction` · inject: `["tools"]`
- apply() duration: 4 ms
- registered tools: **17 / 17**
- missing: —
- extra: —
- checks: **171 pass / 0 fail / 0 warn / 0 skip / 0 not ready**

## Tool table

| # | tool | group | desc len | params | required | contract params missing | schema |
|---|---|---|---|---|---|---|---|
| 1 | `wm_analyze_references` | A | 454 | 3 | 0 | — | ok |
| 2 | `wm_build_scene_spec` | A | 399 | 3 | 1 | — | ok |
| 3 | `wm_match_camera` | A | 381 | 5 | 2 | — | ok |
| 4 | `wm_validate_multiview` | A | 314 | 3 | 0 | — | ok |
| 5 | `wm_generate_roof` | B | 909 | 19 | 0 | — | ok |
| 6 | `wm_generate_timber` | B | 560 | 12 | 0 | — | ok |
| 7 | `wm_generate_interior` | B | 825 | 14 | 0 | — | ok |
| 8 | `wm_generate_diorama` | B | 604 | 11 | 0 | — | ok |
| 9 | `wm_export_glb` | B | 364 | 5 | 0 | — | ok |
| 10 | `wm_capture_views` | C | 439 | 7 | 0 | — | ok |
| 11 | `wm_compare_reference` | C | 412 | 5 | 2 | — | ok |
| 12 | `wm_generate_diff_report` | C | 328 | 4 | 0 | — | ok |
| 13 | `wm_propose_geometry_changes` | C | 355 | 4 | 0 | — | ok |
| 14 | `wm_inspect_scene` | D | 365 | 2 | 0 | — | ok |
| 15 | `wm_check_art_frames` | D | 309 | 3 | 0 | — | ok |
| 16 | `wm_check_export` | D | 301 | 2 | 0 | — | ok |
| 17 | `wm_performance_report` | D | 314 | 4 | 0 | — | ok |

## Parameters per tool

### `wm_analyze_references`

- params (3): `images`, `outDir`, `makeContactSheet`
- required (0): —

### `wm_build_scene_spec`

- params (3): `observations`, `measurementsPath`, `outPath`
- required (1): `observations`

### `wm_match_camera`

- params (5): `image`, `correspondences`, `imageSize`, `init`, `outPath`
- required (2): `image`, `correspondences`

### `wm_validate_multiview`

- params (3): `specPath`, `views`, `outPath`
- required (0): —

### `wm_generate_roof`

- params (19): `baseBlend`, `outBlend`, `fromProjectModel`, `overwrite`, `style`, `footprintX`, `footprintY`, `eaveZ`, `ridgeZ`, `overhang`, `cornerLift`, `slopePower`, `ridgeHalf`, `tileRows`, `tileCover`, `tileSegments`, `tileThickness`, `ridgeOrnament`, `detail`
- required (0): —

### `wm_generate_timber`

- params (12): `baseBlend`, `outBlend`, `fromProjectModel`, `overwrite`, `baysX`, `baysY`, `columnRadius`, `f1H`, `f2H`, `dougongLevels`, `rafterSpacing`, `detail`
- required (0): —

### `wm_generate_interior`

- params (14): `baseBlend`, `outBlend`, `fromProjectModel`, `overwrite`, `voidX`, `voidY`, `corridorWidth`, `railingHeight`, `stairWidth`, `stairRisers`, `ceilingStyle`, `displayWalls`, `lanterns`, `detail`
- required (0): —

### `wm_generate_diorama`

- params (11): `baseBlend`, `outBlend`, `fromProjectModel`, `overwrite`, `baseSize`, `plinthHeight`, `frieze`, `medallion`, `paving`, `props`, `detail`
- required (0): —

### `wm_export_glb`

- params (5): `blend`, `out`, `copyTo`, `yUp`, `draco`
- required (0): —

### `wm_capture_views`

- params (7): `blend`, `views`, `camerasPath`, `width`, `height`, `samples`, `outDir`
- required (0): —

### `wm_compare_reference`

- params (5): `reference`, `render`, `outDir`, `align`, `cameraPath`
- required (2): `reference`, `render`

### `wm_generate_diff_report`

- params (4): `comparisons`, `comparisonPaths`, `outDir`, `title`
- required (0): —

### `wm_propose_geometry_changes`

- params (4): `comparisonPath`, `reportPath`, `specPath`, `outDir`
- required (0): —

### `wm_inspect_scene`

- params (2): `blend`, `checks`
- required (0): —

### `wm_check_art_frames`

- params (3): `blend`, `expected`, `layoutPath`
- required (0): —

### `wm_check_export`

- params (2): `glb`, `profile`
- required (0): —

### `wm_performance_report`

- params (4): `blend`, `glb`, `triangleBudget`, `sizeBudgetMb`
- required (0): —

## Failures

None.

## Contract drift (warnings — decision for the contract owner)

None.
