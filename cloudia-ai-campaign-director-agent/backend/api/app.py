from fastapi import FastAPI


def register_routes(app: FastAPI) -> None:
    from backend.api.routes import (
        campaigns,
        calendar,
        assets,
        approvals,
        publishing,
        analytics,
        settings as settings_router,
        internal,
    )
    from backend.api.routes import oauth
    from backend.api import websocket as ws_module

    app.include_router(campaigns.router, prefix="/api")
    app.include_router(calendar.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(approvals.router, prefix="/api")
    app.include_router(publishing.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(settings_router.router, prefix="/api")
    app.include_router(oauth.router, prefix="/api")
    app.include_router(internal.router)
    app.add_api_websocket_route("/ws/{campaign_id}", ws_module.pipeline_ws)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}
