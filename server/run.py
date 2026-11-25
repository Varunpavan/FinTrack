import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    is_dev = settings.ENVIRONMENT.lower() != "production"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        loop="asyncio",
        reload=is_dev
    )
