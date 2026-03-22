/**
 * Problem Editor interactivity.
 * Handles saving, section toggling, alternative/participant management.
 */

// --- Section Toggling ---
function toggleSection(id) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('section-collapsed');
}

// --- Data Collection ---
function collectProblemData() {
    const data = {
        title: document.getElementById('problem-title').value.trim(),
        description: document.getElementById('problem-description').value.trim(),
        axes: { x: {}, y: {} },
        scenarios: [],
    };

    // Axes
    document.querySelectorAll('.axis-input').forEach(el => {
        const axis = el.dataset.axis;
        const field = el.dataset.field;
        const value = el.value.trim();

        if (field === 'label') {
            data.axes[axis].label = value;
        } else {
            // e.g., "highPole.label" or "highPole.description"
            const [pole, subField] = field.split('.');
            if (!data.axes[axis][pole]) data.axes[axis][pole] = {};
            data.axes[axis][pole][subField] = value;
        }
    });

    // Scenarios
    const scenarioIds = new Set();
    document.querySelectorAll('.scenario-input').forEach(el => {
        scenarioIds.add(el.dataset.scenario);
    });

    scenarioIds.forEach(sid => {
        const nameEl = document.querySelector(`[data-scenario="${sid}"][data-field="name"]`);
        const narrativeEl = document.querySelector(`[data-scenario="${sid}"][data-field="narrative"]`);
        data.scenarios.push({
            id: sid,
            name: nameEl ? nameEl.value.trim() : '',
            narrative: narrativeEl ? narrativeEl.value.trim() : '',
        });
    });

    return data;
}

// --- Save ---
async function saveProblem() {
    const data = collectProblemData();
    const statusEl = document.getElementById('save-status');
    statusEl.textContent = 'Saving...';

    try {
        const res = await fetch(`/api/v1/problems/${PROBLEM_ID}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (res.ok) {
            statusEl.textContent = 'Saved ✓';
            setTimeout(() => { statusEl.textContent = ''; }, 2000);
        } else {
            const err = await res.json();
            statusEl.textContent = `Error: ${err.detail || 'Save failed'}`;
        }
    } catch (e) {
        statusEl.textContent = 'Connection error';
    }
}

document.getElementById('save-btn').addEventListener('click', saveProblem);

// Auto-save on Ctrl+S / Cmd+S
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveProblem();
    }
});

// --- Alternatives ---
document.getElementById('add-alt-btn').addEventListener('click', async () => {
    const name = prompt('Alternative name:');
    if (!name) return;
    const desc = prompt('Description (optional):') || '';

    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/alternatives`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: desc }),
    });
    if (res.ok) {
        window.location.reload();
    } else {
        const data = await res.json();
        alert(data.detail || 'Error adding alternative');
    }
});

async function removeAlternative(altId) {
    if (!confirm('Remove this alternative?')) return;
    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/alternatives/${altId}`, {
        method: 'DELETE',
    });
    if (res.ok) window.location.reload();
}

// --- Participants ---
document.getElementById('add-participant-btn').addEventListener('click', async () => {
    const name = document.getElementById('new-participant-name').value.trim();
    if (!name) return alert('Enter a participant name');
    const pin = document.getElementById('new-participant-pin').value.trim() || null;

    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/participants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, pin }),
    });
    if (res.ok) {
        window.location.reload();
    } else {
        const data = await res.json();
        alert(data.detail || 'Error adding participant');
    }
});

async function removeParticipant(pid) {
    if (!confirm('Remove this participant?')) return;
    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/participants/${pid}`, {
        method: 'DELETE',
    });
    if (res.ok) window.location.reload();
}

function copyLink(token) {
    const link = `${window.location.origin}/participate/${PROBLEM_ID}/${token}`;
    navigator.clipboard.writeText(link).then(() => {
        alert('Link copied to clipboard!');
    });
}

// --- Config ---
document.getElementById('anonymous-mode').addEventListener('change', async (e) => {
    await fetch(`/api/v1/problems/${PROBLEM_ID}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anonymousMode: e.target.checked }),
    });
});

document.getElementById('pin-protected').addEventListener('change', async (e) => {
    await fetch(`/api/v1/problems/${PROBLEM_ID}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pinProtected: e.target.checked }),
    });
});

// --- Round Management ---
async function closeRound() {
    if (!confirm('Close the current round?')) return;
    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/round/close`, { method: 'POST' });
    if (res.ok) window.location.reload();
    else alert((await res.json()).detail || 'Error');
}

async function reopenRound() {
    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/round/reopen`, { method: 'POST' });
    if (res.ok) window.location.reload();
    else alert((await res.json()).detail || 'Error');
}

async function newRound() {
    if (!confirm('Open a new round? This will close the current round.')) return;
    const res = await fetch(`/api/v1/problems/${PROBLEM_ID}/round/new`, { method: 'POST' });
    if (res.ok) window.location.reload();
    else alert((await res.json()).detail || 'Error');
}
