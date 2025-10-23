"""Application entry point for the collector project."""

from __future__ import annotations

import uvicorn

from collector.api.routes import app


if __name__ == "__main__":
    uvicorn.run("collector.api.routes:app", host="0.0.0.0", port=8000, reload=True)
