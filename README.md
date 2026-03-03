# Focus Scoring Service

[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.2-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.32-blue.svg)](https://developers.google.com/mediapipe)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A sophisticated backend service built with **FastAPI** and **MediaPipe** for real-time focus detection and engagement scoring. This system combines head pose estimation, eye tracking, and face presence detection to monitor and report student engagement during study sessions.

---

## 🚀 Features

-   **AI-Powered Focus Detection**: Real-time analysis of head orientation (pitch, yaw, roll) and Eye Aspect Ratio (EAR).
-   **Absence Tracking**: Monitors and logs periods when the user is away from the camera.
-   **Engagement Reporting**: Generates comprehensive session reports with focus percentages and violation logs.
-   **Secure Authentication**: JWT-based authentication system with Bcrypt password hashing.
-   **Persistence Layer**: Dual-database support with PostgreSQL (SQLAlchemy) and MongoDB.
-   **Configurable Focus Zones**: Adjustable thresholds (Strict, Normal, Relaxed) for different monitoring environments.

---

## 🛠️ Tech Stack

-   **Framework**: FastAPI
-   **Computer Vision**: OpenCV, MediaPipe
-   **Database**: PostgreSQL (SQLAlchemy), MongoDB
-   **Security**: JWT (Jose), Passlib (Bcrypt)
-   **Environment**: Python 3.10

---

## ⚙️ Installation & Setup

Follow these steps to set up the project locally.

### 1. Prerequisites
Ensure you have **Python 3.10** installed on your system.
```bash
python3.10 --version
```

### 2. Create a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.
```bash
# Create the environment using Python 3.10
python3.10 -m venv venv

# Activate the environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# .\venv\Scripts\activate
```

### 3. Install Dependencies
Once the virtual environment is active, install the required packages:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the root directory and configure your settings (refer to `.env.example`):
```bash
cp .env.example .env
```

---

## 🏃 Running the Application

You can start the FastAPI server using `uvicorn`:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 📖 API Documentation
-   **Swagger UI**: `http://127.0.0.1:8000/docs`
-   **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## 📂 Project Structure

```text
├── app/
│   ├── api/            # Route handlers
│   ├── models/         # Database models
│   ├── repositories/   # Data access layer
│   ├── schemas/        # Pydantic models
│   ├── services/       # Business logic
│   └── utils/          # Helper functions
├── frontend/           # React + Vite Frontend
│   ├── src/            # Frontend Source Code
│   │   ├── components/ # React Components (Login, Signup)
│   │   └── ...
│   └── ...
├── focus_detector.py   # Core AI focus detection logic
├── main.py             # FastAPI entry point
├── config.py           # Configuration management
├── requirements.txt    # Project dependencies
└── .env                # Environment variables
```

---

## 🎨 Frontend (User Interface)

A modern and intuitive user interface built using **React** and **Vite**.

### ✨ Features
-   **Modern Design (Navy Theme)**: Deep navy blue aesthetic featuring high-fidelity Glassmorphism effects.
-   **Authentication Flow**: Clean and professional Login and Signup screens.
-   **Fully Responsive**: Smooth motion animations and adaptive layouts for a seamless cross-device experience.

### 🚀 Running the Frontend

To launch the frontend application, execute the following commands:

1.  **Navigate to the frontend directory**:
    ```bash
    cd frontend
    ```

2.  **Install dependencies (Initial setup)**:
    ```bash
    npm install
    ```

3.  **Start the development server**:
    ```bash
    npm run dev
    ```

The application will be accessible at: `http://localhost:3000`

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
