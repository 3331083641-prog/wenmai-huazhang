import React, { useRef, useState, useCallback } from 'react';
import { motion, useReducedMotion } from 'motion/react';

interface TiltCardProps {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number;
  glareOpacity?: number;
}

export function TiltCard({
  children,
  className = '',
  maxTilt = 7,
  glareOpacity = 0.22,
}: TiltCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [glarePos, setGlarePos] = useState({ x: 50, y: 50 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (shouldReduceMotion || !cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;

      setTilt({
        x: -(y - 0.5) * maxTilt,
        y: (x - 0.5) * maxTilt,
      });
      setGlarePos({
        x: x * 100,
        y: y * 100,
      });
    },
    [maxTilt, shouldReduceMotion]
  );

  const handleMouseEnter = () => setIsHovered(true);
  const handleMouseLeave = () => {
    setIsHovered(false);
    setTilt({ x: 0, y: 0 });
  };

  return (
    <motion.div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      animate={
        shouldReduceMotion
          ? {}
          : {
              rotateX: tilt.x,
              rotateY: tilt.y,
              scale: isHovered ? 1.012 : 1,
            }
      }
      transition={{ type: 'spring', stiffness: 300, damping: 25, mass: 0.5 }}
      style={{
        transformStyle: 'preserve-3d',
        perspective: 1000,
      }}
      className={`relative overflow-hidden rounded-2xl sm:rounded-3xl border border-gold/25 bg-[#FBF8F2] shadow-xl ${className}`}
    >
      {/* Dynamic Specular / Ambient Spotlight */}
      {!shouldReduceMotion && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-30 transition-opacity duration-500 ease-out"
          style={{
            opacity: isHovered ? glareOpacity : 0,
            background: `radial-gradient(circle 380px at ${glarePos.x}% ${glarePos.y}%, rgba(255, 255, 255, 0.8), rgba(210, 161, 74, 0.25) 30%, transparent 75%)`,
            mixBlendMode: 'overlay',
          }}
        />
      )}
      {children}
    </motion.div>
  );
}
