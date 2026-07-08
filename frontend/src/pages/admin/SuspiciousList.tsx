import { useEffect, useState, useCallback } from 'react';
import client from '../../api/client';

interface SuspiciousItem {
  id: number;
  user_id: number;
  name: string;
  chat_url: string;
  message: string;
  declared_crosses: number;
  normal_crosses: number;
  mode: string;
  step_number: number;
  created_at: string;
}

function SuspiciousList() {
  const [items, setItems] = useState<SuspiciousItem[]>([]);
  const [total, setTotal] = useState(0);
  const [load, setLoad] = useState(true);

  const fetchItems = useCallback(() => {
    setLoad(true);
    client.get('/admin/suspicious/detailed')
      .then((r) => { setItems(r.data.items); setTotal(r.data.total); })
      .finally(() => setLoad(false));
  }, []);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const remove = async (id: number) => {
    if (!window.confirm('Удалить этот подозрительный отчёт?')) return;
    try {
      await client.delete(`/admin/suspicious/${id}`);
      setItems((prev) => prev.filter((x) => x.id !== id));
      setTotal((t) => Math.max(0, t - 1));
    } catch {
      alert('Ошибка удаления');
    }
  };

  const formatDate = (s: string) => s ? new Date(s).toLocaleString('ru-RU') : '—';

  return (
    <>
      <div className="lair-header"><h2>⚠ Подозрительные отчёты</h2></div>
      <div className="lair-content">
        {load ? (
          <div className="lair-skeleton" />
        ) : (
          <>
            <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
              Всего: {total}
            </div>
            <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="lair-table">
                <thead>
                  <tr>
                    <th>VK ID</th>
                    <th>ФИО</th>
                    <th>Чат</th>
                    <th>Сообщение</th>
                    <th>Заявлено</th>
                    <th>Норма</th>
                    <th>Дата</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((r) => (
                    <tr key={r.id}>
                      <td>{r.user_id}</td>
                      <td style={{ fontWeight: 600 }}>{r.name}</td>
                      <td>
                        <a href={r.chat_url} target="_blank" rel="noreferrer" className="lair-btn lair-btn-sm lair-btn-outline">
                          Открыть чат →
                        </a>
                      </td>
                      <td style={{ maxWidth: 360, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 13 }}>
                        {r.message || '—'}
                      </td>
                      <td style={{ color: '#d474a0', fontWeight: 700 }}>{r.declared_crosses}</td>
                      <td>{r.normal_crosses}</td>
                      <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(r.created_at)}</td>
                      <td>
                        <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => remove(r.id)}>
                          🗑 Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr><td colSpan={8} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Подозрительных отчётов нет</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default SuspiciousList;
