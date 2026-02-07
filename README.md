# FlowFit Web Platform

FlowFit is a frictionless fitness tracking platform that combines a modern dashboard with an intelligent AI Coach ("Gent").

## 🚀 Key Features

*   **Frictionless Auth**: No passwords. Just enter a username to start.
*   **Hybrid Dashboard**: Visualize your progress with interactive charts using Recharts.
*   **Tile-Based Logging**: One-click access to log common exercises.
*   **AI Coach "Gent"**: A persistent chat companion that answers questions and **automatically logs workouts** for you ("I just squat 100kg for 5 reps").

## 🛠 Tech Stack

### Frontend
*   **Framework**: Next.js 14 (App Router)
*   **Styling**: Tailwind CSS
*   **Icons**: Lucide React
*   **Charts**: Recharts

### Backend (AI Service)
*   **Runtime**: Python 3.10+
*   **Framework**: FastAPI
*   **AI**: LangChain + OpenAI/Gemini (function calling enabled)

### Database
*   **Supabase** (PostgreSQL)

## 🏗 Architecture

The system uses a **Hybrid Architecture**:
1.  **Frontend** reads directly from Supabase for fast data visualization.
2.  **Frontend** sends chat messages to the **Python Backend**.
3.  **Python Backend** processes intent and uses **Tools** to write data back to Supabase.

## 📂 Project Structure

*   `/app`: Next.js Frontend application.
*   `/backend`: Python FastAPI service.
*   `/supabase`: Database schema and migration scripts.

## 🏁 Getting Started

### 1. Database Setup
Run the SQL script in `supabase/schema.sql` to create the required tables.

### 2. Frontend
```bash
cd app
npm install
npm run dev
```

### 3. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
