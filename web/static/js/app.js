/**
 * TidyFin Web Application JavaScript
 */

// State management
const state = {
    scannedFiles: [],
    previews: [],
    currentFolderTarget: null,
    currentBrowsePath: null
};

// API helper
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

// UI Helpers
function showLoading(text = 'Processing...') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

function enableStep(stepId) {
    document.getElementById(stepId).classList.remove('disabled');
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

// Settings
function toggleSettings() {
    const panel = document.getElementById('settings-panel');
    panel.classList.toggle('hidden');
    
    if (!panel.classList.contains('hidden')) {
        loadConfig();
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
        document.getElementById('api-status').textContent = 'Settings saved!';
        document.getElementById('api-status').className = 'status-text success';
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
    } else {
        statusEl.textContent = '✗ ' + result.message;
        statusEl.className = 'status-text error';
    }
}

// Folder Browser
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
        console.error(result.error);
        return;
    }
    
    state.currentBrowsePath = result.current;
    document.getElementById('current-path').textContent = result.current;
    
    // Parent button
    const parentBtn = document.getElementById('parent-btn');
    if (result.parent) {
        parentBtn.disabled = false;
        parentBtn.onclick = () => navigateToFolder(result.parent);
    } else {
        parentBtn.disabled = true;
    }
    
    // Folder list
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
    }
    closeFolderModal();
}

// Scanning
async function scanDirectory() {
    const sourceDir = document.getElementById('source-dir').value;
    
    if (!sourceDir) {
        alert('Please enter a source directory');
        return;
    }
    
    showLoading('Scanning for media files...');
    
    try {
        const result = await api('/scan', 'POST', { source_dir: sourceDir });
        hideLoading();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        state.scannedFiles = result.files;
        displayScanResults(result);
        
        // Enable next step
        enableStep('step-destinations');
        activateStep('step-destinations');
        
    } catch (error) {
        hideLoading();
        alert('Error scanning directory: ' + error.message);
    }
}

function displayScanResults(result) {
    const container = document.getElementById('scan-results');
    container.classList.remove('hidden');
    
    const movieCount = result.files.filter(f => f.media_type === 'movie').length;
    const showCount = result.files.filter(f => f.media_type === 'tv_show').length;
    const unknownCount = result.files.filter(f => f.media_type === 'unknown').length;
    
    container.innerHTML = `
        <div class="preview-summary">
            <div class="summary-stat">
                <div class="value">${result.count}</div>
                <div class="label">Total Files</div>
            </div>
            <div class="summary-stat">
                <div class="value">${movieCount}</div>
                <div class="label">Movies</div>
            </div>
            <div class="summary-stat">
                <div class="value">${showCount}</div>
                <div class="label">TV Shows</div>
            </div>
            <div class="summary-stat">
                <div class="value">${unknownCount}</div>
                <div class="label">Unknown</div>
            </div>
        </div>
        <div class="file-list" style="max-height: 300px; overflow-y: auto;">
            ${result.files.slice(0, 50).map(f => `
                <div class="file-item">
                    <span class="file-icon">${f.media_type === 'movie' ? '🎬' : f.media_type === 'tv_show' ? '📺' : '❓'}</span>
                    <span class="file-name">${f.filename}</span>
                    <span class="file-type">${f.media_type}</span>
                    <span class="confidence-badge ${f.confidence}">${f.confidence}</span>
                </div>
            `).join('')}
            ${result.files.length > 50 ? `<p style="text-align: center; color: var(--text-muted); padding: 1rem;">... and ${result.files.length - 50} more files</p>` : ''}
        </div>
    `;
}

// Preview
async function previewOrganization() {
    const moviesDir = document.getElementById('movies-dir').value;
    const showsDir = document.getElementById('shows-dir').value;
    const reviewDir = document.getElementById('review-dir').value;
    
    if (!moviesDir || !showsDir) {
        alert('Please enter Movies and TV Shows directories');
        return;
    }
    
    showLoading('Analyzing files with TMDB...');
    
    try {
        const result = await api('/preview', 'POST', {
            movies_dir: moviesDir,
            shows_dir: showsDir,
            review_dir: reviewDir
        });
        hideLoading();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        state.previews = result.previews;
        displayPreview(result);
        
        // Enable next step
        enableStep('step-preview');
        activateStep('step-preview');
        
    } catch (error) {
        hideLoading();
        alert('Error generating preview: ' + error.message);
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
            <div class="label">Total</div>
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
    container.innerHTML = result.previews.map(p => `
        <div class="preview-item ${p.confidence}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="confidence-badge ${p.confidence}">${p.confidence} (${Math.round(p.confidence_score * 100)}%)</span>
                <span style="color: var(--text-muted); font-size: 0.8125rem;">${p.media_type === 'movie' ? '🎬 Movie' : '📺 TV Show'}</span>
            </div>
            <div class="preview-source">📄 ${p.filename}</div>
            ${p.tmdb_match ? `
                <div class="preview-match">
                    ✓ TMDB: ${p.tmdb_match.title}${p.tmdb_match.year ? ` (${p.tmdb_match.year})` : ''}
                    ${p.tmdb_match.season ? ` - S${String(p.tmdb_match.season).padStart(2, '0')}E${String(p.tmdb_match.episode).padStart(2, '0')}` : ''}
                </div>
            ` : ''}
            <div class="preview-dest">
                ${p.action === 'move' ? '→' : '⚠️'} ${p.destination_path || 'Manual Review'}
            </div>
        </div>
    `).join('');
}

// Execute
async function executeOrganization() {
    const moviesDir = document.getElementById('movies-dir').value;
    const showsDir = document.getElementById('shows-dir').value;
    const reviewDir = document.getElementById('review-dir').value;
    
    if (!confirm('Are you sure you want to organize these files? This will move files to their new locations.')) {
        return;
    }
    
    showLoading('Organizing files...');
    
    try {
        const result = await api('/execute', 'POST', {
            movies_dir: moviesDir,
            shows_dir: showsDir,
            review_dir: reviewDir
        });
        hideLoading();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        displayResults(result);
        
    } catch (error) {
        hideLoading();
        alert('Error organizing files: ' + error.message);
    }
}

function displayResults(result) {
    // Hide other sections
    document.querySelectorAll('.step-card').forEach(card => {
        card.classList.add('hidden');
    });
    
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.remove('hidden');
    
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

function resetPreview() {
    // Reset state
    state.scannedFiles = [];
    state.previews = [];
    
    // Reset UI
    document.getElementById('scan-results').classList.add('hidden');
    document.getElementById('preview-container').innerHTML = '';
    document.getElementById('preview-summary').classList.add('hidden');
    document.getElementById('results-section').classList.add('hidden');
    
    // Reset steps
    document.querySelectorAll('.step-card').forEach(card => {
        card.classList.remove('hidden');
    });
    disableStep('step-destinations');
    disableStep('step-preview');
    activateStep('step-scan');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
});
