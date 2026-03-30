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

// Save via the owner assessment API
async function saveOwnerAssessment(submit = false) {
    const cells = collectCells();
    const btn = submit ? document.getElementById('submit-btn') : document.getElementById('save-draft-btn');
    const original = btn.textContent;
    btn.textContent = submit ? 'Submitting...' : 'Saving...';
    btn.disabled = true;

    try {
        const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/assessment`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cells, submit }),
        });

        if (res.ok) {
            btn.textContent = submit ? 'Submitted ✓' : 'Saved ✓';
            setTimeout(() => { btn.textContent = original; }, 2000);
        } else {
            const err = await res.json();
            btn.textContent = original;
            alert(err.detail || 'Save failed');
        }
    } catch (e) {
        btn.textContent = original;
        alert('Connection error');
    }
    btn.disabled = false;
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
