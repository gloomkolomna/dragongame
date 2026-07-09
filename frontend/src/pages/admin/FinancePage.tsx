import { useState } from 'react';
import FinanceOrders from './FinanceOrders';
import PricingConfig from './PricingConfig';
import DragonSets from './DragonSets';

interface WithHide {
  hideHeader?: boolean;
}

const TABS: { key: string; label: string; component: React.ComponentType<WithHide> }[] = [
  { key: 'orders', label: '🧾 Платежи', component: FinanceOrders },
  { key: 'pricing', label: '💰 Цена яйца', component: PricingConfig },
  { key: 'sets', label: '📦 Наборы', component: DragonSets },
];

function FinancePage() {
  const [tab, setTab] = useState('orders');
  const Active = TABS.find((t) => t.key === tab)?.component || FinanceOrders;

  return (
    <>
      <div className="lair-header" style={{ flexWrap: 'wrap', gap: 8, paddingBottom: 12 }}>
        <h2 style={{ flexShrink: 0 }}>💳 Финансы</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              className={tab === t.key ? 'lair-btn' : 'lair-btn lair-btn-outline'}
              style={{ fontSize: 15 }}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <Active hideHeader />
    </>
  );
}

export default FinancePage;
