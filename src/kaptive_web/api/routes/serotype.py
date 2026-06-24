import os
import tempfile
import orjson
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException

from kaptive_web.core.responses import KaptiveORJSONResponse
from kaptive_web.api.routes.auth import get_current_user, get_repository
from kaptive_web.db.repository import Repository, User
from kaptive_web.services.pipeline import process_genomes
from kaptive_web.core.state import state

router = APIRouter(prefix="/serotype", tags=["serotyping"])

@router.get("/species", response_class=KaptiveORJSONResponse)
async def get_species():
    """Returns a list of all installed species."""
    return list(state.databases.keys())

@router.get("/databases/{species}", response_class=KaptiveORJSONResponse)
async def get_databases(species: str):
    """Fetches metadata for all loaded databases for a species."""
    if species not in state.databases:
        raise HTTPException(status_code=400, detail=f"Species '{species}' is not supported or initialized.")
        
    db_info = []
    for key, db in state.databases[species].items():
        meta = db.metadata
        db_info.append({
            "key": key,
            "name": meta.name,
            "version": meta.version,
            "organism": meta.organism,
            "doi": meta.doi
        })
        
    return db_info

@router.post("/{species}", response_class=KaptiveORJSONResponse)
async def submit_serotyping_job(
    species: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """
    Submits a batch of genome FASTA files for in silico serotyping.
    Saves files temporarily, creates a Run record, and launches a background task.
    """
    # Ensure the species pipeline is initialized
    try:
        state.get_pipeline(species)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Species '{species}' is not supported or initialized.")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    if len(files) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 files allowed per run.")

    # Create run record
    run = await repo.create_run(current_user.id, species, len(files))

    # Save uploaded files to temporary disk
    temp_dir = tempfile.gettempdir()
    file_paths = []
    
    for upload_file in files:
        # Use the original filename to track genome ID, fallback to something random
        filename = upload_file.filename or "unknown.fasta"
        temp_path = os.path.join(temp_dir, f"{run.id}_{filename}")
        
        with open(temp_path, "wb") as buffer:
            # chunked read from the spooled upload file
            while content := await upload_file.read(1024 * 1024):
                buffer.write(content)
                
        file_paths.append(temp_path)

    # Launch background task
    background_tasks.add_task(process_genomes, run.id, species, file_paths)

    return {
        "message": "Job submitted successfully.",
        "run_id": run.id,
        "status": run.status,
        "genome_count": len(files)
    }

@router.get("/runs", response_class=KaptiveORJSONResponse)
async def list_runs(
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Lists all past serotyping runs for the current user."""
    runs = await repo.get_runs_for_user(current_user.id)
    return runs

@router.get("/runs/{run_id}", response_class=KaptiveORJSONResponse)
async def get_run_results(
    run_id: str,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Fetches the status and detailed results for a specific run."""
    run = await repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
        
    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this run.")

    results = await repo.get_run_results(run_id)
    
    # We parse the results_json so it returns as a proper JSON object instead of a stringified string
    parsed_results = {res.genome_id: orjson.loads(res.results_json) for res in results}
    
    return {
        "run_id": run.id,
        "status": run.status,
        "species": run.species,
        "created_at": run.created_at,
        "total_genomes": run.total_genomes,
        "completed_genomes": len(results),
        "results": parsed_results
    }

@router.get("/results", response_class=KaptiveORJSONResponse)
async def get_all_results(
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Fetches a flattened, time-sorted list of all genome results for the current user."""
    results = await repo.get_all_results_for_user(current_user.id)
    runs = await repo.get_runs_for_user(current_user.id)
    run_species_map = {run.id: run.species for run in runs}
    
    # Parse results_json and structure into a flat list
    flattened_results = []
    for res in results:
        flattened_results.append({
            "genome_id": res.genome_id,
            "completed_at": res.completed_at,
            "run_id": res.run_id,
            "species": run_species_map.get(res.run_id, "Unknown"),
            "databases": orjson.loads(res.results_json)
        })
        
    return flattened_results

@router.get("/plot/{run_id}/{genome_id}/{database_key}", response_class=KaptiveORJSONResponse)
async def get_plot(
    run_id: str,
    genome_id: str,
    database_key: str,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Dynamically reconstructs a SerotypingResult and generates a Plotly JSON schema for the frontend."""
    # Ensure user owns the run
    run = await repo.get_run(run_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized or run not found.")

    # Get results for the run
    results = await repo.get_run_results(run_id)
    target_res = next((r for r in results if r.genome_id == genome_id), None)
    if not target_res:
        raise HTTPException(status_code=404, detail="Genome result not found.")

    parsed_json = orjson.loads(target_res.results_json)
    if database_key not in parsed_json:
        raise HTTPException(status_code=404, detail=f"Database {database_key} not found for this genome.")

    # Deserialize the dictionary back into a full SerotypingResult
    from kaptive.serotyping.serotyper import SerotypingResult
    try:
        result_obj = SerotypingResult.from_dict(parsed_json[database_key])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deserialize result: {str(e)}")

    # Generate the Plotly figure
    from kaptive.plotting import SerotypeResultPlotter
    plotter = SerotypeResultPlotter()
    fig = plotter(result_obj)

    return orjson.loads(fig.to_json())

from fastapi.responses import Response

@router.get("/runs/{run_id}/download/json")
async def download_run_json(
    run_id: str,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Generates a downloadable results.json file for a run using orjson."""
    run = await repo.get_run(run_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized or run not found.")

    results = await repo.get_run_results(run_id)
    
    # We use orjson to rapidly construct the JSON bytes
    parsed_results = {res.genome_id: ororjson.loads(res.results_json) for res in results}
    json_bytes = orjson.dumps(parsed_results, option=orjson.OPT_INDENT_2)
    
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="results_{run_id}.json"'}
    )



import io
import gzip
import zipfile
from pydantic import BaseModel
from fastapi.responses import Response, StreamingResponse
from kaptive.serotyping.serotyper import SerotypingResult
from kaptive.serotyping.io import TsvWriter, KaptiveRow

class DownloadRequest(BaseModel):
    genome_ids: list[str]

@router.post("/results/download/jsonl")
async def download_jsonl(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Generates a gzipped JSONL download for selected genomes."""
    results = await repo.get_all_results_for_user(current_user.id)
    runs = await repo.get_runs_for_user(current_user.id)
    run_species_map = {run.id: run.species for run in runs}
    
    # Filter by selected genomes
    selected_set = set(request.genome_ids)
    if selected_set:
        results = [r for r in results if r.genome_id in selected_set]
        
    def iter_jsonl():
        for res in results:
            data = {
                "genome_id": res.genome_id,
                "completed_at": res.completed_at,
                "run_id": res.run_id,
                "species": run_species_map.get(res.run_id, "Unknown"),
                "databases": orjson.loads(res.results_json)
            }
            yield orjson.dumps(data) + b"\n"
            
    # GZIP compress it in memory (or streaming if we wanted, but in-memory is fine for most outputs)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
        for chunk in iter_jsonl():
            gz.write(chunk)
            
    buf.seek(0)
    
    return Response(
        content=buf.getvalue(),
        media_type="application/gzip",
        headers={"Content-Disposition": 'attachment; filename="kaptive_results.jsonl.gz"'}
    )

@router.post("/results/download/tsv")
async def download_tsv(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Generates a zipped archive of TSVs for each database for selected genomes."""
    results = await repo.get_all_results_for_user(current_user.id)
    runs = await repo.get_runs_for_user(current_user.id)
    run_species_map = {run.id: run.species for run in runs}
    
    selected_set = set(request.genome_ids)
    if selected_set:
        results = [r for r in results if r.genome_id in selected_set]
        
    # Group SerotypingResults by database_key
    db_results = {} # dict[str, list[SerotypingResult]]
    db_evaluators = {}
    
    for res in results:
        species = run_species_map.get(res.run_id)
        if not species: continue
        
        parsed_json = orjson.loads(res.results_json)
        evaluator = state.get_evaluator(species)
        
        for db_key, db_dict in parsed_json.items():
            try:
                result_obj = SerotypingResult.from_dict(db_dict)
            except Exception:
                continue
                
            if db_key not in db_results:
                db_results[db_key] = []
                db_evaluators[db_key] = evaluator
                
            db_results[db_key].append(result_obj)
            
    # Write TSVs into memory buffers
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for db_key, result_list in db_results.items():
            tsv_buf = io.BytesIO()
            evaluator = db_evaluators[db_key]
            
            with TsvWriter(tsv_buf, KaptiveRow, evaluator) as writer:
                for r in result_list:
                    writer.write(r)
            
            # Write bytes to zip archive
            zf.writestr(f"kaptive_results_{db_key}.tsv", tsv_buf.getvalue())
            
    zip_buf.seek(0)
    
    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="kaptive_results_tsv.zip"'}
    )
