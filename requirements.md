# Project Requirements & Development Checklist

## 1. Frontend (Next.js)
### 1.1 Core UI Structure
- [x] **Initialize Next.js Project** (Done)
- [x] **Setup Tailwind CSS & Globals** (Done, Cute Orange Theme)
- [x] **Global Navigation**
    - [x] Implement a `Navbar` component present on all pages.
    - [x] Navigation Buttons: **Workout (Home)**, **Nutrition**, **AI Coach**.
- [ ] **Routes & Pages**
    - [ ] `app/page.js`: **Main Dashboard** (Charts Only).
        - [ ] Workout Volume/Frequency Chart.
        - [ ] Daily Calories/Macros Chart.
    - [x] `app/workout/page.js`: **Workout Data** (List View).
        - [x] List of past workouts (Text/Table).
        - [x] "Add Workout" Button.
    - [x] `app/food/page.js`: **Nutrition Data** (List View).
        - [x] List of meal logs (Text/Table).
        - [x] "Upload Food" Button.
    - [ ] `app/chat/page.js`: **AI Coach** (Full screen chat).

### 1.2 Feature Details
- [ ] **Dashboard**
    - [ ] Daily Summary (Calories, Workout Volume).
    - [ ] Quick Actions (Log Workout, Upload Food).
- [ ] **Workout System**
    - [ ] Exercise Tile Grid (Quick Select).
    - [ ] Custom Set/Rep Form.
- [ ] **Nutrition System**
    - [ ] Image Upload UI -> Send to Backend Vision API.
    - [ ] Manual override for nutrition stats.
- [ ] **AI Chat Page**
    - [ ] Full-screen accessible chat interface.
    - [ ] History streaming.

## 2. Backend (Phase 3-2: AI & FastAPI)
### 2.1 Backend Architecture & Structure
- [x] **Folder Structure** (Strict Layered Architecture)
    - [x] `backend/app/main.py`: Entry point, CORS, Router include.
    - [ ] `backend/app/config.py`: Environment variables (`.env`).
    - [x] `backend/app/schemas.py`: Pydantic Models for Type Safety.
        - [x] `FoodAnalysisResult`: Structured Output (Name, Macros, Score).
    - [x] `backend/app/services/`: Business Logic.
        - [x] `ai_service.py`: OpenAI GPT-4o integration.
    - [x] `backend/app/repositories/`: Data Access.
        - [x] `food_repository.py`: Surpoabse CRUD.
    - [x] `backend/app/routers/`: API Endpoints.
        - [x] `food.py`: `POST /api/v1/food/analyze` (Integrated in main.py).

### 2.2 API Endpoints
- [x] `POST /api/v1/food/analyze`:
    - Input: `AnalyzeRequest` (Base64 Image).
    - Process: `AIService` -> `FoodRepository`.
    - Output: `FoodAnalysisResult`.

### 2.3 AI Services (`services/`)
- [x] **AI Service (`ai_service.py`)**
    - [x] Use `client.beta.chat.completions.parse` for Structured Outputs.
    - [x] Prompt: Conservative Nutritionist.
- [x] **Food Repository (`food_repository.py`)**
    - [x] Save results to `food_logs` table in Supabase.
    - [ ] **Test**: `test_user_creation`: Verify ID formatting.

### 2.3 Agent Tools (The "Hands")
- [ ] **Workout Tool**
    - [ ] Function: `record_workout(exercise, weight, reps, sets)`.
    - [ ] **Test**: Call function -> Verify Supabase row created.
- [ ] **Nutrition Tool**
    - [ ] Function: `record_food(food_name, calories, macros)`.
    - [ ] **Test**: Call function -> Verify Supabase row created.

## 3. Database (Supabase)
- [x] **Schema Design** (Done)
    - [x] `users` (No Auth, just ID/Username)
    - [x] `workout_logs`
    - [ ] `chat_logs`
    - [ ] **Migration**: Ensure RLS policies allow the single-user flow.

## 4. Integration Tests
- [ ] **E2E Flow**
    - [ ] Frontend sends "I ate a burger" -> Backend parses -> DB updates -> Frontend Chart updates.
