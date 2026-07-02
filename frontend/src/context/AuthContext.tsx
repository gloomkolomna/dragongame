import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import client from '../api/client';

interface User {
  id: number;
  vk_id: string;
  username: string;
  first_name: string | null;
  last_name: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  setToken: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      delete client.defaults.headers.common['Authorization'];
    }
  }, [token]);

  async function fetchUser() {
    try {
      const response = await client.get('/auth/me');
      setUser(response.data);
    } catch {
      setToken(null);
      localStorage.removeItem('token');
    }
  }

  function setTokenAndSave(newToken: string) {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  }

  function logout() {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
  }

  return (
    <AuthContext.Provider
      value={{ user, token, setToken: setTokenAndSave, logout, isAuthenticated: !!token }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
