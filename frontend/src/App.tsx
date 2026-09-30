/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Home from './pages/Home';
import AICreator from './pages/AICreator';
import StyleLibrary from './pages/StyleLibrary';
import ProductStudio from './pages/ProductStudio';
import Scenarios from './pages/Scenarios';
import About from './pages/About';

export default function App() {
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
        </Route>
      </Routes>
    </Router>
  );
}
