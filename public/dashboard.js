/**
 * Analytic AI — Dashboard Logic
 * Connects the 6-step UI to the FastAPI backend at localhost:8000
 */

// API_URL: uses config.js in production (Firebase), falls back to localhost for local dev
const API = (typeof CONFIG !== 'undefined' && CONFIG.API_URL)
    ? CONFIG.API_URL
    : 'http://127.0.0.1:8000';

let datasetId = null;   // Active dataset ID from the backend
let kpisCache = null;   // Cached KPI results
let chartCache = {};     // Cached chart base64 per chart_type

/** Safely extract an error message from any Response (JSON or plain text/HTML) */
async function extractError(res) {
    const text = await res.text();
    try {
        const j = JSON.parse(text);
        return j.detail || j.message || JSON.stringify(j);
    } catch {
        if (res.status === 500) return 'Server error (500). The server crashed — check the uvicorn terminal for the traceback. If you just restarted the backend, please re-upload your file first.';
        if (res.status === 404) return 'Dataset not found (404). Please re-upload your file — it was lost when the server restarted.';
        if (res.status === 422) return 'Validation error: ' + text.slice(0, 200);
        return `Error ${res.status}: ${text.slice(0, 150)}`;
    }
}

// ─────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkApiStatus();
    setupUploadZone();
    setupPipelineNav();
    setupChartTabs();
    loadDatasetList();
    wireButtons();
});

// ─────────────────────────────────────────────────────────────
// API health check
// ─────────────────────────────────────────────────────────────
async function checkApiStatus() {
    const dot = document.getElementById('api-status');
    const label = document.getElementById('api-label');
    try {
        const res = await fetch(`${API}/health`, { signal: AbortSignal.timeout(4000) });
        if (res.ok) {
            dot.classList.replace('offline', 'online');
            label.textContent = 'API connected';
        } else { throw new Error(); }
    } catch {
        dot.classList.add('offline');
        label.textContent = 'API offline — start uvicorn';
        showToast('⚠️ Backend not reachable. Run: uvicorn main:app --reload', 'error', 6000);
    }
}

// ─────────────────────────────────────────────────────────────
// Step navigation
// ─────────────────────────────────────────────────────────────
function setupPipelineNav() {
    document.querySelectorAll('.step-item:not(.locked)').forEach(item => {
        item.addEventListener('click', () => {
            if (!item.classList.contains('locked')) showStep(item.dataset.step);
        });
    });
}

function showStep(name) {
    document.querySelectorAll('.step-section').forEach(s => {
        s.classList.add('hidden'); s.classList.remove('active');
    });
    document.querySelectorAll('.step-item').forEach(i => i.classList.remove('active'));
    const sec = document.getElementById(`step-${name}`);
    if (sec) { sec.classList.remove('hidden'); sec.classList.add('active'); }
    const nav = document.getElementById(`nav-${name}`);
    if (nav) nav.classList.add('active');
}

function unlockStep(name) {
    const nav = document.getElementById(`nav-${name}`);
    if (nav) nav.classList.remove('locked');
}

function markDone(name) {
    const nav = document.getElementById(`nav-${name}`);
    if (!nav) return;
    nav.classList.add('done'); nav.classList.remove('locked');
    const tick = nav.querySelector('.step-tick');
    if (tick) tick.classList.remove('hidden');
}

// ─────────────────────────────────────────────────────────────
// Wire all action buttons in one place (avoids double-listener issues)
// ─────────────────────────────────────────────────────────────
function wireButtons() {
    // Step 1 → 2
    document.getElementById('go-clean-btn').addEventListener('click', () => {
        showStep('clean'); populateCleanPreview();
    });
    // Step 2
    document.getElementById('run-clean-btn').addEventListener('click', runClean);
    document.getElementById('go-analytics-btn').addEventListener('click', () => showStep('analytics'));
    // Step 3
    document.getElementById('run-analytics-btn').addEventListener('click', runAnalytics);
    document.getElementById('run-forecast-btn').addEventListener('click', runForecast);
    document.getElementById('go-charts-btn').addEventListener('click', () => showStep('charts'));
    // Step 5
    document.getElementById('run-insights-btn').addEventListener('click', runInsights);
    document.getElementById('go-insights-btn').addEventListener('click', () => showStep('insights'));
    // Step 5 → 6
    document.getElementById('go-reports-btn').addEventListener('click', () => { showStep('reports'); unlockStep('reports'); });
    // Step 6
    document.getElementById('dl-pdf-btn').addEventListener('click', () => downloadReport('pdf'));
    document.getElementById('dl-excel-btn').addEventListener('click', () => downloadReport('excel'));
    // Start over
    document.getElementById('start-over-btn').addEventListener('click', resetAll);
}

// ─────────────────────────────────────────────────────────────
// STEP 1 — Upload
// ─────────────────────────────────────────────────────────────
function setupUploadZone() {
    const zone = document.getElementById('drop-zone');
    const input = document.getElementById('file-input');
    const browse = document.getElementById('browse-btn');
    const sample = document.getElementById('sample-btn');

    browse.addEventListener('click', () => input.click());
    zone.addEventListener('click', e => { if (e.target !== browse) input.click(); });
    input.addEventListener('change', () => { if (input.files[0]) uploadFile(input.files[0]); });

    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
        e.preventDefault(); zone.classList.remove('drag-over');
        if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
    });

    sample.addEventListener('click', loadSampleData);
}

async function uploadFile(file) {
    const allowed = ['.csv', '.xlsx', '.xls'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showToast('❌ Only .csv, .xlsx, or .xls files allowed.', 'error'); return;
    }

    showProgress(file.name);
    const formData = new FormData();
    formData.append('file', file);
    const endpoint = ext === '.csv' ? '/upload/csv' : '/upload/excel';

    try {
        animateProgress(0, 60, 800);
        const res = await fetch(`${API}${endpoint}`, { method: 'POST', body: formData });
        animateProgress(60, 100, 400);
        if (!res.ok) throw new Error(await extractError(res));
        const data = await res.json();
        datasetId = data.dataset_id;
        kpisCache = null; chartCache = {};
        showUploadResult(data);
        markDone('upload'); unlockStep('clean');
        loadDatasetList();
        showToast(`✅ "${file.name}" uploaded (${data.rows.toLocaleString()} rows)`);
    } catch (err) {
        hideProgress();
        showToast(`❌ ${err.message}`, 'error');
    }
}

async function loadSampleData() {
    showLoading('Loading sample data…');
    try {
        const csv = `date,product,branch,revenue,cost,quantity,customer_id
2025-01-05,Maize Flour 2kg,Nairobi CBD,1200,820,40,C001
2025-01-06,Cooking Oil 1L,Westlands,850,560,25,C002
2025-01-07,Sugar 1kg,Eastleigh,450,290,60,C003
2025-02-03,Maize Flour 2kg,Nairobi CBD,1400,820,47,C001
2025-02-08,Rice 2kg,Eastleigh,940,620,28,C008
2025-02-20,Rice 2kg,Westlands,1020,620,31,C005
2025-03-04,Maize Flour 2kg,Nairobi CBD,1500,820,50,C001
2025-03-10,Rice 2kg,Nairobi CBD,1100,620,33,C004
2025-04-02,Rice 2kg,Westlands,950,620,28,C008
2025-04-15,Maize Flour 2kg,Nairobi CBD,1600,820,53,C013`;
        const blob = new Blob([csv], { type: 'text/csv' });
        const sample = new File([blob], 'sample_sales.csv', { type: 'text/csv' });
        const fd = new FormData(); fd.append('file', sample);

        const res = await fetch(`${API}/upload/csv`, { method: 'POST', body: fd });
        if (!res.ok) throw new Error(await extractError(res));
        const data = await res.json();
        datasetId = data.dataset_id;
        kpisCache = null; chartCache = {};
        showUploadResult(data);
        markDone('upload'); unlockStep('clean');
        loadDatasetList();
        showToast('✅ Sample data loaded!');
    } catch (err) {
        showToast(`❌ ${err.message}`, 'error');
    } finally { hideLoading(); }
}

function showUploadResult(data) {
    hideProgress();
    document.getElementById('result-name').textContent = data.name;
    document.getElementById('result-meta').textContent =
        `${data.rows.toLocaleString()} rows · ${data.columns.length} columns`;
    renderTable(data.preview, data.columns, 'preview-table');
    document.getElementById('upload-result').classList.remove('hidden');
}

// ─────────────────────────────────────────────────────────────
// STEP 2 — Clean
// ─────────────────────────────────────────────────────────────
function populateCleanPreview() {
    if (!datasetId) return;
    const meta = document.getElementById('result-meta').textContent;
    const rows = meta.split(' rows')[0] || '—';
    const cols = (meta.split('· ')[1] || '').split(' col')[0] || '—';
    document.querySelector('#cs-rows .cs-num').textContent = rows;
    document.querySelector('#cs-cols .cs-num').textContent = cols;
    document.querySelector('#cs-status .cs-num').textContent = 'Pending';
    document.querySelector('#cs-status .cs-num').style.color = '';
}

async function runClean() {
    if (!datasetId) { showToast('Upload a file first', 'error'); return; }
    showLoading('🧹 Cleaning data…');
    try {
        const res = await fetch(`${API}/clean/${datasetId}`, { method: 'POST' });
        if (!res.ok) throw new Error(await extractError(res));
        const data = await res.json();
        showCleanResult(data);
        markDone('clean'); unlockStep('analytics');
        showToast('✅ Data cleaned successfully!');
    } catch (err) { showToast(`❌ ${err.message}`, 'error'); }
    finally { hideLoading(); }
}

function showCleanResult(data) {
    document.querySelector('#cs-rows .cs-num').textContent = (data.rows_after || 0).toLocaleString();
    const statusEl = document.querySelector('#cs-status .cs-num');
    statusEl.textContent = '✅ Clean';
    statusEl.style.color = 'var(--green)';

    const stats = [
        { v: data.rows_before, l: 'Rows Before' },
        { v: data.rows_after, l: 'Rows After' },
        { v: data.rows_removed, l: 'Rows Removed' },
        { v: data.duplicates_removed, l: 'Duplicates Removed' },
        { v: data.nulls_filled, l: 'Nulls Filled' },
        { v: data.outliers_flagged, l: 'Outliers Flagged' },
    ];
    document.getElementById('clean-stats-grid').innerHTML = stats.map(s =>
        `<div class="stat-box"><div class="sv">${(s.v || 0).toLocaleString()}</div><div class="sl">${s.l}</div></div>`
    ).join('');
    document.getElementById('clean-result').classList.remove('hidden');
}

// ─────────────────────────────────────────────────────────────
// STEP 3 — Analytics
// ─────────────────────────────────────────────────────────────
async function runAnalytics() {
    if (!datasetId) return;
    showLoading('⚡ Computing KPIs…');
    try {
        const res = await fetch(`${API}/analytics/${datasetId}`);
        if (!res.ok) throw new Error(await extractError(res));
        const data = await res.json();
        kpisCache = data;
        renderKPIs(data);
        markDone('analytics'); unlockStep('charts');
        showToast('✅ KPIs computed!');
    } catch (err) { showToast(`❌ ${err.message}`, 'error'); }
    finally { hideLoading(); }
}

function renderKPIs(data) {
    const fmtKES = v => v != null ? `KES ${(+v).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—';
    const fmtPct = v => v != null ? `${(+v).toFixed(2)}%` : '—';
    const growthClass = v => v == null ? '' : v >= 0 ? 'kpi-growth-pos' : 'kpi-growth-neg';
    const growthArrow = v => v == null ? '' : v >= 0 ? '▲ ' : '▼ ';

    const cards = [
        { label: 'Total Revenue', value: fmtKES(data.total_revenue), sub: data.currency || 'KES' },
        { label: 'Profit Margin', value: fmtPct(data.profit_margin), sub: 'Net / Revenue' },
        { label: 'Monthly Growth', value: fmtPct(data.growth_rate), sub: 'Month-on-Month', growth: data.growth_rate },
        { label: 'Top Product', value: data.top_product || '—', sub: 'Best seller' },
        { label: 'Top Branch', value: data.top_branch || '—', sub: 'Highest revenue' },
        { label: 'Annual Customer LTV', value: fmtKES(data.clv), sub: 'Lifetime value est.' },
    ];

    document.getElementById('kpi-grid').innerHTML = cards.map(c => `
    <div class="kpi-card">
      <div class="kpi-label">${c.label}</div>
      <div class="kpi-value ${c.growth != null ? growthClass(c.growth) : ''}">${c.growth != null ? growthArrow(c.growth) : ''}${c.value}</div>
      <div class="kpi-sub">${c.sub}</div>
    </div>`).join('');

    const monthly = data.monthly_revenue || [];
    if (monthly.length > 0) {
        const maxRev = Math.max(...monthly.map(m => m.revenue));
        document.getElementById('monthly-bars').innerHTML = monthly.map(m => {
            const pct = maxRev > 0 ? (m.revenue / maxRev * 100).toFixed(1) : 0;
            const g = m.growth_rate;
            const gStr = g != null
                ? `<span class="${g >= 0 ? 'kpi-growth-pos' : 'kpi-growth-neg'}">${g >= 0 ? '+' : ''}${g.toFixed(1)}%</span>`
                : '<span></span>';
            return `<div class="month-row">
        <span class="month-label">${m.period}</span>
        <div class="month-bar-wrap"><div class="month-bar-fill" style="width:${pct}%"></div></div>
        <span class="month-value">KES ${(+m.revenue).toLocaleString()}</span>
        <span class="month-growth">${gStr}</span>
      </div>`;
        }).join('');
        document.getElementById('monthly-section').classList.remove('hidden');
    }
    document.getElementById('analytics-result').classList.remove('hidden');
}

// ─────────────────────────────────────────────────────────────
// Forecast
// ─────────────────────────────────────────────────────────────
async function runForecast() {
    if (!datasetId) return;
    showLoading('🔮 Running AI forecasting model (Linear Regression)…');
    try {
        const res = await fetch(`${API}/forecast/${datasetId}?periods=3`);
        if (!res.ok) throw new Error(await extractError(res));
        const data = await res.json();
        renderForecast(data);
        showToast('✅ Forecast generated!');
    } catch (err) { showToast(`❌ ${err.message}`, 'error'); }
    finally { hideLoading(); }
}

function renderForecast(data) {
    const section = document.getElementById('forecast-section');
    const grid = document.getElementById('forecast-grid');

    if (!data.forecast || data.forecast.length === 0) {
        showToast('No forecast available', 'warning');
        return;
    }

    grid.innerHTML = data.forecast.map(f => `
    <div class="kpi-card" style="border: 1px solid var(--purple)">
      <div class="kpi-label">${f.period_label}</div>
      <div class="kpi-value kpi-growth-pos">KES ${(+f.forecasted_revenue).toLocaleString('en-KE', { maximumFractionDigits: 0 })}</div>
    </div>`).join('');

    section.classList.remove('hidden');
}

// ─────────────────────────────────────────────────────────────
// STEP 4 — Charts
// ─────────────────────────────────────────────────────────────
function setupChartTabs() {
    document.querySelectorAll('.chart-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            loadChart(tab.dataset.chart);
        });
    });
}

async function loadChart(chartType) {
    if (!datasetId) { showToast('Upload data first', 'error'); return; }
    const display = document.getElementById('chart-display');

    if (chartCache[chartType]) {
        display.innerHTML = `<img src="${chartCache[chartType]}" alt="${chartType}" style="width:100%;border-radius:12px" />`;
        return;
    }

    display.innerHTML = `<div class="chart-placeholder"><div class="spinner" style="margin:0 auto"></div><p style="margin-top:1rem">Generating chart…</p></div>`;
    try {
        const res = await fetch(`${API}/visualize/${datasetId}/${chartType}`);
        if (!res.ok) throw new Error(await extractError(res));
        const data = await res.json();
        chartCache[chartType] = data.data_url;
        display.innerHTML = `<img src="${data.data_url}" alt="${data.title}" style="width:100%;border-radius:12px" />`;
        markDone('charts'); unlockStep('insights');
    } catch (err) {
        display.innerHTML = `<div class="chart-placeholder"><p style="color:var(--red)">❌ ${err.message}</p></div>`;
        showToast(`❌ ${err.message}`, 'error');
    }
}

// ─────────────────────────────────────────────────────────────
// STEP 5 — Insights
// ─────────────────────────────────────────────────────────────
async function runInsights() {
    if (!datasetId) return;
    showLoading('💡 Generating insights…');
    try {
        const res = await fetch(`${API}/insights/${datasetId}`);
        if (!res.ok) throw new Error(await extractError(res));
        const data = await res.json();
        renderInsights(data);
        markDone('insights'); unlockStep('reports');
        showToast('✅ Insights generated!');
    } catch (err) { showToast(`❌ ${err.message}`, 'error'); }
    finally { hideLoading(); }
}

function renderInsights(data) {
    const summaryEl = document.getElementById('exec-summary');
    summaryEl.innerHTML = '<h4>Executive Summary</h4>' +
        (data.executive_summary || '')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

    const icons = { info: 'ℹ️', warning: '⚠️', critical: '🚨' };
    document.getElementById('insights-list').innerHTML = (data.insights || []).map(i => `
    <div class="insight-item ${i.severity}">
      <span class="insight-tag ${i.severity}">${i.category}</span>
      <p>${icons[i.severity] || '•'} ${i.text}</p>
    </div>`).join('');

    document.getElementById('insights-result').classList.remove('hidden');
}

// ─────────────────────────────────────────────────────────────
// STEP 6 — Reports
// ─────────────────────────────────────────────────────────────
async function downloadReport(format) {
    if (!datasetId) { showToast('No dataset selected', 'error'); return; }
    const btn = document.getElementById(`dl-${format}-btn`);
    btn.disabled = true; btn.textContent = '⏳ Generating…';
    showLoading(`📄 Generating ${format.toUpperCase()} report…`);
    try {
        const res = await fetch(`${API}/reports/${datasetId}/${format}`);
        if (!res.ok) throw new Error(await extractError(res));
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AnalyticAI_Report.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
        a.click(); URL.revokeObjectURL(url);
        showToast(`✅ ${format.toUpperCase()} downloaded!`);
    } catch (err) { showToast(`❌ ${err.message}`, 'error'); }
    finally {
        hideLoading();
        btn.disabled = false;
        btn.textContent = `⬇ Download ${format.toUpperCase()}`;
    }
}

// ─────────────────────────────────────────────────────────────
// Dataset sidebar
// ─────────────────────────────────────────────────────────────
async function loadDatasetList() {
    try {
        const res = await fetch(`${API}/datasets`);
        if (!res.ok) return;
        const list = await res.json();
        const ul = document.getElementById('dataset-list');

        if (!list.length) { ul.innerHTML = '<li class="ds-empty">No datasets yet</li>'; return; }

        ul.innerHTML = list.map(ds => `
      <li class="${ds.id === datasetId ? 'ds-active' : ''}" data-id="${ds.id}" title="${ds.name}">
        ${ds.status === 'analyzed' ? '📈' : ds.status === 'cleaned' ? '✅' : '📁'}
        ${ds.name.length > 18 ? ds.name.slice(0, 18) + '…' : ds.name}
      </li>`).join('');

        ul.querySelectorAll('li[data-id]').forEach(li => {
            li.addEventListener('click', () => {
                datasetId = Number(li.dataset.id);
                kpisCache = null; chartCache = {};
                ul.querySelectorAll('li').forEach(x => x.classList.remove('ds-active'));
                li.classList.add('ds-active');
                ['clean', 'analytics', 'charts', 'insights', 'reports'].forEach(s => unlockStep(s));
                showToast(`Switched to: ${li.textContent.trim()}`);
            });
        });
    } catch { /* API may be offline */ }
}

// ─────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────
function resetAll() {
    datasetId = null; kpisCache = null; chartCache = {};
    showStep('upload');
    document.getElementById('upload-result').classList.add('hidden');
    document.getElementById('clean-result').classList.add('hidden');
    document.getElementById('analytics-result').classList.add('hidden');
    document.getElementById('insights-result').classList.add('hidden');
    ['clean', 'analytics', 'charts', 'insights', 'reports'].forEach(s => {
        const nav = document.getElementById(`nav-${s}`);
        if (nav) {
            nav.classList.add('locked'); nav.classList.remove('done', 'active');
            const tick = nav.querySelector('.step-tick');
            if (tick) tick.classList.add('hidden');
        }
    });
}

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────
function renderTable(rows, columns, tableId) {
    const tbl = document.getElementById(tableId);
    if (!rows || !rows.length) { tbl.innerHTML = '<tr><td>No data</td></tr>'; return; }
    const cols = columns || Object.keys(rows[0]);
    tbl.innerHTML = `
    <thead><tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(r => `<tr>${cols.map(c => `<td>${r[c] ?? ''}</td>`).join('')}</tr>`).join('')}</tbody>`;
}

function showProgress(filename) {
    document.getElementById('upload-filename').textContent = filename;
    document.getElementById('upload-status-text').textContent = 'Uploading…';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('upload-progress').classList.remove('hidden');
    document.getElementById('upload-result').classList.add('hidden');
}

function hideProgress() { document.getElementById('upload-progress').classList.add('hidden'); }

function animateProgress(from, to, ms) {
    const bar = document.getElementById('progress-bar');
    const step = (to - from) / (ms / 16);
    let cur = from;
    const t = setInterval(() => {
        cur = Math.min(cur + step, to);
        bar.style.width = cur + '%';
        if (cur >= to) clearInterval(t);
    }, 16);
}

let toastTimer;
function showToast(msg, type = 'success', duration = 3500) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.add('hidden'), duration);
}

function showLoading(msg = 'Processing…') {
    document.getElementById('loader-msg').textContent = msg;
    document.getElementById('loader').classList.remove('hidden');
}

function hideLoading() { document.getElementById('loader').classList.add('hidden'); }
