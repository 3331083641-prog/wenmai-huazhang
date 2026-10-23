/**
 * Minimal host typings for the DSH 0.2.1-rc.2 Cordis plugin surface this
 * package uses.
 *
 * The plugin deliberately imports NOTHING from `@deepseek-ai/*` at runtime:
 * the profile it is installed into does not own a copy of the DSH runtime, and
 * a second copy of cordis/dsh-tools would be a real compatibility hazard. The
 * tool registry only needs plain `ToolDefinition` objects, so this file models
 * exactly that wire shape. Keep it in sync with `@deepseek-ai/dsh-tools`
 * (`defineTool` output) when the host version changes.
 */
export {};
