from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import products, carts, orders, misc
from app.core.logging_middleware import LoggingMiddleware
from app.core.exceptions import app_exception_handler, AppError


def create_app() -> FastAPI:
    app = FastAPI(title="Distributed E-Commerce Order Engine", version="1.0")

    # CORS (example - tighten in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # request logging
    app.add_middleware(LoggingMiddleware)

    # include routers (routers already define their own prefixes)
    app.include_router(products.router)
    app.include_router(carts.router)
    app.include_router(orders.router)
    app.include_router(misc.router)

    @app.get("/", tags=["root"])
    def read_root():
        return {
            "service": "Distributed E-Commerce Order Engine",
            "status": "ok",
            "docs": "/docs",
            "api_prefix": "/api/v1",
        }

    # exception handlers
    app.add_exception_handler(AppError, app_exception_handler)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
