/**
 * TidyFin Web Application JavaScript
 * Premium UI with theme toggle, batch selection, and toast notifications
 */

// State management
const state = {
    scannedFiles: [],
    selectedFiles: new Set(),
    previews: [],
    currentFolderTarget: null,
    currentBrowsePath: null,
    theme: localStorage.getItem('theme') || 'dark'
};

// Initialize theme on load
document.addEventListener('DOMContentLoaded', () => {
    setTheme(state.theme);
    loadConfig();
    animateDashboard();
});

// ==================== Theme Toggle ====================
function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    setTheme(state.theme);
    localStorage.setItem('theme', state.theme);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('theme-icon');
    icon.textContent = theme === 'dark' ? '🌙' : '☀️';
    icon.style.transform = 'rotate(360deg)';
    setTimeout(() => icon.style.transform = '', 300);
}

// ==================== Toast Notifications ====================
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

    toast.innerHTML = `
        <span class="icon">${icons[type] || icons.info}</span>
        <span class="message">${message}</span>
        <button class="close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastSlide 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ==================== Dashboard Animation ====================
function animateDashboard() {
    const stats = document.querySelectorAll('.stat-value');
    stats.forEach(stat => {
        animateNumber(stat, 0, 0, 500);
    });
}

function animateNumber(element, start, end, duration) {
    const range = end - start;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        element.textContent = Math.floor(start + range * easeOut);

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function updateDashboard(files) {
    const total = files.length;
    const movies = files.filter(f => f.media_type === 'movie').length;
    const shows = files.filter(f => f.media_type === 'tv_show').length;
    const unknown = files.filter(f => f.media_type === 'unknown').length;

    animateNumber(document.getElementById('stat-total'), 0, total, 800);
    animateNumber(document.getElementById('stat-movies'), 0, movies, 800);
    animateNumber(document.getElementById('stat-shows'), 0, shows, 800);
    animateNumber(document.getElementById('stat-unknown'), 0, unknown, 800);
}

// ==================== API Helper ====================
async function api(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) {
        options.body = JSON.stringify(data);
    }
    const response = await fetch(`/api${endpoint}`, options);
    return response.json();
}

// ==================== UI Helpers ====================
function showLoading(text = 'Processing...') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

function enableStep(stepId) {
    const step = document.getElementById(stepId);
    step.classList.remove('disabled');
    step.style.animation = 'slideUp 0.4s ease-out';
}

function disableStep(stepId) {
    document.getElementById(stepId).classList.add('disabled');
}

function activateStep(stepId) {
    document.querySelectorAll('.step-card').forEach(card => {
        card.classList.remove('active');
    });
    document.getElementById(stepId).classList.add('active');
}

// ==================== Settings ====================
function toggleSettings() {
    const panel = document.getElementById('settings-panel');
    panel.classList.toggle('hidden');

    if (!panel.classList.contains('hidden')) {
        loadConfig();
        panel.style.animation = 'slideDown 0.3s ease-out';
    }
}

async function loadConfig() {
    const config = await api('/config');
    if (config.tmdb_api_key) {
        document.getElementById('api-key').value = config.tmdb_api_key;
    }
    if (config.default_movies_dir) {
        document.getElementById('movies-dir').value = config.default_movies_dir;
    }
    if (config.default_shows_dir) {
        document.getElementById('shows-dir').value = config.default_shows_dir;
    }
    if (config.default_review_dir) {
        document.getElementById('review-dir').value = config.default_review_dir;
    }
}

async function saveSettings() {
    const apiKey = document.getElementById('api-key').value;

    if (apiKey && !apiKey.startsWith('***')) {
        await api('/config', 'POST', { tmdb_api_key: apiKey });
        showToast('Settings saved successfully!', 'success');
    }
}

async function testApiKey() {
    showLoading('Testing API connection...');
    const result = await api('/test-tmdb', 'POST');
    hideLoading();

    const statusEl = document.getElementById('api-status');
    if (result.success) {
        statusEl.textContent = '✓ ' + result.message;
        statusEl.className = 'status-text success';
        showToast('TMDB API connected!', 'success');
    } else {
        statusEl.textContent = '✗ ' + result.message;
        statusEl.className = 'status-text error';
        showToast('API connection failed', 'error');
    }
}

// ==================== Folder Browser ====================
function browseFolder(targetInputId) {
    state.currentFolderTarget = targetInputId;
    const currentValue = document.getElementById(targetInputId).value;
    openFolderBrowser(currentValue || '');
}

async function openFolderBrowser(path) {
    document.getElementById('folder-modal').classList.remove('hidden');
    await navigateToFolder(path);
}

function closeFolderModal() {
    document.getElementById('folder-modal').classList.add('hidden');
    state.currentFolderTarget = null;
}

async function navigateToFolder(path) {
    const result = await api('/browse', 'POST', { path });

    if (result.error) {
        showToast(result.error, 'error');
        return;
    }

    state.currentBrowsePath = result.current;
    document.getElementById('current-path').textContent = result.current;

    const parentBtn = document.getElementById('parent-btn');
    if (result.parent) {
        parentBtn.disabled = false;
        parentBtn.onclick = () => navigateToFolder(result.parent);
    } else {
        parentBtn.disabled = true;
    }

    const folderList = document.getElementById('folder-list');
    folderList.innerHTML = result.directories.map(dir => `
        <div class="folder-item" onclick="navigateToFolder('${dir.path.replace(/\\/g, '\\\\')}')">
            <span class="icon">📁</span>
            <span class="name">${dir.name}</span>
        </div>
    `).join('');
}

function goToParent() {
    // Handled by onclick set in navigateToFolder
}

function selectCurrentFolder() {
    if (state.currentFolderTarget && state.currentBrowsePath) {
        document.getElementById(state.currentFolderTarget).value = state.currentBrowsePath;
        showToast('Folder selected', 'success');
    }
    closeFolderModal();
}

// ==================== File Selection ====================
function toggleFileSelection(index) {
    if (state.selectedFiles.has(index)) {
        state.selectedFiles.delete(index);
    } else {
        state.selectedFiles.add(index);
    }
    updateFileSelectionUI();
}

function selectAllFiles() {
    state.scannedFiles.forEach((_, i) => state.selectedFiles.add(i));
    updateFileSelectionUI();
}

function deselectAllFiles() {
    state.selectedFiles.clear();
    updateFileSelectionUI();
}

function updateFileSelectionUI() {
    const batchActions = document.getElementById('batch-actions');
    const selectedCount = document.getElementById('selected-count');

    if (state.selectedFiles.size > 0) {
        batchActions.classList.remove('hidden');
        selectedCount.textContent = state.selectedFiles.size;
    } else {
        batchActions.classList.add('hidden');
    }

    // Update file items
    document.querySelectorAll('.file-item').forEach((item, index) => {
        if (state.selectedFiles.has(index)) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
}

// ==================== Scanning ====================
async function scanDirectory() {
    const sourceDir = document.getElementById('source-dir').value;

    if (!sourceDir) {
        showToast('Please enter a source directory', 'warning');
        return;
    }

    showLoading('Scanning for media files...');

    try {
        const result = await api('/scan', 'POST', { source_dir: sourceDir });
        hideLoading();

        if (result.error) {
            showToast('Error: ' + result.error, 'error');
            return;
        }

        state.scannedFiles = result.files;
        state.selectedFiles.clear();

        updateDashboard(result.files);
        displayScanResults(result);

        enableStep('step-destinations');
        activateStep('step-destinations');

        showToast(`Found ${result.count} media files!`, 'success');

    } catch (error) {
        hideLoading();
        showToast('Error scanning directory: ' + error.message, 'error');
    }
}

function displayScanResults(result) {
    const container = document.getElementById('scan-results');
    const fileList = document.getElementById('file-list');

    container.classList.remove('hidden');

    fileList.innerHTML = result.files.map((f, index) => {
        const icon = f.media_type === 'movie' ? '🎬' : f.media_type === 'tv_show' ? '📺' : '❓';
        const badgeClass = f.media_type === 'movie' ? 'badge-movie' : f.media_type === 'tv_show' ? 'badge-tv' : 'badge-unknown';
        const typeLabel = f.media_type === 'movie' ? 'Movie' : f.media_type === 'tv_show' ? 'TV Show' : 'Unknown';

        return `
            <div class="file-item" onclick="toggleFileSelection(${index})">
                <div class="file-checkbox"></div>
                <div class="file-poster">${icon}</div>
                <div class="file-info">
                    <div class="file-name">${f.filename}</div>
                    <div class="file-meta">
                        ${f.parsed_title ? `<span>${f.parsed_title}</span>` : ''}
                        ${f.parsed_year ? `<span>(${f.parsed_year})</span>` : ''}
                        ${f.parsed_season ? `<span>S${String(f.parsed_season).padStart(2, '0')}E${String(f.parsed_episode).padStart(2, '0')}</span>` : ''}
                    </div>
                </div>
                <div class="file-badges">
                    <span class="badge ${badgeClass}">${typeLabel}</span>
                    <span class="confidence-badge ${f.confidence}">${f.confidence}</span>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== Preview ====================
async function previewOrganization() {
    const moviesDir = document.getElementById('movies-dir').value;
    const showsDir = document.getElementById('shows-dir').value;
    const reviewDir = document.getElementById('review-dir').value;

    if (!moviesDir || !showsDir) {
        showToast('Please enter Movies and TV Shows directories', 'warning');
        return;
    }

    // Check if any files are selected
    if (state.selectedFiles.size === 0) {
        showToast('Please select files to organize (click on files to select them)', 'warning');
        return;
    }

    // Get selected file indices
    const selectedIndices = Array.from(state.selectedFiles);

    showLoading(`Analyzing ${selectedIndices.length} files with TMDB...`);

    try {
        const result = await api('/preview', 'POST', {
            movies_dir: moviesDir,
            shows_dir: showsDir,
            review_dir: reviewDir,
            selected_indices: selectedIndices
        });
        hideLoading();

        if (result.error) {
            showToast('Error: ' + result.error, 'error');
            return;
        }

        state.previews = result.previews;
        displayPreview(result);

        enableStep('step-preview');
        activateStep('step-preview');

        showToast('Preview generated!', 'success');

    } catch (error) {
        hideLoading();
        showToast('Error generating preview: ' + error.message, 'error');
    }
}

function displayPreview(result) {
    const container = document.getElementById('preview-container');
    const summaryEl = document.getElementById('preview-summary');

    // Summary
    summaryEl.classList.remove('hidden');
    summaryEl.innerHTML = `
        <div class="summary-stat">
            <div class="value">${result.summary.total}</div>
            <div class="label">Total Files</div>
        </div>
        <div class="summary-stat">
            <div class="value" style="color: var(--success)">${result.summary.movies}</div>
            <div class="label">Movies</div>
        </div>
        <div class="summary-stat">
            <div class="value" style="color: var(--success)">${result.summary.shows}</div>
            <div class="label">TV Shows</div>
        </div>
        <div class="summary-stat">
            <div class="value" style="color: var(--warning)">${result.summary.manual_review}</div>
            <div class="label">Manual Review</div>
        </div>
    `;

    // Preview items
    container.innerHTML = result.previews.map(p => {
        const icon = p.media_type === 'movie' ? '🎬' : '📺';
        const confidencePercent = Math.round(p.confidence_score * 100);

        // Use poster image if available, otherwise fallback to icon
        let posterContent;
        if (p.tmdb_match?.poster_url) {
            posterContent = `<img src="${p.tmdb_match.poster_url}" alt="Poster" onerror="this.parentElement.innerHTML='${icon}'">`;
        } else {
            posterContent = icon;
        }

        return `
            <div class="preview-item ${p.confidence}">
                <div class="preview-poster">${posterContent}</div>
                <div class="preview-content">
                    <div class="preview-header">
                        <span class="preview-title">
                            ${p.tmdb_match ? p.tmdb_match.title : p.filename}
                            ${p.tmdb_match?.year ? `(${p.tmdb_match.year})` : ''}
                            ${p.tmdb_match?.season ? `S${String(p.tmdb_match.season).padStart(2, '0')}E${String(p.tmdb_match.episode).padStart(2, '0')}` : ''}
                        </span>
                        <span class="confidence-badge ${p.confidence}">${p.confidence} (${confidencePercent}%)</span>
                    </div>
                    <div class="preview-source">📄 ${p.filename}</div>
                    <div class="preview-dest">
                        <span class="arrow">${p.action === 'move' ? '→' : '⚠️'}</span>
                        <span>${p.destination_path || 'Manual Review'}</span>
                    </div>
                    ${p.tmdb_match?.episode_title ? `<div class="preview-match">📝 ${p.tmdb_match.episode_title}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ==================== Execute ====================
async function executeOrganization() {
    const moviesDir = document.getElementById('movies-dir').value;
    const showsDir = document.getElementById('shows-dir').value;
    const reviewDir = document.getElementById('review-dir').value;

    if (!confirm('Are you sure you want to organize these files? This will move files to their new locations.')) {
        return;
    }

    // Show progress
    const progressSection = document.getElementById('progress-section');
    progressSection.classList.remove('hidden');
    document.getElementById('execute-btn').disabled = true;

    // Simulate progress (actual API call is instant, so we animate for UX)
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        updateProgress(progress, 'Organizing files...');
    }, 200);

    try {
        const result = await api('/execute', 'POST', {
            movies_dir: moviesDir,
            shows_dir: showsDir,
            review_dir: reviewDir
        });

        clearInterval(progressInterval);
        updateProgress(100, 'Complete!');

        setTimeout(() => {
            if (result.error) {
                showToast('Error: ' + result.error, 'error');
                progressSection.classList.add('hidden');
                document.getElementById('execute-btn').disabled = false;
                return;
            }

            displayResults(result);
            showToast('Files organized successfully!', 'success');
        }, 500);

    } catch (error) {
        clearInterval(progressInterval);
        progressSection.classList.add('hidden');
        document.getElementById('execute-btn').disabled = false;
        showToast('Error organizing files: ' + error.message, 'error');
    }
}

function updateProgress(percent, status) {
    document.getElementById('progress-fill').style.width = `${percent}%`;
    document.getElementById('progress-percentage').textContent = `${Math.round(percent)}%`;
    document.getElementById('progress-status').textContent = status;
}

function displayResults(result) {
    // Hide other sections
    document.querySelectorAll('.step-card').forEach(card => {
        card.classList.add('hidden');
    });

    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.remove('hidden');
    resultsSection.style.animation = 'successPop 0.5s ease-out';

    document.getElementById('final-results').innerHTML = `
        <div class="result-stat success">
            <div class="value">${result.summary.movies_organized}</div>
            <div class="label">Movies Organized</div>
        </div>
        <div class="result-stat success">
            <div class="value">${result.summary.shows_organized}</div>
            <div class="label">TV Shows Organized</div>
        </div>
        <div class="result-stat warning">
            <div class="value">${result.summary.manual_review}</div>
            <div class="label">Manual Review</div>
        </div>
        <div class="result-stat ${result.summary.errors > 0 ? 'error' : ''}">
            <div class="value">${result.summary.errors}</div>
            <div class="label">Errors</div>
        </div>
    `;
}

// ==================== Reset ====================
function resetPreview() {
    state.previews = [];

    document.getElementById('preview-container').innerHTML = '';
    document.getElementById('preview-summary').classList.add('hidden');
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('execute-btn').disabled = false;

    disableStep('step-preview');
    activateStep('step-destinations');
}

function resetAll() {
    state.scannedFiles = [];
    state.selectedFiles.clear();
    state.previews = [];

    // Reset UI
    document.getElementById('scan-results').classList.add('hidden');
    document.getElementById('file-list').innerHTML = '';
    document.getElementById('batch-actions').classList.add('hidden');
    document.getElementById('preview-container').innerHTML = '';
    document.getElementById('preview-summary').classList.add('hidden');
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('execute-btn').disabled = false;

    // Reset dashboard
    ['stat-total', 'stat-movies', 'stat-shows', 'stat-unknown'].forEach(id => {
        document.getElementById(id).textContent = '0';
    });

    // Reset steps
    document.querySelectorAll('.step-card').forEach(card => {
        card.classList.remove('hidden');
    });
    disableStep('step-destinations');
    disableStep('step-preview');
    activateStep('step-scan');

    showToast('Ready to organize more files!', 'info');
}
