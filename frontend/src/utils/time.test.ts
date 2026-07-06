import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formatRemaining } from './time';

const REAL_NOW = Date.now();

function setNow(iso: string) {
  vi.setSystemTime(new Date(iso));
}

function makeUntil(minutesFromNow: number): string {
  const d = new Date(Date.now() + minutesFromNow * 60000);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

describe('formatRemaining', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns 0м for expired timeout', () => {
    setNow('2026-07-06T10:30:00+03:00');
    expect(formatRemaining('2026-07-06T10:00:00')).toBe('0м');
  });

  it('returns 0м for exactly now', () => {
    setNow('2026-07-06T10:30:00+03:00');
    expect(formatRemaining('2026-07-06T10:30:00')).toBe('0м');
  });

  it('shows minutes when less than 1 hour remains', () => {
    setNow('2026-07-06T10:00:00+03:00');
    expect(formatRemaining('2026-07-06T10:45:00')).toBe('45м');
  });

  it('shows minutes with ceil when less than 1 hour with seconds', () => {
    setNow('2026-07-06T10:00:00+03:00');
    expect(formatRemaining('2026-07-06T10:44:30')).toBe('45м');
  });

  it('shows hours and minutes when more than 1 hour', () => {
    setNow('2026-07-06T10:00:00+03:00');
    expect(formatRemaining('2026-07-06T11:30:00')).toBe('1ч 30м');
  });

  it('shows 1 hour when ceil wraps 59.5 minutes', () => {
    setNow('2026-07-06T10:00:00+03:00');
    expect(formatRemaining('2026-07-06T10:59:30')).toBe('1ч 0м');
  });

  it('shows 1м for 30 seconds remaining', () => {
    setNow('2026-07-06T10:00:00+03:00');
    expect(formatRemaining('2026-07-06T10:00:30')).toBe('1м');
  });

  it('handles timezone offset in string', () => {
    setNow('2026-07-06T10:00:00+03:00');
    expect(formatRemaining('2026-07-06T10:45:00+03:00')).toBe('45м');
  });

  it('handles date rollover across midnight', () => {
    setNow('2026-07-06T23:30:00+03:00');
    expect(formatRemaining('2026-07-07T00:15:00')).toBe('45м');
  });
});
