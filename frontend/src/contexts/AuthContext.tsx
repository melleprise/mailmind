import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/api'; // Keep this correct import
import { getErrorMessage } from '../utils/error'; // Import error helper

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  login: (token: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

interface User {
  email: string;
  id: number; // Changed from pk to id, and made it required
  // Add other user properties as needed
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));

  const navigate = useNavigate();

  // Run checkAuth when the component mounts
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const storedToken = localStorage.getItem('token');
    setToken(storedToken);
    if (!storedToken) {
      setIsAuthenticated(false);
      setUser(null);
      setLoading(false);
      return;
    }

    // Ensure the api instance uses the token for this request
    // (interceptor should handle this, but added safeguard)
    // api.defaults.headers.common['Authorization'] = `Token ${token}`;

    try {
      // Token exists, verify it by fetching user data
      const userData = await authApi.getCurrentUser();
      setIsAuthenticated(true);
      setUser(userData); // Set user data from API response
    } catch (error) {
      console.error("Auth check failed:", getErrorMessage(error));
      // Token is invalid or expired, or API error
      // Clear potentially invalid token and reset state
      localStorage.removeItem('token'); 
      setToken(null);
      setIsAuthenticated(false);
      setUser(null);
      // No navigation here, let protected routes handle redirect if needed
    } finally {
      setLoading(false); // Finished loading
    }
  };

  const login = async (tokenValue: string): Promise<void> => {
    setLoading(true);
    localStorage.setItem('token', tokenValue);
    setToken(tokenValue);
    // Ensure the api instance uses the new token for the next request
    // api.defaults.headers.common['Authorization'] = `Token ${token}`;
    
    try {
      // Fetch user data after successful login to ensure user state is correct
      const userData = await authApi.getCurrentUser();
      setIsAuthenticated(true);
      setUser(userData);
      setLoading(false);
      navigate('/leads'); // Nach Login zu /leads weiterleiten
    } catch (error) {
      console.error("Failed to fetch user data after login:", getErrorMessage(error));
      // Handle case where fetching user data fails even after login response was okay
      logout(); // Log out if user data cannot be fetched
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    // delete api.defaults.headers.common['Authorization']; // Clear token from axios instance
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    setLoading(false); // Set loading false on logout
    navigate('/login');
  };

  const value = {
    isAuthenticated,
    user,
    token,
    login,
    logout,
    loading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext; 