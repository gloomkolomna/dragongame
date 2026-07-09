import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';
import { useTableControls, type Column } from '../../components/admin/useTableControls';
import { DataTableHead, TableToolbar } from '../../components/admin/DataTable';

interface Treasure {
  id: number;
  name: string;
  description: string;
  image_path: string;
  dragon_id: number;
  is_active: boolean;
}

const COLUMNS: Column<Treasure>[] = [
  { key: 'image', label: '', width: 60 },
  { key: 'name', label: 'Название', value: (t) => t.name, filter: 'text' },
  { key: 'description', label: 'Описание', value: (t) => t.description, filter: 'text' },
  { key: 'dragon', label: 'Дракон', value: (t) => `#${t.dragon_id}`, sortValue: (t) => t.dragon_id },
  { key: 'actions', label: '', width: 60 },
];

function TreasuresList() {
  const nav = useNavigate();
  const [items, setItems] = useState<Treasure[]>([]);
  const [loading, setLoading] = useState(true);
  const t = useTableControls(items, COLUMNS);

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
          <div className="lair-skeleton" />
        ) : items.length === 0 ? (
          <div className="lair-card"><p style={{ color: 'var(--text-secondary)' }}>Сокровищ пока нет. Нажми «➕ Создать» выше или создай сокровище из карточки редкого дракона.</p></div>
        ) : (
          <>
            <TableToolbar controls={t} />
            <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="lair-table">
                <DataTableHead controls={t} allRows={items} />
                <tbody>
                  {t.rows.map((tr) => (
                    <tr key={tr.id} className="clickable" onClick={() => nav(`/admin/dragons/${tr.dragon_id}/treasure`)}>
                      <td>{tr.image_path && <img src={`/dragons${tr.image_path}`} alt="" style={{ width: 48, height: 48, objectFit: 'contain', borderRadius: 6 }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />}</td>
                      <td>{tr.name}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{tr.description}</td>
                      <td>#{tr.dragon_id}</td>
                      <td><button className="lair-btn lair-btn-sm lair-btn-outline" onClick={(e) => { e.stopPropagation(); nav(`/admin/dragons/${tr.dragon_id}/treasure`); }}>✎</button></td>
                    </tr>
                  ))}
                  {t.rows.length === 0 && <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>Ничего не найдено</td></tr>}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default TreasuresList;
