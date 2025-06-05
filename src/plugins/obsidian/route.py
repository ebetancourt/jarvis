from fastapi import APIRouter
from fastapi.responses import JSONResponse
from plugins.obsidian.indexer import run_index

router = APIRouter()


@router.get("/index")
def obsidian_index():
    try:
        run_index()
        return JSONResponse(
            {"status": "success", "message": "Obsidian index completed."}
        )
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
