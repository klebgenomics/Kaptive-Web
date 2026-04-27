document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileListUI = document.getElementById('file-list');
    const fileListContainer = document.getElementById('file-list-container');
    const jobForm = document.getElementById('job-form');
    const submitBtn = document.getElementById('submit-btn');
    
    // Results DOM Elements
    const statusContainer = document.getElementById('status-container');
    const statusText = document.getElementById('status-text');
    const resultsTableContainer = document.getElementById('results-table-container');
    const resultsTbody = document.getElementById('results-tbody');
    const noResults = document.getElementById('no-results');

    // Modal DOM Elements
    const svgModal = document.getElementById('svg-modal');
    const svgModalBody = document.getElementById('svg-modal-body');
    const closeButtons = document.querySelectorAll('.close-modal');

    let queuedFiles = [];
    let currentJobId = null;
    let pollInterval = null;

    // --- 1. Drag & Drop Event Listeners ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('has-background-white-ter');
            dropZone.style.borderColor = '#00d1b2'; // Bulma primary color
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('has-background-white-ter');
            dropZone.style.borderColor = '#dbdbdb';
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const files = Array.from(e.dataTransfer.files);
        queueFiles(files);
    });

    // --- 2. Click-to-Browse Fallback ---
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        queueFiles(Array.from(e.target.files));
        fileInput.value = ''; // Reset input to allow selecting the same file again
    });

    // --- 3. Queue Management ---
    function queueFiles(files) {
        files.forEach(file => {
            // Basic frontend validation to match our backend logic (e.g., 20MB limit)
            if (file.size > 20 * 1024 * 1024) {
                alert(`${file.name} is too large (>20MB).`);
                return;
            }
            
            // Check extension
            const validExts = ['.fasta', '.fas', '.fna', '.fa'];
            const isValidExt = validExts.some(ext => file.name.toLowerCase().endsWith(ext));
            if (!isValidExt) {
                alert(`${file.name} does not appear to be a FASTA file.`);
                return;
            }

            queuedFiles.push(file);

            // Add to the visual list
            const li = document.createElement('li');
            li.innerHTML = `<span>${file.name}</span> <span class="has-text-grey">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>`;
            fileListUI.appendChild(li);
        });

        if (queuedFiles.length > 0) {
            fileListContainer.classList.remove('is-hidden');
            submitBtn.disabled = false;
        }
    }

    // --- 4. The Concurrent Upload Logic ---
    jobForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // SPA behavior: No hard reload
        
        if (queuedFiles.length === 0) return;

        submitBtn.classList.add('is-loading');
        submitBtn.disabled = true;

        const formData = new FormData();
        queuedFiles.forEach(file => formData.append('files', file));
        
        formData.append('species', document.getElementById('species-select').value);
        formData.append('min_cov', document.getElementById('min-cov').value);
        formData.append('percent_expected', document.getElementById('percent-expected').value);
        formData.append('max_other_genes', document.getElementById('max-other-genes').value);

        try {
            // Reset UI for new job
            noResults.classList.add('is-hidden');
            resultsTableContainer.classList.add('is-hidden');
            statusContainer.classList.remove('is-hidden', 'is-success', 'is-danger');
            statusContainer.classList.add('is-info');
            statusText.textContent = "Uploading files...";
            resultsTbody.innerHTML = ''; // Clear old results

            const response = await fetch('/api/jobs/submit', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                currentJobId = result.job_id;
                statusText.innerHTML = `<strong>Job ${currentJobId} submitted.</strong> Processing...`;
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

    // --- 5. Polling for Job Status ---
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
                        statusText.innerHTML = `<strong>Job Completed!</strong>`;
                        renderResults(result.data);
                        resetFormState(true);
                    } else if (result.status === 'failed') {
                        clearInterval(pollInterval);
                        showErrorStatus(result.error || 'Job failed during processing.');
                        resetFormState();
                    } else {
                        // Processing or queued
                        statusText.textContent = `Status: ${result.status}...`;
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
        }, 2000); // Poll every 2 seconds
    }

    function showErrorStatus(message) {
        statusContainer.classList.replace('is-info', 'is-danger');
        statusText.textContent = `Error: ${message}`;
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

    // --- 6. Dynamic DOM Updates for Results ---
    function renderResults(data) {
        if (!data || data.length === 0) {
            resultsTbody.innerHTML = '<tr><td colspan="5" class="has-text-centered">No matches found.</td></tr>';
        } else {
            // Expected data format: Array of objects
            // { assembly: "file.fasta", match: "KL1", coverage: 0.99, confidence: "Perfect", svg_url: "/api/svg/..." }
            
            data.forEach(item => {
                const tr = document.createElement('tr');
                
                // Color coding confidence
                let confidenceClass = '';
                let confidenceText = item.confidence || 'Unknown';
                const confidenceLower = confidenceText.toLowerCase();
                
                if (confidenceLower === 'perfect') confidenceClass = 'is-success';
                else if (confidenceLower === 'very high' || confidenceLower === 'high') confidenceClass = 'is-info';
                else if (confidenceLower === 'good') confidenceClass = 'is-primary';
                else if (confidenceLower === 'low') confidenceClass = 'is-warning';
                else if (confidenceLower === 'none') confidenceClass = 'is-danger';
                else confidenceClass = 'is-light';
                
                const confidenceTag = `<span class="tag ${confidenceClass}">${confidenceText}</span>`;

                tr.innerHTML = `
                    <td class="is-vcentered"><strong>${item.assembly || 'Unknown'}</strong></td>
                    <td class="is-vcentered">${item.match || 'N/A'}</td>
                    <td class="is-vcentered">${item.coverage ? (item.coverage * 100).toFixed(1) + '%' : 'N/A'}</td>
                    <td class="is-vcentered">${confidenceTag}</td>
                    <td class="is-vcentered">
                        <button class="button is-small is-outlined is-link view-svg-btn" data-assembly="${item.assembly}" data-match="${item.match}">
                            <span class="icon is-small"><i class="fas fa-eye"></i></span>
                            <span>View Diagram</span>
                        </button>
                    </td>
                `;
                
                resultsTbody.appendChild(tr);
            });

            // Attach event listeners to new buttons
            document.querySelectorAll('.view-svg-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const assembly = e.currentTarget.dataset.assembly;
                    const match = e.currentTarget.dataset.match;
                    fetchAndShowSvg(currentJobId, assembly, match);
                });
            });
        }
        
        resultsTableContainer.classList.remove('is-hidden');
    }

    // --- 7. Modal & SVG Injection Logic ---
    async function fetchAndShowSvg(jobId, assembly, match) {
        svgModalBody.innerHTML = '<span class="icon is-large"><i class="fas fa-spinner fa-spin fa-2x"></i></span><p class="mt-2">Loading diagram...</p>';
        svgModal.classList.add('is-active');

        try {
            // Adjust this URL to match actual API endpoint for retrieving the raw SVG string
            const response = await fetch(`/api/jobs/${jobId}/svg?assembly=${encodeURIComponent(assembly)}&match=${encodeURIComponent(match)}`);
            if (!response.ok) throw new Error(`Failed to load SVG (Status: ${response.status})`);
            
            const svgContent = await response.text();
            
            // Inject directly into modal body
            svgModalBody.innerHTML = svgContent;
            
            // Optional: style the injected SVG to fit the modal
            const svgElement = svgModalBody.querySelector('svg');
            if (svgElement) {
                svgElement.style.maxWidth = '100%';
                svgElement.style.height = 'auto';
            }
            
        } catch (error) {
            console.error("SVG load error", error);
            svgModalBody.innerHTML = `<div class="notification is-danger is-light">
                <span class="icon"><i class="fas fa-exclamation-triangle"></i></span>
                Error loading diagram: ${error.message}
            </div>`;
        }
    }

    // Close Modal Logic
    function closeModal() {
        svgModal.classList.remove('is-active');
        // Small delay to allow fade out if any before clearing
        setTimeout(() => {
            svgModalBody.innerHTML = '';
        }, 200);
    }

    closeButtons.forEach(btn => btn.addEventListener('click', closeModal));
    
    // Close modal on background click
    document.querySelector('.modal-background').addEventListener('click', closeModal);
    
    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && svgModal.classList.contains('is-active')) {
            closeModal();
        }
    });
});