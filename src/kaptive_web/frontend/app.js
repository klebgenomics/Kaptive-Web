document.addEventListener('DOMContentLoaded', async () => {
    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileListUI = document.getElementById('file-list');
    const fileListContainer = document.getElementById('file-list-container');
    const jobForm = document.getElementById('job-form');
    const submitBtn = document.getElementById('submit-btn');
    
    // Results DOM Elements
    const statusContainer = document.getElementById('status-container');
    const statusTitle = document.getElementById('status-title');
    const statusText = document.getElementById('status-text');
    const resultsTableContainer = document.getElementById('results-table-container');
    const resultsTbody = document.getElementById('results-tbody');
    const noResults = document.getElementById('no-results');
    const refreshBtn = document.getElementById('refresh-btn');

    // Modal DOM Elements
    const svgModal = document.getElementById('svg-modal');
    const svgModalBody = document.getElementById('svg-modal-body');
    const closeButtons = document.querySelectorAll('.close-modal');

    // Sliders
    const minCovSlider = document.getElementById('min-cov');
    const minCovVal = document.getElementById('min-cov-val');
    const pctExpSlider = document.getElementById('percent-expected');
    const pctExpVal = document.getElementById('percent-expected-val');
    const maxGenesSlider = document.getElementById('max-other-genes');
    const maxGenesVal = document.getElementById('max-other-genes-val');

    // Metadata
    const metadataBadge = document.getElementById('metadata-badge');
    const kaptiveVersion = document.getElementById('kaptive-version');
    const footerAuthors = document.getElementById('footer-authors');

    let queuedFiles = [];
    let currentJobId = null;
    let pollInterval = null;

    // --- 0. Fetch Metadata ---
    try {
        const metaRes = await fetch('/api/metadata');
        if (metaRes.ok) {
            const meta = await metaRes.json();
            kaptiveVersion.textContent = `v${meta.version}`;
            metadataBadge.classList.remove('is-hidden');
            footerAuthors.textContent = `by ${meta.author}`;
        }
    } catch (e) {
        console.warn('Could not load Kaptive metadata', e);
    }

    // --- 1. Sliders Logic ---
    function updateSliderValue(slider, displayElement, format = 'float') {
        const val = slider.value;
        if (format === 'float') {
            displayElement.textContent = parseFloat(val).toFixed(2);
        } else {
            displayElement.textContent = val;
        }
    }
    
    minCovSlider.addEventListener('input', () => updateSliderValue(minCovSlider, minCovVal, 'float'));
    pctExpSlider.addEventListener('input', () => updateSliderValue(pctExpSlider, pctExpVal, 'float'));
    maxGenesSlider.addEventListener('input', () => updateSliderValue(maxGenesSlider, maxGenesVal, 'int'));


    // --- 2. Drag & Drop Event Listeners ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const files = Array.from(e.dataTransfer.files);
        queueFiles(files);
    });

    // --- 3. Click-to-Browse Fallback ---
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        queueFiles(Array.from(e.target.files));
        fileInput.value = ''; // Reset input to allow selecting the same file again
    });

    // --- 4. Queue Management ---
    function queueFiles(files) {
        files.forEach(file => {
            if (file.size > 20 * 1024 * 1024) {
                alert(`${file.name} is too large (>20MB).`);
                return;
            }
            
            const validExts = ['.fasta', '.fas', '.fna', '.fa'];
            const isValidExt = validExts.some(ext => file.name.toLowerCase().endsWith(ext));
            if (!isValidExt) {
                alert(`${file.name} does not appear to be a FASTA file.`);
                return;
            }

            queuedFiles.push(file);

            const li = document.createElement('li');
            li.innerHTML = `
                <div class="is-flex is-justify-content-space-between is-align-items-center mb-1">
                    <span class="has-text-weight-medium"><i class="fas fa-file-alt has-text-grey-light mr-2"></i>${file.name}</span> 
                    <span class="has-text-grey">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                </div>
            `;
            fileListUI.appendChild(li);
        });

        if (queuedFiles.length > 0) {
            fileListContainer.classList.remove('is-hidden');
            submitBtn.disabled = false;
        }
    }

    // --- 5. The Concurrent Upload Logic ---
    jobForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (queuedFiles.length === 0) return;

        submitBtn.classList.add('is-loading');
        submitBtn.disabled = true;

        const formData = new FormData();
        queuedFiles.forEach(file => formData.append('files', file));
        
        formData.append('species', document.getElementById('species-select').value);
        formData.append('min_cov', minCovSlider.value);
        formData.append('percent_expected', pctExpSlider.value);
        formData.append('max_other_genes', maxGenesSlider.value);

        try {
            noResults.classList.add('is-hidden');
            resultsTableContainer.classList.add('is-hidden');
            refreshBtn.classList.add('is-hidden');
            statusContainer.classList.remove('is-hidden', 'is-success', 'is-danger', 'is-warning');
            statusContainer.classList.add('is-info');
            statusTitle.textContent = "Uploading Files";
            statusText.textContent = "Sending assemblies to server...";
            statusContainer.querySelector('.icon i').className = 'fas fa-cloud-upload-alt fa-2x';
            resultsTbody.innerHTML = '';

            const response = await fetch('/api/jobs/submit', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                currentJobId = result.job_id;
                statusTitle.textContent = "Processing Job";
                statusText.innerHTML = `Job ID: <code>${currentJobId.substring(0,8)}...</code>`;
                statusContainer.querySelector('.icon i').className = 'fas fa-circle-notch fa-spin fa-2x';
                startPolling(currentJobId);
            } else {
                throw new Error(result.detail || 'Upload failed');
            }
        } catch (error) {
            console.error("Upload failed", error);
            showErrorStatus(error.message);
            resetFormState();
        }
    });

    // --- 6. Polling for Job Status ---
    function startPolling(jobId) {
        if (pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/jobs/${jobId}/status`);
                const result = await response.json();

                if (response.ok) {
                    if (result.status === 'completed') {
                        clearInterval(pollInterval);
                        statusContainer.classList.replace('is-info', 'is-success');
                        statusTitle.textContent = "Job Completed!";
                        statusText.textContent = "Your typing results are ready.";
                        statusContainer.querySelector('.icon i').className = 'fas fa-check-circle fa-2x';
                        renderResults(result.data);
                        resetFormState(true);
                    } else if (result.status === 'failed') {
                        clearInterval(pollInterval);
                        showErrorStatus(result.error || 'Job failed during processing.');
                        resetFormState();
                    } else {
                        statusText.innerHTML = `Status: <strong>${result.status}</strong>...`;
                    }
                } else {
                    throw new Error(result.detail || 'Failed to fetch status');
                }
            } catch (error) {
                console.error("Polling failed", error);
                clearInterval(pollInterval);
                showErrorStatus(error.message);
                resetFormState();
            }
        }, 2000);
    }

    function showErrorStatus(message) {
        statusContainer.classList.replace('is-info', 'is-danger');
        statusContainer.classList.replace('is-success', 'is-danger');
        statusTitle.textContent = "Error";
        statusText.textContent = message;
        statusContainer.querySelector('.icon i').className = 'fas fa-exclamation-triangle fa-2x';
    }

    function resetFormState(clearFiles = false) {
        submitBtn.classList.remove('is-loading');
        
        if (clearFiles) {
            queuedFiles = [];
            fileListUI.innerHTML = '';
            fileListContainer.classList.add('is-hidden');
            submitBtn.disabled = true;
            fileInput.value = '';
        } else {
            submitBtn.disabled = queuedFiles.length === 0;
        }
    }

    // --- 7. Dynamic DOM Updates for Results ---
    function renderResults(data) {
        if (!data || data.length === 0) {
            resultsTbody.innerHTML = '<tr><td colspan="5" class="has-text-centered py-5 has-text-grey">No matches found.</td></tr>';
        } else {
            data.forEach(item => {
                const tr = document.createElement('tr');
                
                let confidenceClass = '';
                let confidenceText = item.confidence || 'Unknown';
                const confidenceLower = confidenceText.toLowerCase();
                
                if (confidenceLower === 'perfect') confidenceClass = 'confidence-Perfect';
                else if (confidenceLower === 'very high') confidenceClass = 'confidence-Very High';
                else if (confidenceLower === 'high') confidenceClass = 'confidence-High';
                else if (confidenceLower === 'good') confidenceClass = 'confidence-Good';
                else if (confidenceLower === 'low') confidenceClass = 'confidence-Low';
                else if (confidenceLower === 'none') confidenceClass = 'confidence-None';
                else confidenceClass = 'confidence-None';
                
                // Fallback class name handling
                const badgeClass = `confidence-badge ${confidenceClass.replace(' ', '.')}`;

                tr.innerHTML = `
                    <td class="is-vcentered"><span class="has-text-weight-medium">${item.assembly || 'Unknown'}</span></td>
                    <td class="is-vcentered"><span class="has-text-info-dark has-text-weight-bold">${item.match || 'N/A'}</span></td>
                    <td class="is-vcentered">${item.coverage ? (item.coverage * 100).toFixed(1) + '%' : 'N/A'}</td>
                    <td class="is-vcentered"><span class="${badgeClass}">${confidenceText}</span></td>
                    <td class="is-vcentered">
                        <button class="button is-small is-primary is-light view-svg-btn" data-assembly="${item.assembly}" data-match="${item.match}">
                            <span class="icon is-small"><i class="fas fa-project-diagram"></i></span>
                            <span>Diagram</span>
                        </button>
                    </td>
                `;
                
                resultsTbody.appendChild(tr);
            });

            document.querySelectorAll('.view-svg-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const assembly = e.currentTarget.dataset.assembly;
                    const match = e.currentTarget.dataset.match;
                    fetchAndShowSvg(currentJobId, assembly, match);
                });
            });
        }
        
        resultsTableContainer.classList.remove('is-hidden');
        refreshBtn.classList.remove('is-hidden');
        
        refreshBtn.onclick = () => {
            noResults.classList.remove('is-hidden');
            resultsTableContainer.classList.add('is-hidden');
            statusContainer.classList.add('is-hidden');
            refreshBtn.classList.add('is-hidden');
            resultsTbody.innerHTML = '';
        };
    }

    // --- 8. Modal & SVG Injection Logic ---
    async function fetchAndShowSvg(jobId, assembly, match) {
        svgModalBody.innerHTML = '<div class="is-flex is-justify-content-center is-align-items-center" style="min-height: 200px;"><span class="icon is-large has-text-primary"><i class="fas fa-spinner fa-pulse fa-3x"></i></span></div>';
        svgModal.classList.add('is-active');

        try {
            const response = await fetch(`/api/jobs/${jobId}/plot?assembly=${encodeURIComponent(assembly)}&match=${encodeURIComponent(match)}`);
            if (!response.ok) throw new Error(`Failed to load SVG (Status: ${response.status})`);
            
            const result = await response.json();
            
            svgModalBody.innerHTML = `<div class="notification is-info is-light">Plotly JSON structure received. Rendering logic would go here. ${result.message}</div>`;
            
        } catch (error) {
            console.error("Plotly load error", error);
            svgModalBody.innerHTML = `<div class="notification is-danger is-light">
                <span class="icon"><i class="fas fa-exclamation-triangle"></i></span>
                Error loading diagram: ${error.message}
            </div>`;
        }
    }

    function closeModal() {
        svgModal.classList.remove('is-active');
        setTimeout(() => {
            svgModalBody.innerHTML = '';
        }, 200);
    }

    closeButtons.forEach(btn => btn.addEventListener('click', closeModal));
    document.querySelector('.modal-background').addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && svgModal.classList.contains('is-active')) {
            closeModal();
        }
    });
});