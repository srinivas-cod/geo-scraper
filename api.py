"""FastAPI endpoint for the Google Maps Business Extractor."""

from __future__ import annotations

import threading
import uuid
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: object, **kwargs: object) -> bool:
        return False

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import AppConfig
from app.exporter import Exporter
from app.logger import get_logger
from app.scraper import Scraper

# Load environment variables
project_root = Path(__file__).resolve().parent
load_dotenv(project_root / ".env")

app = FastAPI(
    title="Google Maps Business Extractor API",
    description="Extract business details from Google Maps search results using Playwright.",
    version="1.0.0",
)

# In-memory job storage
jobs: dict[str, dict] = {}


class ExtractRequest(BaseModel):
    keyword: str


class ExtractResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    keyword: str
    records_count: int
    records: list[dict] | None = None
    excel_path: str | None = None
    csv_path: str | None = None
    json_path: str | None = None
    error: str | None = None


def _run_extraction(job_id: str, keyword: str) -> None:
    config = AppConfig.from_env()
    logger = get_logger(config=config)

    try:
        jobs[job_id]["status"] = "running"

        scraper = Scraper(keyword=keyword, config=config, logger=logger)
        exporter = Exporter(config=config, logger=logger)

        records = scraper.run()

        excel_path = exporter.export_excel(records)
        csv_path = exporter.export_csv(records)
        json_path = exporter.export_json(records)

        results = [record.to_dict() for record in records]

        jobs[job_id].update({
            "status": "done",
            "records_count": len(results),
            "records": results,
            "excel_path": str(excel_path),
            "csv_path": str(csv_path),
            "json_path": str(json_path),
        })
    except Exception as exc:
        jobs[job_id].update({
            "status": "failed",
            "error": str(exc),
        })


@app.post("/extract", response_model=ExtractResponse)
def start_extraction(request: ExtractRequest):
    job_id = str(uuid.uuid4())[:8]

    jobs[job_id] = {
        "status": "started",
        "keyword": request.keyword,
        "records_count": 0,
        "records": None,
        "excel_path": None,
        "csv_path": None,
        "json_path": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_extraction,
        args=(job_id, request.keyword),
        daemon=True,
    )
    thread.start()

    return ExtractResponse(
        job_id=job_id,
        status="started",
        message=f"Extraction started in the background. Check /results/{job_id}",
    )


@app.get("/results/{job_id}", response_model=JobStatusResponse)
def get_results(job_id: str):
    if job_id not in jobs:
        return JobStatusResponse(job_id=job_id, status="not_found", keyword="", records_count=0, error="Not found")
    job = jobs[job_id]
    return JobStatusResponse(job_id=job_id, **job)


@app.get("/download/{job_id}/{file_type}")
def download_file(job_id: str, file_type: str):
    if job_id not in jobs:
        return {"error": "Job ID not found."}
    job = jobs[job_id]
    if job["status"] != "done":
        return {"error": "Wait for job to finish."}
    
    path_key = f"{file_type.lower()}_path"
    if path_key not in job or not job[path_key]:
        return {"error": "Invalid file type."}
    
    file_path = Path(job[path_key])
    return FileResponse(path=str(file_path), filename=file_path.name, media_type="application/octet-stream")


@app.get("/")
def root():
    ui_file = Path(__file__).parent / "index.html"
    if ui_file.exists():
        return FileResponse(path=str(ui_file))
    return {"app": "Google Maps Extractor API", "docs": "Visit /docs"}
