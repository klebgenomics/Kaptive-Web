# Kaptive Web API Reference

The Kaptive Web API allows programmatic access to the serotyping engine and your account's history.

## Authentication

Endpoints require authentication via session cookie (web frontend) or by providing an API key in the `X-API-Key` header.

## Endpoints

### Authentication

- `GET /auth/github/login` - Initiate GitHub OAuth login.
- `GET /auth/orcid/login` - Initiate ORCID OAuth login.
- `GET /auth/user` - Get current user details and API key.
- `POST /auth/logout` - Logout and clear session.
- `DELETE /auth/account` - Delete your account and all history.
- `POST /auth/api-key` - Generate a new API key.

### Serotyping

- `POST /serotype/run` - Upload and analyze genome assemblies (FASTA/GZ). Returns a JSON object with a unique `run_id`.
- `GET /serotype/run/{run_id}` - Retrieve the status and results of a serotyping run.
- `GET /serotype/run/{run_id}/{genome_id}` - Retrieve the `SerotypingResult` JSON object for a specific genome in a run.
- `GET /serotype/history` - Retrieve your account's history of serotyping runs.
- `DELETE /serotype/run/{run_id}` - Delete a serotyping run from your history.

### Downloads and Export

- `POST /serotype/run/{run_id}/download` - Download results for specific genomes as JSON.
- `GET /serotype/run/{run_id}/download/json` - Download all results for a run as JSON.
- `GET /serotype/run/{run_id}/download/tsv` - Download Kaptive standard TSV report.
- `GET /serotype/run/{run_id}/download/pha4ge` - Download PHA4GE standard TSV report.

### Visualization

- `GET /serotype/run/{run_id}/{genome_id}/plot/{database_key}` - Get Plotly JSON figure for a specific locus.
- `GET /serotype/run/{run_id}/{genome_id}/summary/{database_key}` - Get markdown summary for a specific locus.
- `POST /serotype/compare` - Compare multiple loci side-by-side.
- `GET /serotype/compare/{task_id}/plot` - Get Plotly JSON figure for the comparison.
