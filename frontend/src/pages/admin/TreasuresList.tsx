import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Treasure {
  id: number;
  name: string;
  description: string;
  image_path: string;
  dragon_id: number;
  is_active: boolean;
}

function TreasuresList() {
  const nav = useNavigate();
  const [items, setItems] = useState<Treasure[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get('/admin/treasures').then((r) => setItems(r.data)).finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="lair-header" style={{ display: 'flex', alignItems: 'center' }}>
        <h2>💎 Сокровища</h2>
        <button className="lair-btn lair-btn-sm" style={{ marginLeft: 'auto' }} onClick={() => nav('/admin/treasures/new')}>➕ Создать</button>
      </div>
      <div className="lair-content">
        {loading ? (
          <div className="dragon-skeleton-card" style={{ height: 200 }} />
        ) : items.length === 0 ? (
          <div className="lair-card"><p style={{ color: 'var(--text-secondary)' }}>Сокровищ пока нет. Нажми «➕ Создать» выше или создай сокровище из карточки редкого дракона.</p></div>
        ) : (
          <table className="lair-table">
            <thead>
              <tr><th></th><th>Название</th><th>Описание</th><th>Дракон</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((t) => (
                <tr key={t.id} className="clickable" onClick={() => nav(`/admin/dragons/${t.dragon_id}/treasure`)}>
                  <td>{t.image_path && <img src={`/dragons${t.image_path}`} alt="" style={{ width: 48, height: 48, objectFit: 'contain', borderRadius: 6 }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />}</td>
                  <td>{t.name}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t.description}</td>
                  <td>#{t.dragon_id}</td>
                  <td><button className="lair-btn lair-btn-sm lair-btn-outline" onClick={(e) => { e.stopPropagation(); nav(`/admin/dragons/${t.dragon_id}/treasure`); }}>✎</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <style>{`.dragon-skeleton-card{height:200px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shimmer 1.5s infinite}@keyframes shimmer{0%{opacity:.4}50%{opacity:.7}100%{opacity:.4}}`}</style>
    </>
  );
}

export default TreasuresList;
