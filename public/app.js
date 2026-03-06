// ============================================================
// ANALYTIC AI — Course Catalog  |  app.js
// Firebase Firestore integration + UI rendering + filters
// ============================================================

// ── Firebase Configuration ────────────────────────────────
const firebaseConfig = {
  apiKey: "AIzaSyASF9zYa7qx_ExqUmfSVVTOhFkzD85PBqo",
  authDomain: "analytic-ai-icg.firebaseapp.com",
  projectId: "analytic-ai-icg",
  storageBucket: "analytic-ai-icg.firebasestorage.app",
  messagingSenderId: "661294589503",
  appId: "1:661294589503:web:194188919026f0d2e9fa8a"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

// ── Course Data (seed + fallback) ─────────────────────────
const COURSE_DATA = [
  {
    id: "P1",
    order: 1,
    title: "Data Upload Layer",
    tag: "upload",
    theme: "theme-blue",
    icon: "📤",
    level: 1,
    levelLabel: "Beginner",
    description: "Ingest business data from any source — CSV, Excel (.xlsx), MySQL, PostgreSQL, or POS system exports — through a secure web interface and API endpoint pipeline.",
    tools: ["FastAPI", "Django", "PostgreSQL", "MySQL", "AWS S3", "Azure Blob"],
    keyPoints: [
      "Multi-format file upload (CSV, XLS)",
      "Direct DB connection (MySQL / PostgreSQL)",
      "POS system export parsing",
      "Cloud storage integration"
    ]
  },
  {
    id: "P2",
    order: 2,
    title: "Data Cleaning Engine",
    tag: "cleaning",
    theme: "theme-teal",
    icon: "🧹",
    level: 2,
    levelLabel: "Intermediate",
    description: "Automated Python + Pandas cleaning pipeline: removes duplicates, normalizes column names, handles missing values, detects outliers with IQR/Z-score, and formats Kenyan Shillings (KES).",
    tools: ["pandas", "numpy", "scikit-learn", "Python 3.11+"],
    keyPoints: [
      "Blank/duplicate row removal",
      "Column name normalization",
      "Median/mean imputation for numerics",
      "IQR & Z-score outlier detection",
      "KES currency formatting"
    ]
  },
  {
    id: "P3",
    order: 3,
    title: "SQL Storage & Query Layer",
    tag: "storage",
    theme: "theme-purple",
    icon: "🗄️",
    level: 2,
    levelLabel: "Intermediate",
    description: "After cleaning, data lands in a structured SQL database. Build and run KPI queries, filter by date/branch/product, and power scalable business intelligence at any volume.",
    tools: ["PostgreSQL", "MySQL", "SQLAlchemy", "Alembic"],
    keyPoints: [
      "Structured schema from cleaned data",
      "SUM / AVG / GROUP BY KPI queries",
      "Multi-branch and date filtering",
      "Scalable indexing strategy"
    ]
  },
  {
    id: "P4",
    order: 4,
    title: "Analytical Engine",
    tag: "analytics",
    theme: "theme-amber",
    icon: "📐",
    level: 2,
    levelLabel: "Intermediate",
    description: "NumPy-powered KPI engine that auto-calculates Total Revenue, Monthly Growth Rate, Profit Margin, CLV, Client Retention Rate, and more — fully vectorized for speed.",
    tools: ["numpy", "pandas", "scipy", "Python"],
    keyPoints: [
      "Monthly growth rate = (curr - prev) / prev",
      "Profit margin = (net / revenue) × 100",
      "Customer Lifetime Value calculation",
      "Retail & service KPI presets",
      "Inventory turnover metrics"
    ]
  },
  {
    id: "P5",
    order: 5,
    title: "Visualization Layer",
    tag: "viz",
    theme: "theme-green",
    icon: "📊",
    level: 2,
    levelLabel: "Intermediate",
    description: "Auto-generate revenue trend lines, product distribution pie charts, branch performance bar graphs, sales heatmaps, and customer segmentation scatter plots using Seaborn and Matplotlib.",
    tools: ["seaborn", "matplotlib", "plotly", "Dash"],
    keyPoints: [
      "Revenue trend line chart",
      "Pie chart — product distribution",
      "Bar graph — branch performance",
      "Heatmap — sales by weekday",
      "Scatter — customer segmentation"
    ]
  },
  {
    id: "P6",
    order: 6,
    title: "Automated Insight Generator",
    tag: "insights",
    theme: "theme-rose",
    icon: "💡",
    level: 3,
    levelLabel: "Advanced",
    description: "The differentiator: the system writes human-readable business insights like 'Revenue dropped 12% in February. Product X is underperforming. Consider revising pricing.' Rule-based + AI hybrid logic.",
    tools: ["Python", "OpenAI API", "spaCy", "Jinja2"],
    keyPoints: [
      "Rule-based insight templates",
      "AI-augmented narrative generation",
      "Month-over-month commentary",
      "Actionable recommendations",
      "Auto-triggered on new data load"
    ]
  },
  {
    id: "P7",
    order: 7,
    title: "Output Reports",
    tag: "reports",
    theme: "theme-indigo",
    icon: "📄",
    level: 2,
    levelLabel: "Intermediate",
    description: "One-click export of professional PDF reports, cleaned Excel sheets, KPI summary spreadsheets, and executive summary documents — ready to share with stakeholders.",
    tools: ["ReportLab", "openpyxl", "WeasyPrint", "Jinja2"],
    keyPoints: [
      "PDF report with charts embedded",
      "Cleaned data Excel export",
      "KPI summary sheet (XLSX)",
      "Executive summary (branded)",
      "Scheduled weekly/monthly delivery"
    ]
  },
  {
    id: "P8",
    order: 8,
    title: "Predictive Analytics",
    tag: "ml",
    theme: "theme-orange",
    icon: "🔮",
    level: 3,
    levelLabel: "Advanced",
    description: "Go beyond reporting — use linear regression, time-series forecasting, and demand prediction to anticipate future revenue, stock needs, and growth trajectories for your business.",
    tools: ["scikit-learn", "statsmodels", "prophet", "numpy"],
    keyPoints: [
      "Linear regression for revenue",
      "Time series (Prophet / ARIMA)",
      "Demand prediction model",
      "Confidence intervals",
      "Automated retraining pipeline"
    ]
  },
  {
    id: "P9",
    order: 9,
    title: "SME Dashboard & ML Suite",
    tag: "dashboard",
    theme: "theme-cyan",
    icon: "🖥️",
    level: 3,
    levelLabel: "Advanced",
    description: "The complete SME owner experience: a secure login dashboard showing live KPIs, growth trends, and AI alerts — plus ML modules for K-Means segmentation, churn prediction, and fraud detection.",
    tools: ["Streamlit", "Dash", "Firebase Auth", "scikit-learn"],
    keyPoints: [
      "Secure business owner login",
      "Live KPI dashboard view",
      "K-Means customer segmentation",
      "Churn prediction model",
      "Fraud detection pipeline",
      "Mobile-responsive design"
    ]
  }
];

// ── Particles ──────────────────────────────────────────────
function initParticles() {
  const container = document.getElementById('particles');
  if (!container) return;
  for (let i = 0; i < 25; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    p.style.cssText = `
      left: ${Math.random() * 100}%;
      top: ${Math.random() * 100}%;
      animation-duration: ${6 + Math.random() * 10}s;
      animation-delay: ${Math.random() * 8}s;
      width: ${1 + Math.random() * 3}px;
      height: ${1 + Math.random() * 3}px;
      opacity: 0;
    `;
    container.appendChild(p);
  }
}

// ── Render a single course card ────────────────────────────
function renderCard(course, index) {
  const levelDots = [1,2,3].map(d =>
    `<span class="level-dot ${d <= course.level ? 'active' : ''}"></span>`
  ).join('');

  const tools = (course.tools || []).map(t =>
    `<span class="tool-chip">${t}</span>`
  ).join('');

  const card = document.createElement('article');
  card.className = `course-card ${course.theme || ''}`;
  card.setAttribute('data-tag', course.tag || 'all');
  card.style.animationDelay = `${index * 0.07}s`;
  card.setAttribute('id', `card-${course.id}`);

  card.innerHTML = `
    <div class="card-header">
      <div class="card-icon">${course.icon || '📦'}</div>
      <div class="card-meta">
        <span class="card-number">MODULE ${String(course.order).padStart(2,'0')}</span>
        <span class="card-tag">${course.tag?.toUpperCase()}</span>
      </div>
    </div>
    <h3 class="card-title">${course.title}</h3>
    <p class="card-desc">${course.description}</p>
    <div class="card-tools">${tools}</div>
    <div class="card-footer">
      <div class="card-level">
        <div class="level-dots">${levelDots}</div>
        <span>${course.levelLabel || 'Beginner'}</span>
      </div>
      <span class="card-cta">Explore Module →</span>
    </div>
  `;
  return card;
}

// ── Render all cards from array ────────────────────────────
function renderCourses(courses) {
  const grid = document.getElementById('courses-grid');
  const loading = document.getElementById('loading-state');
  if (loading) loading.remove();
  grid.innerHTML = '';

  const sorted = [...courses].sort((a, b) => (a.order || 0) - (b.order || 0));
  sorted.forEach((course, i) => {
    grid.appendChild(renderCard(course, i));
  });

  const statEl = document.getElementById('stat-modules');
  if (statEl) statEl.textContent = sorted.length;

  initFilters(sorted);
}

// ── Filter Logic ───────────────────────────────────────────
function initFilters(courses) {
  const bar = document.getElementById('filter-bar');
  if (!bar) return;

  bar.addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;

    bar.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const filter = btn.dataset.filter;
    const cards = document.querySelectorAll('.course-card');
    cards.forEach(card => {
      const match = filter === 'all' || card.dataset.tag === filter;
      card.classList.toggle('hidden', !match);
      if (match) {
        card.style.animation = 'none';
        void card.offsetHeight; // reflow
        card.style.animation = '';
      }
    });
  });
}

// ── Seed Firestore (one-time) ──────────────────────────────
async function seedFirestore(courses) {
  const batch = db.batch();
  courses.forEach(course => {
    const ref = db.collection('courses').doc(course.id);
    batch.set(ref, course, { merge: true });
  });
  await batch.commit();
  console.log('✅ Firestore seeded with', courses.length, 'courses.');
}

// ── Load courses from Firestore ────────────────────────────
async function loadCourses() {
  try {
    const snap = await db.collection('courses').get();

    if (snap.empty) {
      // First run: seed Firestore then render
      console.log('🌱 Seeding Firestore...');
      await seedFirestore(COURSE_DATA);
      renderCourses(COURSE_DATA);
    } else {
      const courses = snap.docs.map(doc => ({ ...doc.data(), id: doc.id }));
      renderCourses(courses);
    }
  } catch (err) {
    console.warn('⚠️ Firestore unavailable — using local data.', err.message);
    renderCourses(COURSE_DATA);
  }
}

// ── Navbar scroll effect ───────────────────────────────────
function initNavbar() {
  const nav = document.getElementById('navbar');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 40
      ? '0 4px 30px rgba(0,0,0,0.4)'
      : 'none';
  }, { passive: true });
}

// ── Init ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  initNavbar();
  loadCourses();
});
