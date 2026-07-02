import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import bridge, { parseURLSearchParamsForGetLaunchParams } from '@vkontakte/vk-bridge';

interface VkContextType {
  vkUserId: number | null;
  isVkWebView: boolean;
  isDemo: boolean;
  launchParams: Record<string, string>;
  loading: boolean;
}

const VkBridgeContext = createContext<VkContextType>({
  vkUserId: null,
  isVkWebView: false,
  isDemo: false,
  launchParams: {},
  loading: true,
});

const DEMO_VK_ID = import.meta.env.VITE_DEMO_VK_ID
  ? Number(import.meta.env.VITE_DEMO_VK_ID)
  : null;

function parseVkParams(): { vkUserId: number | null; params: Record<string, string> } {
  // Запасной способ: разбор query-string (работает и вне VK-окружения).
  const qs = window.location.search.substring(1);
  const params: Record<string, string> = {};
  let vkUserId: number | null = null;

  qs.split('&').forEach((p) => {
    const [k, v] = p.split('=');
    if (!k) return;
    const val = decodeURIComponent(v || '');
    params[k] = val;
    if (k === 'vk_user_id') vkUserId = Number(val);
  });

  return { vkUserId, params };
}

export function VkBridgeProvider({ children }: { children: ReactNode }) {
  const [vkUserId, setVkUserId] = useState<number | null>(null);
  const [isVkWebView, setIsVkWebView] = useState(false);
  const [isDemo, setIsDemo] = useState(false);
  const [launchParams, setLaunchParams] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      // 1. Запускаем приложение в VK — ОБЯЗАТЕЛЬНЫЙ вызов для Mini App.
      //    Без него VK считает приложение «не инициализированным».
      //    send() безопасен и вне VK (вернёт reject/timeout), поэтому вызываем всегда.
      try {
        await bridge.send('VKWebAppInit');
      } catch {
        // вне VK-окружения — нормально, идём дальше
      }

      if (cancelled) return;

      // 2. Определяем параметры запуска. В VK-окружении bridge даёт их напрямую,
      //    вне VK — разбираем query-string (dev-режим / прямой переход).
      let id: number | null = null;
      let params: Record<string, string> = {};
      let inVk = false;

      try {
        const lp = parseURLSearchParamsForGetLaunchParams(window.location.search);
        if (lp && (lp as any).vk_user_id) {
          inVk = true;
          id = Number((lp as any).vk_user_id);
          params = Object.fromEntries(
            Object.entries(lp as any).map(([k, v]) => [k, String(v)])
          ) as Record<string, string>;
        }
      } catch {
        // функция может бросать вне VK-окружения
      }

      if (!id) {
        const fallback = parseVkParams();
        if (fallback.vkUserId) {
          inVk = true;
          id = fallback.vkUserId;
          params = fallback.params;
        }
      }

      if (id) {
        setIsVkWebView(true);
        setVkUserId(id);
        setLaunchParams(params);
      } else if (DEMO_VK_ID) {
        setIsDemo(true);
        setVkUserId(DEMO_VK_ID);
      }

      if (!cancelled) setLoading(false);
    }

    init();
    return () => { cancelled = true; };
  }, []);

  return (
    <VkBridgeContext.Provider value={{ vkUserId, isVkWebView, isDemo, launchParams, loading }}>
      {children}
    </VkBridgeContext.Provider>
  );
}

export function useVkBridge() {
  return useContext(VkBridgeContext);
}
