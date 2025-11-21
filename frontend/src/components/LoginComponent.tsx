// frontend/src/components/LoginComponent.tsx

import React, { useState } from 'react';
import { loginUser, setAuthToken } from '../api/api';

interface LoginComponentProps {
  onLogin: (token: string) => void;
  onToggleToRegister: () => void; // <<< Included the new prop in the interface
}

const LoginComponent: React.FC<LoginComponentProps> = ({ onLogin, onToggleToRegister }) => { // <<< Destructured the new prop
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); // Clear previous errors

    try {
      // 1. Call your Django /api/token-auth/ endpoint
      const response = await loginUser(username, password);
      const token = response.data.token;

      if (token) {
        // 2. Set the token in the global axios instance
        setAuthToken(token); 
        // 3. Pass the token up to the App.tsx component to update the UI
        onLogin(token); 
      } else {
        setError('Login failed: Token not received.');
      }
    } catch (err) {
      // Handle 400 Bad Request, 401 Unauthorized, or other network errors
      setError('Login failed. Check username and password.');
      console.error("Login Error:", err);
    }
  };

  return (
    
    <div style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '8px', maxWidth: '400px', margin: '20px auto' }}>
      <h2>API Login</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Username:</label>
          <input 
            type="text" 
            value={username} 
            onChange={(e) => setUsername(e.target.value)} 
            required
            style={{ display: 'block', margin: '5px 0 15px 0', padding: '8px', width: '100%' }}
          />
        </div>
        <div>
          <label>Password:</label>
          <input 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            required
            style={{ display: 'block', margin: '5px 0 15px 0', padding: '8px', width: '100%' }}
          />
        </div>
        <button type="submit" style={{ padding: '10px 15px' }}>Login</button>
        {error && <p style={{ color: 'red', marginTop: '10px' }}>{error}</p>}
      </form>
      
      {/* ADDED: Link to toggle to the Registration view */}
      <p style={{ marginTop: '15px', textAlign: 'center' }}>
          Don't have an account? <a href="#" onClick={onToggleToRegister}>Register here</a>
      </p>

    </div>
  );
};

export default LoginComponent;