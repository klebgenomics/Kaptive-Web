"""Serotyping routes module."""

import re
import uuid
from collections.abc import Iterator
from typing import IO, Any, cast

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from kaptive.compare import LocusComparator
from kaptive.plotting import LocusComparisonPlotter, SerotypingResultPlotter
from kaptive.serotyping import GeneState, KaptiveRow, Pha4geRow, SerotypingProblem, SerotypingResult
from orjson import OPT_APPEND_NEWLINE, OPT_SERIALIZE_NUMPY, dumps, loads
from pydantic import BaseModel

from kaptive_web.api.routes.auth import get_current_user, get_repository
from kaptive_web.core.responses import KaptiveORJSONResponse
from kaptive_web.core.state import AppState
from kaptive_web.db.repository import Repository, User
from kaptive_web.services.pipeline import process_genomes

# Globals --------------------------------------------------------------------------------------------------------------
logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/serotype", tags=["serotyping"])

# Global memory cache for ephemeral locus comparison tasks
comparison_tasks = {}


# Models ---------------------------------------------------------------------------------------------------------------
class DownloadRequest(BaseModel):
    """Request model for downloading results."""

    genome_ids: list[str]


class CompareRequest(BaseModel):
    """Request model for comparison."""

    run_id: str
    genome_ids: list[str]
    database_key: str
    dark_mode: bool = False
    show_all_links: bool = False
    reference_loci: list[str] = []


# Functions ------------------------------------------------------------------------------------------------------------
def summarise_result(result: SerotypingResult) -> str:
    """Generates a markdown-formatted text report of the serotyping result."""
    lines = [
        f"**Genome:** {result.genome}",
        f"**Best Match:** {result.best_locus_name} ({'Typeable' if result.typeable else 'Untypeable'})",
        f"**Phenotype:** {result.phenotype or 'Unknown'}",
        "\n### Match Statistics",
        f"- **Score:** {result.best_locus_score:.2f}",
        f"- **Completeness:** {result.best_locus_completeness * 100:.2f}%",
        f"- **Coverage:** {result.percent_coverage:.2f}%",
        f"- **Identity:** {result.percent_identity:.2f}%",
        f"- **Length Discrepancy:** {result.length_discrepancy:.2f}"
        if result.length_discrepancy is not None
        else "- **Length Discrepancy:** N/A",
        "\n### Problems",
    ]

    problems = result.problems
    if problems == SerotypingProblem.NONE:
        lines.append("- None")
    else:
        if problems & SerotypingProblem.FRAGMENTED:
            lines.append(f"- Fragmented (found in {len(result.locus_pieces)} pieces)")
        if problems & SerotypingProblem.MISSING_GENES:
            lines.append("- Missing expected genes")
        if problems & SerotypingProblem.NOVEL_GENES:
            lines.append("- Novel genes present")
        if problems & SerotypingProblem.TRUNCATED_GENES:
            lines.append("- Truncated or partial genes present")
        if problems & SerotypingProblem.UNEXPECTED_GENES:
            lines.append("- Unexpected genes present")

    lines.append("\n### Gene Hits")

    state_names = {
        GeneState.PARTIAL.value: "Partial",
        GeneState.TRUNCATED.value: "Truncated",
        GeneState.NOVEL.value: "Novel",
    }

    # Sort genes by expected position
    expected_genes = []
    extra_genes = []

    for i in range(len(result.gene_hits)):
        name = result.gene_hits.gene_ids[i]
        identity = result.protein_identities[i]
        coverage = result.gene_hits.coverages[i]

        state_val = result.gene_states[i]
        if state_val == GeneState.NORMAL.value:
            state_str = ""
        else:
            state_str = f" (*{state_names.get(state_val, 'Unknown')}*)"

        s = result.gene_hits.t_starts[i]
        e = result.gene_hits.t_ends[i]
        strand = "+" if result.gene_hits.strands[i] > 0 else "-"
        coords = f"`{s}-{e} ({strand})`"

        line = f" - **{name}**: {identity:.1f}% ID, {coverage:.1f}% Cov, {coords}{state_str}"

        if result.gene_hits.is_expected[i]:
            expected_genes.append((result.gene_hits.expected_positions[i], line))
        else:
            extra_genes.append(line)

    # expected_genes.sort(key=lambda x: x[0])

    for _, line in expected_genes:
        lines.append(line)

    if result.missing_expected_genes:
        lines.append("\n### Missing Expected Genes")
        for gene in result.missing_expected_genes:
            lines.append(f"- **{gene}**: Missing")

    if extra_genes:
        lines.append("\n### Extra/Unexpected Genes")
        for line in extra_genes:
            lines.append(line)

    lines.append("\n### Locus Coordinates")
    for i in range(len(result.locus_pieces)):
        ctg = result.locus_seqs.ids[i]
        s = result.locus_pieces.starts[i]
        e = result.locus_pieces.ends[i]
        strand = "+" if result.locus_pieces.strands[i] > 0 else "-"
        lines.append(f"- **Piece {i + 1}**: `{ctg}` at `{s}-{e} ({strand})`")

    return "\n".join(lines)


async def run_locus_comparison_task(
    task_id: str,
    run_id: str,
    genome_ids: list[str],
    database_key: str,
    dark_mode: bool,
    show_all_links: bool,
    reference_loci: list[str],
    repo: Repository,
) -> None:
    """Run locus comparison task in background."""
    try:
        results = await repo.get_run_results(run_id)
        # Filter to requested genomes
        target_results = [r for r in results if r.genome_id in genome_ids]

        # Parse into SerotypingResult objects
        serotyping_results = []
        for r in target_results:
            parsed = loads(r.results_json)
            if database_key in parsed:
                res = SerotypingResult.from_dict(parsed[database_key])
                serotyping_results.append(res)

        comparison_tasks[task_id]["progress"] = 25.0

        if len(serotyping_results) < 2:
            comparison_tasks[task_id]["status"] = "failed"
            comparison_tasks[task_id]["error"] = "Not enough valid results found for comparison."
            return

        # Extract generalized locus data
        locus_inputs = [res.to_locus_data() for res in serotyping_results]

        # Include reference loci from the database
        run = await repo.get_run(run_id)
        if run and run.species in AppState.databases and database_key in AppState.databases[run.species]:
            db = AppState.databases[run.species][database_key]

            ref_locus_names = set(reference_loci or [])

            for loc_name in ref_locus_names:
                try:
                    locus_inputs.append(db.get_locus_data(loc_name))
                except ValueError:
                    pass

        comparison_tasks[task_id]["progress"] = 50.0

        comparator = LocusComparator()
        comparisons = comparator(locus_inputs)

        comparison_tasks[task_id]["progress"] = 75.0

        plotter = LocusComparisonPlotter()
        fig = plotter(comparisons=comparisons, dark_mode=dark_mode, show_all_links=show_all_links)

        comparison_tasks[task_id]["progress"] = 100.0
        comparison_tasks[task_id]["status"] = "completed"
        comparison_tasks[task_id]["result"] = loads(fig.to_json())

    except Exception as e:
        comparison_tasks[task_id]["status"] = "failed"
        comparison_tasks[task_id]["error"] = str(e)


async def get_target_serotyping_result(
    run_id: str,
    genome_id: str,
    database_key: str,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> SerotypingResult:
    """Reusable dependency to extract and deserialize a specific SerotypingResult."""
    run = await repo.get_run(run_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized or run not found.")

    # Get results for the run
    results = await repo.get_run_results(run_id)
    target_res = next((r for r in results if r.genome_id == genome_id), None)
    if not target_res:
        raise HTTPException(status_code=404, detail="Genome result not found.")

    parsed_json = loads(target_res.results_json)
    if database_key not in parsed_json:
        raise HTTPException(
            status_code=404,
            detail=f"Database {database_key} not found for this genome.",
        )

    try:
        return SerotypingResult.from_dict(parsed_json[database_key])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deserialize result: {str(e)}")


# Router GET -----------------------------------------------------------------------------------------------------------
@router.get("/species", response_class=KaptiveORJSONResponse)
async def get_species() -> list[str]:
    """Returns a list of all installed species."""
    return list(AppState.databases.keys())


@router.get("/databases/{species}", response_class=KaptiveORJSONResponse)
async def get_databases(species: str) -> list[dict[str, Any]]:
    """Fetches metadata for all loaded databases for a species."""
    if species not in AppState.databases:
        raise HTTPException(status_code=400, detail=f"Species '{species}' is not supported or initialized.")

    db_info = []
    for key, db in AppState.databases[species].items():
        meta = db.metadata
        db_info.append(
            {
                "key": key,
                "name": meta.name,
                "version": meta.version,
                "organism": meta.organism,
                "doi": meta.doi,
                "antigen": meta.antigen,
                "pathway": meta.pathway,
                "loci_count": len(db.loci),
                "genes_count": len(db.genes),
                "contact": meta.contact,
                "loci_names": list(db.loci.ids),
            }
        )

    return db_info


@router.get("/runs", response_class=KaptiveORJSONResponse)
async def list_runs(
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> list[Any]:
    """Lists all past serotyping runs for the current user."""
    runs = await repo.get_runs_for_user(current_user.id)
    return runs


@router.get("/runs/{run_id}", response_class=KaptiveORJSONResponse)
async def get_run_results(
    run_id: str,
    include_results: bool = False,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> Response:
    """Fetches the status and optionally detailed results for a specific run."""
    run = await repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this run.")

    if not include_results:
        count = await repo.count_run_results(run_id)
        meta = {
            "run_id": run.id,
            "status": run.status,
            "species": run.species,
            "created_at": run.created_at,
            "total_genomes": run.total_genomes,
            "completed_genomes": count,
        }
        return Response(content=dumps(meta), media_type="application/json")

    results = await repo.get_run_results(run_id)

    # Manually construct JSON using lightning-fast byte concatenation
    results_bytes = b"{%b}" % b",".join(b"%b: %b" % (dumps(r.genome_id), r.results_json) for r in results)

    # Construct metadata bytes, strip the closing '}', and attach our results mapping
    meta = {
        "run_id": run.id,
        "status": run.status,
        "species": run.species,
        "created_at": run.created_at,
        "total_genomes": run.total_genomes,
        "completed_genomes": len(results),
    }
    meta_bytes = dumps(meta)
    final_bytes = b'%b, "results": %b}' % (meta_bytes[:-1], results_bytes)

    return Response(
        content=final_bytes,
        media_type="application/json",
    )


@router.get("/results", response_class=KaptiveORJSONResponse)
async def get_all_results(
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> Response:
    """Fetches a flattened, time-sorted list of all genome results for the current user."""
    results = await repo.get_all_results_for_user(current_user.id)
    runs = await repo.get_runs_for_user(current_user.id)
    run_species_map = {run.id: run.species for run in runs}
    run_name_map = {run.id: run.name for run in runs}

    # Structure into a flat list using byte concatenation for a massive performance boost
    json_parts = []
    for res in results:
        meta = {
            "genome_id": res.genome_id,
            "completed_at": res.completed_at,
            "run_id": res.run_id,
            "run_name": run_name_map.get(res.run_id) or res.run_id,
            "species": run_species_map.get(res.run_id, "Unknown"),
        }
        meta_bytes = dumps(meta)

        # Slice off closing brace and inject the raw BLOB dictionary
        row_bytes = b'%b, "databases": %b}' % (meta_bytes[:-1], res.results_json)
        json_parts.append(row_bytes)

    final_json = b"[%b]" % b",".join(json_parts)
    return Response(content=final_json, media_type="application/json")


@router.get("/plot/{run_id}/{genome_id}/{database_key}", response_class=KaptiveORJSONResponse)
async def get_plot(
    dark_mode: bool = False, result_obj: SerotypingResult = Depends(get_target_serotyping_result)
) -> dict[str, Any]:  # noqa: E501
    """Generates a Plotly JSON schema for the frontend."""
    plotter = SerotypingResultPlotter()
    fig = plotter(result_obj, dark_mode=dark_mode)
    return loads(fig.to_json())


@router.get(
    "/plot/{run_id}/{genome_id}/{database_key}/summary",
    response_class=KaptiveORJSONResponse,
)
async def get_summary(result_obj: SerotypingResult = Depends(get_target_serotyping_result)) -> dict[str, str]:
    """Generates a text summary for the frontend."""
    return {"summary": summarise_result(result_obj)}


# Router POST ----------------------------------------------------------------------------------------------------------
@router.post("/compare")
async def start_comparison(
    req: CompareRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> dict[str, str]:
    """Starts a locus comparison background task."""
    run = await repo.get_run(req.run_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized or run not found.")

    task_id = str(uuid.uuid4())
    comparison_tasks[task_id] = {
        "status": "running",
        "progress": 0.0,
        "result": None,
        "error": None,
    }

    background_tasks.add_task(
        run_locus_comparison_task,
        task_id=task_id,
        run_id=req.run_id,
        genome_ids=req.genome_ids,
        database_key=req.database_key,
        dark_mode=req.dark_mode,
        show_all_links=req.show_all_links,
        reference_loci=req.reference_loci,
        repo=repo,
    )

    return {"task_id": task_id}


@router.get("/compare/{task_id}")
async def get_comparison_status(task_id: str) -> dict[str, Any]:
    """Gets the status of a comparison task."""
    if task_id not in comparison_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return comparison_tasks[task_id]


@router.post("/{species}", response_class=KaptiveORJSONResponse)
async def submit_serotyping_job(
    species: str,
    background_tasks: BackgroundTasks,
    run_name: str = Form(None),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> dict[str, Any]:
    """Submits a batch of genome FASTA files for in silico serotyping.

    Saves files temporarily, creates a Run record, and launches a background task.
    """
    # Ensure the species pipeline is initialized
    try:
        AppState.get_serotypers(species)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Species '{species}' is not supported or initialized.",
        )

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    if len(files) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 files allowed per run.")

    # Create run record
    run = await repo.create_run(current_user.id, species, len(files), run_name)

    import asyncio
    from typing import Any

    from kaptive.core.genome import GenomeAssembly

    def _parse(u_file: Any, fname: str, original_fname: str) -> GenomeAssembly:  # noqa: ANN401
        import bz2
        import gzip
        import lzma

        file_obj = u_file.file
        if original_fname.endswith(".gz"):
            file_obj = gzip.GzipFile(fileobj=u_file.file, mode="rb")
        elif original_fname.endswith(".bz2"):
            file_obj = bz2.BZ2File(u_file.file, mode="rb")
        elif original_fname.endswith(".xz"):
            file_obj = lzma.LZMAFile(u_file.file, mode="rb")

        # Parse directly from the binary stream, bypassing temporary file writes
        return GenomeAssembly.from_stream(cast(IO[bytes], file_obj), id_=fname)

    async def _parse_async(u_file: Any, fname: str, original_fname: str) -> GenomeAssembly:  # noqa: ANN401
        return await asyncio.to_thread(_parse, u_file, fname, original_fname)

    parse_tasks = []
    seen_filenames = set()
    for upload_file in files:
        # Use the original filename to track genome ID, fallback to something random
        raw_filename = upload_file.filename or "unknown.fasta"

        # Sanitize filename: replace anything that isn't alphanumeric, a dash, or a dot with an underscore
        filename = re.sub(r"[^\w.-]", "_", raw_filename)

        # Strip sequence file extensions (and optional compression suffixes)
        if m := GenomeAssembly._SEQUENCE_FILE_REGEX.search(filename):
            filename = filename[: m.start()]

        if not filename or filename.strip("._-") == "":
            filename = f"genome_{uuid.uuid4().hex[:8]}"

        # Deduplicate identical filenames in the same batch
        original_base = filename
        counter = 1
        while filename in seen_filenames:
            filename = f"{original_base}_{counter}"
            counter += 1
        seen_filenames.add(filename)

        parse_tasks.append(_parse_async(upload_file, filename, raw_filename))

    genomes = await asyncio.gather(*parse_tasks)

    # Launch background task
    background_tasks.add_task(process_genomes, run.id, species, genomes)

    return {
        "message": "Job submitted successfully.",
        "run_id": run.id,
        "status": run.status,
        "genome_count": len(files),
    }


@router.post("/results/download/jsonl")
async def download_jsonl(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> StreamingResponse:
    """Generates a JSONL download for selected genomes."""
    results = await repo.get_all_results_for_user(current_user.id)

    # Filter by selected genomes
    if selected_set := set(request.genome_ids):
        results = [r for r in results if r.genome_id in selected_set]

    def iter_jsonl() -> Iterator[bytes]:
        for res in results:
            # Unpack the stored BLOB dictionary and yield each result independently
            for result_dict in loads(res.results_json).values():
                yield dumps(result_dict, option=OPT_APPEND_NEWLINE | OPT_SERIALIZE_NUMPY)

    return StreamingResponse(
        content=iter_jsonl(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="kaptive_results.jsonl"'},
    )


@router.post("/results/download/tsv")
async def download_tsv(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> StreamingResponse:
    """Generates a combined TSV report for selected genomes."""
    results = await repo.get_all_results_for_user(current_user.id)
    if selected_set := set(request.genome_ids):
        results = [r for r in results if r.genome_id in selected_set]

    def iter_tsv() -> Iterator[bytes]:
        yield KaptiveRow.header()
        for res in results:
            for res_dict in loads(res.results_json).values():
                res_obj = SerotypingResult.from_dict(res_dict)
                yield bytes(KaptiveRow.from_result(res_obj))  # KaptiveRow has a __bytes__() method

    return StreamingResponse(
        content=iter_tsv(),
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": 'attachment; filename="kaptive_results.tsv"'},
    )


@router.post("/results/download/pha4ge")
async def download_pha4ge(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> StreamingResponse:
    """Generates a combined PHA4GE TSV report for selected genomes."""
    results = await repo.get_all_results_for_user(current_user.id)
    if selected_set := set(request.genome_ids):
        results = [r for r in results if r.genome_id in selected_set]

    def iter_tsv() -> Iterator[bytes]:
        yield Pha4geRow.header()
        for res in results:
            for res_dict in loads(res.results_json).values():
                res_obj = SerotypingResult.from_dict(res_dict)
                yield bytes(Pha4geRow.from_result(res_obj))  # Pha4geRow has a __bytes__() method

    return StreamingResponse(
        content=iter_tsv(),
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": 'attachment; filename="kaptive_results.pha4ge"'},
    )


@router.post("/results/delete")
async def delete_results(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> dict[str, str]:
    """Deletes selected genomes from the database."""
    await repo.delete_results(current_user.id, request.genome_ids)
    return {"status": "deleted"}
