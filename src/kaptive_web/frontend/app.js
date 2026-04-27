const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileListUI = document.getElementById('file-list');
const submitBtn = document.getElementById('submit-btn');
const referenceDb = document.getElementById('reference-db');

let queuedFiles = [];

// --- 1. Drag & Drop Event Listeners ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault(); // Prevents the browser from just opening the file
    dropZone.classList.add('drag-over-active'); // Add a CSS class to highlight the box
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over-active');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over-active');

    // Grab the files from the drag event and add them to our queue
    const files = Array.from(e.dataTransfer.files);
    queueFiles(files);
});

// --- 2. Click-to-Browse Fallback ---
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => queueFiles(Array.from(e.target.files)));

// --- 3. Queue Management ---
function queueFiles(files) {
    files.forEach(file => {
        // Basic frontend validation to match our backend logic
        if (file.size > 20 * 1024 * 1024) {
            alert(`${file.name} is too large (>20MB).`);
            return;
        }
        queuedFiles.push(file);

        // Add to the visual list
        const li = document.createElement('li');
        li.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        fileListUI.appendChild(li);
    });

    if (queuedFiles.length > 0) submitBtn.disabled = false;
}

// --- 4. The Concurrent Upload Logic ---
submitBtn.addEventListener('click', async () => {
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    // FormData automatically formats a proper multipart/form-data request
    const formData = new FormData();

    // Append all files to the same 'files' key.
    // FastAPI's `List[UploadFile]` catches this automatically!
    queuedFiles.forEach(file => {
        formData.append('files', file);
    });
    formData.append('reference_db', referenceDb.value);

    try {
        const response = await fetch('/api/jobs/submit', {
            method: 'POST',
            body: formData // The browser handles the concurrent streaming of this payload
        });

        const result = await response.json();

        if (response.ok) {
            alert(`Success! Job ID: ${result.job_id}`);
            // Here you would redirect to your status page or start polling
        } else {
            alert(`Error: ${result.detail}`);
            submitBtn.disabled = false;
            submitBtn.textContent = "Submit Job";
        }
    } catch (error) {
        console.error("Upload failed", error);
    }
});