import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { api } from '../services/api'

export interface User {
  id: number;
  name: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAdmin: boolean;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (name: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(api.getToken());
  const [loading, setLoading] = useState(true);

  const isAdmin = user?.role === 'ADMIN';
  const isAuthenticated = !!user && !!token;

  // On mount: validate stored token
  useEffect(() => {
    const storedToken = api.getToken();
    if (storedToken) {
      api.me()
        .then((data) => {
          setUser(data);
          setToken(storedToken);
        })
        .catch(() => {
          // Token invalid — clear
          api.setToken(null);
          setToken(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    api.setToken(data.token);
    setToken(data.token);
    setUser(data.user);
  }, []);

  const register = useCallback(async (name: string, username: string, password: string) => {
    const data = await api.register(name, username, password);
    api.setToken(data.token);
    setToken(data.token);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    api.setToken(null);
    setToken(null);
    setUser(null);
    window.location.href = '/login';
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isAdmin, isAuthenticated, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
