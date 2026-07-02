import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import client from '../../api/client';

interface Stats {
  dragons_total: number; dragons_active: number; pins_total: number;
  pins_active: number; pins_used: number; users_total: number; dragons_collected_total: number;
}

function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    client.get('/admin/stats').then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const cards = [
    { value: stats?.dragons_total ?? '—', label: 'Всего драконов', icon: '🐉' },
    { value: stats?.dragons_active ?? '—', label: 'Активных', icon: '✨' },
    { value: stats?.pins_total ?? '—', label: 'Всего PIN', icon: '🔑' },
    { value: stats?.pins_active ?? '—', label: 'PIN активны', icon: '🟢' },
    { value: stats?.users_total ?? '—', label: 'Игроков', icon: '👥' },
    { value: stats?.dragons_collected_total ?? '—', label: 'Выращено', icon: '⭐' },
  ];

  return (
    <>
      <div className="lair-header"><h2>Дашборд</h2></div>
      <div className="lair-content">
        <div className="lair-stat-grid">
          {cards.map((c, i) => (
            <motion.div
              key={i}
              className="lair-stat-card"
              initial={{ opacity: 0, y: 20, rotateX: 10 }}
              animate={{ opacity: 1, y: 0, rotateX: 0 }}
              transition={{ delay: i * 0.06, duration: 0.5, ease: 'easeOut' }}
            >
              <div className="lair-stat-value">{c.value}</div>
              <div className="lair-stat-label">{c.icon} {c.label}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </>
  );
}

export default Dashboard;
