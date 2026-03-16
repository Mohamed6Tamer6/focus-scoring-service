# System Architecture & Development Reference (Work Intelligence Platform)

***AI INSTRUCTION: When starting a new session or receiving a task, READ THIS FILE FIRST. It serves as your absolute source of truth for the codebase to save tokens and prevent redundant file exploration. DO NOT explore the codebase manually if the answer is here.***

## 1. Project Vision & Purpose
**Work Intelligence Platform** is a SaaS platform designed to measure and analyze the productivity of remote employees and freelancers. It goes beyond time tracking by analyzing *actual work, focus levels, task completion speed, and personal work patterns* using computer vision and AI. The goal is to detect burnout early, provide clear performance insights, and improve overall team productivity.

## 2. Core System Components

### 2.1 Focus Detection System [🟢 COMPLETED]
A real-time system that measures user focus during work sessions using the webcam.
- **Tech Used**: OpenCV, MediaPipe (Face Mesh), SciPy.
- **Core Metrics Tracked**:
  - `focus_time`: Time spent actively looking at the screen.
  - `unfocus_time`: Time spent looking away (pitch/yaw/roll deviations exceeding threshold for >2s).
  - `absence_time`: Time when the face is completely out of frame.
  - `total_blinks` & Blink frequency (EAR - Eye Aspect Ratio) to detect drowsiness.
- **Micro-interactions**: Supports `strict`, `normal`, `relaxed` focus zones.
- **Real-Time Delivery**: Frames are sent via WebSocket (`/focus/ws`).
- **Reporting**: Generates a PDF report at the end of the session (`fpdf2`) and uploads it to Supabase Storage. Saves session stats to DB.

### 2.2 Deep Work Detection [⏳ TO DO]
System to measure periods of deep, uninterrupted work where the user operates with maximum focus.
- **Expected Features**: Detect consecutive periods of high focus, track deep work duration, frequency, and advanced analytics.

### 2.3 Task Productivity Analyzer [⏳ TO DO]
Correlates focus and deep work metrics with actual tasks to calculate task completion speed, productivity patterns, and performance benchmarking.

---

## 3. Technology Stack & Environment
- **Backend Framework**: Python 3.10, FastAPI.
- **Database**: PostgreSQL (hosted on Supabase).
- **ORM & Migrations**: SQLAlchemy 2.0.x, Alembic.
- **Authentication**: JWT (Access & Refresh tokens). Dual-hashing security for Refresh Tokens (SHA-256 for fast lookup, Bcrypt for validation).
- **Storage**: Supabase Storage (PDF reports).
- **Computer Vision**: `opencv-python-headless`, `mediapipe`, `numpy`, `scipy`.
- **Frontend Framework**: React (via Vite).
- **Styling**: Vanilla CSS.

---

## 4. Database Schema Overview (SQLAlchemy Models)
Path: `app/models/`
- **User** (`users`): `id`, `name`, `email`, `hashed_password`, `created_at`.
- **RefreshToken** (`refresh_tokens`): `token_hash`, `token_verifier`, `user_id`, `expires_at`, `revoked`.
- **FocusSession** (`focus`): Link to user. Stores `total_time`, `focus_time`, `unfocus_time`, `absence_time`, percentages, `total_blinks`, `unfocused_periods` (JSON array), `absence_periods` (JSON array), `overall_rating`, `report_path`.
- **RBAC Models**: `Role` (admin, user), `Permission`, `UserRole`, `RolePermission`.

---

## 5. Codebase Directory Map (File-by-File Guide)

### 🔹 Backend (`/media/mohamed/B/focus-scoring-service/` base)
* `main.py`: App entry point. Configures CORS, DB creation, and mounts routers.
* `config.py`: Loads `.env` configuration (DB URL, JWT Secret, Supabase keys).
* `alembic/` & `alembic.ini`: Database migration engine.

**Core AI / Business Logic (`app/core/`, `app/services/`)**
* `app/core/focus_detector.py`: **[CRITICAL]** Contains `HeadPoseEstimator` and `EnhancedFocusDetector`. Calculates pitch/yaw/roll, EAR (Eye Aspect Ratio), handles frame-by-frame focus/absence state, and generates the final stat dict.
* `app/services/focus_service.py`: Managing active focus sessions. Handles the WebSocket logic (`handle_focus_websocket`), orchestrates `focus_detector`, saves DB records on stop, creates PDFs, and handles Supabase uploads.
* `app/services/auth.py`: Business logic for Register, Login, Token Refresh/Revoke, and initial RBAC assignment.
* `app/services/rbac_service.py`: Caching and resolution of user roles and permissions.

**API Routes (`app/api/route/`)**
* `auth.py`: `/register`, `/login`, `/refresh`, `/logout`.
* `focus.py`: `/focus/ws` (WebSocket connection), `/focus/sessions` (GET history), `/focus/sessions/{id}/pdf` (Download PDF).
* `rbac.py`: Endpoints for managing roles/permissions (Admin only).

**Database Interaction (`app/repositories/`)**
* `focus_repository.py`: CRUD for `FocusSession`.
* `user_repository.py` & `refresh_token_repository.py`: CRUD for Auth.
* `rbac_repository.py`: CRUD for roles and permissions.

**Utilities (`app/utils/`)**
* `pdf_generator.py`: Generates the session report PDF using `fpdf2`.
* `supabase_storage.py`: Handles Supabase bucket uploads and generating signed URLs.
* `jwt.py` & `token_utils.py` & `hashing.py`: Security mechanisms.

### 🔹 Frontend (`/media/mohamed/B/focus-scoring-service/frontend/src/`)
* `components/Dashboard.jsx`: **[CRITICAL]** Main user interface.
  - Handles WebCam rendering using `navigator.mediaDevices.getUserMedia`.
  - Captures frames as compressed JPEG base64 and sends them via WebSocket.
  - Receives live feedback, draws the MediaPipe mesh using the `canvas` element overlaid on the video.
  - Displays real-time focus percentage bars, logs, and renders historical sessions.
* `components/Dashboard.css`: Styles for the Dashboard.
* `components/Login.jsx`, `Signup.jsx`, `AuthForm.css`: Auth UI handling JWT storage in `localStorage`.

---

## 6. How the System Works (Data Flows)
1. **Focus Session Flow**:
   - User clicks "Start Tracking" on Frontend (`Dashboard.jsx`).
   - Frontend starts WebCam, connects to `ws://.../focus/ws` with JWT token.
   - Backend `handle_focus_websocket` authenticates token, creates a `FocusProcessor` for the user.
   - Frontend captures a frame every ~125ms (8 FPS) and sends base64 to WebSocket.
   - Backend decodes image, runs MediaPipe. `focus_detector.py` calculates Head Pose & EAR.
   - Backend sends back JSON with `is_focused`, `focus_score`, face mesh coordinates.
   - Frontend canvas updates live.
   - User clicks "Stop". Frontend sends `{ action: 'stop' }`.
   - Backend triggers `stop_session`. `focus_detector` calculates final stats.
   - Backend generates PDF, uploads to Supabase, saves record to DB `focus`.
   - Backend sends final report JSON to frontend to display.

---

## 7. Instructions for the AI Agent
When the user asks you to implement a new feature (like Deep Work Detection or Task Productivity Analyzer), follow these steps:
1. **Identify required DB Models**: Update `app/models/` and create migrations using Alembic (`alembic revision --autogenerate -m "..."` then `alembic upgrade head`).
2. **Identify core Logic**: Where does the logic belong? (`app/core/` for AI/algorithms, `app/services/` for business/app logic).
3. **Database Repositories**: Add CRUD functions in `app/repositories/`.
4. **API Endpoints**: Expose the functionality in `app/api/routes/` and create associated Pydantic schemas in `app/schemas/`.
5. **Frontend Integration**: Update React components to use the new endpoints. Ensure styling aligns with the existing dark/modern aesthetic.
6. **No Speculation**: Use the exact paths referenced in this document. Only use search tools if a specific detail inside a file is missing from here.

---

## 8. Recent Key Fixes and Enhancements

### 8.1 Backend & Database Stabilizations
- **Database Connection Resilience**: Enhanced SQLAlchemy configuration in `app/database.py` to use `pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`, and `pool_timeout=10` to prevent stale connection errors caused by Supabase Pooler network drops.
- **Asynchronous Unblocking**: Prevented the FastAPI event loop from being blocked by CPU-bound or synchronous tasks (like `bcrypt` password hashing and DB I/O) by wrapping the login logic inside `run_in_threadpool`.

### 8.2 Authentication Flow Improvements
- **Graceful Form/JSON parsing**: The `/login` route now correctly parses both `application/json` and `application/x-www-form-urlencoded` payloads without permanently hanging the request body stream.
- **Proxy Configuration**: Migrated Vite proxy settings in `vite.config.js` to route via `127.0.0.1` instead of `localhost` to bypass IPv6 resolution timeouts that were causing indefinite "Signing in..." states on the frontend.

### 8.3 Admin Dashboard state management
### 8.4 Docker & Containerization Readiness
- **Docker Compose Sync**: The project is fully equipped with a `docker-compose.yml` that orchestrates both the `backend` (FastAPI) and `frontend` (Vite/React -> NGINX).
- **Nginx Reverse Proxy**: Configured `frontend/nginx.conf` properly to strip the `/api` prefix when proxying requests to the internal backend container (`http://backend:8000/`), ensuring identical fetch paths between local bleeding-edge Vite dev-server usage and production Dockerized usage.

---
