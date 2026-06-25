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
    const filterPopover = document.getElementById('column-filter-popover');
    const filterPopoverTitle = document.getElementById('filter-popover-title');
    const filterSortAsc = document.getElementById('filter-sort-asc');
    const filterSortDesc = document.getElementById('filter-sort-desc');
    const filterSearchInput = document.getElementById('filter-search-input');
    const filterSelectAll = document.getElementById('filter-select-all');
    const filterClearAll = document.getElementById('filter-clear-all');
    const filterCheckboxList = document.getElementById('filter-checkbox-list');
    const filterApplyBtn = document.getElementById('filter-apply-btn');
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
                'layout.template': activeTheme === 'light' ? 'plotly_white' : 'plotly_dark',
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)'
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
let activeColumnFilters = {};
let currentSortConfig = { colId: null, direction: 'asc' };
let currentFilterColId = null;
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
                let contactsHtml = '';
                if (db.contact) {
                    const contactsList = Object.entries(db.contact).map(([name, email]) => {
                        if (email && email.includes('@')) {
                            return `<span style="white-space: nowrap;">${name} <a href="mailto:${email}" target="_blank" rel="noopener noreferrer" title="Email ${name}" style="text-decoration: none;">📧</a></span>`;
                        }
                        return `<span>${name}</span>`;
                    }).join(', ');
                    contactsHtml = `<p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;"><strong>Curators:</strong> ${contactsList}</p>`;
                }
                
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.2rem;">
                        <h4 style="margin: 0; font-size: 1rem;">${db.name}</h4>
                        <span class="badge" style="font-size: 0.7rem; background: var(--glass-hover-bg); color: var(--text-muted);">v${db.version}</span>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.2rem; margin-top: 0;">
                        <strong>Antigen:</strong> ${db.antigen || 'Unknown'} (${db.pathway || 'Unknown'} pathway)
                    </p>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem; margin-top: 0;">
                        <strong>Size:</strong> ${db.loci_count} Loci | ${db.genes_count} Genes
                    </p>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">${doiList}</div>
                    ${contactsHtml}
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
        let superHeaders = `<tr><th colspan="2" style="border-bottom: 1px solid var(--glass-border);">Sample Info</th>`;
        let subHeaders = `<tr class="sub-headers">
            <th class="filterable" data-col="genome_id"><div class="th-content"><span>Genome</span><span class="filter-icon">▼</span></div></th>
            <th class="filterable" data-col="run_id"><div class="th-content"><span>Run</span><span class="filter-icon">▼</span></div></th>
        `;
        
        currentDatabases.forEach((db, index) => {
            const colorClass = index % 2 === 0 ? 'db-k' : 'db-o'; 
            superHeaders += `<th colspan="4" class="db-header ${colorClass}">${db.name}</th>`;
            subHeaders += `
                <th class="filterable" data-col="db_${db.key}_locus"><div class="th-content"><span>Locus</span><span class="filter-icon">▼</span></div></th>
                <th class="filterable" data-col="db_${db.key}_serotype"><div class="th-content"><span>Serotype</span><span class="filter-icon">▼</span></div></th>
                <th class="filterable" data-col="db_${db.key}_confidence"><div class="th-content"><span>Confidence</span><span class="filter-icon">▼</span></div></th>
                <th>Plot</th>
            `;
        });
        superHeaders += `</tr>`;
        subHeaders += `</tr>`;
        thead.innerHTML = superHeaders + subHeaders;
        
        // Bind click listeners
        thead.querySelectorAll('.filterable').forEach(th => {
            const colId = th.dataset.col;
            if (activeColumnFilters[colId] && activeColumnFilters[colId].size > 0) {
                th.classList.add('filtered');
            }
            if (currentSortConfig.colId === colId) {
                th.querySelector('.filter-icon').textContent = currentSortConfig.direction === 'asc' ? '↓' : '↑';
                th.querySelector('.filter-icon').style.opacity = '1';
                th.querySelector('.filter-icon').style.color = 'var(--primary)';
            }
            th.addEventListener('click', (e) => {
                openFilterPopover(e, colId, th.querySelector('span').textContent);
            });
        });

        if (speciesResults.length === 0) {
            const colspan = 1 + (currentDatabases.length * 4);
            resultsTbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align: center; padding: 2rem;">No results found for ${currentSpecies}. Start a run on the Home tab!</td></tr>`;
            return;
        }

        let lastSelectedIndex = null;

        speciesResults.forEach((res, index) => {
            const tr = document.createElement('tr');
            if (selectedGenomes.has(res.genome_id)) {
                tr.classList.add('selected');
            }
            
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', (e) => {
                // Ignore clicks on buttons
                if (e.target.tagName.toLowerCase() === 'button') return;
                
                const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
                const isCmdCtrl = isMac ? e.metaKey : e.ctrlKey;
                const isShift = e.shiftKey;

                if (isShift && lastSelectedIndex !== null) {
                    // Range selection
                    const start = Math.min(lastSelectedIndex, index);
                    const end = Math.max(lastSelectedIndex, index);

                    if (!isCmdCtrl) {
                        selectedGenomes.clear();
                        Array.from(resultsTbody.children).forEach(row => row.classList.remove('selected'));
                    }
                    
                    for (let i = start; i <= end; i++) {
                        const targetRes = speciesResults[i];
                        selectedGenomes.add(targetRes.genome_id);
                        resultsTbody.children[i].classList.add('selected');
                    }
                    // Keep lastSelectedIndex the same for consecutive shift-clicks
                } else if (isCmdCtrl) {
                    // Toggle selection
                    if (selectedGenomes.has(res.genome_id)) {
                        selectedGenomes.delete(res.genome_id);
                        tr.classList.remove('selected');
                    } else {
                        selectedGenomes.add(res.genome_id);
                        tr.classList.add('selected');
                        lastSelectedIndex = index;
                    }
                } else {
                    // Normal click: select ONLY this row
                    selectedGenomes.clear();
                    Array.from(resultsTbody.children).forEach(row => row.classList.remove('selected'));
                    selectedGenomes.add(res.genome_id);
                    tr.classList.add('selected');
                    lastSelectedIndex = index;
                }
                
                updateTally();
                
                // Clear text selection that naturally happens with shift-click
                if (isShift) {
                    window.getSelection().removeAllRanges();
                }
            });

            let trHtml = `
                <td class="genome-name">${res.genome_id}</td>
                <td><span class="badge" style="background: var(--glass-hover-bg);">${res.run_id ? res.run_id.slice(0,8) + '...' : 'N/A'}</span></td>
            `;
            
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

    // --- Search / Filter & Sort ---
    function applyFilters() {
        // 1. Filter by Species
        let resultPool = allResults.filter(res => res.species === currentSpecies);
        
        // 2. Apply Column Filters
        resultPool = resultPool.filter(res => {
            for (const [colId, selectedValues] of Object.entries(activeColumnFilters)) {
                if (selectedValues.size === 0) continue; // no filter active for this col
                
                let val = getColValueForRes(res, colId);
                if (!selectedValues.has(val)) return false;
            }
            return true;
        });
        
        // 3. Apply Sorting
        if (currentSortConfig.colId) {
            resultPool.sort((a, b) => {
                let valA = getColValueForRes(a, currentSortConfig.colId);
                let valB = getColValueForRes(b, currentSortConfig.colId);
                
                if (valA === valB) return 0;
                
                const modifier = currentSortConfig.direction === 'asc' ? 1 : -1;
                
                // Handle missing values
                if (valA === '-') return 1 * modifier;
                if (valB === '-') return -1 * modifier;
                
                // String comparison
                return String(valA).localeCompare(String(valB), undefined, {numeric: true}) * modifier;
            });
        }
        
        filteredResults = resultPool;
        renderTable(filteredResults);
        updateTally();
    }
    
    function getColValueForRes(res, colId) {
        if (colId === 'genome_id') return res.genome_id;
        if (colId === 'run_id') return res.run_id || 'N/A';
        
        // Dynamic DB columns
        if (colId.startsWith('db_')) {
            const parts = colId.split('_');
            const dbKey = parts[1] + '_' + parts[2]; // e.g. db_ab_k_locus -> ab_k
            const field = parts[3]; // locus, serotype, confidence
            
            const dbData = res.databases[dbKey] || {};
            if (field === 'locus') return dbData.best_locus_name || '-';
            if (field === 'serotype') return dbData.phenotype || '-';
            if (field === 'confidence') {
                return dbData.is_typeable !== undefined ? (dbData.is_typeable ? 'Typeable' : 'Untypeable') : '-';
            }
        }
        return '-';
    }

    // --- Popover Logic ---
    function openFilterPopover(e, colId, colName) {
        currentFilterColId = colId;
        filterPopoverTitle.textContent = 'Filter ' + colName;
        
        // Calculate unique values for this column from current species results (pre-column-filter)
        const speciesRes = allResults.filter(res => res.species === currentSpecies);
        const uniqueValues = new Set();
        speciesRes.forEach(res => {
            uniqueValues.add(getColValueForRes(res, colId));
        });
        
        // Populate checkboxes
        populateFilterCheckboxes(Array.from(uniqueValues).sort((a, b) => String(a).localeCompare(String(b), undefined, {numeric: true})));
        
        // Position popover
        const rect = e.currentTarget.getBoundingClientRect();
        filterPopover.style.top = (rect.bottom + window.scrollY) + 'px';
        filterPopover.style.left = (rect.left + window.scrollX) + 'px';
        
        filterSearchInput.value = '';
        filterPopover.classList.remove('hidden');
        
        // Prevent click from bubbling to document body which closes it
        e.stopPropagation();
    }
    
    function populateFilterCheckboxes(values) {
        filterCheckboxList.innerHTML = '';
        const searchTerm = filterSearchInput.value.toLowerCase();
        
        values.forEach(val => {
            if (searchTerm && !String(val).toLowerCase().includes(searchTerm)) return;
            
            const div = document.createElement('div');
            div.className = 'filter-checkbox-item';
            
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = val;
            
            // Check if active
            if (activeColumnFilters[currentFilterColId] && activeColumnFilters[currentFilterColId].has(val)) {
                cb.checked = true;
            }
            
            // If no active filters exist for this col, everything is checked by default visually
            if (!activeColumnFilters[currentFilterColId] || activeColumnFilters[currentFilterColId].size === 0) {
                 cb.checked = true;
            }
            
            const label = document.createElement('span');
            label.textContent = val;
            
            div.appendChild(cb);
            div.appendChild(label);
            
            div.addEventListener('click', (e) => {
                if (e.target !== cb) cb.checked = !cb.checked;
            });
            
            filterCheckboxList.appendChild(div);
        });
    }
    
    // Close popover when clicking outside
    document.addEventListener('click', (e) => {
        if (!filterPopover.contains(e.target)) {
            filterPopover.classList.add('hidden');
        }
    });
    
    filterSearchInput.addEventListener('input', () => {
        // Re-populate using all unique values
        const speciesRes = allResults.filter(res => res.species === currentSpecies);
        const uniqueValues = new Set();
        speciesRes.forEach(res => uniqueValues.add(getColValueForRes(res, currentFilterColId)));
        populateFilterCheckboxes(Array.from(uniqueValues).sort((a, b) => String(a).localeCompare(String(b), undefined, {numeric: true})));
    });
    
    filterSelectAll.addEventListener('click', (e) => {
        e.preventDefault();
        filterCheckboxList.querySelectorAll('input').forEach(cb => cb.checked = true);
    });
    
    filterClearAll.addEventListener('click', (e) => {
        e.preventDefault();
        filterCheckboxList.querySelectorAll('input').forEach(cb => cb.checked = false);
    });
    
    filterApplyBtn.addEventListener('click', () => {
        const checked = Array.from(filterCheckboxList.querySelectorAll('input:checked')).map(cb => cb.value);
        const visibleValues = Array.from(filterCheckboxList.querySelectorAll('input')).map(cb => cb.value);
        
        if (!activeColumnFilters[currentFilterColId]) {
            activeColumnFilters[currentFilterColId] = new Set();
        }
        
        // If all visible items are checked, and there is no search filter, we are clearing the filter
        if (checked.length === visibleValues.length && filterSearchInput.value === '') {
            activeColumnFilters[currentFilterColId].clear();
        } else {
            // Need to retain previously checked values that are currently hidden by search!
            // First remove any visible values from the active set
            visibleValues.forEach(val => activeColumnFilters[currentFilterColId].delete(val));
            // Then add back the checked ones
            checked.forEach(val => activeColumnFilters[currentFilterColId].add(val));
        }
        
        filterPopover.classList.add('hidden');
        applyFilters();
    });
    
    filterSortAsc.addEventListener('click', () => {
        currentSortConfig = { colId: currentFilterColId, direction: 'asc' };
        filterPopover.classList.add('hidden');
        applyFilters();
    });
    
    filterSortDesc.addEventListener('click', () => {
        currentSortConfig = { colId: currentFilterColId, direction: 'desc' };
        filterPopover.classList.add('hidden');
        applyFilters();
    });

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
