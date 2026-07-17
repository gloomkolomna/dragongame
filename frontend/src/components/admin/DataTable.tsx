import { useMemo } from 'react';
import type { Column, TableControls } from './useTableControls';

function SortIcon({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
  if (!active) return <span style={{ opacity: 0.3, marginLeft: 3 }}>⇅</span>;
  return <span style={{ marginLeft: 3 }}>{dir === 'asc' ? '↑' : '↓'}</span>;
}

interface HeadProps<T> {
  controls: TableControls<T>;
  allRows: T[];
}

export function DataTableHead<T>({ controls, allRows }: HeadProps<T>) {
  const { columns, sortKey, sortDir, toggleSort, filters, setFilter } = controls;

  const hasFilters = columns.some((c) => c.filter);

  const optionsFor = (c: Column<T>): string[] => {
    if (c.options) return c.options;
    const set = new Set<string>();
    if (c.filterValues) {
      allRows.forEach((r) => {
        c.filterValues!(r).forEach((v) => {
          const s = String(v ?? '').trim();
          if (s) set.add(s);
        });
      });
      return Array.from(set).sort((a, b) => a.localeCompare(b));
    }
    if (!c.value) return [];
    allRows.forEach((r) => {
      const v = String(c.value!(r) ?? '').trim();
      if (v) set.add(v);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  };

  return (
    <thead>
      <tr>
        {columns.map((c) => {
          const sortable = c.sortable !== false && (!!c.value || !!c.sortValue);
          return (
            <th
              key={c.key}
              onClick={sortable ? () => toggleSort(c.key) : undefined}
              style={{
                ...(c.width ? { width: c.width } : {}),
                ...(sortable ? { cursor: 'pointer', userSelect: 'none' } : {}),
                ...(c.thStyle || {}),
              }}
            >
              {c.label}
              {sortable && <SortIcon active={sortKey === c.key} dir={sortDir} />}
            </th>
          );
        })}
      </tr>
      {hasFilters && (
        <tr>
          {columns.map((c) => (
            <th key={c.key} style={{ paddingTop: 4, paddingBottom: 8 }}>
              {c.filter === 'text' && (
                <input
                  className="lair-input"
                  value={filters[c.key] || ''}
                  onChange={(e) => setFilter(c.key, e.target.value)}
                  placeholder="..."
                  style={{ width: '100%', padding: '4px 8px', fontSize: 15 }}
                />
              )}
              {c.filter === 'select' && (
                <select
                  className="lair-input"
                  value={filters[c.key] || ''}
                  onChange={(e) => setFilter(c.key, e.target.value)}
                  style={{ width: '100%', padding: '4px 8px', fontSize: 15 }}
                >
                  <option value="">Все</option>
                  {optionsFor(c).map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              )}
            </th>
          ))}
        </tr>
      )}
    </thead>
  );
}

interface ToolbarProps<T> {
  controls: TableControls<T>;
  placeholder?: string;
}

export function TableToolbar<T>({ controls, placeholder }: ToolbarProps<T>) {
  const active = controls.search || Object.values(controls.filters).some((v) => v) || controls.sortKey;
  const showReset = useMemo(() => !!active, [active]);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
      <input
        className="lair-input"
        value={controls.search}
        onChange={(e) => controls.setSearch(e.target.value)}
        placeholder={placeholder || '🔍 Поиск...'}
        style={{ maxWidth: 300, fontSize: 16, padding: '8px 12px' }}
      />
      <span style={{ color: 'var(--parchment-faded)', fontSize: 14 }}>
        Показано {controls.shown} из {controls.total}
      </span>
      {showReset && (
        <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={controls.reset}>Сбросить</button>
      )}
    </div>
  );
}
