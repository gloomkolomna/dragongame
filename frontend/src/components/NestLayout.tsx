import { useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import ParticlesBackground from './ParticlesBackground';

interface Props { children: ReactNode; }

function NestLayout({ children }: Props) {
  useEffect(() => {
    document.body.style.background = '';
  }, []);

  return (
    <>
      <ParticlesBackground />
      {children}
    </>
  );
}

export default NestLayout;
