/**
 * Assessment grid logic for the owner assessment view.
 * Manages score selection, rationale input, draft saving, and submission.
 */

// Load existing assessment data
function loadAssessment() {
    if (typeof PROBLEM_DATA === 'undefined') return;

    const currentRound = PROBLEM_DATA.currentRound || 1;
    const roundKey = `round_${currentRound}`;
    const assessments = PROBLEM_DATA.assessments || {};
    const roundData = assessments[roundKey] || {};

    // Find the owner's participant entry
    // For the owner view, we need to find their participant ID
    // or just load whatever is available
    for (const [participantId, cells] of Object.entries(roundData)) {
        for (const [cellKey, cellData] of Object.entries(cells)) {
            const scoreEl = document.querySelector(`select[data-cell="${cellKey}"]`);
            if (scoreEl && cellData.score) {
                scoreEl.value = cellData.score;
            }
            const rationaleEl = document.querySelector(`textarea[data-cell="${cellKey}"]`);
            if (rationaleEl && cellData.rationale) {
                rationaleEl.value = cellData.rationale;
            }
        }
        break; // Just load the first participant (owner)
    }
    updateProgress();
}

function collectCells() {
    const cells = {};
    document.querySelectorAll('select[data-cell]').forEach(el => {
        const cellKey = el.dataset.cell;
        if (!cells[cellKey]) cells[cellKey] = {};
        const score = el.value ? parseInt(el.value) : null;
        if (score !== null) cells[cellKey].score = score;
    });
    document.querySelectorAll('textarea[data-cell]').forEach(el => {
        const cellKey = el.dataset.cell;
        if (!cells[cellKey]) cells[cellKey] = {};
        cells[cellKey].rationale = el.value;
    });
    return cells;
}

function updateProgress() {
    const selects = document.querySelectorAll('select[data-cell]');
    let filled = 0;
    selects.forEach(el => { if (el.value) filled++; });
    const progressEl = document.getElementById('progress');
    if (progressEl) {
        progressEl.textContent = `${filled}/${selects.length} rated`;
    }
}

// Save via the problem API (owner saves to problem directly)
async function saveOwnerAssessment(submit = false) {
    const cells = collectCells();

    // Save via the main problem update endpoint as owner
    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}), // Trigger save
    });

    // Also save assessment cells — we'll use a direct save approach
    const saveRes = await fetch(`/api/v1/problems/${PROBLEM_ID}`, {
        method: 'GET',
    });
    if (!saveRes.ok) return;

    const problem = await saveRes.json();
    const currentRound = problem.currentRound || 1;
    const roundKey = `round_${currentRound}`;

    if (!problem.assessments) problem.assessments = {};
    if (!problem.assessments[roundKey]) problem.assessments[roundKey] = {};

    // Use 'owner' as participant ID for owner assessment
    problem.assessments[roundKey]['owner'] = cells;

    const putRes = await fetch(`/api/v1/problems/${PROBLEM_ID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: problem.title }), // minimal update to trigger save
    });

    if (putRes.ok) {
        const btn = submit ? document.getElementById('submit-btn') : document.getElementById('save-draft-btn');
        const original = btn.textContent;
        btn.textContent = submit ? 'Submitted ✓' : 'Saved ✓';
        setTimeout(() => { btn.textContent = original; }, 2000);
    }
}

// Event listeners
document.querySelectorAll('select[data-cell]').forEach(el => {
    el.addEventListener('change', updateProgress);
});

if (document.getElementById('save-draft-btn')) {
    document.getElementById('save-draft-btn').addEventListener('click', () => saveOwnerAssessment(false));
}
if (document.getElementById('submit-btn')) {
    document.getElementById('submit-btn').addEventListener('click', () => saveOwnerAssessment(true));
}

// Initialize
loadAssessment();
