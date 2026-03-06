# Analytic AI — README
# =======================

## 🚀 Quick Start

### 1. Create virtual environment
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env if needed (default uses SQLite — no setup required)
```

### 4. Start the API server
```bash
uvicorn main:app --reload
```

The API is now running at:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**:      http://127.0.0.1:8000/redoc
- **Health**:     http://127.0.0.1:8000/health

---

## 📡 API Workflow

```
1. POST /upload/csv          → Upload your data file
2. POST /clean/{id}          → Auto-clean the dataset
3. GET  /analytics/{id}      → Compute KPIs (revenue, margin, growth…)
4. GET  /visualize/{id}      → Generate all 5 charts (PNG base64)
5. GET  /insights/{id}       → Get written business insights
6. GET  /reports/{id}/pdf    → Download PDF report
7. GET  /reports/{id}/excel  → Download Excel report
```

---

## 🧪 Run Tests

```bash
cd backend
pytest tests/ -v
```

---

## 📁 Directory Structure

```
backend/
├── main.py             ← FastAPI entry point
├── requirements.txt    ← Python dependencies
├── .env.example        ← Environment template
├── conftest.py         ← pytest path setup
├── core/
│   ├── config.py       ← App settings
│   └── database.py     ← SQLAlchemy async DB
├── engines/
│   ├── cleaner.py      ← Pandas cleaning pipeline
│   ├── analytics.py    ← NumPy KPI engine
│   ├── visualizer.py   ← Seaborn/Matplotlib charts
│   ├── insight_gen.py  ← Rule-based insight writer
│   └── reporter.py     ← PDF + Excel export
├── routers/
│   ├── upload.py       ← POST /upload/*
│   ├── clean.py        ← POST /clean/{id}
│   ├── analytics.py    ← GET /analytics/{id}
│   ├── visualize.py    ← GET /visualize/{id}/*
│   ├── insights.py     ← GET /insights/{id}
│   └── reports.py      ← GET /reports/{id}/pdf|excel
├── models/
│   ├── dataset.py      ← SQLAlchemy ORM models
│   └── schemas.py      ← Pydantic schemas
├── uploads/            ← Uploaded raw files
├── outputs/            ← Generated charts, PDFs, Excel
└── tests/
    ├── sample_sales.csv
    └── test_engines.py
```

---

## 🌐 Frontend

The accompanying course catalog frontend is live at:
**https://analytic-ai-icg.web.app**

To connect the frontend to this backend, update `CORS_ORIGINS` in `.env`.
