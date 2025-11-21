// frontend/src/api/api.ts - FINAL, DEFINITIVE FIX

import axios from 'axios';

// CRITICAL FIX: Set the baseURL directly to the Django server's host and port.
// This completely bypasses any potential conflicts with the React proxy setup
const API = axios.create({
  baseURL: 'http://127.0.0.1:8000/', 
  timeout: 5000,
});

// --- Function to set the Authorization Header ---
export const setAuthToken = (token: string | null) => {
  if (token) {
    // Using the 'Token' scheme
    API.defaults.headers.common['Authorization'] = `Token ${token}`;
    window.localStorage.setItem('authToken', token); 
  } else {
    delete API.defaults.headers.common['Authorization'];
    window.localStorage.removeItem('authToken');
  }
};

// --- CRITICAL FIX: Token Reload Logic ---
// Load the token from local storage immediately when the module loads 
// to ensure the Authorization header is set for the very first request
const storedToken = window.localStorage.getItem('authToken');
if (storedToken) {
    setAuthToken(storedToken);
    console.log("Token reloaded from local storage.");
}
// ------------------------------------------


// --- API Endpoint Functions ---

// 1. Initial Login/Token Retrieval - Uses the path relative to the baseURL
// Full request path: http://127.0.0.1:8000/api/token-auth/
export const loginUser = (username: string, password: string) => 
  API.post('api/token-auth/', { username, password });

export interface HistoryPart {
  role: 'user' | 'model'; 
  text: string;
}

// 2. Chat/AI Interaction - Full path: http://127.0.0.1:8000/api/ninja/core/chat
export const sendMessage = (message: string, history: HistoryPart[]) => 
  API.post('api/ninja/core/chat', { message, history });

// 3. Retrieve Found Items - Full path: http://127.0.0.1:8000/api/ninja/core/found_items/
export const getFoundItems = () =>
  API.get('api/ninja/core/found_items/');

// 4. Submit Found Item - Full path: http://127.0.0.1:8000/api/ninja/core/found_items/
export const reportFoundItem = (data: any) =>    
  API.post('api/ninja/core/found_items/', data);


interface RegisterData {
    username: string;
    password: string;
    email: string;
}

// 5. User Registration - Full path: http://127.0.0.1:8000/api/ninja/core/register
export const registerUser = (data: RegisterData) => {
    return API.post('api/ninja/core/register', data);
};