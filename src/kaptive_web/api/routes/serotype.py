import os
import tempfile
import orjson
from typing import List
import io
import gzip
import zipfile

import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import Response

from kaptive_web.core.responses import KaptiveORJSONResponse
from kaptive_web.api.routes.auth import get_current_user, get_repository
from kaptive_web.db.repository import Repository, User
from kaptive_web.services.pipeline import process_genomes
from kaptive_web.core.state import state

from kaptive.serotyping import SerotypingResult, KaptiveRow
from kaptive.plotting import SerotypingResultPlotter, LocusComparisonPlotter
from kaptive.compare import LocusComparator


router = APIRouter(prefix="/serotype", tags=["serotyping"])

# Global memory cache for ephemeral locus comparison tasks
comparison_tasks = {}

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
            "doi": meta.doi,
            "antigen": meta.antigen,
            "pathway": meta.pathway,
            "loci_count": len(db.loci),
            "genes_count": len(db.genes),
            "contact": meta.contact
        })
        
    return db_info

class CompareRequest(BaseModel):
    run_id: str
    genome_ids: list[str]
    database_key: str
    dark_mode: bool = False
    show_all_links: bool = False

async def run_locus_comparison_task(task_id: str, run_id: str, genome_ids: list[str], database_key: str, dark_mode: bool, show_all_links: bool, repo: Repository):
    try:
        results = await repo.get_run_results(run_id)
        # Filter to requested genomes
        target_results = [r for r in results if r.genome_id in genome_ids]
        
        # Parse into SerotypingResult objects
        serotyping_results = []
        for r in target_results:
            parsed = orjson.loads(r.results_json)
            if database_key in parsed:
                res = SerotypingResult.from_dict(parsed[database_key])
                serotyping_results.append(res)
        
        comparison_tasks[task_id]["progress"] = 25.0
        
        if len(serotyping_results) < 2:
            comparison_tasks[task_id]["status"] = "failed"
            comparison_tasks[task_id]["error"] = "Not enough valid results found for comparison."
            return
            
        loci = []
        backbones = []
        names = []
        locus_pieces = []
        gene_ctg_indices = []
        
        for res in serotyping_results:
            mask = res.gene_hits.is_inside & ~res.gene_hits.is_extra
            loci.append(res.translations[mask])
            backbones.append(res.gene_hits.t_intervals[mask])
            gene_ctg_indices.append(res.gene_hits.t_indices[mask])
            names.append(res.genome)
            locus_pieces.append(res.locus_pieces)
        
        comparison_tasks[task_id]["progress"] = 50.0
        
        comparator = LocusComparator()
        comparisons = comparator(
            loci, 
            locus_names=names, 
            backbones=backbones, 
            locus_pieces=locus_pieces,
            gene_ctg_indices=gene_ctg_indices
        )
        
        comparison_tasks[task_id]["progress"] = 75.0
        
        plotter = LocusComparisonPlotter()
        fig = plotter(comparisons=comparisons, dark_mode=dark_mode, show_all_links=show_all_links)
        
        comparison_tasks[task_id]["progress"] = 100.0
        comparison_tasks[task_id]["status"] = "completed"
        comparison_tasks[task_id]["result"] = orjson.loads(fig.to_json())
        
    except Exception as e:
        comparison_tasks[task_id]["status"] = "failed"
        comparison_tasks[task_id]["error"] = str(e)


@router.post("/compare")
async def start_comparison(
    req: CompareRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    run = await repo.get_run(req.run_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized or run not found.")
        
    task_id = str(uuid.uuid4())
    comparison_tasks[task_id] = {
        "status": "running",
        "progress": 0.0,
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(
        run_locus_comparison_task,
        task_id=task_id,
        run_id=req.run_id,
        genome_ids=req.genome_ids,
        database_key=req.database_key,
        dark_mode=req.dark_mode,
        show_all_links=req.show_all_links,
        repo=repo
    )
    
    return {"task_id": task_id}


@router.get("/compare/{task_id}")
async def get_comparison_status(task_id: str):
    if task_id not in comparison_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return comparison_tasks[task_id]


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
    
    # Manually construct JSON to bypass parsing overhead
    json_parts = []
    for res in results:
        genome_id_json = orjson.dumps(res.genome_id).decode('utf-8')
        json_parts.append(f"{genome_id_json}: {res.results_json}")
        
    final_json = "{" + ",".join(json_parts) + "}"
    
    return Response(content=f'{{"run_id": "{run.id}", "status": "{run.status}", "species": "{run.species}", "created_at": "{run.created_at}", "total_genomes": {run.total_genomes}, "completed_genomes": {len(results)}, "results": {final_json}}}', media_type="application/json")

@router.get("/results", response_class=KaptiveORJSONResponse)
async def get_all_results(
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Fetches a flattened, time-sorted list of all genome results for the current user."""
    results = await repo.get_all_results_for_user(current_user.id)
    runs = await repo.get_runs_for_user(current_user.id)
    run_species_map = {run.id: run.species for run in runs}
    
    # Parse results_json and structure into a flat list manually for massive performance boost
    json_parts = []
    for res in results:
        species = run_species_map.get(res.run_id, "Unknown")
        genome_id_json = orjson.dumps(res.genome_id).decode('utf-8')
        completed_at_json = orjson.dumps(res.completed_at).decode('utf-8')
        run_id_json = orjson.dumps(res.run_id).decode('utf-8')
        species_json = orjson.dumps(species).decode('utf-8')
        
        row_json = f'{{"genome_id": {genome_id_json}, "completed_at": {completed_at_json}, "run_id": {run_id_json}, "species": {species_json}, "databases": {res.results_json}}}'
        json_parts.append(row_json)
        
    final_json = "[" + ",".join(json_parts) + "]"
    return Response(content=final_json, media_type="application/json")

async def get_target_serotyping_result(
    run_id: str,
    genome_id: str,
    database_key: str,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository)
):
    """Reusable dependency to extract and deserialize a specific SerotypingResult."""
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

    try:
        return SerotypingResult.from_dict(parsed_json[database_key])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deserialize result: {str(e)}")

@router.get("/plot/{run_id}/{genome_id}/{database_key}", response_class=KaptiveORJSONResponse)
async def get_plot(dark_mode: bool = False, result_obj = Depends(get_target_serotyping_result)):
    """Generates a Plotly JSON schema for the frontend."""
    plotter = SerotypingResultPlotter()
    fig = plotter(result_obj, dark_mode=dark_mode)

    return orjson.loads(fig.to_json())

@router.get("/plot/{run_id}/{genome_id}/{database_key}/summary", response_class=KaptiveORJSONResponse)
async def get_summary(result_obj = Depends(get_target_serotyping_result)):
    """Generates a text summary for the frontend."""
    return {"summary": result_obj.to_summary()}

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
    
    # Manually construct JSON to bypass massive parsing overhead
    json_parts = []
    for res in results:
        genome_id_json = orjson.dumps(res.genome_id).decode('utf-8')
        json_parts.append(f"{genome_id_json}: {res.results_json}")
        
    final_json = "{\n  " + ",\n  ".join(json_parts) + "\n}"
    json_bytes = final_json.encode('utf-8')
    
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="results_{run_id}.json"'}
    )

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
            tsv_buf.write(KaptiveRow.header())
            tsv_buf.write(''.join(bytes(KaptiveRow.from_result(r, evaluator(r))) for r in result_list))
            # Write bytes to zip archive
            zf.writestr(f"kaptive_results_{db_key}.tsv", tsv_buf.getvalue())
            
    zip_buf.seek(0)
    
    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="kaptive_results_tsv.zip"'}
    )

