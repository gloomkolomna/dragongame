import { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Dragon { id: number; name: string; rarity: number; egg_type: string; steps_count: number; is_active: boolean; family_id: number | null; pin_code: string | null; }
interface Family { id: number; name: string; color: string; }

const RARITY = ['', 'Обычный', 'Редкий', 'Эпический', 'Легендарный'];

type SortCol = 'name' | 'rarity' | 'egg_type' | 'steps_count' | 'is_active' | 'family';

function FilterInput({ col, value, onChange }: { col: string; value: string; onChange: (col: string, val: string) => void }) {
  return (
    <input className="lair-input" value={value}
           onChange={(e) => onChange(col, e.target.value)}
           placeholder="..." style={{ width: '100%', padding: '3px 6px', fontSize: 10, marginTop: 2 }} />
  );
}

function DragonsList() {
  const [dragons, setDragons] = useState<Dragon[]>([]);
  const [families, setFamilies] = useState<Family[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<SortCol>('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      client.get('/admin/dragons'),
      client.get('/admin/families'),
    ]).then(([dr, fa]) => {
      setDragons(dr.data);
      setFamilies(fa.data);
    }).finally(() => setLoading(false));
  }, []);

  const familyMap = useMemo(() => {
    const m: Record<number, Family> = {};
    families.forEach((f) => { m[f.id] = f; });
    return m;
  }, [families]);

  const sorted = useMemo(() => {
    let list = [...dragons];

    const f = (val: string, col: string) => {
      if (!filters[col]) return true;
      return val.toLowerCase().includes(filters[col].toLowerCase());
    };

    list = list.filter((d) =>
      f(d.name, 'name') &&
      f(RARITY[d.rarity], 'rarity') &&
      f(d.egg_type, 'egg_type') &&
      f(String(d.steps_count), 'steps_count') &&
      f(d.pin_code || '', 'pin') &&
      (d.family_id ? f(familyMap[d.family_id]?.name ?? '', 'family') : !filters['family'])
    );

    list.sort((a, b) => {
      let va: any, vb: any;
      switch (sortCol) {
        case 'family':
          va = a.family_id ? familyMap[a.family_id]?.name ?? '' : '';
          vb = b.family_id ? familyMap[b.family_id]?.name ?? '' : '';
          break;
        case 'name': va = a.name; vb = b.name; break;
        case 'rarity': va = a.rarity; vb = b.rarity; break;
        case 'egg_type': va = a.egg_type; vb = b.egg_type; break;
        case 'steps_count': va = a.steps_count; vb = b.steps_count; break;
        case 'is_active': va = a.is_active ? 1 : 0; vb = b.is_active ? 1 : 0; break;
        default: return 0;
      }
      if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortDir === 'asc' ? va - vb : vb - va;
    });
    return list;
  }, [dragons, filters, sortCol, sortDir, familyMap]);

  const toggleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortCol(col); setSortDir('asc'); }
  };

  const handleFilterChange = useCallback((col: string, val: string) => {
    setFilters((prev) => ({ ...prev, [col]: val }));
  }, []);

  const SortIcon = ({ col }: { col: SortCol }) => {
    if (sortCol !== col) return <span style={{ opacity: 0.3, marginLeft: 3 }}>⇅</span>;
    return <span style={{ marginLeft: 3 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <>
      <div className="lair-header">
        <h2>Драконы</h2>
        <span style={{ marginLeft: 'auto', color: 'var(--parchment-faded)', fontSize: 12 }}>{sorted.length} из {dragons.length}</span>
        <button className="lair-btn" style={{ marginLeft: 12 }} onClick={() => navigate('/admin/dragons/new')}>+ Создать</button>
      </div>
      <div className="lair-content">
        {loading ? <div className="lair-skeleton" /> : (
          <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="lair-table">
              <thead>
                <tr>
                  <th onClick={() => toggleSort('family')} style={{ cursor: 'pointer', userSelect: 'none', width: 60 }}>Сем.<SortIcon col="family" /></th>
                  <th onClick={() => toggleSort('name')} style={{ cursor: 'pointer', userSelect: 'none' }}>Имя<SortIcon col="name" /></th>
                  <th onClick={() => toggleSort('rarity')} style={{ cursor: 'pointer', userSelect: 'none' }}>Ред.<SortIcon col="rarity" /></th>
                  <th onClick={() => toggleSort('egg_type')} style={{ cursor: 'pointer', userSelect: 'none' }}>Яйцо<SortIcon col="egg_type" /></th>
                  <th onClick={() => toggleSort('steps_count')} style={{ cursor: 'pointer', userSelect: 'none', width: 70 }}>Шагов<SortIcon col="steps_count" /></th>
                  <th onClick={() => toggleSort('is_active')} style={{ cursor: 'pointer', userSelect: 'none', width: 50 }}>Акт.<SortIcon col="is_active" /></th>
                  <th style={{ width: 80 }}>PIN</th>
                  <th style={{ width: 170 }}></th>
                </tr>
                <tr>
                  <th><FilterInput col="family" value={filters['family'] || ''} onChange={handleFilterChange} /></th>
                  <th><FilterInput col="name" value={filters['name'] || ''} onChange={handleFilterChange} /></th>
                  <th><FilterInput col="rarity" value={filters['rarity'] || ''} onChange={handleFilterChange} /></th>
                  <th><FilterInput col="egg_type" value={filters['egg_type'] || ''} onChange={handleFilterChange} /></th>
                  <th><FilterInput col="steps_count" value={filters['steps_count'] || ''} onChange={handleFilterChange} /></th>
                  <th></th>
                  <th><FilterInput col="pin" value={filters['pin'] || ''} onChange={handleFilterChange} /></th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((d) => {
                  const fam = d.family_id ? familyMap[d.family_id] : null;
                  return (
                    <tr key={d.id}>
                      <td>
                        {fam ? (
                          <div style={{ width: 20, height: 20, borderRadius: 5, background: fam.color, border: '2px solid var(--bronze)', cursor: 'pointer' }}
                               title={`${fam.name} — перейти к сетке`}
                               onClick={(e) => { e.stopPropagation(); navigate(`/admin/grid?family_id=${d.family_id}`); }} />
                        ) : (
                          <div style={{ width: 20, height: 20, borderRadius: 5, border: '2px dashed var(--bronze)', opacity: 0.3 }}
                               title="Без семейства / союза" />
                        )}
                      </td>
                      <td style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/dragons/${d.id}/edit`)}>{d.name}</td>
                      <td><span className={`lair-badge ${['','lair-badge-common','lair-badge-rare','lair-badge-legendary','lair-badge-legendary'][d.rarity] || 'lair-badge-common'}`}>{RARITY[d.rarity]}</span></td>
                      <td>{d.egg_type}</td>
                      <td><span style={{ color: 'var(--gold)', fontWeight: 600 }}>{d.steps_count}</span></td>
                      <td>{d.is_active ? '✅' : '❌'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{d.pin_code || '—'}</td>
                      <td>
                        <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => navigate(`/admin/dragons/${d.id}/steps`)} style={{ marginRight: 4 }}>📝 Шаги</button>
                        <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => navigate(`/admin/dragons/${d.id}/edit`)} style={{ marginRight: 4 }}>Ред.</button>
                        <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => { if (window.confirm(`Удалить «${d.name}»?`)) { client.delete(`/admin/dragons/${d.id}`).then(() => setDragons((prev) => prev.filter((x) => x.id !== d.id))); } }}>Уд.</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

export default DragonsList;
