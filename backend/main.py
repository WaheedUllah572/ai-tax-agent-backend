from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ✅ Corrected imports for Render (absolute imports)
from backend.routes.gmail_routes import router as gmail_router
from backend.routes.quickbooks_routes import router as quickbooks_router

app = FastAPI(
    title="AI Tax Agent Backend",
    description="Handles QuickBooks, Gmail, and document analysis endpoints.",
    version="1.0.0",
)

# ✅ CORS Configuration
allowed_origins = [
    "http://localhost:3000",
    "https://ai-tax-agent-frontend.vercel.app",
    "https://taxmate.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "✅ AI Tax Agent Backend is running successfully."}

@app.get("/health")
def health_check():
    return {"status": "ok", "services": {"gmail": True, "quickbooks": True}}

app.include_router(gmail_router, prefix="/gmail", tags=["Gmail"])
app.include_router(quickbooks_router, prefix="/quickbooks", tags=["QuickBooks"])

@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=200, content={"status": "OK"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
