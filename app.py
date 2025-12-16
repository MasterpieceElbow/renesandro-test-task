import os
from fastapi import FastAPI

from routers.routers import router


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app

app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)