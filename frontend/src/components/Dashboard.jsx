import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/focus/ws`;
const API_BASE = '/api';

const Dashboard = () => {
    const navigate = useNavigate();
    const videoRef = useRef(null);
    const captureCanvasRef = useRef(null);
    const meshCanvasRef = useRef(null);
    const wsRef = useRef(null);
    const streamRef = useRef(null);
    const intervalRef = useRef(null);

    const [isTracking, setIsTracking] = useState(false);
    const [isStopping, setIsStopping] = useState(false);
    const [wsConnected, setWsConnected] = useState(false);
    const [focusZone, setFocusZone] = useState('normal');
    const [cameraReady, setCameraReady] = useState(false);
    const [showDebug, setShowDebug] = useState(true);
    const [mirror, setMirror] = useState(true);

    // Live frame data
    const [liveData, setLiveData] = useState(null);

    // Final report after stopping
    const [report, setReport] = useState(null);

    // Past sessions
    const [sessions, setSessions] = useState([]);
    const [loadingSessions, setLoadingSessions] = useState(false);

    const token = localStorage.getItem('token');

    // Fetch past sessions on mount
    useEffect(() => {
        fetchSessions();
    }, []);

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

    const fetchSessions = async () => {
        setLoadingSessions(true);
        try {
            const res = await fetch(`${API_BASE}/focus/sessions`, {
                headers: { Authorization: `Bearer ${token}` },
            });
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
        setReport(null);
        setLiveData(null);

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
            if (data.type === 'status' && data.status === 'started') {
                setIsTracking(true);
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

        ws.onclose = () => {
            setWsConnected(false);
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
        const id = (typeof sessionId === 'string') ? sessionId : (report && report.id);

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
            if (!res.ok) throw new Error("Failed to generate PDF");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `focus_report_${id}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('PDF Download Error:', err);
            alert(`Error downloading PDF: ${err.message}`);
        }
    };

    return (
        <div className="dashboard">
            <aside className="sidebar">
                <h2>Settings</h2>
                <div className="sidebar-section">
                    <div className="setting-item">
                        <label>Camera Index <span className="help-icon">?</span></label>
                        <input type="number" defaultValue={0} />
                    </div>

                    <label className="setting-checkbox">
                        <input type="checkbox" checked={mirror} onChange={(e) => setMirror(e.target.checked)} />
                        Flip Horizontal (Mirror)
                    </label>

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

                    <button className="logout-btn" onClick={handleLogout} style={{ marginTop: '20px' }}>
                        Logout
                    </button>

                    <div className="database-msg">
                        📌 Database is automatically configured via environment
                    </div>
                </div>
            </aside>

            <main className="main-content">
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

                {sessions.length > 0 && !isTracking && !report && (
                    <div className="past-sessions animate-fade-in" style={{ marginTop: '20px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                            <h3 style={{ margin: 0 }}>📋 Session History</h3>
                            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Showing last 10 sessions</span>
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
                            <div style={{ flex: 0.5, textAlign: 'right' }}>Action</div>
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
                                            border: `1px solid ${s.overall_rating === 'Excellent' ? 'rgba(16, 185, 129, 0.2)' : (s.overall_rating === 'Poor' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(59, 130, 246, 0.2)')}`
                                        }}>
                                            {s.overall_rating}
                                        </span>
                                    </div>
                                    <div style={{ flex: 0.5, textAlign: 'right' }}>
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
            </main>
        </div>
    );
};

export default Dashboard;
