import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

interface AuthContextType {
  isAuthenticated: boolean;
  user: any | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  token: null,
  login: async () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const navigate = useNavigate();

  useEffect(() => {
    const initialToken = localStorage.getItem('token');
    setToken(initialToken);
    if (initialToken) {
      api.defaults.headers.common['Authorization'] = `Token ${initialToken}`;
      checkAuthStatus(initialToken);
    } else {
      setIsAuthenticated(false);
      setUser(null);
    }
  }, []);

  const checkAuthStatus = async (currentToken: string | null) => {
    if (!currentToken) {
      handleLogout();
      return;
    }
    try {
      api.defaults.headers.common['Authorization'] = `Token ${currentToken}`;
      const response = await api.get('/api/auth/user/');
      setUser(response.data);
      setIsAuthenticated(true);
      setToken(currentToken);
    } catch (error) {
      console.error('Auth check failed:', error);
      handleLogout();
    }
  };

  const handleLogin = async (email: string, password: string) => {
    try {
      const response = await api.post('/api/auth/login/', {
        email,
        password,
      });

      const { token: newToken } = response.data;
      localStorage.setItem('token', newToken);
      api.defaults.headers.common['Authorization'] = `Token ${newToken}`;
      setToken(newToken);
      setIsAuthenticated(true);
      await checkAuthStatus(newToken);
      navigate('/');
    } catch (error) {
      console.error('Login failed:', error);
      handleLogout();
      throw new Error('Login fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
    setIsAuthenticated(false);
    setToken(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        token,
        login: handleLogin,
        logout: handleLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}; 