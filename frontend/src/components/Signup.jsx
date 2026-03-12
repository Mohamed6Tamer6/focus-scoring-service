import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './AuthForm.css';

const Signup = () => {
    const [formData, setFormData] = useState({
        fullName: '',
        email: '',
        password: '',
        confirmPassword: '',
    });

    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.fullName,
                    email: formData.email,
                    password: formData.password
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                let errorMessage = 'Registration failed';
                if (data.detail) {
                    if (Array.isArray(data.detail)) {
                        errorMessage = data.detail.map(err => `${err.loc[1]}: ${err.msg}`).join(', ');
                    } else {
                        errorMessage = data.detail;
                    }
                }
                throw new Error(errorMessage);
            }

            console.log('Registration successful');
            window.location.href = '/login';
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-card animate-fade-in">
            <div className="auth-header">
                <h2>Create Account</h2>
                <p>Join Focus Scoring today</p>
            </div>
            <form onSubmit={handleSubmit} className="auth-form">
                {error && <div className="error-message">{error}</div>}
                <div className="form-group">
                    <label htmlFor="fullName">Full Name</label>
                    <input
                        type="text"
                        id="fullName"
                        placeholder="John Doe"
                        value={formData.fullName}
                        onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                        required
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="email">Email Address</label>
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
                <div className="form-group">
                    <label htmlFor="confirmPassword">Confirm Password</label>
                    <input
                        type="password"
                        id="confirmPassword"
                        placeholder="••••••••"
                        value={formData.confirmPassword}
                        onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                        required
                    />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                    {loading ? 'Creating Account...' : 'Create Account'}
                </button>
            </form>
            <div className="auth-footer">
                <p>Already have an account? <Link to="/login">Sign in</Link></p>
            </div>
        </div>
    );
};

export default Signup;
