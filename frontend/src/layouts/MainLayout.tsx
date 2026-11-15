import { Outlet, useLocation } from 'react-router-dom';
import { motion } from 'motion/react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function MainLayout() {
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col bg-paper text-ink font-sans">
      <Navbar />
      <main className="flex-grow pt-16">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
        >
          <Outlet />
        </motion.div>
      </main>
      <Footer />
    </div>
  );
}
