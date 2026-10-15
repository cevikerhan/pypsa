# PyPSA Studio

This directory contains a professional starter GUI for PyPSA with a FastAPI backend and a React + Material UI frontend.

## Overview

- Backend: Python/FastAPI
- Frontend: React + TypeScript + Vite + Material UI
- Visualization: Recharts
- PyPSA integration: opens PyPSA example networks and runs optimization flows

## Quick start

### 1) Backend

```bash
cd gui/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

```bash
cd gui/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Then open: http://localhost:5173

## Included in this scaffold

- Sidebar-based professional dashboard
- PyPSA system overview cards
- Network summary panel
- Run optimization workflow button
- Results area with KPIs and charts
- API endpoints for PyPSA model loading and optimization

## Notes

This is a polished starter implementation meant to be expanded into a full PyPSA desktop-style web application.
