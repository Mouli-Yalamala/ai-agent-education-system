# AI Agent Educational Content Pipeline

This repository contains a modular AI agent pipeline that automatically generates, reviews, and refines educational content. The system uses a FastAPI backend to orchestrate interactions with the Groq API, and a React frontend for the user interface.

## Live Demo
**[Insert Deployed Frontend URL Here]**

**CRITICAL NOTE FOR REVIEWERS:** 
The API backend is hosted on a free-tier cloud service which automatically spins down after periods of inactivity. **The very first time you click "Generate," it may take up to 60 seconds for the backend server to wake up.** Please be patient during the first generation! Subsequent requests will be instantaneous.

## Architecture

The application is built on a straightforward decoupled architecture:
1. Backend (FastAPI): Manages the LLM agents. Features strict Pydantic JSON schema validation and a built-in retry mechanism.
2. Frontend (React): A single page application built with Vite and custom CSS. It consumes the backend REST API to display the generation and review steps.

## Agent Pipeline Flow

The AI pipeline logic consists of two main agents:
- Generator Agent: Receives a grade and topic, then generates simple explanations and multiple-choice questions. It is forced to output strict JSON.
- Reviewer Agent: Evaluates the generator's output. If the content is too advanced or inaccurate, the reviewer fails the output and logs specific critiques. The pipeline then triggers a single retry constraint to refine the initial generation.

---

## Local Setup Instructions

If you prefer to run this application locally on your own machine instead of the live demo, follow these steps.

### 1. Backend Setup

Open a terminal and navigate to the backend directory:
```bash
cd Backend
```

Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

Install the required python packages:
```bash
pip install -r requirements.txt
```

Create a .env file in the Backend directory with your Groq API key:
```text
GROQ_API_KEY=your_key_here
```

Start the FastAPI server:
```bash
uvicorn main:app --reload
```
The backend API will run on http://127.0.0.1:8000. 

### 2. Frontend Setup

Open a separate terminal and navigate to the frontend directory:
```bash
cd Frontend
```

Install the node modules for the React application:
```bash
npm install
```

Start the local development server:
```bash
npm run dev
```

Open your browser and navigate to the link provided in the terminal (usually http://localhost:5173). The React application is now connected to the FastAPI backend.
