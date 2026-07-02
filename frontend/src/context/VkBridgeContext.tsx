import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

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

function parseVkIdFromUrl(): number | null {
  const qs = window.location.search;
  const m = qs.match(/[?&]vk_user_id=(\d+)/);
  if (m) return Number(m[1]);
  return null;
}

export function VkBridgeProvider({ children }: { children: ReactNode }) {
  const [vkUserId, setVkUserId] = useState<number | null>(null);
  const [isVkWebView, setIsVkWebView] = useState(false);
  const [isDemo, setIsDemo] = useState(false);
  const [launchParams, setLaunchParams] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const urlVkId = parseVkIdFromUrl();

    if (urlVkId) {
      setIsVkWebView(true);
      setVkUserId(urlVkId);

      // Parse all vk_ params for future use
      const params: Record<string, string> = {};
      const qs = window.location.search.substring(1);
      qs.split('&').forEach((p) => {
        const [k, v] = p.split('=');
        if (k.startsWith('vk_')) params[k] = decodeURIComponent(v || '');
      });
      setLaunchParams(params);
    } else if (DEMO_VK_ID) {
      setIsDemo(true);
      setVkUserId(DEMO_VK_ID);
    }

    setLoading(false);
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
