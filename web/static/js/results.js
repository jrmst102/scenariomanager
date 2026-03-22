/**
 * Results dashboard: heatmap rendering, ranking display, consensus panel, AI narrative.
 */

const HEATMAP_COLORS = {
    1: '#fee2e2',
    2: '#fed7aa',
    3: '#fef08a',
    4: '#bbf7d0',
    5: '#86efac',
};

const SCORE_LABELS = {
    1: 'Very Weak',
    2: 'Weak',
    3: 'Moderate',
    4: 'Strong',
    5: 'Very Strong',
};

// Fetch and display results
async function loadResults() {
    if (typeof PROBLEM_ID === 'undefined' && typeof PROBLEM_DATA === 'undefined') return;

    const problemId = typeof PROBLEM_ID !== 'undefined' ? PROBLEM_ID : PROBLEM_DATA.problemId;

    try {
        const res = await fetch(`/api/v1/problems/${problemId}/consensus`);
        if (!res.ok) {
            showFallbackResults();
            return;
        }
        const data = await res.json();
        renderRanking(data.robustness || []);
        renderHeatmap(data.aggregated || {});
        renderConsensus(data.overall || {}, data.per_scenario || {});
    } catch (e) {
        showFallbackResults();
    }
}

function showFallbackResults() {
    const loadingEl = document.getElementById('ranking-loading');
    if (loadingEl) loadingEl.textContent = 'No assessment data available yet.';
}

function renderRanking(ranking) {
    const loadingEl = document.getElementById('ranking-loading');
    const tableEl = document.getElementById('ranking-table');
    const bodyEl = document.getElementById('ranking-body');

    if (!bodyEl || !ranking.length) {
        if (loadingEl) loadingEl.textContent = 'No assessment data available.';
        return;
    }

    if (loadingEl) loadingEl.classList.add('hidden');
    if (tableEl) tableEl.classList.remove('hidden');

    const scenarios = PROBLEM_DATA ? PROBLEM_DATA.scenarios : [];

    bodyEl.innerHTML = ranking.map((r, i) => {
        const scoreCells = scenarios.map(s => {
            const score = r.scores[s.id];
            const bg = score ? HEATMAP_COLORS[Math.round(score)] || '#f3f4f6' : '#f3f4f6';
            return `<td class="text-center px-4 py-2 text-sm" style="background:${bg}">${score !== null ? score : '—'}</td>`;
        }).join('');

        const barWidth = (r.meanScore / 5) * 100;
        return `
            <tr class="border-b border-gray-100">
                <td class="px-4 py-2 text-sm text-gray-500">${i + 1}</td>
                <td class="px-4 py-2 text-sm font-medium text-gray-800">${r.name}</td>
                <td class="px-4 py-2 text-center">
                    <div class="flex items-center gap-2">
                        <div class="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                            <div class="bg-blue-500 h-2 rounded-full" style="width:${barWidth}%"></div>
                        </div>
                        <span class="text-sm font-medium">${r.meanScore}</span>
                    </div>
                </td>
                <td class="px-4 py-2 text-center text-sm ${r.fragility > 1.0 ? 'text-red-600 font-medium' : 'text-gray-600'}">${r.fragility}</td>
                ${scoreCells}
            </tr>
        `;
    }).join('');

    // Also render in report view
    const reportRanking = document.getElementById('report-ranking');
    if (reportRanking) {
        reportRanking.innerHTML = `
            <table class="w-full text-sm">
                <thead><tr class="border-b">
                    <th class="text-left py-1">Rank</th>
                    <th class="text-left py-1">Alternative</th>
                    <th class="text-center py-1">Mean</th>
                    <th class="text-center py-1">Fragility</th>
                </tr></thead>
                <tbody>${ranking.map((r, i) =>
                    `<tr class="border-b border-gray-100">
                        <td class="py-1">${i + 1}</td>
                        <td class="py-1">${r.name}</td>
                        <td class="text-center py-1">${r.meanScore}</td>
                        <td class="text-center py-1">${r.fragility}</td>
                    </tr>`
                ).join('')}</tbody>
            </table>
        `;
    }
}

function renderHeatmap(aggregated) {
    const container = document.getElementById('heatmap-container');
    if (!container || !PROBLEM_DATA) return;

    const alternatives = PROBLEM_DATA.alternatives || [];
    const scenarios = PROBLEM_DATA.scenarios || [];

    if (!alternatives.length || !scenarios.length) {
        container.innerHTML = '<p class="text-gray-400">No data to display.</p>';
        return;
    }

    let html = '<table class="w-full"><thead><tr>';
    html += '<th class="text-left px-3 py-2 text-sm font-medium text-gray-700">Alternative</th>';
    scenarios.forEach(s => {
        html += `<th class="text-center px-3 py-2 text-sm font-medium text-gray-700">${s.name || s.id}</th>`;
    });
    html += '</tr></thead><tbody>';

    alternatives.forEach(alt => {
        html += '<tr class="border-b border-gray-100">';
        html += `<td class="px-3 py-2 text-sm font-medium">${alt.id}. ${alt.name}</td>`;
        scenarios.forEach(s => {
            const cellKey = `${alt.id}_${s.id}`;
            const cell = aggregated[cellKey] || {};
            const score = cell.median || cell.score;
            const bg = score ? HEATMAP_COLORS[Math.round(score)] || '#f9fafb' : '#f9fafb';
            const label = score ? `${score.toFixed(1)}` : '—';
            const iqr = cell.iqr !== null && cell.iqr !== undefined ? `IQR: ${cell.iqr}` : '';
            html += `<td class="text-center px-3 py-2 text-sm" style="background:${bg}" title="${iqr}">${label}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderConsensus(overall, perScenario) {
    const panel = document.getElementById('consensus-panel');
    if (!panel) return;

    let html = '';

    if (overall.W !== null && overall.W !== undefined) {
        html += `
            <div class="grid grid-cols-3 gap-4 mb-6">
                <div class="bg-gray-50 rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-gray-900">${overall.W}</div>
                    <div class="text-sm text-gray-500">Kendall's W</div>
                </div>
                <div class="bg-gray-50 rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-gray-900">${overall.chi2}</div>
                    <div class="text-sm text-gray-500">χ² statistic</div>
                </div>
                <div class="bg-gray-50 rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-gray-900">${overall.p_value}</div>
                    <div class="text-sm text-gray-500">p-value</div>
                </div>
            </div>
            <p class="text-sm text-gray-700 mb-4">${overall.interpretation}</p>
        `;
    } else {
        html += `<p class="text-gray-400">${overall.interpretation || 'Insufficient data for consensus analysis.'}</p>`;
    }

    // Per-scenario breakdown
    if (Object.keys(perScenario).length > 0) {
        html += '<h4 class="text-sm font-medium text-gray-700 mb-2">Per-Scenario Agreement</h4>';
        html += '<div class="grid grid-cols-2 gap-3">';
        for (const [sid, data] of Object.entries(perScenario)) {
            const scenario = PROBLEM_DATA ? PROBLEM_DATA.scenarios.find(s => s.id === sid) : null;
            const name = scenario ? scenario.name || sid : sid;
            html += `
                <div class="bg-gray-50 rounded-lg p-3">
                    <div class="font-medium text-sm">${name}</div>
                    <div class="text-xs text-gray-500">
                        W: ${data.W !== null ? data.W : 'N/A'} | Mean IQR: ${data.mean_iqr !== null ? data.mean_iqr : 'N/A'}
                    </div>
                    <div class="text-xs text-gray-600">${data.interpretation}</div>
                </div>
            `;
        }
        html += '</div>';
    }

    panel.innerHTML = html;

    // Report consensus
    const reportConsensus = document.getElementById('report-consensus');
    if (reportConsensus) {
        reportConsensus.innerHTML = html;
    }
}

// AI Narrative Generation
const narrativeBtn = document.getElementById('generate-narrative-btn');
if (narrativeBtn) {
    narrativeBtn.addEventListener('click', async () => {
        narrativeBtn.disabled = true;
        narrativeBtn.textContent = 'Generating...';

        try {
            const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/report/narrative`, {
                method: 'POST',
            });
            const data = await res.json();

            if (res.ok) {
                const contentEl = document.getElementById('narrative-content');
                contentEl.innerHTML = `
                    <div class="prose max-w-none text-gray-700" contenteditable="true" id="narrative-text">${data.narrative}</div>
                    <div class="text-xs text-gray-400 mt-4">
                        Generated ${data.generatedAt} using ${data.model}
                    </div>
                `;
                narrativeBtn.textContent = '✨ Regenerate Narrative';
            } else {
                alert(data.detail || 'Failed to generate narrative');
                narrativeBtn.textContent = '✨ Generate AI Narrative';
            }
        } catch (e) {
            alert('Connection error');
            narrativeBtn.textContent = '✨ Generate AI Narrative';
        }
        narrativeBtn.disabled = false;
    });
}

// Initialize
loadResults();
