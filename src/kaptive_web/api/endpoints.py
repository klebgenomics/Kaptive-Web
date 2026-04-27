import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from kaptive_plot import KaptivePlotter
from sqlalchemy.orm import Session

from kaptive_web.api.auth import get_current_user
from kaptive_web.api.schemas import JobStatusResponse, JobSubmitResponse
from kaptive_web.models.database import Job, User, get_db
from kaptive_web.services.cache import KaptiveDatabaseCache
from kaptive_web.services.runner import KaptiveRunner

# Constants ------------------------------------------------------------------------------------------------------------
UPLOAD_BASE_DIR = Path("/tmp/kaptive_uploads")

# Init router ----------------------------------------------------------------------------------------------------------
router = APIRouter()

# Routers --------------------------------------------------------------------------------------------------------------
@router.post("/api/jobs/submit", response_model=JobSubmitResponse)
async def submit_job(
        background_tasks: BackgroundTasks,
        species: str = Form(...),
        min_cov: float = Form(90.0),
        percent_expected: float = Form(100.0),
        max_other_genes: int = Form(0),
        files: list[UploadFile] = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_BASE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    saved_files = []

    for file in files:
        file_path = job_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(str(file_path))

    # Determine which databases to run based on the species
    species_db_map = {
        "Klebsiella pneumoniae": {"K_Locus": "k_db.gbk", "O_Locus": "o_db.gbk"},
        "Acinetobacter baumannii": {"K_Locus": "aba_k_db.gbk", "OC_Locus": "aba_oc_db.gbk"}
    }
    databases_to_run = species_db_map.get(species, {})

    new_job = Job(
        id=job_id, 
        species=species, 
        status="Pending", 
        user_id=current_user.id if current_user else None
    )
    db.add(new_job)
    db.commit()

    runner = KaptiveRunner(db_session=db, job_id=job_id)
    background_tasks.add_task(runner.execute, saved_files, databases_to_run, min_cov, percent_expected, max_other_genes)

    return JobSubmitResponse(
        job_id=job_id,
        status="Pending",
        species=species,
        assemblies_queued=len(saved_files),
        databases_to_run=list(databases_to_run.keys()),
        message="Assemblies queued successfully."
    )


@router.get("/api/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Returns the parsed Pydantic object, containing the exact metrics for the UI."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    data = []
    if job.results:
        for db_name, assemblies in job.results.items():
            for asm in assemblies:
                data.append({
                    "assembly": asm["sample_name"],
                    "match": asm["best_match"],
                    "coverage": asm["coverage"] / 100.0 if asm["coverage"] > 1 else asm["coverage"],
                    "confidence": asm["confidence"]
                })
                
    return {"status": job.status, "data": data, "error": job.error_message}


@router.get("/api/users/me/jobs")
async def get_user_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Protected endpoint returning historical jobs for the authenticated user."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
        
    jobs = db.query(Job).filter(Job.user_id == current_user.id).all()
    return [
        {
            "id": j.id, 
            "status": j.status, 
            "species": j.species, 
            "start_time": j.start_time
        } 
        for j in jobs
    ]


@router.get("/api/jobs/{job_id}/plot")
async def get_job_plot(job_id: str, db: Session = Depends(get_db)):
    """Fetches the TypingResult and returns the KaptivePlotter Plotly figure as JSON."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or not job.results:
        raise HTTPException(status_code=404, detail="Job or results not found")
        
    try:
        # Determine the correct DB based on species 
        species_db_map = {
            "Klebsiella pneumoniae": "k_db.gbk",
            "Acinetobacter baumannii": "aba_k_db.gbk"
        }
        db_path = species_db_map.get(job.species, "k_db.gbk")
        kaptive_db = KaptiveDatabaseCache.get_db(db_path)
        
        plotter = KaptivePlotter(kaptive_db)
        
        # MOCK: Assuming we retrieved the full TypingResult 
        # actual_result = rehydrate_typing_result(job.results[0])
        # fig = plotter.plotly(actual_result)
        # return JSONResponse(content=json.loads(fig.to_json()))
        
        return JSONResponse(content={"message": "Plotly Figure JSON", "job": job_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/api/metadata")
# async def get_metadata():
#     from kaptive_web import _METADATA, _KAPTIVE_METADATA
#     # Extract desired fields
#     return {
#         "name": dist.get("Name", "Kaptive"),
#         "version": dist.get("Version", "Unknown"),
#         "summary": dist.get("Summary", ""),
#         "author": dist.get("Author", "Unknown"),
#         "keywords": dist.get("Keywords", ""),
#     }
