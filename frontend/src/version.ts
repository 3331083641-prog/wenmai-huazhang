/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { projectBrand } from './data/projectBrand';

export const APP_VERSION = {
  version: '2.4.2-competition-ready',
  buildTag: '2026.11-competition-ready',
  edition: projectBrand.subtitle,
  releaseName: `${projectBrand.name} VNext 历史作品一致性与竞赛级品质验收版`,
  updatedAt: '2026-11-16',
};

if (typeof window !== 'undefined') {
  // eslint-disable-next-line no-console
  console.info(
    `%c ${projectBrand.name} %c ${APP_VERSION.version} (${APP_VERSION.buildTag}) %c`,
    'background: #9E241B; color: #fff; padding: 3px 6px; border-radius: 3px 0 0 3px; font-weight: bold; font-family: serif;',
    'background: #D2A14A; color: #3F2B1F; padding: 3px 6px; border-radius: 0 3px 3px 0; font-weight: bold;',
    'background: transparent;'
  );
}
