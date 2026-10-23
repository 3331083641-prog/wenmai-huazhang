/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter, HashRouter, Routes, Route } from 'react-router-dom';
import Gallery from './pages/Gallery';
import MainLayout from './layouts/MainLayout';
import Home from './pages/Home';
import AICreator from './pages/AICreator';
import StyleLibrary from './pages/StyleLibrary';
import ProductStudio from './pages/ProductStudio';
import Scenarios from './pages/Scenarios';
import About from './pages/About';
import Experience from './pages/Experience';
import Story from './pages/Story';
import Wander from './pages/Wander';
import HeritageGallery from './pages/HeritageGallery';

export default function App() {
  const Router = import.meta.env.VITE_STATIC_SHOWCASE === 'true' ? HashRouter : BrowserRouter;
  return (
    <Router>
      <Routes>
        {/*
          纹脉展馆放在 MainLayout 之外：
          它需要占满视口做沉浸式 3D，站内的固定导航与页脚会破坏构图。
          返回入口由页面自己在左上角提供。
        */}
        <Route path="/heritage-gallery" element={<HeritageGallery />} />
        {/* 画境漫游同理：入画时要占满视口，站内导航与页脚会破坏沉浸感。 */}
        <Route path="/wander/:id" element={<Wander />} />
        <Route element={<MainLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/styles" element={<StyleLibrary />} />
          <Route path="/products" element={<ProductStudio />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="/about" element={<About />} />
          <Route path="/creator" element={<AICreator />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/experience/:id" element={<Experience />} />
          <Route path="/story/:id" element={<Story />} />
        </Route>
      </Routes>
    </Router>
  );
}
