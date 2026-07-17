import { useMemo, useState } from 'react';

export interface Column<T> {
  key: string;
  label: string;
  value?: (row: T) => string;
  filterValues?: (row: T) => string[];
  sortValue?: (row: T) => string | number;
  sortable?: boolean;
  filter?: 'text' | 'select';
  options?: string[];
  width?: number;
  thStyle?: React.CSSProperties;
}

export interface TableControls<T> {
  rows: T[];
  total: number;
  shown: number;
  search: string;
  setSearch: (v: string) => void;
  sortKey: string | null;
  sortDir: 'asc' | 'desc';
  toggleSort: (key: string) => void;
  filters: Record<string, string>;
  setFilter: (key: string, val: string) => void;
  columns: Column<T>[];
  reset: () => void;
}

export function useTableControls<T>(rows: T[], columns: Column<T>[]): TableControls<T> {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [filters, setFilters] = useState<Record<string, string>>({});

  const colMap = useMemo(() => {
    const m: Record<string, Column<T>> = {};
    columns.forEach((c) => { m[c.key] = c; });
    return m;
  }, [columns]);

  const processed = useMemo(() => {
    let list = [...rows];

    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter((r) =>
        columns.some((c) => c.value && String(c.value(r) ?? '').toLowerCase().includes(q)),
      );
    }

    for (const key of Object.keys(filters)) {
      const val = filters[key];
      if (!val) continue;
      const c = colMap[key];
      if (!c || (!c.value && !c.filterValues)) continue;
      if (c.filter === 'select') {
        if (c.filterValues) {
          list = list.filter((r) => c.filterValues!(r).includes(val));
        } else {
          list = list.filter((r) => String(c.value!(r) ?? '') === val);
        }
      } else {
        const acc = c.value ?? ((r: T) => c.filterValues!(r).join(', '));
        list = list.filter((r) => String(acc(r) ?? '').toLowerCase().includes(val.toLowerCase()));
      }
    }

    if (sortKey) {
      const c = colMap[sortKey];
      const acc = c?.sortValue || c?.value;
      if (acc) {
        list.sort((a, b) => {
          const va = acc(a);
          const vb = acc(b);
          if (typeof va === 'number' && typeof vb === 'number') {
            return sortDir === 'asc' ? va - vb : vb - va;
          }
          const sa = String(va ?? '');
          const sb = String(vb ?? '');
          return sortDir === 'asc' ? sa.localeCompare(sb) : sb.localeCompare(sa);
        });
      }
    }

    return list;
  }, [rows, columns, colMap, search, filters, sortKey, sortDir]);

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const setFilter = (key: string, val: string) => setFilters((p) => ({ ...p, [key]: val }));
  const reset = () => { setSearch(''); setFilters({}); setSortKey(null); setSortDir('asc'); };

  return {
    rows: processed,
    total: rows.length,
    shown: processed.length,
    search, setSearch,
    sortKey, sortDir, toggleSort,
    filters, setFilter,
    columns,
    reset,
  };
}
