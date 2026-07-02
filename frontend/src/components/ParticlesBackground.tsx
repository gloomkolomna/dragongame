import { useEffect, useRef } from 'react';

function ParticlesBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = 0, h = 0;
    const particles: Array<{ x: number; y: number; vx: number; vy: number; r: number; o: number; life: number; maxLife: number }> = [];
    const MAX = 80;

    const resize = () => {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const spawn = () => {
      if (particles.length < MAX) {
        particles.push({
          x: Math.random() * w,
          y: h + 20,
          vx: (Math.random() - 0.5) * 0.6,
          vy: -(Math.random() * 1.4 + 0.5),
          r: Math.random() * 3.5 + 1.5,
          o: Math.random() * 0.6 + 0.4,
          life: 0,
          maxLife: Math.random() * 280 + 120,
        });
      }
    };

    let animId: number;
    const tick = () => {
      ctx.clearRect(0, 0, w, h);
      if (Math.random() < 0.25) spawn();

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life++;

        const fade = 1 - p.life / p.maxLife;
        const alpha = p.o * fade;

        // main spark
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${170 + Math.random() * 40}, ${100 + Math.random() * 50}, 255, ${alpha})`;
        ctx.fill();

        // inner bright core
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 0.4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(220, 190, 255, ${alpha * 1.2})`;
        ctx.fill();

        // outer glow
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(153, 102, 255, ${alpha * 0.08})`;
        ctx.fill();

        if (p.life >= p.maxLife || p.y < -20) {
          particles.splice(i, 1);
        }
      }
      animId = requestAnimationFrame(tick);
    };
    tick();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}
    />
  );
}

export default ParticlesBackground;
