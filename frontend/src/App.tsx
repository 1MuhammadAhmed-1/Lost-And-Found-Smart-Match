import React, { useState, useEffect } from 'react';
import LoginComponent from './components/LoginComponent';
import ChatComponent from './components/ChatComponent'; 
import RegisterComponent from './components/RegisterComponent';
// import ManualActionComponent from './components/ManualActionComponent'; // <<< REMOVED: Manual actions are now handled by AI Chat
import { setAuthToken } from './api/api'; 
import './App.css'; 

// Define the types for the different unauthenticated views
type AuthView = 'login' | 'register';

// Define the types for the content displayed when logged in. 
// We simplify this to only 'chat' as 'manual' is removed.
type ContentView = 'chat'; 

function App() {
    // State to hold the authentication token, initialized from localStorage
    const [token, setToken] = useState<string | null>(localStorage.getItem('authToken'));
    
    // STATE: To switch between Login and Register views when logged out
    const [authView, setAuthView] = useState<AuthView>('login'); 
    
    // STATE: To manage the content view. We keep this initialized to 'chat' 
    // but the functionality to change it is removed below.
    const [contentView, setContentView] = useState<ContentView>('chat'); 

    // 1. Initialize Axios header on component mount.
    useEffect(() => {
        const initialToken = localStorage.getItem('authToken');
        setAuthToken(initialToken);
    }, []); // Run only once on mount

    const handleLogin = (newToken: string) => {
        // 1. Save the token to local storage for persistence
        localStorage.setItem('authToken', newToken); 
        
        // 2. Update the state
        setToken(newToken);
        // 3. Reset content view to chat on successful login
        setContentView('chat'); 
    };

    const handleLogout = () => {
        // 1. Clear the token from global Axios instance and localStorage
        setAuthToken(null); 
        localStorage.removeItem('authToken'); // Clear local storage explicitly
        
        // 2. Clear the state and reset view to login
        setToken(null);
        setAuthView('login'); 
    };
    
    // Helper function to switch the Login/Register view
    const toggleAuthView = (view: AuthView) => {
        setAuthView(view);
    };

    // Note: The handleContentViewChange function is no longer needed since 
    // we only have one logged-in view ('chat').
    
    // Content to render when logged out (token is null)
    const renderAuthView = () => {
        if (authView === 'login') {
            return (
                <LoginComponent 
                    onLogin={handleLogin} 
                    onToggleToRegister={() => toggleAuthView('register')}
                />
            );
        } else {
            return (
                <RegisterComponent 
                    onSuccess={() => toggleAuthView('login')} 
                    onToggleToLogin={() => toggleAuthView('login')}
                />
            );
        }
    };

    return (
        <div className="App">
            <header className="App-header">
                <h1>Lost & Found Smart Match</h1>
            </header>

            {/* Conditional Rendering: Show Chat if logged in, otherwise show Auth Forms */}
            {token ? (
                <div className="main-content-container">
                    
                    {/* Navigation/Toggle Bar - Simplified to remove Manual Actions button */}
                    <div className="nav-bar"> 
                        {/* The Talk to Assistant button is always active and is now the only content view */}
                        <button 
                            className={'active'} // Always active
                            // onClick={() => handleContentViewChange('chat')} // No longer needed
                        >
                            💬 Talk to Assistant
                        </button>
                        
                        {/* The Manual Actions button has been removed */}
                        
                        <button onClick={handleLogout} className="logout-button">Logout</button>
                    </div>

                    {/* Content is now always the ChatComponent */}
                    <ChatComponent />
                    
                </div>
            ) : (
                // Renders either LoginComponent or RegisterComponent
                renderAuthView()
            )}
        </div>
    );
}

export default App;