// OpEx_Guard Main JavaScript Integration

document.addEventListener('DOMContentLoaded', () => {
    initSeedButton();
    initCategorySelectors();
    initEmailCategorySelectors();
    initAnomalyResolvers();
    initReceiptModals();
    initActionHandlers();
    initInboxScanHandler();
    initEmailActionHandlers();
});

// Seed Sample Data Handler
function initSeedButton() {
    const seedBtns = document.querySelectorAll('.btn-seed-data');
    seedBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            btn.disabled = true;
            btn.innerHTML = '⚡ Seeding Data...';
            
            try {
                const res = await fetch('/api/seed', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast('Sample dataset loaded & reconciled successfully!', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 800);
                } else {
                    showToast('Error seeding data: ' + (data.error || 'Unknown error'), 'danger');
                    btn.disabled = false;
                    btn.innerHTML = '⚡ Load Sample Dataset';
                }
            } catch (err) {
                console.error(err);
                showToast('Failed to seed data', 'danger');
                btn.disabled = false;
                btn.innerHTML = '⚡ Load Sample Dataset';
            }
        });
    });
}

// Category Override Handler
function initCategorySelectors() {
    const selects = document.querySelectorAll('.category-select');
    selects.forEach(select => {
        select.addEventListener('change', async (e) => {
            const txId = select.dataset.txId;
            const newCategory = select.value;
            const originalVal = select.dataset.original;

            try {
                const res = await fetch('/api/feedback/categorize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        transaction_id: txId,
                        category: newCategory,
                        save_rule: true
                    })
                });
                const data = await res.json();
                if (data.success) {
                    select.dataset.original = newCategory;
                    showToast(`Updated category to '${newCategory}' & saved rule!`, 'success');
                } else {
                    select.value = originalVal;
                    showToast('Failed to update category', 'danger');
                }
            } catch (err) {
                select.value = originalVal;
                showToast('Error connecting to server', 'danger');
            }
        });
    });
}

// Resolve/Unflag Anomaly Handler
function initAnomalyResolvers() {
    const resolveBtns = document.querySelectorAll('.btn-resolve-anomaly');
    resolveBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const anomalyId = btn.dataset.anomalyId;
            const note = prompt('Add resolution note (optional):', 'Verified standard expense');
            
            try {
                const res = await fetch(`/api/anomalies/${anomalyId}/resolve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ note: note || 'Resolved by user' })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Anomaly resolved & unflagged!', 'success');
                    const card = document.getElementById(`anomaly-card-${anomalyId}`);
                    if (card) {
                        card.style.opacity = '0.5';
                        btn.replaceWith(document.createTextNode('✓ Resolved'));
                    }
                } else {
                    showToast('Failed to resolve anomaly', 'danger');
                }
            } catch (err) {
                showToast('Error resolving anomaly', 'danger');
            }
        });
    });
}

function initActionHandlers() {
    document.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const actionId = btn.dataset.actionId;
            const action = btn.dataset.action;
            try {
                const res = await fetch(`/api/actions/${actionId}/${action}`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    btn.textContent = action === 'approve' ? 'Approved' : 'Rejected';
                    btn.disabled = true;
                    showToast(data.message, 'success');
                } else {
                    showToast(data.error || 'Action update failed', 'danger');
                }
            } catch (err) {
                showToast('Failed to update action', 'danger');
            }
        });
    });
}

function initInboxScanHandler() {
    const scanBtn = document.querySelector('.btn-scan-inbox');
    if (!scanBtn) return;

    scanBtn.addEventListener('click', async () => {
        scanBtn.disabled = true;
        scanBtn.textContent = 'Scanning...';

        try {
            const res = await fetch('/api/scan-inbox', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showToast(`Discovered ${data.count} new email receipts.`, 'success');
                setTimeout(() => window.location.reload(), 800);
            } else {
                showToast(data.error || 'Inbox scan failed', 'danger');
            }
        } catch (err) {
            showToast('Failed to scan inbox', 'danger');
        } finally {
            scanBtn.disabled = false;
            scanBtn.textContent = '⚡ Scan Inbox for New Receipts';
        }
    });
}

function initEmailCategorySelectors() {
    document.querySelectorAll('.email-category-select').forEach(select => {
        select.addEventListener('change', () => {
            select.dataset.original = select.value;
        });
    });
}

function initEmailActionHandlers() {
    document.querySelectorAll('[data-email-action]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const itemId = btn.dataset.emailActionId;
            const action = btn.dataset.emailAction;
            const select = document.querySelector(`.email-category-select[data-item-id="${itemId}"]`);
            const category = select ? select.value : null;

            try {
                const res = await fetch(`/api/email-actions/${itemId}/${action}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category })
                });
                const data = await res.json();
                if (data.success) {
                    btn.textContent = action === 'approve' ? 'Approved' : 'Dismissed';
                    btn.disabled = true;
                    showToast(data.message, 'success');
                } else {
                    showToast(data.error || 'Email action failed', 'danger');
                }
            } catch (err) {
                showToast('Failed to process email action', 'danger');
            }
        });
    });
}

// Receipt Modal Handler
function initReceiptModals() {
    const modalBackdrop = document.getElementById('receipt-modal-backdrop');
    if (!modalBackdrop) return;

    const closeBtns = modalBackdrop.querySelectorAll('.btn-close-modal');
    closeBtns.forEach(btn => btn.addEventListener('click', () => modalBackdrop.classList.remove('active')));
    modalBackdrop.addEventListener('click', (e) => {
        if (e.target === modalBackdrop) modalBackdrop.classList.remove('active');
    });

    const auditBtns = document.querySelectorAll('.btn-view-receipt');
    auditBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const rawText = btn.dataset.receiptText || 'No raw receipt text available.';
            const vendor = btn.dataset.vendor || 'Receipt Details';
            const amount = btn.dataset.amount || '0.00';
            const date = btn.dataset.date || '';

            document.getElementById('modal-vendor').textContent = vendor;
            document.getElementById('modal-amount').textContent = `$${amount}`;
            document.getElementById('modal-date').textContent = date;
            document.getElementById('modal-raw-text').textContent = rawText;

            modalBackdrop.classList.add('active');
        });
    });
}

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgColor = type === 'success' ? '#DCFCE7' : type === 'danger' ? '#FEE2E2' : '#DBEAFE';
    const textColor = type === 'success' ? '#166534' : type === 'danger' ? '#991B1B' : '#1E40AF';
    const borderColor = type === 'success' ? '#86EFAC' : type === 'danger' ? '#FCA5A5' : '#93C5FD';

    toast.style.cssText = `background-color: ${bgColor}; color: ${textColor}; border: 1px solid ${borderColor}; padding: 12px 20px; border-radius: 8px; font-weight: 500; font-size: 0.875rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: opacity 0.3s ease;`;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
