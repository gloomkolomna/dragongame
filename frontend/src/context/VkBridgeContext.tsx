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

function parseVkParams(): { vkUserId: number | null; params: Record<string, string> } {
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
    const { vkUserId: id, params } = parseVkParams();

    if (id) {
      setIsVkWebView(true);
      setVkUserId(id);
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
