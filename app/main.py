"""本地演示服务：页面、导入与问答。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.examples import EXAMPLES
from app.generate.answer import answer_question
from app.ingest.service import ingest_file, ingest_path
from app.retrieve.store import connect, count_documents, list_documents
from app.schemas import AskRequest, AskResponse, DocumentOut, ExampleQuestion, IngestResult

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
_ALLOWED = {".md", ".txt", ".markdown"}


def create_app(settings: Settings | None = None, *, auto_ingest: bool = False) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if auto_ingest and settings.sample_path.exists():
            conn = connect(settings.db_path)
            try:
                if count_documents(conn) == 0:
                    ingest_path(conn, settings.sample_path)
            finally:
                conn.close()
        yield

    app = FastAPI(title="Herbal RAG Demo", lifespan=lifespan)
    app.state.settings = settings

    def get_conn():
        conn = connect(settings.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @app.get("/api/health")
    def health(conn=Depends(get_conn)) -> dict:
        return {
            "status": "ok",
            "llm_mode": settings.llm_mode,
            "llm_ready": settings.llm_ready,
            "documents": count_documents(conn),
        }

    @app.get("/api/examples", response_model=list[ExampleQuestion])
    def examples() -> list[ExampleQuestion]:
        return EXAMPLES

    @app.get("/api/documents", response_model=list[DocumentOut])
    def documents(conn=Depends(get_conn)) -> list[dict]:
        return list_documents(conn)

    @app.post("/api/ask", response_model=AskResponse)
    def ask(body: AskRequest, conn=Depends(get_conn)) -> AskResponse:
        return answer_question(body.question, conn, settings)

    @app.post("/api/ingest", response_model=IngestResult)
    def ingest(file: UploadFile, conn=Depends(get_conn)) -> dict:
        name = Path(file.filename or "upload.txt").name
        if Path(name).suffix.lower() not in _ALLOWED:
            raise HTTPException(status_code=400, detail="只支持 Markdown 或 TXT")
        data = file.file.read()
        if not data:
            raise HTTPException(status_code=400, detail="文件是空的")
        if len(data) > 1_000_000:
            raise HTTPException(status_code=400, detail="文件需小于 1MB")
        settings.uploads_path.mkdir(parents=True, exist_ok=True)
        dest = settings.uploads_path / name
        dest.write_bytes(data)
        return ingest_file(conn, dest)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app(auto_ingest=True)
