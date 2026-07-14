import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Stats {
  dragons_total: number; dragons_active: number; pins_total: number;
  pins_active: number; pins_used: number; users_total: number; dragons_collected_total: number;
  suspicious_total: number;
  total_norm_crosses: number;
  total_shop_crosses: number;
}

interface SuspiciousItem {
  id: number; user_id: number; name: string; dragon_id: number | null; dragon_name: string | null;
  step_number: number; declared_crosses: number; normal_crosses: number; mode: string; created_at: string;
}

interface SuspiciousFeed {
  total_pending: number;
  items: SuspiciousItem[];
}

interface ServiceStatus {
  status: string;
  last_seen: string | null;
}

interface Health {
  services: Record<string, ServiceStatus>;
  checked_at: string;
}

function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [cheats, setCheats] = useState<SuspiciousFeed | null>(null);
  const navigate = useNavigate();

  const fetchHealth = useCallback(() => {
    client.get('/admin/health').then((r) => setHealth(r.data)).catch(() => {});
  }, []);

  const fetchCheats = useCallback(() => {
    client.get('/admin/suspicious/recent').then((r) => setCheats(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    client.get('/admin/stats').then((r) => setStats(r.data)).catch(() => {});
    fetchHealth();
    fetchCheats();
    const timer = setInterval(() => { fetchHealth(); fetchCheats(); }, 30000);
    return () => clearInterval(timer);
  }, [fetchHealth, fetchCheats]);

  const cards = [
    { value: stats?.dragons_total ?? '—', label: 'Всего драконов', icon: '🐲' },
    { value: stats?.dragons_active ?? '—', label: 'Активных', icon: '✨' },
    { value: stats?.pins_total ?? '—', label: 'Всего PIN', icon: '🔑' },
    { value: stats?.pins_active ?? '—', label: 'PIN активны', icon: '🟢' },
    { value: stats?.users_total ?? '—', label: 'Игроков', icon: '👥' },
    { value: stats?.dragons_collected_total ?? '—', label: 'Выращено', icon: '⭐' },
    { value: stats?.total_norm_crosses?.toLocaleString('ru-RU') ?? '—', label: 'Норм крестиков', icon: '🧵' },
    { value: stats?.total_shop_crosses?.toLocaleString('ru-RU') ?? '—', label: 'Крестиков в магазине', icon: '🛒' },
  ];

  const statusEmoji = (s: string) => {
    if (s === 'online') return '🟢';
    if (s === 'offline') return '🔴';
    return '⚪';
  };

  const statusLabel = (s: string) => {
    if (s === 'online') return 'Онлайн';
    if (s === 'offline') return 'Офлайн';
    return 'Нет данных';
  };

  const formatDate = (s: string | null) => {
    if (!s) return '—';
    try { return new Date(s).toLocaleString('ru-RU'); } catch { return s; }
  };

  const cheatItems = cheats?.items ?? [];

  return (
    <>
      <div className="lair-header"><h2>Дашборд</h2></div>
      <div className="lair-content">
        {cheatItems.length > 0 && (
          <motion.div
            className="lair-card"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={{ marginBottom: 24, borderLeft: '3px solid var(--fire)' }}
          >
            <h3 style={{ color: '#d474a0', margin: '0 0 12px', fontSize: 16 }}>
              ⚠ Подозрение на читерство ({cheats?.total_pending ?? cheatItems.length})
            </h3>
            <div className="lair-table-responsive">
              <table className="lair-table">
                <thead><tr><th>Дата</th><th>Игрок</th><th>Дракон</th><th>Шаг</th><th>Заявлено</th><th>Норма</th><th></th></tr></thead>
                <tbody>{cheatItems.map((c) => (
                  <tr key={c.id}>
                    <td style={{ fontSize: 13 }}>{c.created_at?.slice(0, 16).replace('T', ' ')}</td>
                    <td style={{ fontWeight: 600 }}>{c.name}</td>
                    <td style={{ fontSize: 13 }}>{c.dragon_name || '—'}</td>
                    <td>{c.step_number}</td>
                    <td style={{ color: '#d474a0', fontWeight: 700 }}>{c.declared_crosses}</td>
                    <td>{c.normal_crosses}</td>
                    <td>
                      <button className="lair-btn lair-btn-sm" onClick={() => navigate(`/admin/users?vk_id=${c.user_id}`)}>
                        Перейти →
                      </button>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </motion.div>
        )}

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
          <motion.div
            className="lair-stat-card"
            onClick={() => navigate('/admin/suspicious')}
            initial={{ opacity: 0, y: 20, rotateX: 10 }}
            animate={{ opacity: 1, y: 0, rotateX: 0 }}
            transition={{ delay: cards.length * 0.06, duration: 0.5, ease: 'easeOut' }}
            style={{ cursor: 'pointer', borderLeft: '3px solid var(--fire)' }}
          >
            <div className="lair-stat-value" style={{ color: '#d474a0' }}>{stats?.suspicious_total ?? '—'}</div>
            <div className="lair-stat-label">⚠ Подозрительные отчёты →</div>
          </motion.div>
        </div>

        <h3 style={{ color: 'var(--gold)', margin: '28px 0 14px', fontSize: 17 }}>Состояние сервисов</h3>
        <div className="lair-stat-grid">
          {health?.services && Object.entries(health.services).map(([name, svc]) => (
            <motion.div
              key={name}
              className="lair-stat-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              style={{
                borderLeft: svc.status === 'online' ? '3px solid var(--success)' : '3px solid var(--fire)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 24 }}>{statusEmoji(svc.status)}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 16, textTransform: 'uppercase', color: 'var(--gold)' }}>
                    {name === 'bot' ? '🤖 Бот' : name === 'donor_sync' ? '💎 Бот донатов' : name}
                  </div>
                  <div style={{ fontSize: 14, color: svc.status === 'online' ? 'var(--success)' : 'var(--fire)', fontWeight: 600 }}>
                    {statusLabel(svc.status)}
                  </div>
                </div>
              </div>
              <div style={{ fontSize: 12, color: 'var(--parchment-faded)', marginTop: 8 }}>
                Обновлён: {formatDate(svc.last_seen)}
              </div>
            </motion.div>
          ))}
          {!health && (
            <div className="lair-stat-card" style={{ opacity: 0.5 }}>
              <span style={{ fontSize: 24 }}>⚪</span>
              <div style={{ fontWeight: 600, fontSize: 14 }}>Загрузка...</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default Dashboard;
