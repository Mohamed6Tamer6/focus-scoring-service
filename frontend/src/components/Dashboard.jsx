import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

const WS_URL = `ws://${window.location.host}/api/focus/ws`;
const API_BASE = '/api';

const Dashboard = () => {
    const navigate = useNavigate();
    const videoRef = useRef(null);
    const captureCanvasRef = useRef(null);
    const meshCanvasRef = useRef(null);
    const wsRef = useRef(null);
    const streamRef = useRef(null);
    const intervalRef = useRef(null);
    const isTrackingRef = useRef(false);
    const isStoppingRef = useRef(false);
    const reportRef = useRef(null);
    const hasReceivedDataRef = useRef(false);

    const [isTracking, _setIsTracking] = useState(false);
    const [isStopping, _setIsStopping] = useState(false);
    const [report, _setReport] = useState(null);
    const [wsConnected, setWsConnected] = useState(false);
    const [focusZone, setFocusZone] = useState('normal');
    const [cameraReady, setCameraReady] = useState(false);
    const [showDebug, setShowDebug] = useState(true);
    const [mirror, setMirror] = useState(true);

    const setIsTracking = (val) => {
        isTrackingRef.current = val;
        _setIsTracking(val);
    };
    const setIsStopping = (val) => {
        isStoppingRef.current = val;
        _setIsStopping(val);
    };
    const setReport = (val) => {
        reportRef.current = val;
        _setReport(val);
    };

    const [userProfile, setUserProfile] = useState(null);
    const [subordinates, setSubordinates] = useState([]);
    const [selectedSub, setSelectedSub] = useState(null);
    const [targetDate, setTargetDate] = useState(new Date().toISOString().split('T')[0]);
    const [subDates, setSubDates] = useState([]);
    const [availableAdmins, setAvailableAdmins] = useState([]);
    const [loadingSubordinates, setLoadingSubordinates] = useState(false);
    const [subError, setSubError] = useState(null);

    // Live frame data
    const [liveData, setLiveData] = useState(null);

    // Past sessions
    const [sessions, setSessions] = useState([]);
    const [loadingSessions, setLoadingSessions] = useState(false);

    const [selectedAdmin, setSelectedAdmin] = useState('');

    const token = localStorage.getItem('token');

    // Fetch profile and data on mount
    useEffect(() => {
        fetchProfile();
    }, []);

    const fetchProfile = async () => {
        try {
            const res = await fetch(`${API_BASE}/auth/profile`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (res.ok) {
                const data = await res.json();
                setUserProfile(data);
                if (data.roles.includes('admin')) {
                    fetchSubordinates();
                } else {
                    if (!data.admin_id) {
                        fetchAvailableAdmins();
                    }
                    fetchSessions();
                }
            }
        } catch (err) {
            console.error('Failed to fetch profile:', err);
        }
    };

    const fetchAvailableAdmins = async () => {
        try {
            const res = await fetch(`${API_BASE}/auth/admins`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                setAvailableAdmins(await res.json());
            }
        } catch (e) {
            console.error('Failed to fetch available admins:', e);
        }
    };

    const handleSaveManager = async () => {
        if (!selectedAdmin) return;
        try {
            const res = await fetch(`${API_BASE}/auth/profile`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ admin_id: selectedAdmin })
            });
            if (res.ok) {
                fetchProfile();
            }
        } catch (e) {
            console.error("Failed to save manager:", e);
        }
    };

    const fetchSubordinates = async () => {
        setLoadingSubordinates(true);
        setSubError(null);
        try {
            const res = await fetch(`${API_BASE}/auth/subordinates`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setSubordinates(data);
                // Auto-select first subordinate if none selected and data exists
                if (data.length > 0 && !selectedSub) {
                    // setSelectedSub(data[0]); // Optional: user might prefer manual selection
                }
            } else {
                setSubError("Failed to load subordinates");
            }
        } catch (err) {
            console.error('Failed to fetch subordinates:', err);
            setSubError("Network error loading team");
        } finally {
            setLoadingSubordinates(false);
        }
    };

    const fetchSubDates = async (userId) => {
        setLoadingSessions(true);
        try {
            const res = await fetch(`${API_BASE}/focus/admin/sessions/${userId}/dates`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const dates = await res.json();
                setSubDates(dates);
                if (dates.length > 0) {
                    if (!dates.includes(targetDate)) {
                        setTargetDate(dates[0]); // This triggers useEffect for fetchSessions
                    } else {
                        fetchSessions(userId, targetDate); // It's already the targetDate, fetch manually
                    }
                } else {
                    setSessions([]);
                }
            }
        } catch (err) {
            console.error("Failed to fetch sub dates:", err);
        } finally {
            setLoadingSessions(false);
        }
    };

    const fetchSessions = async (userId = null, overrideDate = null) => {
        setLoadingSessions(true);
        try {
            let url = `${API_BASE}/focus/sessions`;
            if (userId) {
                const dateToFetch = overrideDate || targetDate;
                url = `${API_BASE}/focus/admin/sessions/${userId}?target_date=${dateToFetch}`;
            }

            const res = await fetch(url, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (res.ok) {
                const data = await res.json();
                setSessions(data);
            }
        } catch (err) {
            console.error('Failed to fetch sessions:', err);
        } finally {
            setLoadingSessions(false);
        }
    };

    const isAdmin = userProfile?.roles.includes('admin');

    useEffect(() => {
        if (selectedSub) {
            fetchSubDates(selectedSub.id);
            setSessions([]); // Reset sessions view when switching users
            setReport(null);
        }
    }, [selectedSub]);

    useEffect(() => {
        if (selectedSub && targetDate) {
            fetchSessions(selectedSub.id);
            setReport(null);
        }
    }, [targetDate]);

    // Draw facemesh on the overlay canvas
    useEffect(() => {
        if (liveData?.facemesh && meshCanvasRef.current && videoRef.current) {
            const canvas = meshCanvasRef.current;
            const video = videoRef.current;
            const ctx = canvas.getContext('2d');

            // Sync canvas size with video
            if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
            }

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            if (showDebug) {
                // Draw all 468 face landmarks as dots
                ctx.fillStyle = liveData.is_focused ? '#10b981' : '#ef4444';
                liveData.facemesh.forEach((point) => {
                    const x = point.x * canvas.width;
                    const y = point.y * canvas.height;
                    ctx.beginPath();
                    ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
                    ctx.fill();
                });

                // Draw violations text on camera if any
                if (liveData.violations?.length > 0) {
                    ctx.fillStyle = '#ff4b4b';
                    ctx.font = 'bold 18px Inter';
                    liveData.violations.forEach((v, i) => {
                        ctx.fillText(`⚠️ ${v}`, 20, 40 + (i * 30));
                    });
                }
            }
        } else if (!liveData && meshCanvasRef.current) {
            const ctx = meshCanvasRef.current.getContext('2d');
            ctx.clearRect(0, 0, meshCanvasRef.current.width, meshCanvasRef.current.height);
        }
    }, [liveData, showDebug]);

    // Start camera
    const startCamera = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: 'user' },
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
            setCameraReady(true);
        } catch (err) {
            console.error('Camera error:', err);
            setCameraReady(false);
        }
    }, []);

    const stopCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((t) => t.stop());
            streamRef.current = null;
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        setCameraReady(false);
    }, []);

    // Capture frame as JPEG base64
    const captureFrame = useCallback(() => {
        if (!videoRef.current || !captureCanvasRef.current) return null;
        const video = videoRef.current;
        const canvas = captureCanvasRef.current;
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/jpeg', 0.6);
    }, []);

    // Start tracking
    const handleStart = async () => {
        if (isTrackingRef.current || isStoppingRef.current) return;

        // Disable button immediately
        setIsTracking(true);
        setReport(null);
        setLiveData(null);
        hasReceivedDataRef.current = false;

        // Close any existing connection just in case
        if (wsRef.current) {
            try {
                wsRef.current.close();
            } catch (e) { }
        }

        // 1. Start camera
        await startCamera();

        // 2. Connect WebSocket
        const ws = new WebSocket(`${WS_URL}?token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => {
            setWsConnected(true);
            ws.send(JSON.stringify({ action: 'start', focus_zone: focusZone }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            hasReceivedDataRef.current = true;
            if (data.type === 'status' && data.status === 'started') {
                // Already set to true, but ensuring state is correct
                setIsTracking(true);
                if (intervalRef.current) clearInterval(intervalRef.current);
                intervalRef.current = setInterval(() => {
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                        const frame = captureFrame();
                        if (frame) wsRef.current.send(JSON.stringify({ action: 'frame', frame }));
                    }
                }, 125); // ~8 FPS
            } else if (data.type === 'frame_result') {
                setLiveData(data);
            } else if (data.type === 'report') {
                setReport(data.report);
                setIsTracking(false);
                setIsStopping(false);
                setLiveData(null);
                fetchSessions();
                ws.close();
                stopCamera();
            }
        };

        ws.onclose = (event) => {
            setWsConnected(false);
            const wasTracking = isTrackingRef.current;
            const wasStopping = isStoppingRef.current;
            const currentReport = reportRef.current;

            // If it's a normal close (code 1000) or we have a report, don't alert
            const isNormalClose = event.code === 1000 || currentReport !== null;

            if (!isNormalClose && !wasStopping) {
                // If it closed unexpectedly and it's not a normal completion
                console.error("WebSocket connection lost.", event);

                // Only alert if we never really got ANY data (indicating a connection/auth failure)
                if (!hasReceivedDataRef.current) {
                    alert("Session expired or connection failed. Please log in again.");
                    handleLogout();
                }
            }

            setIsTracking(false);
            setIsStopping(false);
            if (intervalRef.current) clearInterval(intervalRef.current);
        };

        ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };
    };

    const handleStop = () => {
        setIsStopping(true);
        // Stop sending frames immediately
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }

        // IMPORTANT: Stop camera immediately for better UX
        stopCamera();

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            // Signal server to stop and wait for report
            wsRef.current.send(JSON.stringify({ action: 'stop' }));
        } else {
            setIsTracking(false);
            setIsStopping(false);
            setLiveData(null);
        }
    };

    const handleRefresh = () => {
        if (isAdmin) {
            fetchSubordinates();
            if (selectedSub) {
                fetchSubDates(selectedSub.id);
            }
        } else {
            fetchProfile();
            fetchSessions();
        }
    };

    const handleLogout = async () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
            if (wsRef.current) wsRef.current.close();
            stopCamera();
        };
    }, [stopCamera]);

    const formatTime = (seconds) => {
        if (seconds === undefined || seconds === null) return '0s';
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        const m = Math.floor(seconds / 60);
        const s = (seconds % 60).toFixed(0);
        return `${m}m ${s}s`;
    };

    const handleDownloadJSON = () => {
        if (!report) return;
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(report, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `focus_report_${report.id || 'session'}.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    };

    const handleDownloadPDF = async (sessionId) => {
        // If sessionId is an event object (from onClick={handleDownloadPDF}), use report.id
        const id = (typeof sessionId === 'string' || typeof sessionId === 'number' || (sessionId && (sessionId.length > 5 || typeof sessionId === 'string'))) ? sessionId : (report && report.id);

        if (!id) {
            alert("Session ID not available to download PDF.");
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/focus/sessions/${id}/pdf`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (!res.ok) throw new Error("Failed to generate PDF");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `focus_report_${id}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error('PDF Download Error:', err);
            alert(`Error downloading PDF: ${err.message}`);
        }
    };

    return (
        <div className="dashboard">
            <aside className="sidebar">
                <h2>{isAdmin ? 'Admin Panel' : 'Settings'}</h2>
                <div className="sidebar-section">
                    {!isAdmin ? (
                        <>
                            <div className="setting-item">
                                <label>Camera Index <span className="help-icon">?</span></label>
                                <input type="number" defaultValue={0} />
                            </div>

                            <label className="setting-checkbox">
                                <input type="checkbox" checked={mirror} onChange={(e) => setMirror(e.target.checked)} />
                                Flip Horizontal (Mirror)
                            </label>

                            <div className="setting-item" style={{ marginTop: '10px' }}>
                                <label>Your Manager</label>
                                {userProfile?.admin_id ? (
                                    <div style={{ fontSize: '0.85rem', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '10px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                                        ✅ {userProfile.admin_info?.name} ({userProfile.admin_info?.email})
                                    </div>
                                ) : (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <select
                                            className="select-input"
                                            onChange={(e) => setSelectedAdmin(e.target.value)}
                                            value={selectedAdmin}
                                            style={{ background: '#31333f', color: 'white', borderRadius: '4px', padding: '8px' }}
                                        >
                                            <option value="">-- Select Manager --</option>
                                            {availableAdmins.map(a => (
                                                <option key={a.id} value={a.id}>{a.name}</option>
                                            ))}
                                        </select>
                                        <button
                                            onClick={handleSaveManager}
                                            disabled={!selectedAdmin}
                                            style={{ padding: '8px', background: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', opacity: selectedAdmin ? 1 : 0.5 }}
                                        >
                                            Save Manager
                                        </button>
                                        <p style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Select a manager to share your reports with them.</p>
                                    </div>
                                )}
                            </div>

                            <div className="setting-item">
                                <label>Focus Sensitivity</label>
                                <select value={focusZone} onChange={(e) => setFocusZone(e.target.value)}>
                                    <option value="strict">strict</option>
                                    <option value="normal">normal</option>
                                    <option value="relaxed">relaxed</option>
                                </select>
                            </div>

                            <label className="setting-checkbox">
                                <input type="checkbox" checked={showDebug} onChange={(e) => setShowDebug(e.target.checked)} />
                                Show Debug Overlay
                            </label>

                            <button className="btn-start" onClick={handleStart} disabled={isTracking}>
                                {isTracking ? 'Tracking In Progress...' : 'Start Tracking'}
                            </button>

                            <button className="btn-stop" onClick={handleStop} disabled={!isTracking || isStopping}>
                                {isStopping ? 'Finalizing Report...' : 'Stop Tracking'}
                            </button>
                        </>
                    ) : (
                        <div className="user-list">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3>My Team</h3>
                                {loadingSubordinates && <div className="loading-spinner-tiny"></div>}
                            </div>

                            {subError && <p style={{ fontSize: '0.8rem', color: '#ef4444' }}>⚠️ {subError}</p>}

                            {!loadingSubordinates && subordinates.length === 0 && !subError && (
                                <p className="hint-text">No users reporting to you yet.</p>
                            )}

                            {subordinates.map(sub => (
                                <div
                                    key={sub.id}
                                    className={`user-item ${selectedSub?.id === sub.id ? 'active' : ''}`}
                                    onClick={() => setSelectedSub(sub)}
                                >
                                    <strong>{sub.name}</strong>
                                    <span>{sub.email}</span>
                                </div>
                            ))}

                            {loadingSubordinates && subordinates.length === 0 && (
                                <div className="skeleton-list">
                                    {[1, 2, 3].map(i => (
                                        <div key={i} className="user-item skeleton" style={{ opacity: 0.5, height: '40px' }}></div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    <button className="logout-btn" onClick={handleLogout} style={{ marginTop: '20px' }}>
                        Logout
                    </button>

                    <div className="database-msg" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%', justifyContent: 'space-between' }}>
                            <span style={{ fontWeight: 700 }}>Profile</span>
                            <button onClick={handleRefresh} style={{ background: 'none', border: 'none', color: '#3b82f6', fontSize: '0.75rem', cursor: 'pointer', padding: 0 }}>Refresh 🔄</button>
                        </div>
                        <div style={{ fontSize: '0.85rem' }}>{userProfile?.name}</div>
                        <div style={{ fontSize: '0.7rem', opacity: 0.7, wordBreak: 'break-all' }}>{userProfile?.email}</div>
                        <div style={{ fontSize: '0.7rem', color: isAdmin ? '#ff4b4b' : '#10b981', fontWeight: 600 }}>{isAdmin ? '🛡️ Admin' : '👤 User'}</div>
                    </div>
                </div>
            </aside>

            <main className="main-content">
                {!isAdmin && (
                    <div className="video-wrapper">
                        <video ref={videoRef} autoPlay playsInline muted style={{ transform: mirror ? 'scaleX(-1)' : 'none' }} />
                        <canvas ref={meshCanvasRef} className="mesh-canvas" style={{ transform: mirror ? 'scaleX(-1)' : 'none' }} />
                        <canvas ref={captureCanvasRef} style={{ display: 'none' }} />
                        {!cameraReady && !isTracking && !report && (
                            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
                                Camera inactive. Press Start Tracking.
                            </div>
                        )}
                    </div>
                )}

                {isAdmin && !selectedSub && (
                    <div className="welcome-admin animate-fade-in" style={{ textAlign: 'center', marginTop: '100px' }}>
                        <div style={{ fontSize: '4rem', marginBottom: '20px' }}>📁</div>
                        <h2>Welcome to Admin Dashboard</h2>
                        <p style={{ color: '#94a3b8' }}>Please select a team member from the sidebar to view their history.</p>
                    </div>
                )}

                {isAdmin && selectedSub && !report && (
                    <div className="admin-drilldown animate-fade-in">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '20px' }}>
                            <div>
                                <h2 style={{ margin: 0 }}>Analytics: {selectedSub.name}</h2>
                                <p style={{ color: '#94a3b8', margin: '5px 0 0 0' }}>{selectedSub.email}</p>
                            </div>
                            <button
                                onClick={handleRefresh}
                                style={{
                                    background: '#3b82f622',
                                    border: '1px solid #3b82f6',
                                    color: '#3b82f6',
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                }}
                            >
                                <span>🔄</span> Refresh Data
                            </button>
                        </div>

                        <div className="drilldown-sections">
                            <div className="dates-card" style={{ background: '#262730', borderRadius: '12px', padding: '20px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                <h3 style={{ marginTop: 0, marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    📅 Session Days
                                </h3>
                                {loadingSessions && <p>Loading days...</p>}
                                {!loadingSessions && subDates.length === 0 && <p className="hint-text">No activity recorded for this user.</p>}
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '10px' }}>
                                    {subDates.map(date => (
                                        <button
                                            key={date}
                                            className={`date-pill ${targetDate === date ? 'active' : ''}`}
                                            onClick={() => setTargetDate(date)}
                                            style={{
                                                background: targetDate === date ? '#ff4b4b' : 'rgba(255,255,255,0.05)',
                                                color: 'white',
                                                border: 'none',
                                                padding: '10px',
                                                borderRadius: '8px',
                                                cursor: 'pointer',
                                                fontSize: '0.9rem',
                                                fontWeight: targetDate === date ? 'bold' : 'normal'
                                            }}
                                        >
                                            {new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {targetDate && sessions.length > 0 && (
                                <div className="sessions-display animate-fade-in" style={{ marginTop: '30px' }}>
                                    <h3>Sessions on {new Date(targetDate).toLocaleDateString()}</h3>
                                    <div className="event-list">
                                        {sessions.map(s => (
                                            <div key={s.id} className="event-dropdown" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px' }}>
                                                <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                                                    <span style={{ fontSize: '1.2rem' }}>🕒</span>
                                                    <div>
                                                        <div style={{ fontWeight: 'bold' }}>{new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                                                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Duration: {formatTime(s.total_time)}</div>
                                                    </div>
                                                </div>
                                                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                                    <span style={{
                                                        padding: '4px 10px',
                                                        borderRadius: '20px',
                                                        fontSize: '0.75rem',
                                                        fontWeight: '600',
                                                        backgroundColor: s.overall_rating === 'Excellent' ? 'rgba(16, 185, 129, 0.1)' : (s.overall_rating === 'Poor' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(59, 130, 246, 0.1)'),
                                                        color: s.overall_rating === 'Excellent' ? '#10b981' : (s.overall_rating === 'Poor' ? '#ef4444' : '#3b82f6')
                                                    }}>
                                                        {s.overall_rating}
                                                    </span>
                                                    <button onClick={() => setReport(s)} className="view-btn">Full Report</button>
                                                    <button onClick={() => handleDownloadPDF(s.id)} className="pdf-btn">📄</button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {isTracking && (
                    <div className="live-focus-bar animate-fade-in">
                        <div
                            className="focus-progress"
                            style={{
                                width: `${(liveData?.focus_score || 0) * 100}%`,
                                backgroundColor: (liveData?.is_focused) ? '#10b981' : '#ef4444'
                            }}
                        />
                        <div className="focus-text">
                            {(liveData?.is_focused) ? 'Focused' : (liveData?.face_detected ? 'Unfocused' : 'Absent')}
                        </div>
                    </div>
                )}

                {report && (
                    <div className="results-header animate-fade-in">
                        <div className={`rating-box ${report.overall_rating?.toLowerCase() || 'poor'}`}>
                            <h2 style={{ color: report.overall_rating === 'Excellent' ? '#10b981' : (report.overall_rating === 'Poor' ? '#ef4444' : '#3b82f6') }}>
                                Overall Rating: {report.overall_rating || 'Poor'}
                            </h2>
                            <div className="rate-line">Effective Focus Rate (while present): {report.effective_focus_rate?.toFixed(1) || '0.0'}%</div>
                        </div>

                        <div className="event-analysis">
                            <h2>🔍 Detailed Event Analysis</h2>
                            <div className="event-columns">
                                <div className="event-column">
                                    <h3>📉 Unfocus Periods</h3>
                                    <div className="total-events">Total Events: {report.unfocus_events}</div>
                                    {report.unfocus_events === 0 ? (
                                        <div className="no-event-box">No unfocus events detected. ✅</div>
                                    ) : (
                                        <div className="event-list">
                                            {report.unfocused_periods?.map((p, i) => (
                                                <div key={i} className="event-dropdown">
                                                    Event {i + 1}: {formatTime(p.duration)} ({new Date(p.start).toLocaleTimeString()} → {new Date(p.end).toLocaleTimeString()})
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <div className="event-column">
                                    <h3>🚶 Absence Periods</h3>
                                    <div className="total-events">Total Events: {report.absence_events}</div>
                                    {report.absence_events === 0 ? (
                                        <div className="no-event-box" style={{ borderColor: '#3b82f6', color: '#3b82f6', background: 'rgba(59, 130, 246, 0.1)' }}>
                                            No absence events detected. ✅
                                        </div>
                                    ) : (
                                        <div className="event-dropdown">Show All {report.absence_events} Absence Events</div>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="reports-section">
                            <h3>📥 Download Reports</h3>
                            <div className="report-buttons">
                                <button className="btn-report" onClick={handleDownloadJSON}>📥 Download Session Data (JSON)</button>
                                <button className="btn-report" onClick={handleDownloadPDF}>📄 Download Full Report (PDF)</button>
                                <button className="btn-report" style={{ background: '#334155' }} onClick={() => setReport(null)}>← Back to List</button>
                            </div>
                        </div>

                        <div className="raw-data-panel">
                            <div className="raw-data-header" onClick={() => setShowDebug(!showDebug)}>
                                {showDebug ? '▼ Hide' : '▶ View'} Raw Session Data
                            </div>
                            {showDebug && (
                                <div className="json-block">
                                    {JSON.stringify(report, null, 2)}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {sessions.length > 0 && !isTracking && !report && !isAdmin && (
                    <div className="past-sessions animate-fade-in" style={{ marginTop: '20px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                            <h3 style={{ margin: 0 }}>📋 Session History</h3>
                            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Recent Activity</span>
                        </div>
                        <div className="history-header" style={{
                            display: 'flex',
                            padding: '10px 12px',
                            color: '#94a3b8',
                            fontSize: '0.75rem',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            borderBottom: '1px solid rgba(255,255,255,0.05)'
                        }}>
                            <div style={{ flex: 1.5 }}>Date & Time</div>
                            <div style={{ flex: 1, textAlign: 'center' }}>Rating</div>
                            <div style={{ flex: 0.5, textAlign: 'right' }}>Actions</div>
                        </div>
                        <div className="event-list">
                            {sessions.slice(0, 10).map((s) => (
                                <div key={s.id} className="event-dropdown" style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '15px 12px',
                                    borderBottom: '1px solid rgba(255,255,255,0.02)'
                                }}>
                                    <div style={{ flex: 1.5 }}>
                                        <div style={{ color: '#fafafb', fontSize: '0.9rem' }}>{new Date(s.created_at).toLocaleDateString()} {new Date(s.created_at).toLocaleTimeString()}</div>
                                    </div>
                                    <div style={{ flex: 1, textAlign: 'center' }}>
                                        <span style={{
                                            padding: '4px 10px',
                                            borderRadius: '20px',
                                            fontSize: '0.75rem',
                                            fontWeight: '600',
                                            backgroundColor: s.overall_rating === 'Excellent' ? 'rgba(16, 185, 129, 0.1)' : (s.overall_rating === 'Poor' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(59, 130, 246, 0.1)'),
                                            color: s.overall_rating === 'Excellent' ? '#10b981' : (s.overall_rating === 'Poor' ? '#ef4444' : '#3b82f6'),
                                            border: `1px solid ${s.overall_rating === 'Excellent' ? 'rgba(16, 185, 129, 0.2)' : (s.overall_rating === 'Poor' ? 'rgba(239, 68, 68, 0.2)' : (s.overall_rating === 'Poor' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(59, 130, 246, 0.2)'))}`
                                        }}>
                                            {s.overall_rating}
                                        </span>
                                    </div>
                                    <div style={{ flex: 0.5, textAlign: 'right', display: 'flex', gap: '5px', justifyContent: 'flex-end' }}>
                                        <button onClick={() => setReport(s)} style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid #3b82f6', color: '#3b82f6', padding: '4px 8px', borderRadius: '4px', fontSize: '0.7rem' }}>View</button>
                                        <button
                                            onClick={() => handleDownloadPDF(s.id)}
                                            style={{
                                                background: 'rgba(255,255,255,0.05)',
                                                border: '1px solid rgba(255,255,255,0.1)',
                                                color: 'white',
                                                borderRadius: '6px',
                                                padding: '6px 10px',
                                                cursor: 'pointer',
                                                fontSize: '0.8rem'
                                            }}
                                        >
                                            📄 PDF
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {loadingSessions && !selectedSub && <p style={{ textAlign: 'center', marginTop: '20px', color: '#94a3b8' }}>Loading your data...</p>}
            </main>
        </div>
    );
};

export default Dashboard;
