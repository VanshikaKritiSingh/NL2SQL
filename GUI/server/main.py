# main.py - NL2SQL FastAPI Server
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, APP_TITLE, APP_VERSION, APP_DESCRIPTION
from routers import query, approval, schema, analysis, ws

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under /api
app.include_router(query.router, prefix="/api")
app.include_router(approval.router, prefix="/api")
app.include_router(schema.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(ws.router)  # /ws/{user_id} at root


@app.get("/")
async def root():
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "docs_url": "/docs",
        "health": "healthy",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
