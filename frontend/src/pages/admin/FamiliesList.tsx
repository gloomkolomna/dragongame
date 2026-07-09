import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';
import { useTableControls, type Column } from '../../components/admin/useTableControls';
import { DataTableHead, TableToolbar } from '../../components/admin/DataTable';

interface Family { id: number; name: string; description: string; sort_order: number; color: string; image_path: string; dragon_count: number; }

const COLUMNS: Column<Family>[] = [
  { key: 'icon', label: '', width: 40 },
  { key: 'name', label: 'Название', value: (f) => f.name, filter: 'text' },
  { key: 'description', label: 'Описание', value: (f) => f.description, filter: 'text' },
  { key: 'color', label: 'Цвет', value: (f) => f.color || '#9b6fc7' },
  { key: 'sort_order', label: 'Порядок', value: (f) => String(f.sort_order), sortValue: (f) => f.sort_order },
  { key: 'dragon_count', label: 'Драконов', value: (f) => String(f.dragon_count), sortValue: (f) => f.dragon_count },
  { key: 'actions', label: '', width: 100 },
];

function FamiliesList() {
  const [families, setFamilies] = useState<Family[]>([]);
  const [load, setLoad] = useState(true);
  const nav = useNavigate();
  const t = useTableControls(families, COLUMNS);

  useEffect(() => {
    client.get('/admin/families').then((r) => setFamilies(r.data)).finally(() => setLoad(false));
  }, []);

  const del = async (id: number) => {
    if (!confirm('Удалить семейство / союз? Драконы останутся без него.')) return;
    await client.delete(`/admin/families/${id}`);
    setFamilies((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <>
      <div className="lair-header">
        <h2>📂 Семейства / Союзы</h2>
        <button className="lair-btn" style={{ marginLeft: 'auto' }} onClick={() => nav('/admin/families/new')}>+ Создать</button>
      </div>
      <div className="lair-content">
        <TableToolbar controls={t} />
        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          {load ? <div className="lair-skeleton" /> : (
            <table className="lair-table">
              <DataTableHead controls={t} allRows={families} />
              <tbody>{t.rows.map((f) => (
                <tr key={f.id}>
                  <td><div style={{ width: 20, height: 20, borderRadius: 6, background: f.color || '#9b6fc7', border: '2px solid var(--bronze)' }} /></td>
                  <td style={{ fontWeight: 600 }}>{f.name}</td>
                  <td style={{ color: 'var(--parchment-dim)', fontSize: 14 }}>{f.description}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}>{f.color || '#9b6fc7'}</td>
                  <td>{f.sort_order}</td>
                  <td>{f.dragon_count}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => nav(`/admin/families/${f.id}/edit`)}>✎</button>
                      <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => del(f.id)}>✕</button>
                    </div>
                  </td>
                </tr>
              ))}
              {t.rows.length === 0 && <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>Ничего не найдено</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

export default FamiliesList;
