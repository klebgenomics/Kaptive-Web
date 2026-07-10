/**
 * API wrapper for communicating with Kaptive-Web backend.
 */
class KaptiveAPI {
    constructor() {
        this.baseUrl = window.location.origin;
        // Simple LRU cache for Plotly JSON to avoid memory bloat and network latency
        this.plotCache = new Map();
        this.MAX_CACHE_SIZE = 50;
    }

    async getVersion() {
        try {
            const res = await fetch(`${this.baseUrl}/api/version`);
            if (!res.ok) return null;
            return await res.json();
        } catch (e) {
            return null;
        }
    }

    getApiKey() {
        return localStorage.getItem('kaptive_api_key');
    }

    setApiKey(key) {
        localStorage.setItem('kaptive_api_key', key);
    }

    clearApiKey() {
        localStorage.removeItem('kaptive_api_key');
    }

    getHeaders(isFormData = false) {
        const key = this.getApiKey();
        if (!key) throw new Error("No API key found.");
        const headers = {
            'X-API-Key': key
        };
        if (!isFormData) {
            headers['Content-Type'] = 'application/json';
        }
        return headers;
    }

    async testAuth() {
        // If we can fetch results, auth works
        try {
            const res = await fetch(`${this.baseUrl}/serotype/results`, { headers: this.getHeaders() });
            if (res.status === 401 || res.status === 403) return false;
            return true;
        } catch (e) {
            return false;
        }
    }

    async getMe() {
        const res = await fetch(`${this.baseUrl}/auth/me`, { headers: this.getHeaders() });
        if (!res.ok) throw new Error(`Auth Error: ${res.status}`);
        return await res.json();
    }

    async deleteMe() {
        const res = await fetch(`${this.baseUrl}/auth/me`, { 
            method: 'DELETE', 
            headers: this.getHeaders() 
        });
        if (!res.ok) throw new Error(`Delete Error: ${res.status}`);
        return await res.json();
    }

    async getSpecies() {
        const res = await fetch(`${this.baseUrl}/serotype/species`);
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        return await res.json();
    }

    async getDatabases(species) {
        const res = await fetch(`${this.baseUrl}/serotype/databases/${encodeURIComponent(species)}`);
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        return await res.json();
    }

    async uploadGenomes(species, formData) {
        const res = await fetch(`${this.baseUrl}/serotype/${encodeURIComponent(species)}`, {
            method: 'POST',
            headers: this.getHeaders(true),
            body: formData
        });
        if (!res.ok) throw new Error(`Upload Error: ${res.status}`);
        return await res.json();
    }

    async checkRunStatus(runId) {
        const res = await fetch(`${this.baseUrl}/serotype/runs/${runId}`, {
            headers: this.getHeaders()
        });
        if (!res.ok) throw new Error(`Status Error: ${res.status}`);
        return await res.json();
    }

    async getResults() {
        const res = await fetch(`${this.baseUrl}/serotype/results`, { headers: this.getHeaders() });
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        return await res.json();
    }

    async getPlotJson(runId, genomeId, dbKey, darkMode = false) {
        const cacheKey = `${runId}_${genomeId}_${dbKey}_${darkMode}`;
        
        // LRU Cache hit
        if (this.plotCache.has(cacheKey)) {
            // Move to end to mark as recently used
            const data = this.plotCache.get(cacheKey);
            this.plotCache.delete(cacheKey);
            this.plotCache.set(cacheKey, data);
            return data;
        }

        // Cache miss, fetch from network
        const res = await fetch(`${this.baseUrl}/serotype/plot/${runId}/${genomeId}/${dbKey}?dark_mode=${darkMode}`, {
            headers: this.getHeaders()
        });
        
        if (!res.ok) throw new Error(`Plot API Error: ${res.status}`);
        
        const data = await res.json();
        
        // Add to cache
        this.plotCache.set(cacheKey, data);
        
        // Enforce max size
        if (this.plotCache.size > this.MAX_CACHE_SIZE) {
            // Delete oldest (first item in Map)
            const oldestKey = this.plotCache.keys().next().value;
            this.plotCache.delete(oldestKey);
        }
        
        return data;
    }

    async getPlotSummary(runId, genomeId, dbKey) {
        const cacheKey = `summary_${runId}_${genomeId}_${dbKey}`;
        
        if (this.plotCache.has(cacheKey)) {
            const data = this.plotCache.get(cacheKey);
            this.plotCache.delete(cacheKey);
            this.plotCache.set(cacheKey, data);
            return data;
        }

        const res = await fetch(`${this.baseUrl}/serotype/plot/${runId}/${genomeId}/${dbKey}/summary`, {
            headers: this.getHeaders()
        });
        
        if (!res.ok) throw new Error(`Summary API Error: ${res.status}`);
        
        const data = await res.json();
        
        this.plotCache.set(cacheKey, data);
        if (this.plotCache.size > this.MAX_CACHE_SIZE) {
            const oldestKey = this.plotCache.keys().next().value;
            this.plotCache.delete(oldestKey);
        }
        
        return data;
    }

    async startComparison(runId, genomeIds, dbKey, showAllLinks = false, darkMode = false) {
        const res = await fetch(`${this.baseUrl}/serotype/compare`, {
            method: 'POST',
            headers: {
                ...this.getHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                run_id: runId,
                genome_ids: genomeIds,
                database_key: dbKey,
                show_all_links: showAllLinks,
                dark_mode: darkMode
            })
        });
        if (!res.ok) {
            let errBody = "";
            try { errBody = await res.text(); } catch(e) {}
            throw new Error(`API Error: ${res.status} ${errBody}`);
        }
        return await res.json();
    }

    async getComparisonStatus(taskId) {
        const res = await fetch(`${this.baseUrl}/serotype/compare/${taskId}`, { headers: this.getHeaders() });
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        return await res.json();
    }

    async deleteResults(genomeIds) {
        const res = await fetch(`${this.baseUrl}/serotype/results/delete`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ genome_ids: genomeIds })
        });
        if (!res.ok) throw new Error(`Delete Error: ${res.status}`);
        return await res.json();
    }
}

// Export a singleton
const api = new KaptiveAPI();
