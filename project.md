# Project: FlowFit (GentleGains)

**Role**: AI Collaborative Project
**Current Phase**: Phase 1 - Foundation & Navigation
**Last Update**: 2026-01-21

## 1. Project Overview & Architecture
**FlowFit** is a personal, single-user fitness web application designed to be frictionless.
It combines a **Next.js Frontend** for visualization/logging with a **Python FastAPI Backend** that hosts an **AI Agent (Gent)**.

### Architecture: Hybrid Full-Stack
- **Frontend**: Next.js 14+ (App Router) -> Direct Read from Supabase (for charts).
- **Backend**: Python FastAPI -> Writing to Supabase (via Agent Tools).
- **Database**: Supabase (PostgreSQL).
- **Auth**: None (Single User Mode).

## 2. Progress & Task Checklist

### Phase 1: Foundation & Navigation (📍 Current Focus)
- [ ] **Frontend Structure**
    - [ ] `app/page.js`: **Main Dashboard** (Charts Only).
    - [ ] `app/layout.js`: Global Navbar (Home/Workout, Food, Chat).
    - [ ] `app/workouts/page.js`: Workout List View.
    - [ ] `app/food/page.js`: Nutrition List View.
    - [ ] `app/chat/page.js`: Full-screen AI Chat.
- [ ] **Backend Structure**
    - [ ] Initialize `backend/` folder.
    - [ ] Setup `main.py`, `routers/`, `services/`, `tools/`.

### Phase 2: Feature Implementation
- [ ] **Dashboard Widgets**
    - [ ] Workout Volume Chart (Recharts).
    - [ ] Daily Calories/Macros Pie Chart.
- [ ] **Data Entry**
    - [ ] `app/workouts/add/page.js`: Manual Exercise Entry Form.
    - [ ] `app/food/upload/page.js`: Image Upload to Backend.
- [ ] **AI Backend**
    - [ ] Implement `agent_service.py` (LangChain).
    - [ ] Implement `tools/workout_tool.py` (DB Write).
    - [ ] Implement `tools/food_tool.py` (Vision + DB Write).

### Phase 3: Integration
- [ ] Connect Chat UI to `POST /api/chat`.
- [ ] Verify End-to-End Flow (Chat -> DB -> Dashboard Chart).

## 3. Detailed Requirements

### 3.1 Frontend (Next.js)
**Theme**: Warm Orange / Energetic Cute.
**Navigation**: Persistent Navbar on all pages.

| Page | Path | Functionality |
| :--- | :--- | :--- |
| **Dashboard** | `/` | **Charts Only**. Visual summary of progress. No logs list here. |
| **Workout** | `/workouts` | **List View**. History of workouts. Button to "Add Workout". |
| **Add Workout**| `/workouts/add`| Form/Tile UI to input Exercise, Weight, Reps, Sets. |
| **Food** | `/food` | **List View**. History of meals. Button to "Upload Food". |
| **Upload Food**| `/food/upload` | Image Input -> Sends to Backend Vision API. |
| **AI Chat** | `/chat` | Full-screen chat interface to talk to "Gent". |

### 3.2 Backend (FastAPI)
The backend is an **Agentic System** that listens for chat messages and performs actions using **Tools (MCP)**.

**Folder Structure**:
```text
backend/app/
├── main.py              # Entry Point
├── routers/
│   └── chat.py          # POST /api/chat
├── services/
│   ├── agent_service.py # LangChain Logic (Brain)
│   └── db.py            # Supabase Singleton
└── tools/               # The "Hands"
    ├── workout_tool.py  # func: record_workout(...)
    └── food_tool.py     # func: record_food(...)
```

### 3.3 Database Schema (Supabase)
- **`users`**: `id`, `username` (Simple Identity).
- **`workout_logs`**: `user_id`, `exercise`, `weight`, `reps`, `sets`, `created_at`.
- **`food_logs`**: `user_id`, `food_name`, `calories`, `protein`, `carbs`, `fat`, `created_at`.
- **`chat_logs`**: `session_id`, `user_query`, `ai_response`.

## 4. Agent Capabilities (MCP)
The Agent must be capable of **Function Calling**:
1.  **Intent Detection**: If user says "I squatted 100kg", recognize intent to Log Workout.
2.  **Tool Execution**: Call `tools.workout_tool.record_workout`.
3.  **Confirmation**: Reply "Great job! Logged 100kg Squat."
