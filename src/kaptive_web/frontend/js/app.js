/**
 * Main application logic for Kaptive-Web
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Fetch and display version
    const verData = await api.getVersion();
    if (verData && verData.version) {
        const verSpan = document.getElementById('app-version');
        if (verSpan) verSpan.textContent = `v${verData.version}`;
    }
    // --- Elements ---
    // Theme elements
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const iconSystem = document.getElementById('theme-icon-system');
    const iconLight = document.getElementById('theme-icon-light');
    const iconDark = document.getElementById('theme-icon-dark');
    
    // Auth elements
    const authView = document.getElementById('auth-view');
    const dashboardView = document.getElementById('dashboard-view');
    const guestBtn = document.getElementById('guest-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const loginNavBtn = document.getElementById('login-nav-btn');
    const usernameDisplay = document.getElementById('username-display');
    
    // Settings elements
    const settingsNavBtn = document.getElementById('settings-nav-btn');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const copyApiKeyBtn = document.getElementById('copy-api-key-btn');
    const settingsApiKeyInput = document.getElementById('settings-api-key');
    const deleteAccountBtn = document.getElementById('delete-account-btn');

    // Tab elements
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    // Home / Upload elements
    const dbList = document.getElementById('db-list');
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const startRunBtn = document.getElementById('start-run-btn');
    const fileCountDisplay = document.getElementById('file-count');
    const uploadLock = document.getElementById('upload-lock');
    const loginPromptBtn = document.querySelector('.login-prompt-btn');
    
    // Progress bar
    const floatingProgress = document.getElementById('floating-progress');
    const progressStatus = document.getElementById('progress-status');
    const progressRunId = document.getElementById('progress-run-id');

    // Analysis / Results elements
    const resultsTbody = document.getElementById('results-tbody');
    const tableLoading = document.getElementById('table-loading');
    const searchInput = document.getElementById('search-input');
    const plotViewport = document.getElementById('plot-viewport');
    const viewportTitle = document.getElementById('viewport-title');
    const closeViewportBtn = document.getElementById('close-viewport-btn');
    const toggleMaximizeBtn = document.getElementById('toggle-maximize-btn');


    async function triggerDownload(endpoint, format) {
        let ids = Array.from(selectedGenomes);
        if (ids.length === 0) {
            ids = filteredResults.map(r => r.genome_id);
        }
        
        try {
            const headers = api.getHeaders();
            headers['Content-Type'] = 'application/json';
            const res = await fetch(`${api.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ genome_ids: ids })
            });
            
            if (!res.ok) throw new Error(`Failed to download ${format}`);
            
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = format === 'tsv' ? 'kaptive_results_tsv.zip' : (format === 'jsonl' ? 'kaptive_results.jsonl.gz' : 'kaptive_results.json');
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error(err);
            alert(`Download ${format} failed.`);
        }
    }

    const downloadJsonBtn = document.getElementById('download-json-btn');
    if (downloadJsonBtn) {
        downloadJsonBtn.addEventListener('click', async () => {
            downloadJsonBtn.disabled = true;
            downloadJsonBtn.textContent = 'Downloading...';
            await triggerDownload('/serotype/results/download/jsonl', 'jsonl');
            downloadJsonBtn.disabled = false;
            downloadJsonBtn.textContent = '📥 Download JSON';
        });
    }

    const downloadTsvBtn = document.getElementById('download-tsv-btn');
    if (downloadTsvBtn) {
        downloadTsvBtn.addEventListener('click', async () => {
            downloadTsvBtn.disabled = true;
            downloadTsvBtn.textContent = 'Downloading...';
            await triggerDownload('/serotype/results/download/tsv', 'tsv');
            downloadTsvBtn.disabled = false;
            downloadTsvBtn.textContent = '📥 Download TSV';
        });
    }


    const plotlyContainer = document.getElementById('plotly-container');
    const plotEmptyState = document.getElementById('plot-empty-state');
    const plotLoading = document.getElementById('plot-loading');

    // --- Theme Management ---
    let currentTheme = localStorage.getItem('kaptive_theme') || 'system';

    function applyTheme() {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        let activeTheme = currentTheme;
        
        if (currentTheme === 'system') {
            activeTheme = prefersDark ? 'dark' : 'light';
        }
        
        // Update DOM
        if (activeTheme === 'light') {
            document.body.classList.add('theme-light');
            document.body.classList.remove('theme-dark');
        } else {
            document.body.classList.add('theme-dark');
            document.body.classList.remove('theme-light');
        }
        
        // Update Icons
        iconSystem.classList.add('hidden');
        iconLight.classList.add('hidden');
        iconDark.classList.add('hidden');
        
        if (currentTheme === 'system') {
            iconSystem.classList.remove('hidden');
            themeToggleBtn.title = 'Toggle Theme (System)';
        } else if (currentTheme === 'light') {
            iconLight.classList.remove('hidden');
            themeToggleBtn.title = 'Toggle Theme (Light)';
        } else {
            iconDark.classList.remove('hidden');
            themeToggleBtn.title = 'Toggle Theme (Dark)';
        }
        
        // Update any open plotly graphs
        if (!plotlyContainer.classList.contains('hidden') && plotViewport.classList.contains('maximized') || !plotViewport.classList.contains('minimized')) {
            // Need to relayout if active
            const update = {
                'layout.template': activeTheme === 'light' ? 'plotly_white' : 'plotly_dark'
            };
            try {
                Plotly.relayout('plotly-container', update);
            } catch (e) {}
        }
    }
    
    themeToggleBtn.addEventListener('click', () => {
        if (currentTheme === 'system') currentTheme = 'light';
        else if (currentTheme === 'light') currentTheme = 'dark';
        else currentTheme = 'system';
        
        localStorage.setItem('kaptive_theme', currentTheme);
        applyTheme();
    });
    
    // Listen to system changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (currentTheme === 'system') applyTheme();
    });
    
    // Initial theme apply
    applyTheme();

    let allResults = [];
let filteredResults = [];
const selectedGenomes = new Set();
const resultsRunFilter = document.getElementById('results-run-filter');
const resultsConfidenceFilter = document.getElementById('results-confidence-filter');
const selectionTally = document.getElementById('selection-tally');

function updateTally() {
    if (selectionTally) {
        selectionTally.textContent = `${selectedGenomes.size} / ${filteredResults.length} genomes selected`;
    }
}

    let selectedFiles = [];
    let currentSpecies = "";
    let currentDatabases = [];
    const speciesFilter = document.getElementById('global-species-filter');
    const resultsSpeciesFilter = document.getElementById('results-species-filter');

    // --- Tab Logic ---
    function switchTab(tabId) {
        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabPanes.forEach(pane => pane.classList.remove('active'));
        
        document.querySelector(`.tab-btn[data-tab="${tabId}"]`).classList.add('active');
        document.getElementById(tabId).classList.add('active');
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // --- Setup Species ---
    async function initSpeciesDropdown() {
        try {
            const speciesList = await api.getSpecies();
            speciesFilter.innerHTML = '';
            resultsSpeciesFilter.innerHTML = '';
            
            if (speciesList.length === 0) {
                speciesFilter.innerHTML = '<option value="" disabled selected>No databases installed</option>';
                resultsSpeciesFilter.innerHTML = '<option value="" disabled selected>No databases installed</option>';
                return;
            }

            speciesList.forEach(sp => {
                const opt1 = document.createElement('option');
                opt1.value = sp;
                opt1.textContent = sp;
                speciesFilter.appendChild(opt1);

                const opt2 = document.createElement('option');
                opt2.value = sp;
                opt2.textContent = sp;
                resultsSpeciesFilter.appendChild(opt2);
            });
            
            // Default to first
            currentSpecies = speciesList[0];
            speciesFilter.value = currentSpecies;
            resultsSpeciesFilter.value = currentSpecies;
            
            // Listen for changes
            async function onSpeciesChange(e) {
                currentSpecies = e.target.value;
                speciesFilter.value = currentSpecies;
                resultsSpeciesFilter.value = currentSpecies;
                await fetchAvailableDatabases();
                if (document.getElementById('analysis-tab').classList.contains('active')) {
                    applyFilters();
                }
            }

            speciesFilter.addEventListener('change', onSpeciesChange);
            resultsSpeciesFilter.addEventListener('change', onSpeciesChange);

            await fetchAvailableDatabases();
        } catch (e) {
            console.error("Failed to load species", e);
        }
    }

    // --- Authentication Flow ---
    // Extract API Key from URL if present (from OAuth callback)
    const urlParams = new URLSearchParams(window.location.search);
    const urlApiKey = urlParams.get('api_key');
    if (urlApiKey) {
        api.setApiKey(urlApiKey);
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    async function checkAuth() {
        if (api.getApiKey()) {
            try {
                const user = await api.getMe();
                showDashboard(true, user);
            } catch (e) {
                api.clearApiKey();
                showAuthView();
            }
        } else {
            showAuthView();
        }
    }

    function showDashboard(isAuthenticated, user = null) {
        authView.classList.remove('active');
        dashboardView.classList.add('active');
        
        if (isAuthenticated && user) {
            usernameDisplay.textContent = user.username;
            logoutBtn.classList.remove('hidden');
            settingsNavBtn.classList.remove('hidden');
            loginNavBtn.classList.add('hidden');
            uploadLock.classList.add('hidden');
            
            // Populate settings modal
            settingsApiKeyInput.value = user.api_key;
            
            initSpeciesDropdown();
            loadResults();
        } else {
            usernameDisplay.textContent = "Guest Mode";
            logoutBtn.classList.add('hidden');
            settingsNavBtn.classList.add('hidden');
            loginNavBtn.classList.remove('hidden');
            uploadLock.classList.remove('hidden');
            resultsTbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 2rem;">Log in to view results.</td></tr>`;
        }
    }

    function showAuthView() {
        dashboardView.classList.remove('active');
        authView.classList.add('active');
    }

    guestBtn.addEventListener('click', () => {
        api.clearApiKey();
        showDashboard(false);
    });

    logoutBtn.addEventListener('click', () => {
        api.clearApiKey();
        showAuthView();
    });

    loginNavBtn.addEventListener('click', showAuthView);
    loginPromptBtn.addEventListener('click', showAuthView);

    // --- Settings Modal Logic ---
    settingsNavBtn.addEventListener('click', () => {
        settingsModal.classList.remove('hidden');
    });

    closeSettingsBtn.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    copyApiKeyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(settingsApiKeyInput.value);
            const originalText = copyApiKeyBtn.textContent;
            copyApiKeyBtn.textContent = "Copied!";
            setTimeout(() => { copyApiKeyBtn.textContent = originalText; }, 2000);
        } catch (e) {
            alert("Failed to copy to clipboard.");
        }
    });

    deleteAccountBtn.addEventListener('click', async () => {
        if (confirm("Are you sure you want to permanently delete your account and all serotyping data? This cannot be undone.")) {
            try {
                await api.deleteMe();
                api.clearApiKey();
                settingsModal.classList.add('hidden');
                showAuthView();
            } catch (e) {
                alert("Failed to delete account: " + e.message);
            }
        }
    });


    // --- Home Tab: Databases ---
    async function fetchAvailableDatabases() {
        if (!currentSpecies) return;
        try {
            const databases = await api.getDatabases(currentSpecies);
            currentDatabases = databases; // store globally for the table renderer
            
            dbList.innerHTML = '';
            if (databases.length === 0) {
                dbList.innerHTML = '<li>No databases loaded for this species.</li>';
                return;
            }
            databases.forEach(db => {
                const doiList = db.doi ? db.doi.map(d => d === 'TBD' ? `<span class="doi">${d}</span>` : `<a href="https://doi.org/${d}" target="_blank" rel="noopener noreferrer" class="doi">${d}</a>`).join(' ') : '';
                const card = document.createElement('div');
                card.className = 'db-card';
                card.innerHTML = `
                    <h4>${db.name}</h4>
                    <p>Organism: ${db.organism} | Version: ${db.version}</p>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">${doiList}</div>
                `;
                dbList.appendChild(card);
            });
        } catch (e) {
            dbList.innerHTML = `<li style="color: #ff4d4f">Failed to load databases: ${e.message}</li>`;
        }
    }


    // --- Home Tab: Upload ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    function handleFiles(files) {
        if (!files || files.length === 0) return;
        
        const validRegex = /\.(fasta|fa|fna|ffn|fas|faa|gfa)(\.(gz|bz2|xz))?$/i;
        const validFiles = Array.from(files).filter(f => validRegex.test(f.name));
        
        if (validFiles.length === 0) {
            alert("No valid sequence files detected. Please ensure files match the supported formats (.fasta, .fa, .gfa, etc. and optionally .gz/.bz2/.xz).");
            return;
        }
        
        selectedFiles = validFiles;
        fileCountDisplay.textContent = `${selectedFiles.length} file(s) selected`;
        startRunBtn.disabled = false;
    }

    startRunBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;
        
        startRunBtn.disabled = true;
        startRunBtn.textContent = "Uploading...";
        uploadLock.classList.remove('hidden');
        
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        try {
            const res = await api.uploadGenomes(currentSpecies, formData);
            
            // Upload success, start polling
            selectedFiles = [];
            fileCountDisplay.textContent = "0 files selected";
            fileInput.value = "";
            startRunBtn.textContent = "✨ Serotype!";
            
            switchTab('analysis-tab');
            startPolling(res.run_id);
            
        } catch (e) {
            alert("Upload failed: " + e.message);
            startRunBtn.disabled = false;
            startRunBtn.textContent = "✨ Serotype!";
        }
    });

    // --- Polling Progress ---
    function startPolling(runId) {
        floatingProgress.classList.remove('hidden');
        progressRunId.textContent = `ID: ${runId}`;
        progressStatus.textContent = "⚙️ Running...";
        
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.getElementById('progress-text');
        
        progressFill.style.width = '0%';
        if (progressText) progressText.textContent = 'Starting...';
        progressFill.style.background = 'var(--primary)';
        document.querySelector('.spinner-small').style.display = "block";
        
        const intervalId = setInterval(async () => {
            try {
                const data = await api.checkRunStatus(runId);
                const statusStr = (data.status || "").toLowerCase();
                
                const total = data.total_genomes || 0;
                const completed = data.completed_genomes || 0;
                
                if (total > 0) {
                    const percent = Math.round((completed / total) * 100);
                    progressFill.style.width = `${percent}%`;
                    if (progressText) progressText.textContent = `${completed} / ${total} genomes`;
                }
                
                if (statusStr === 'completed') {
                    clearInterval(intervalId);
                    progressStatus.textContent = "✅ Completed!";
                    progressFill.style.width = '100%';
                    if (progressText) progressText.textContent = `${total} / ${total} genomes`;
                    
                    setTimeout(() => {
                        floatingProgress.classList.add('hidden');
                    }, 3000);
                    
                    loadResults(); // Refresh table
                } else if (statusStr === 'failed') {
                    clearInterval(intervalId);
                    progressStatus.textContent = "❌ Failed";
                    progressFill.style.background = "#ff4d4f";
                    document.querySelector('.spinner-small').style.display = "none";
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 1500);
    }


    // --- Analysis Tab: Results Table ---
    async function loadResults() {
        tableLoading.classList.remove('hidden');
        try {
            allResults = await api.getResults();
            
            // Populate Run Filter
            const runs = new Set();
            allResults.forEach(r => {
                if (r.run_id) runs.add(r.run_id);
            });
            resultsRunFilter.innerHTML = '<option value="any">Any Run</option>';
            Array.from(runs).sort().reverse().forEach(run => {
                const opt = document.createElement('option');
                opt.value = run;
                opt.textContent = run.slice(0, 8) + '...'; // display short run ID
                resultsRunFilter.appendChild(opt);
            });
            
            applyFilters();
        } catch (e) {
            console.error("Failed to load results", e);
        } finally {
            tableLoading.classList.add('hidden');
        }
    }

    function renderTable(results) {
        const thead = document.getElementById('results-thead');
        resultsTbody.innerHTML = '';
        thead.innerHTML = '';
        
        // results is already filtered
        const speciesResults = results;

        if (currentDatabases.length === 0) {
            resultsTbody.innerHTML = `<tr><td style="text-align: center; padding: 2rem;">No databases available for ${currentSpecies || "this species"}.</td></tr>`;
            return;
        }

        // Build dynamic thead
        let superHeaders = `<tr><th>Genome</th>`;
        let subHeaders = `<tr class="sub-headers"><th>Name</th>`;
        
        currentDatabases.forEach((db, index) => {
            // Alternate classes for styling if needed, or just standard classes
            const colorClass = index % 2 === 0 ? 'db-k' : 'db-o'; 
            superHeaders += `<th colspan="4" class="db-header ${colorClass}">${db.name}</th>`;
            subHeaders += `
                <th>Locus</th>
                <th>Serotype</th>
                <th>Confidence</th>
                <th>Plot</th>
            `;
        });
        superHeaders += `</tr>`;
        subHeaders += `</tr>`;
        thead.innerHTML = superHeaders + subHeaders;

        if (speciesResults.length === 0) {
            const colspan = 1 + (currentDatabases.length * 4);
            resultsTbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align: center; padding: 2rem;">No results found for ${currentSpecies}. Start a run on the Home tab!</td></tr>`;
            return;
        }

        speciesResults.forEach(res => {
            const tr = document.createElement('tr');
            if (selectedGenomes.has(res.genome_id)) {
                tr.classList.add('selected');
            }
            
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', (e) => {
                // Ignore clicks on buttons
                if (e.target.tagName.toLowerCase() === 'button') return;
                
                if (selectedGenomes.has(res.genome_id)) {
                    selectedGenomes.delete(res.genome_id);
                    tr.classList.remove('selected');
                } else {
                    selectedGenomes.add(res.genome_id);
                    tr.classList.add('selected');
                }
                updateTally();
            });

            let trHtml = `<td class="genome-name">${res.genome_id}</td>`;
            
            currentDatabases.forEach((db, index) => {
                const dbData = res.databases[db.key] || {};
                const badgeClass = index % 2 === 0 ? 'badge-primary' : 'badge-secondary';
                
                trHtml += `
                    <td>${dbData.best_locus_name || '-'}</td>
                    <td><span class="badge ${badgeClass}">${dbData.phenotype || '-'}</span></td>
                    <td>${dbData.is_typeable !== undefined ? (dbData.is_typeable ? 'Typeable' : 'Untypeable') : '-'}</td>
                    <td>${dbData.best_locus_name ? `<button class="btn btn-secondary btn-icon view-plot-btn" data-run="${res.run_id}" data-genome="${res.genome_id}" data-db="${db.key}">Plot</button>` : '-'}</td>
                `;
            });
            
            tr.innerHTML = trHtml;
            resultsTbody.appendChild(tr);
        });

        // Add event listeners to plot buttons
        document.querySelectorAll('.view-plot-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const runId = e.target.getAttribute('data-run');
                const genomeId = e.target.getAttribute('data-genome');
                const dbKey = e.target.getAttribute('data-db');
                loadPlot(runId, genomeId, dbKey);
            });
        });
    }

    // --- Search / Filter ---
    function applyFilters() {
        const term = searchInput.value.toLowerCase();
        const runFilter = resultsRunFilter.value;
        const confFilter = resultsConfidenceFilter.value;
        
        filteredResults = allResults.filter(res => {
            if (res.species !== currentSpecies) return false;
            if (term && !res.genome_id.toLowerCase().includes(term)) return false;
            if (runFilter !== 'any' && res.run_id !== runFilter) return false;
            
            if (confFilter !== 'any') {
                // Check if any database in the genome matches the confidence
                const hasMatch = Object.values(res.databases).some(dbData => {
                    const typeable = dbData.is_typeable;
                    if (confFilter === 'typeable' && typeable) return true;
                    if (confFilter === 'untypeable' && !typeable) return true;
                    return false;
                });
                if (!hasMatch) return false;
            }
            return true;
        });
        
        renderTable(filteredResults);
        updateTally();
    }

    searchInput.addEventListener('input', applyFilters);
    resultsRunFilter.addEventListener('change', applyFilters);
    resultsConfidenceFilter.addEventListener('change', applyFilters);

    // --- Analysis Tab: Plotly Viewport ---
    async function loadPlot(runId, genomeId, dbKey) {
        // Open viewport
        plotViewport.classList.remove('minimized');
        plotEmptyState.classList.add('hidden');
        plotlyContainer.classList.add('hidden');
        plotLoading.classList.remove('hidden');
        
        viewportTitle.textContent = `📈 ${genomeId} - ${dbKey}`;

        try {
            const plotData = await api.getPlotJson(runId, genomeId, dbKey);
            plotLoading.classList.add('hidden');
            plotlyContainer.classList.remove('hidden');
            
            // Adjust plot template based on active theme
            const isLight = document.body.classList.contains('theme-light');
            plotData.layout.template = isLight ? "plotly_white" : "plotly_dark";
            plotData.layout.paper_bgcolor = "rgba(0,0,0,0)";
            plotData.layout.plot_bgcolor = "rgba(0,0,0,0)";
            
            // Plot
            Plotly.newPlot('plotly-container', plotData.data, plotData.layout, {responsive: true});
        } catch (e) {
            plotLoading.classList.add('hidden');
            plotEmptyState.classList.remove('hidden');
            plotEmptyState.innerHTML = `<p style="color: #ff4d4f">Failed to load plot: ${e.message}</p>`;
        }
    }

    closeViewportBtn.addEventListener('click', () => {
        plotViewport.classList.add('minimized');
        Plotly.purge('plotly-container');
        plotEmptyState.classList.remove('hidden');
        plotlyContainer.classList.add('hidden');
    });

    toggleMaximizeBtn.addEventListener('click', () => {
        plotViewport.classList.toggle('maximized');
        if (plotViewport.classList.contains('maximized')) {
            toggleMaximizeBtn.textContent = '🗗';
            toggleMaximizeBtn.title = 'Restore Viewport';
        } else {
            toggleMaximizeBtn.textContent = '⛶';
            toggleMaximizeBtn.title = 'Maximize Viewport';
        }
        
        // Trigger resize event for Plotly
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 300);
    });

    // Initial check
    checkAuth();
});
