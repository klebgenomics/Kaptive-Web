const urlParams = new URLSearchParams(window.location.search);
const jobId = urlParams.get('job_id');

document.getElementById('ui-token').textContent = jobId;

// --- 1. Polling Logic ---
async function pollJobStatus() {
    try {
        const response = await fetch(`/api/jobs/${jobId}/status`);
        const data = await response.json();

        document.getElementById('ui-status').textContent = data.status;

        if (data.status === "Finished") {
            renderResults(data.results);
        } else if (data.status === "Failed") {
            document.getElementById('ui-status').innerHTML = `<span style="color:red">Failed: ${data.error_message}</span>`;
        } else {
            // Check again in 2 seconds
            setTimeout(pollJobStatus, 2000);
        }
    } catch (err) {
        console.error("Error polling status", err);
    }
}

// --- 2. Rendering the Tabs and Tables ---
function renderResults(resultsData) {
    document.getElementById('tabs-container').style.display = 'block';
    const headerContainer = document.getElementById('tab-headers');
    const bodyContainer = document.getElementById('tab-bodies');

    // Assuming resultsData is an object grouped by database:
    // { "K_Locus": [results...], "O_Locus": [results...] }
    const databases = Object.keys(resultsData);

    databases.forEach((dbName, index) => {
        // Create Tab Button
        const btn = document.createElement('button');
        btn.className = `tab-btn ${index === 0 ? 'active' : ''}`;
        btn.textContent = dbName;
        btn.onclick = () => switchTab(dbName);
        headerContainer.appendChild(btn);

        // Create Tab Content Box
        const content = document.createElement('div');
        content.id = `tab-${dbName}`;
        content.className = `tab-content ${index === 0 ? 'active' : ''}`;

        // Build the result table for this database
        content.appendChild(buildResultTable(resultsData[dbName], dbName));
        bodyContainer.appendChild(content);
    });
}

function buildResultTable(assemblyResults, dbName) {
    const table = document.createElement('table');
    table.innerHTML = `
        <thead>
            <tr class="bg-header">
                <th>Sample</th>
                <th>Best Match</th>
                <th>Confidence</th>
                <th>Coverage</th>
                <th>Identity</th>
                <th>Visualization</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;
    const tbody = table.querySelector('tbody');

    assemblyResults.forEach(res => {
        // Apply your specific color logic based on confidence
        const bgClass = res.confidence === "Typeable" ? "bg-typeable" : "bg-untypeable";
        const tr = document.createElement('tr');
        tr.className = bgClass;

        tr.innerHTML = `
            <td><strong>${res.sample_name}</strong></td>
            <td>${res.best_match}</td>
            <td>${res.confidence}</td>
            <td>${res.coverage}%</td>
            <td>${res.identity}%</td>
            <td>
                <button onclick="openDiagram('${res.sample_name}', '${dbName}')">
                    View Diagram
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    return table;
}

// --- 3. Tab Switching Logic ---
function switchTab(targetDb) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`tab-${targetDb}`).classList.add('active');
}

// --- 4. Modal and Diagram Handling ---
const modal = document.getElementById('diagram-modal');
document.getElementById('close-modal').onclick = () => modal.close();

async function openDiagram(sampleName, dbName) {
    modal.showModal();
    const contentDiv = document.getElementById('modal-content');
    document.getElementById('modal-title').textContent = `${dbName} Diagram - ${sampleName}`;
    contentDiv.innerHTML = "<em>Rendering matplotlib diagram...</em>";

    try {
        // Fetch the SVG natively from a new FastAPI endpoint
        const response = await fetch(`/api/jobs/${jobId}/diagram?sample=${sampleName}&db=${dbName}`);
        const svgText = await response.text();
        contentDiv.innerHTML = svgText; // Inject the raw SVG directly into the DOM
    } catch (err) {
        contentDiv.innerHTML = "<span style='color:red'>Failed to load diagram.</span>";
    }
}

// Start polling when the page loads
pollJobStatus();