/**
 * Main application logic for Kaptive-Web
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Lucide icons
    if (window.lucide) {
        window.lucide.createIcons();
    }

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
    const plotlyContainer = document.getElementById('plotly-container');
    const viewPlotToggle = document.getElementById('view-plot-toggle');
    const viewSummaryToggle = document.getElementById('view-summary-toggle');

    // Viewport state
    let currentViewRunId = null;
    let currentViewGenomeId = null;
    let currentViewDbKey = null;
    let activeViewMode = 'plot'; // 'plot' or 'summary'

    // Compare Modal elements
    const compareBtn = document.getElementById('compare-btn');
    const compareModal = document.getElementById('compare-modal');
    const closeCompareModal = document.getElementById('close-compare-modal');
    const compareDbButtonsContainer = document.getElementById('compare-db-buttons');
    const compareLoading = document.getElementById('compare-loading');
    const compareLoadingText = document.getElementById('compare-loading-text');
    const compareProgressBar = document.getElementById('compare-progress-bar');
    const comparePlotContainer = document.getElementById('compare-plot');

    let comparePollingInterval = null;
    let currentCompareParams = null;

    const compareShowAllLinksCheckbox = document.getElementById('compare-show-all-links');
    if (compareShowAllLinksCheckbox) {
        compareShowAllLinksCheckbox.addEventListener('change', () => {
            if (currentCompareParams) {
                startLocusComparison(currentCompareParams.runId, currentCompareParams.genomeIds, currentCompareParams.dbKey);
            }
        });
    }


    // Dropdown Logic
    const optionsDropdownBtn = document.getElementById('options-dropdown-btn');
    const optionsDropdownMenu = document.getElementById('options-dropdown-menu');

    if (optionsDropdownBtn && optionsDropdownMenu) {
        optionsDropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            optionsDropdownMenu.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!optionsDropdownMenu.contains(e.target) && !optionsDropdownBtn.contains(e.target)) {
                optionsDropdownMenu.classList.remove('show');
            }
        });
    }

    // Make Plotly responsive to manual viewport resizing
    const resizeObserver = new ResizeObserver(() => {
        if (plotlyContainer && !plotViewport.classList.contains('minimized') && plotlyContainer.children.length > 0) {
            Plotly.Plots.resize('plotly-container');
        }
    });
    resizeObserver.observe(plotViewport);

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
            a.download = format === 'tsv' ? 'kaptive_results_tsv' : (format === 'jsonl' ? 'kaptive_results.jsonl' : 'kaptive_results.jsonl');
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
            const originalText = downloadJsonBtn.innerHTML;
            downloadJsonBtn.textContent = 'Downloading...';
            await triggerDownload('/serotype/results/download/jsonl', 'jsonl');
            downloadJsonBtn.disabled = false;
            downloadJsonBtn.innerHTML = originalText;
        });
    }

    const downloadTsvBtn = document.getElementById('download-tsv-btn');
    if (downloadTsvBtn) {
        downloadTsvBtn.addEventListener('click', async () => {
            downloadTsvBtn.disabled = true;
            const originalText = downloadTsvBtn.innerHTML;
            downloadTsvBtn.textContent = 'Downloading...';
            await triggerDownload('/serotype/results/download/tsv', 'tsv');
            downloadTsvBtn.disabled = false;
            downloadTsvBtn.innerHTML = originalText;
        });
    }
    
    const downloadPha4geBtn = document.getElementById('download-pha4ge-btn');
    if (downloadPha4geBtn) {
        downloadPha4geBtn.addEventListener('click', async () => {
            downloadPha4geBtn.disabled = true;
            const originalText = downloadPha4geBtn.innerHTML;
            downloadPha4geBtn.textContent = 'Downloading...';
            await triggerDownload('/serotype/results/download/pha4ge', 'pha4ge');
            downloadPha4geBtn.disabled = false;
            downloadPha4geBtn.innerHTML = originalText;
        });
    }

    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', async () => {
            const genomeIds = Array.from(selectedGenomes);
            if (genomeIds.length === 0) return;
            
            if (!confirm(`Are you sure you want to delete results for ${genomeIds.length} genome(s)?`)) return;

            deleteSelectedBtn.disabled = true;
            const originalText = deleteSelectedBtn.innerHTML;
            deleteSelectedBtn.textContent = 'Deleting...';
            
            try {
                await api.deleteResults(genomeIds);
                // Remove deleted from allResults locally to update UI immediately
                const toDelete = new Set(genomeIds);
                allResults = allResults.filter(r => !toDelete.has(r.genome_id));
                selectedGenomes.clear();
                
                // Re-render
                applyFilters();
            } catch (err) {
                alert("Failed to delete results: " + err.message);
            } finally {
                deleteSelectedBtn.disabled = false;
                deleteSelectedBtn.innerHTML = originalText;
            }
        });
    }

    if (compareBtn) {
        compareBtn.addEventListener('click', () => {
            if (selectedGenomes.size < 2) return;

            // Populate database buttons
            compareDbButtonsContainer.innerHTML = '';
            currentDatabases.forEach(db => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-secondary';
                btn.style.padding = '0.3rem 0.6rem';
                btn.style.fontSize = '0.85rem';
                btn.textContent = db.name;

                btn.addEventListener('click', () => {
                    // Start comparison
                    const genomeIds = Array.from(selectedGenomes);
                    const firstSelected = allResults.find(r => r.genome_id === genomeIds[0]);
                    const runId = firstSelected ? firstSelected.run_id : null;
                    startLocusComparison(runId, genomeIds, db.key);
                });

                compareDbButtonsContainer.appendChild(btn);
            });

            compareModal.classList.remove('hidden');
        });
    }

    if (closeCompareModal) {
        closeCompareModal.addEventListener('click', () => {
            compareModal.classList.add('hidden');
            if (comparePollingInterval) {
                clearInterval(comparePollingInterval);
                comparePollingInterval = null;
            }
            compareLoading.classList.add('hidden');
            comparePlotContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">Select a database above to compare loci.</div>';
        });
    }

    async function startLocusComparison(runId, genomeIds, dbKey) {
        currentCompareParams = { runId, genomeIds, dbKey };
        compareLoading.classList.remove('hidden');
        compareLoadingText.textContent = "Generating comparison...";
        compareProgressBar.style.width = "0%";
        comparePlotContainer.innerHTML = '';

        try {
            const isLight = document.body.classList.contains('theme-light');
            const showAllLinks = compareShowAllLinksCheckbox?.checked || false;
            const data = await api.startComparison(runId, genomeIds, dbKey, showAllLinks, !isLight);
            const taskId = data.task_id;

            if (comparePollingInterval) clearInterval(comparePollingInterval);

            comparePollingInterval = setInterval(async () => {
                try {
                    const statusData = await api.getComparisonStatus(taskId);
                    compareProgressBar.style.width = `${statusData.progress || 0}%`;

                    if (statusData.status === 'completed') {
                        clearInterval(comparePollingInterval);
                        comparePollingInterval = null;
                        compareLoading.classList.add('hidden');

                        statusData.result.layout.plot_bgcolor = "rgba(0,0,0,0)";
                        statusData.result.layout.paper_bgcolor = "rgba(0,0,0,0)";
                        Plotly.newPlot(comparePlotContainer, statusData.result.data, statusData.result.layout, { responsive: true });
                        if (!comparePlotContainer._resizeObserver) {
                            comparePlotContainer._resizeObserver = new ResizeObserver(() => {
                                if (comparePlotContainer.data) {
                                    Plotly.Plots.resize(comparePlotContainer);
                                }
                            });
                            comparePlotContainer._resizeObserver.observe(comparePlotContainer);
                        }
                    } else if (statusData.status === 'failed') {
                        clearInterval(comparePollingInterval);
                        comparePollingInterval = null;
                        compareLoadingText.textContent = "❌ Failed: " + (statusData.error || 'Unknown error');
                        compareProgressBar.style.background = "#ff4d4f";
                    }
                } catch (e) {
                    console.error("Polling comparison error:", e);
                }
            }, 1000);

        } catch (e) {
            console.error("Start comparison error:", e);
            compareLoadingText.textContent = "❌ Failed to start comparison.";
            compareProgressBar.style.background = "#ff4d4f";
        }
    }


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
        if (!plotlyContainer.classList.contains('hidden') && (!plotViewport.classList.contains('minimized') || plotViewport.classList.contains('maximized'))) {
            if (activeViewMode === 'plot' && currentViewRunId && currentViewGenomeId && currentViewDbKey) {
                loadPlot(currentViewRunId, currentViewGenomeId, currentViewDbKey);
            }
        }

        // Update comparison plot if open
        if (!compareModal.classList.contains('hidden') && currentCompareParams) {
            startLocusComparison(currentCompareParams.runId, currentCompareParams.genomeIds, currentCompareParams.dbKey);
        }

        // Update API Docs iframe theme (Swagger UI)
        try {
            const apiIframe = document.querySelector('#api-tab iframe');
            const updateIframe = () => {
                try {
                    const doc = apiIframe.contentDocument;
                    if (!doc) return;

                    const links = doc.querySelectorAll('link[rel="stylesheet"]');
                    let targetLink = null;
                    links.forEach(link => {
                        if (link.href.includes('dark_theme.css') || link.href.includes('swagger-ui.css')) {
                            targetLink = link;
                        }
                    });

                    if (targetLink) {
                        if (activeTheme === 'dark') {
                            if (!targetLink.href.includes('dark_theme.css')) {
                                targetLink.href = '/dark_theme.css';
                            }
                        } else {
                            if (!targetLink.href.includes('swagger-ui.css')) {
                                targetLink.href = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css';
                            }
                        }
                    }
                } catch (e) { }
            };
            if (apiIframe) {
                updateIframe();
                apiIframe.addEventListener('load', updateIframe);
            }
        } catch (e) { }
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
        const selectAllCheckbox = document.getElementById('select-all-genomes');
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = selectedGenomes.size > 0 && selectedGenomes.size === filteredResults.length;
            selectAllCheckbox.indeterminate = selectedGenomes.size > 0 && selectedGenomes.size < filteredResults.length;
        }
        if (compareBtn) {
            compareBtn.disabled = selectedGenomes.size < 2;
        }
        const deleteBtn = document.getElementById('delete-selected-btn');
        if (deleteBtn) {
            deleteBtn.disabled = selectedGenomes.size === 0;
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

        if (tabId === 'about-tab' && !document.getElementById('about-content').hasAttribute('data-loaded')) {
            document.getElementById('about-content').innerHTML = '<div class="spinner"></div><p style="margin-top: 1rem;">Loading...</p>';
            fetch('/api/about').then(r => r.json()).then(data => {
                if (window.marked) {
                    document.getElementById('about-content').innerHTML = marked.parse(data.content || "No content");
                    const mermaidBlocks = document.querySelectorAll('#about-content pre code.language-mermaid');
                    if (mermaidBlocks.length > 0) {
                        const loadMermaid = () => {
                            if (window.mermaid) return Promise.resolve(window.mermaid);
                            return new Promise((resolve, reject) => {
                                const script = document.createElement('script');
                                script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js';
                                script.onload = () => resolve(window.mermaid);
                                script.onerror = reject;
                                document.head.appendChild(script);
                            });
                        };
                        
                        loadMermaid().then((mermaidObj) => {
                            mermaidBlocks.forEach(block => {
                                const pre = block.parentNode;
                                const container = document.createElement('div');
                                container.className = 'mermaid';
                                container.textContent = block.textContent;
                                pre.parentNode.replaceChild(container, pre);
                            });
                            mermaidObj.run({ querySelector: '.mermaid' }).catch(e => console.error("Mermaid init error:", e));
                        }).catch(e => console.error("Failed to load mermaid:", e));
                    }
                } else {
                    document.getElementById('about-content').innerHTML = `<pre>${data.content}</pre>`;
                }
                document.getElementById('about-content').setAttribute('data-loaded', 'true');
            }).catch(err => {
                document.getElementById('about-content').innerHTML = '<p style="color: red">Failed to load about info.</p>';
            });
        }
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
            logoutBtn.classList.remove('hidden');
            settingsNavBtn.classList.remove('hidden');
            loginNavBtn.classList.add('hidden');
            uploadLock.classList.add('hidden');

            // Populate settings modal
            settingsApiKeyInput.value = user.api_key;

            initSpeciesDropdown();
            loadResults();
        } else {
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
        settingsModal.classList.add('hidden');
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
            // Sanitize filename on the frontend: replace invalid chars with underscores
            const sanitizedName = file.name.replace(/[^\w.-]/g, '_') || 'unknown.fasta';
            formData.append('files', file, sanitizedName);
        });
        
        const runNameInput = document.getElementById('run-name-input');
        if (runNameInput && runNameInput.value.trim() !== '') {
            formData.append('run_name', runNameInput.value.trim());
        }

        try {
            const res = await api.uploadGenomes(currentSpecies, formData);

            // Upload success, start polling
            selectedFiles = [];
            fileCountDisplay.textContent = "0 files selected";
            if (runNameInput) runNameInput.value = "";
            fileInput.value = "";
            startRunBtn.textContent = "✨ phenotype!";

            switchTab('analysis-tab');
            startPolling(res.run_id);

        } catch (e) {
            alert("Upload failed: " + e.message);
            startRunBtn.disabled = false;
            startRunBtn.textContent = "✨ phenotype!";
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
    
    // Utility to prevent XSS injection
    function escapeHtml(unsafe) {
        if (unsafe == null) return "";
        return unsafe.toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
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
        let superHeaders = `<tr><th colspan="3" style="border-bottom: 1px solid var(--glass-border);">Sample Info</th>`;
        let subHeaders = `<tr class="sub-headers">
            <th style="width: 40px; text-align: center;"><input type="checkbox" id="select-all-genomes" title="Select All"></th>
            <th class="filterable" data-col="run_name"><div class="th-content"><span>Run</span><span class="filter-icon">▼</span></div></th>
            <th class="filterable" data-col="genome_id"><div class="th-content"><span>Genome</span><span class="filter-icon">▼</span></div></th>
        `;

        currentDatabases.forEach((db, index) => {
            const colorClass = index % 2 === 0 ? 'db-k' : 'db-o';
            superHeaders += `<th colspan="4" class="db-header ${colorClass}">${db.name}</th>`;
            subHeaders += `
                <th class="filterable" data-col="db_${db.key}_locus"><div class="th-content"><span>Locus</span><span class="filter-icon">▼</span></div></th>
                <th class="filterable" data-col="db_${db.key}_phenotype"><div class="th-content"><span>Phenotype</span><span class="filter-icon">▼</span></div></th>
                <th class="filterable" data-col="db_${db.key}_confidence"><div class="th-content"><span>Confidence</span><span class="filter-icon">▼</span></div></th>
                <th>View</th>
            `;
        });
        superHeaders += `</tr>`;
        subHeaders += `</tr>`;
        thead.innerHTML = superHeaders + subHeaders;

        const selectAllCheckbox = document.getElementById('select-all-genomes');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    filteredResults.forEach(res => selectedGenomes.add(res.genome_id));
                    Array.from(resultsTbody.children).forEach(row => row.classList.add('selected'));
                    resultsTbody.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = true);
                } else {
                    selectedGenomes.clear();
                    Array.from(resultsTbody.children).forEach(row => row.classList.remove('selected'));
                    resultsTbody.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
                }
                updateTally();
            });
        }

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

            // Selection is now handled entirely by the checkbox

            let trHtml = `
                <td style="text-align: center;"><input type="checkbox" class="row-checkbox" value="${escapeHtml(res.genome_id)}" ${selectedGenomes.has(res.genome_id) ? 'checked' : ''}></td>
                <td><span class="badge badge-secondary">${escapeHtml(res.run_name || res.run_id)}</span></td>
                <td><span class="font-mono">${escapeHtml(res.genome_id)}</span></td>
            `;

            currentDatabases.forEach((db, index) => {
                const dbData = res.databases[db.key] || {};
                const badgeClass = index % 2 === 0 ? 'badge-primary' : 'badge-secondary';

                trHtml += `
                    <td>${escapeHtml(dbData.best_locus_name || '-')}</td>
                    <td><span class="badge ${badgeClass}">${escapeHtml(dbData.phenotype || '-')}</span></td>
                    <td>${dbData.typeable !== undefined ? (dbData.typeable ? 'Typeable' : 'Untypeable') : '-'}</td>
                    <td>${dbData.best_locus_name ? `<button class="btn btn-secondary btn-icon view-btn" data-run="${escapeHtml(res.run_id)}" data-genome="${escapeHtml(res.genome_id)}" data-db="${escapeHtml(db.key)}" title="View Details"><i data-lucide="search" style="width: 16px; height: 16px; margin-right: 4px;"></i> View</button>` : '-'}</td>
                `;
            });

            tr.innerHTML = trHtml;
            resultsTbody.appendChild(tr);

            // Sync checkbox state if row is clicked natively
            const rowCheckbox = tr.querySelector('.row-checkbox');
            if (rowCheckbox) {
                rowCheckbox.addEventListener('change', (e) => {
                    if (e.target.checked) {
                        selectedGenomes.add(res.genome_id);
                        tr.classList.add('selected');
                    } else {
                        selectedGenomes.delete(res.genome_id);
                        tr.classList.remove('selected');
                    }
                    updateTally();
                });
            }
        });

        // Add event listeners to unified view buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const button = e.target.closest('button');
                currentViewRunId = button.getAttribute('data-run');
                currentViewGenomeId = button.getAttribute('data-genome');
                currentViewDbKey = button.getAttribute('data-db');

                if (activeViewMode === 'plot') {
                    loadPlot(currentViewRunId, currentViewGenomeId, currentViewDbKey);
                } else {
                    loadSummary(currentViewRunId, currentViewGenomeId, currentViewDbKey);
                }
            });
        });

        // Ensure new icons are rendered
        if (window.lucide) window.lucide.createIcons();
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
                return String(valA).localeCompare(String(valB), undefined, { numeric: true }) * modifier;
            });
        }

        filteredResults = resultPool;
        renderTable(filteredResults);
        updateTally();
    }

    function getColValueForRes(res, colId) {
        if (colId === 'genome_id') return res.genome_id;
        if (colId === 'run_name') return res.run_name || res.run_id;

        // Dynamic DB columns
        if (colId.startsWith('db_')) {
            const parts = colId.split('_');
            const dbKey = parts[1] + '_' + parts[2]; // e.g. db_ab_k_locus -> ab_k
            const field = parts[3]; // locus, phenotype, confidence

            const dbData = res.databases[dbKey] || {};
            if (field === 'locus') return dbData.best_locus_name || '-';
            if (field === 'phenotype') return dbData.phenotype || '-';
            if (field === 'confidence') {
                return dbData.typeable !== undefined ? (dbData.typeable ? 'Typeable' : 'Untypeable') : '-';
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
        populateFilterCheckboxes(Array.from(uniqueValues).sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true })));

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
        populateFilterCheckboxes(Array.from(uniqueValues).sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true })));
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

    const summaryContainer = document.getElementById('summary-container');
    const summaryContent = document.getElementById('summary-content');
    const viewportGenomeId = document.getElementById('viewport-genome-id');
    const viewportDbSelect = document.getElementById('viewport-db-select');

    if (viewportDbSelect) {
        viewportDbSelect.addEventListener('change', (e) => {
            const selectedDb = e.target.value;
            if (selectedDb && selectedDb !== currentViewDbKey) {
                currentViewDbKey = selectedDb;
                if (activeViewMode === 'plot') {
                    loadPlot(currentViewRunId, currentViewGenomeId, selectedDb);
                } else {
                    loadSummary(currentViewRunId, currentViewGenomeId, selectedDb);
                }
            }
        });
    }

    function updateViewportTitle(runId, genomeId, dbKey) {
        if (viewportGenomeId) {
            const limit = 25;
            if (genomeId.length > limit) {
                viewportGenomeId.textContent = genomeId.substring(0, limit - 3) + '...';
            } else {
                viewportGenomeId.textContent = genomeId;
            }
            viewportGenomeId.title = genomeId; // Tooltip on hover
        }

        const resultObj = allResults.find(r => r.run_id === runId && r.genome_id === genomeId);

        if (resultObj && resultObj.databases && viewportDbSelect) {
            const dbKeys = Object.keys(resultObj.databases);
            viewportDbSelect.innerHTML = '';
            dbKeys.forEach(key => {
                const option = document.createElement('option');
                option.value = key;
                option.textContent = key;
                if (key === dbKey) {
                    option.selected = true;
                }
                viewportDbSelect.appendChild(option);
            });
            viewportDbSelect.classList.remove('hidden');
            viewportDbSelect.style.display = 'block';
        } else if (viewportDbSelect) {
            viewportDbSelect.classList.add('hidden');
            viewportDbSelect.style.display = 'none';
        }
    }

    async function loadSummary(runId, genomeId, dbKey) {
        plotViewport.classList.remove('minimized');
        plotEmptyState.classList.add('hidden');
        plotlyContainer.classList.add('hidden');
        summaryContainer.classList.add('hidden');
        plotLoading.classList.remove('hidden');

        updateViewportTitle(runId, genomeId, dbKey);

        try {
            const sumData = await api.getPlotSummary(runId, genomeId, dbKey);
            plotLoading.classList.add('hidden');
            summaryContainer.classList.remove('hidden');
            summaryContent.innerHTML = marked.parse(sumData.summary);
        } catch (e) {
            plotLoading.classList.add('hidden');
            plotEmptyState.classList.remove('hidden');
            plotEmptyState.innerHTML = `<p style="color: #ff4d4f">Failed to load summary: ${e.message}</p>`;
        }
    }

    async function loadPlot(runId, genomeId, dbKey) {
        // Open viewport
        plotViewport.classList.remove('minimized');
        plotEmptyState.classList.add('hidden');
        plotlyContainer.classList.add('hidden');
        if (summaryContainer) summaryContainer.classList.add('hidden');
        plotLoading.classList.remove('hidden');

        updateViewportTitle(runId, genomeId, dbKey);

        try {
            const isLight = document.body.classList.contains('theme-light');
            const plotData = await api.getPlotJson(runId, genomeId, dbKey, !isLight);
            plotLoading.classList.add('hidden');
            plotlyContainer.classList.remove('hidden');

            // Adjust plot template based on active theme
            plotData.layout.template = isLight ? "plotly_white" : "plotly_dark";
            plotData.layout.paper_bgcolor = "rgba(0,0,0,0)";
            plotData.layout.plot_bgcolor = "rgba(0,0,0,0)";

            // Plot
            Plotly.newPlot('plotly-container', plotData.data, plotData.layout, { responsive: true });
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
        if (summaryContainer) summaryContainer.classList.add('hidden');
        currentViewRunId = null;
        currentViewGenomeId = null;
        currentViewDbKey = null;
    });

    // Viewport Toggle Logic
    viewPlotToggle.addEventListener('click', () => {
        activeViewMode = 'plot';
        viewPlotToggle.style.background = 'var(--glass-hover-bg)';
        viewSummaryToggle.style.background = 'transparent';
        if (currentViewRunId && currentViewGenomeId && currentViewDbKey) {
            loadPlot(currentViewRunId, currentViewGenomeId, currentViewDbKey);
        }
    });

    viewSummaryToggle.addEventListener('click', () => {
        activeViewMode = 'summary';
        viewSummaryToggle.style.background = 'var(--glass-hover-bg)';
        viewPlotToggle.style.background = 'transparent';
        if (currentViewRunId && currentViewGenomeId && currentViewDbKey) {
            loadSummary(currentViewRunId, currentViewGenomeId, currentViewDbKey);
        }
    });

    // Reusable drag functionality
    function makeDraggable(container, header) {
        let isDragging = false;
        let dragStartX, dragStartY, initialLeft, initialTop;

        header.addEventListener('mousedown', (e) => {
            if (container.classList.contains('maximized')) return;
            if (e.target.closest('button') || e.target.closest('select')) return;

            isDragging = true;
            dragStartX = e.clientX;
            dragStartY = e.clientY;

            const rect = container.getBoundingClientRect();
            initialLeft = rect.left;
            initialTop = rect.top;

            container.style.bottom = 'auto';
            container.style.right = 'auto';
            container.style.left = initialLeft + 'px';
            container.style.top = initialTop + 'px';

            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - dragStartX;
            const dy = e.clientY - dragStartY;
            container.style.left = (initialLeft + dx) + 'px';
            container.style.top = (initialTop + dy) + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                document.body.style.userSelect = '';
            }
        });

        // Make the header indicate it's draggable
        header.style.cursor = 'move';
    }

    const viewportHeader = plotViewport.querySelector('.viewport-header');
    makeDraggable(plotViewport, viewportHeader);

    const compareHeader = compareModal.querySelector('.modal-header');
    if (compareHeader) {
        makeDraggable(compareModal, compareHeader);
    }

    // Save state before maximizing
    let preMaxState = { top: '', left: '', bottom: '', right: '', width: '', height: '' };

    toggleMaximizeBtn.addEventListener('click', () => {
        if (!plotViewport.classList.contains('maximized')) {
            // Maximize
            preMaxState = {
                top: plotViewport.style.top,
                left: plotViewport.style.left,
                bottom: plotViewport.style.bottom,
                right: plotViewport.style.right,
                width: plotViewport.style.width,
                height: plotViewport.style.height
            };
            plotViewport.style.top = '';
            plotViewport.style.left = '';
            plotViewport.style.bottom = '';
            plotViewport.style.right = '';
            plotViewport.style.width = '';
            plotViewport.style.height = '';

            plotViewport.classList.add('maximized');
            toggleMaximizeBtn.textContent = '🗗';
            toggleMaximizeBtn.title = 'Restore Viewport';
        } else {
            // Restore
            plotViewport.classList.remove('maximized');
            plotViewport.style.top = preMaxState.top;
            plotViewport.style.left = preMaxState.left;
            plotViewport.style.bottom = preMaxState.bottom;
            plotViewport.style.right = preMaxState.right;
            plotViewport.style.width = preMaxState.width;
            plotViewport.style.height = preMaxState.height;

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
