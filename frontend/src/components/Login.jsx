import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './AuthForm.css';

const Login = () => {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });

    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });

            let data = {};
            const text = await response.text();
            if (text) {
                try {
                    data = JSON.parse(text);
                } catch (e) {
                    console.error('Failed to parse JSON:', text);
                }
            }

            if (!response.ok) {
                let errorMessage = `Server error: ${response.status}`;
                if (data.detail) {
                    if (Array.isArray(data.detail)) {
                        errorMessage = data.detail.map(err => `${err.loc[1]}: ${err.msg}`).join(', ');
                    } else {
                        errorMessage = data.detail;
                    }
                }
                throw new Error(errorMessage);
            }

            localStorage.setItem('token', data.access_token);
            console.log('Login successful');
            window.location.href = '/dashboard';
        } catch (err) {
            setError(err.message === 'Unexpected end of JSON input'
                ? 'Server connection error or invalid response'
                : err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-card animate-fade-in">
            <div className="auth-header">
                <h2>Welcome Back</h2>
                <p>Please enter your details to sign in</p>
            </div>
            <form onSubmit={handleSubmit} className="auth-form">
                {error && <div className="error-message">{error}</div>}
                <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                        type="email"
                        id="email"
                        placeholder="name@company.com"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        required
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        type="password"
                        id="password"
                        placeholder="••••••••"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        required
                    />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                    {loading ? 'Signing in...' : 'Sign in'}
                </button>
            </form>
            <div className="auth-footer">
                <p>Don't have an account? <Link to="/signup">Sign up</Link></p>
            </div>
        </div>
    );
};

export default Login;
