/*
 * Note: Initial code structure and UI boilerplate generated with AI assistance
 * (e.g., Gemini/ChatGPT) as a productivity tool, then fully refactored, customized,
 * and integrated into the RedPatch architecture.
 */

function showDeleteModal(labId) {
    return new Promise((resolve) => {
        const modal = document.getElementById('delete-confirm-modal');
        const labText = document.getElementById('modal-lab-id-text');
        const cancelBtn = document.getElementById('modal-cancel-btn');
        const confirmBtn = document.getElementById('modal-confirm-btn');

        labText.textContent = `${labId}`;
        modal.classList.remove('hidden');

        const handleConfirm = () => {
            cleanup();
            resolve(true);
        };

        const handleCancel = () => {
            cleanup();
            resolve(false);
        };

        const cleanup = () => {
            modal.classList.add('hidden');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
        };

        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
    });
}

async function deleteLab(button) {
    const labId = button.dataset.labId;

    const userConfirmed = await showDeleteModal(labId);
    if (!userConfirmed) return;

    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>Deleting...</span>';

    try {
        const response = await fetch(`/api/labs/${encodeURIComponent(labId)}`, {
            method: 'DELETE'
        });

        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'Delete failed.');

        const card = button.closest('.pt-4');
        const downloadBtn = card.querySelector('.download-lab-button');

        button.style.display = 'none';
        if (downloadBtn) downloadBtn.style.display = 'flex';

    } catch (error) {
        alert(error.message || 'Error occurred while deleting.');
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

async function checkDownloadStatus(labId){
    const response = await fetch(
        `/api/labs/${encodeURIComponent(labId)}/is_downloaded`,
        { method: 'GET' }
    );

    if (!response.ok) throw new Error('Network Error');

    const statusMap = await response.json();

    return statusMap["is_downloaded"];
}

function setDeleteButtonState(state, targetLabId) {
    const button = document.querySelector(`.delete-lab-button[data-lab-id="${targetLabId}"]`);

    if (!state) {
        button.style.display = 'none';
    }
    else {
        button.style.display = 'inline-block';
    }

}

async function checkAllDownloadStatuses() {
    const buttons = document.querySelectorAll('.download-lab-button');
    const labIds = Array.from(buttons).map(btn => btn.dataset.labId);

    if (labIds.length === 0) return;

    try {
        for (const btn of buttons) {
            const labId = btn.dataset.labId;
            let is_downloaded = await checkDownloadStatus(labId);

            if (!is_downloaded) {
                btn.style.display = 'inline-block';
            }
            else {
                btn.style.display = 'none';
            }
            setDeleteButtonState(is_downloaded, labId)
        }

    }
    catch (error) {
        console.error('An error occurred whilst checking the status :', error);
    }
}

async function downloadLab(button) {
    const { module, labId } = button.dataset;
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>Downloading...</span>';
    try {
        const response = await fetch(
            `/api/labs/${encodeURIComponent(module)}/${encodeURIComponent(labId)}/download`,
            { method: 'POST' }
        );
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'Download failed.');
        button.innerHTML = '<i class="fa-solid fa-check"></i><span>Lab Downloaded</span>';
    } catch (error) {
        button.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i><span>Download Failed</span>';
        alert(error.message || 'The lab archive could not be downloaded.');
        setTimeout(() => { button.innerHTML = original; button.disabled = false; }, 1800);
        return;
    }
    button.disabled = false;
}

checkAllDownloadStatuses();
