from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.gmail_routes import router as gmail_router
from routes.quickbooks_routes import router as quickbooks_router


app = FastAPI(
    title="AI Tax Agent Backend",
    description="Handles QuickBooks, Gmail, and document analysis endpoints.",
    version="1.0.0",
)

# ✅ Explicit, strict CORS configuration (no wildcards)
allowed_origins = [
    "http://localhost:3000",                     # Local React dev server
    "https://ai-tax-agent-frontend.vercel.app",  # Your deployed frontend
    "https://taxmate.vercel.app",                # Alternate frontend name if any
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root endpoint
@app.get("/")
def root():
    return {"message": "✅ AI Tax Agent Backend is running successfully."}

# ✅ Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "services": {"gmail": True, "quickbooks": True}}

# ✅ Register Routers
app.include_router(gmail_router, prefix="/gmail", tags=["Gmail"])
app.include_router(quickbooks_router, prefix="/quickbooks", tags=["QuickBooks"])

# ✅ Handle all OPTIONS preflight requests globally
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    """
    Handles preflight OPTIONS requests for any route.
    Ensures browser CORS preflight checks always succeed.
    """
    return JSONResponse(status_code=200, content={"status": "OK"})

# ✅ Uvicorn local startup (for local testing only)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
