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

export default function App() {
  const Router = import.meta.env.VITE_STATIC_SHOWCASE === 'true' ? HashRouter : BrowserRouter;
  return (
    <Router>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/styles" element={<StyleLibrary />} />
          <Route path="/products" element={<ProductStudio />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="/about" element={<About />} />
          <Route path="/creator" element={<AICreator />} />
          <Route path="/gallery" element={<Gallery />} />
        </Route>
      </Routes>
    </Router>
  );
}
