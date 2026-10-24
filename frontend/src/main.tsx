import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
// 双展馆方案已回退：把当时写进 v2 key 的经典馆布展复制回 v1，必须在 store 初始化前执行
import {migrateLegacyGalleryStorage} from './features/heritage-gallery/state/legacyGalleryStorage';

migrateLegacyGalleryStorage();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);