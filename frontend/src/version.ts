/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export const APP_VERSION = {
  version: '2.4.1-reliable-convergence',
  buildTag: '2026.11-reliable-convergence',
  edition: '传统文化视觉智能创作与沉浸式文创应用平台',
  releaseName: '纹脉华章 VNext 交互可靠性与全站质量收敛版',
  updatedAt: '2026-11-16',
};

if (typeof window !== 'undefined') {
  // eslint-disable-next-line no-console
  console.info(
    `%c 纹脉华章 %c ${APP_VERSION.version} (${APP_VERSION.buildTag}) %c`,
    'background: #9E241B; color: #fff; padding: 3px 6px; border-radius: 3px 0 0 3px; font-weight: bold; font-family: serif;',
    'background: #D2A14A; color: #3F2B1F; padding: 3px 6px; border-radius: 0 3px 3px 0; font-weight: bold;',
    'background: transparent;'
  );
}
