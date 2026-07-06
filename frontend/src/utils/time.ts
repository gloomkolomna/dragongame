export function formatRemaining(until: string): string {
  const m = until.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
  const target = m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]) : new Date(until);
  const diff = target.getTime() - Date.now();
  console.log('formatRemaining', { until, diff, target: target.toISOString(), now: new Date().toISOString() });
  if (isNaN(diff) || diff <= 0) return '0м';
  const totalMin = Math.ceil(diff / 60000);
  const h = Math.floor(totalMin / 60);
  const mm = totalMin % 60;
  if (h > 0) return `${h}ч ${mm}м`;
  return `${mm}м`;
}
