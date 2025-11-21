// frontend/src/components/RegisterComponent.tsx

import React, { useState } from 'react';
import { registerUser } from '../api/api';

// Props to communicate success back to the parent component
interface RegisterProps {
    onSuccess: () => void;
    onToggleToLogin: () => void; // Function to switch to the login view
}

const RegisterComponent: React.FC<RegisterProps> = ({ onSuccess, onToggleToLogin }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            // Call the API function
            await registerUser({ username, password, email });

            // On successful registration, notify the user and switch the view back to Login
            alert('Registration successful! Please log in now.');
            onSuccess(); // Triggers App.tsx to switch view to Login

        } catch (err: any) {
            console.error("Registration Error:", err);
            // Assuming the backend sends a friendly error message in the response data
            const errorMessage = err.response?.data?.message || "Registration failed. Please try again.";
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '400px', margin: '50px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h2>Register New User</h2>
            <form onSubmit={handleRegister}>
                {/* Username Field */}
                <div style={{ marginBottom: '15px' }}>
                    <label>Username:</label>
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                    />
                </div>
                
                {/* Email Field */}
                <div style={{ marginBottom: '15px' }}>
                    <label>Email:</label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                    />
                </div>

                {/* Password Field */}
                <div style={{ marginBottom: '15px' }}>
                    <label>Password:</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                    />
                </div>

                {/* Error Message */}
                {error && <p style={{ color: 'red' }}>{error}</p>}

                {/* Submit Button */}
                <button 
                    type="submit" 
                    disabled={isLoading}
                    style={{ width: '100%', padding: '10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                    {isLoading ? 'Registering...' : 'Register'}
                </button>
            </form>
            
            {/* Toggle Link: Uses the onToggleToLogin prop */}
            <p style={{ marginTop: '15px', textAlign: 'center' }}>
                Already have an account? <a href="#" onClick={onToggleToLogin}>Login here</a>
            </p>
        </div>
    );
};

export default RegisterComponent;