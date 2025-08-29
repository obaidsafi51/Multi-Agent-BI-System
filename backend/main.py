"""
AI CFO Backend - FastAPI Gateway
This is a placeholder main.py file for Docker container startup.
Actual implementation will be done in task 9.
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI CFO Backend",
    description="FastAPI Gateway for AI CFO BI Agent",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Validate environment variables on startup"""
    required_env_vars = ['DATABASE_URL', 'REDIS_URL', 'RABBITMQ_URL', 'KIMI_API_KEY', 'SECRET_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError(f"Missing required environment variables: {missing_vars}")
    
    logger.info("Backend started successfully with all required environment variables")

@app.get("/")
async def root():
    return {"message": "AI CFO Backend - Coming Soon!", "status": "placeholder"}

@app.get("/health")
async def health():
    """Health check endpoint for Docker health checks"""
    try:
        # Basic health check - can be expanded to check database, redis, etc.
        return {
            "status": "healthy", 
            "service": "backend",
            "version": "0.1.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_status": "operational",
        "services": {
            "database": "pending_implementation",
            "redis": "pending_implementation", 
            "rabbitmq": "pending_implementation",
            "agents": "pending_implementation"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)