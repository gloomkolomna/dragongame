import { useEffect, useState } from 'react';
import client from '../../api/client';

interface Dragon { id: number; name: string; pin_code: string | null; rarity: number; egg_type: string; is_active: boolean; steps_count: number; }

function PinManager() {
  const [dragons, setDragons] = useState<Dragon[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get('/admin/pins').then((r) => setDragons(r.data)).finally(() => setLoading(false));
  }, []);

  const rarityLabel = (r: number) => ['', 'Common', 'Rare', 'Legendary'][r] || 'Common';
  const rarityCls = (r: number) => ['', 'lair-badge-common', 'lair-badge-rare', 'lair-badge-legendary'][r] || 'lair-badge-common';

  return (
    <>
      <div className="lair-header">
        <h2>🔑 PIN-коды</h2>
      </div>
      <div className="lair-content">
        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="lair-table">
            <thead><tr><th>Дракон</th><th>PIN-код</th><th>Редкость</th><th>Тип яйца</th><th>Шагов</th><th>Активен</th></tr></thead>
            <tbody>{dragons.map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: 18, letterSpacing: 4, color: d.pin_code ? 'var(--gold)' : 'var(--parchment-faded)' }}>
                  {d.pin_code || '—'}
                </td>
                <td><span className={`lair-badge ${rarityCls(d.rarity)}`}>{rarityLabel(d.rarity)}</span></td>
                <td>{d.egg_type}</td>
                <td>{d.steps_count}</td>
                <td>{d.is_active ? '✅' : '❌'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default PinManager;
