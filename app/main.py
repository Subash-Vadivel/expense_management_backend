from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.database.postgres import close_database_connection
from app.mcp.router import router as mcp_router
from app.routes import auth, categories, dashboard, expenses, income, mcp_api_keys

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(income.router, prefix="/api/income", tags=["Income"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(mcp_api_keys.router, prefix="/api/mcp", tags=["MCP API Keys"])
app.include_router(mcp_router, tags=["MCP"])


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root() -> str:
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{settings.app_name}</title>
        <style>
          body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background: #f4f6f1;
            color: #172017;
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }}
          main {{
            width: min(560px, calc(100% - 32px));
            background: #ffffff;
            border: 1px solid #dce3d7;
            border-radius: 8px;
            padding: 28px;
            box-shadow: 0 18px 40px rgba(45, 55, 35, 0.12);
          }}
          h1 {{ margin: 0 0 10px; color: #255d2d; }}
          p {{ margin: 0 0 22px; color: #5d6658; line-height: 1.5; }}
          .links {{ display: flex; gap: 10px; flex-wrap: wrap; }}
          a {{
            display: inline-flex;
            align-items: center;
            min-height: 40px;
            padding: 0 14px;
            border-radius: 8px;
            background: #2f855a;
            color: #ffffff;
            font-weight: 800;
            text-decoration: none;
          }}
          a.secondary {{ background: #edf2e8; color: #32412e; }}
        </style>
      </head>
      <body>
        <main>
          <h1>{settings.app_name}</h1>
          <p>Farm Accounts backend is running. Use the API routes from the web app, or inspect the interactive API documentation.</p>
          <div class="links">
            <a href="/docs">Open API Docs</a>
            <a class="secondary" href="/health">Health Check</a>
          </div>
        </main>
      </body>
    </html>
    """


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_database_connection()


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
