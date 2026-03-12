import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './components/Login'
import Signup from './components/Signup'
import Dashboard from './components/Dashboard'

function App() {
    const isAuthenticated = () => {
        const token = localStorage.getItem('token');
        if (!token) return false;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp * 1000 > Date.now();
        } catch (e) {
            return false;
        }
    };

    return (
        <Router>
            <div className="app-container">
                <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/signup" element={<Signup />} />
                    <Route
                        path="/dashboard"
                        element={
                            isAuthenticated()
                                ? <Dashboard />
                                : <Navigate to="/login" replace />
                        }
                    />
                    <Route path="/" element={<Navigate to="/login" replace />} />
                </Routes>
            </div>
        </Router>
    )
}

export default App
