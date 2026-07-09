import { useEffect, useState, useCallback } from 'react';
import client from '../../api/client';
import { useTableControls, type Column } from '../../components/admin/useTableControls';
import { DataTableHead, TableToolbar } from '../../components/admin/DataTable';

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

const COLUMNS: Column<SuspiciousItem>[] = [
  { key: 'user_id', label: 'VK ID', value: (r) => String(r.user_id), sortValue: (r) => r.user_id, filter: 'text' },
  { key: 'name', label: 'ФИО', value: (r) => r.name, filter: 'text' },
  { key: 'chat', label: 'Чат' },
  { key: 'message', label: 'Сообщение', value: (r) => r.message, filter: 'text' },
  { key: 'declared', label: 'Заявлено', value: (r) => String(r.declared_crosses), sortValue: (r) => r.declared_crosses },
  { key: 'normal', label: 'Норма', value: (r) => String(r.normal_crosses), sortValue: (r) => r.normal_crosses },
  { key: 'mode', label: 'Режим', value: (r) => r.mode, filter: 'select' },
  { key: 'created_at', label: 'Дата', value: (r) => r.created_at, sortValue: (r) => r.created_at },
  { key: 'actions', label: '' },
];

function SuspiciousList() {
  const [items, setItems] = useState<SuspiciousItem[]>([]);
  const [load, setLoad] = useState(true);
  const t = useTableControls(items, COLUMNS);

  const fetchItems = useCallback(() => {
    setLoad(true);
    client.get('/admin/suspicious/detailed')
      .then((r) => setItems(r.data.items))
      .finally(() => setLoad(false));
  }, []);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const remove = async (id: number) => {
    if (!window.confirm('Удалить этот подозрительный отчёт?')) return;
    try {
      await client.delete(`/admin/suspicious/${id}`);
      setItems((prev) => prev.filter((x) => x.id !== id));
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
            <TableToolbar controls={t} />
            <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="lair-table">
                <DataTableHead controls={t} allRows={items} />
                <tbody>
                  {t.rows.map((r) => (
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
                      <td>{r.mode}</td>
                      <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(r.created_at)}</td>
                      <td>
                        <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => remove(r.id)}>
                          🗑 Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                  {t.rows.length === 0 && (
                    <tr><td colSpan={9} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Ничего не найдено</td></tr>
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
