"""Documentation server endpoints: live Swagger UI, OpenAPI JSON, and version history."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import repositories as repo_db
from app.db import documentation as doc_db
from app.schemas.documentation import DocumentationVersionResponse
from app.services.openapi.publisher import OpenAPIPublisher

router = APIRouter(prefix="/repositories", tags=["Documentation"])


@router.get("/{repo_id}/openapi.json", summary="Get current OpenAPI JSON specification")
def get_repository_openapi_json(repo_id: int, db: Session = Depends(get_db)):
    """Serve the active OpenAPI JSON specification for a repository."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    spec = OpenAPIPublisher.get_current_openapi(repo_id, db)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OpenAPI documentation generated yet. Run analysis first."
        )

    return JSONResponse(content=spec)


@router.get("/{repo_id}/docs", response_class=HTMLResponse, summary="Interactive Swagger UI")
def get_repository_swagger_ui(repo_id: int, db: Session = Depends(get_db)):
    """Serve interactive Swagger UI documentation for a repository."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    openapi_url = f"/repositories/{repo_id}/openapi.json"
    title = f"{repo.full_name} - API Documentation"

    swagger_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
    <link rel="icon" type="image/png" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/favicon-32x32.png" sizes="32x32" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #0f172a;
        }}
        .topbar {{
            background-color: #1e293b !important;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #334155;
        }}
        .topbar a {{
            color: #38bdf8;
            text-decoration: none;
            font-family: sans-serif;
            font-size: 16px;
            font-weight: 600;
        }}
        .swagger-ui {{
            background: #ffffff;
            border-radius: 8px;
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <a href="/repositories/{repo_id}/docs">⚡ AI API Documentation Agent — {repo.full_name}</a>
    </div>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"> </script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js" charset="UTF-8"> </script>
    <script>
    window.onload = function() {{
        const ui = SwaggerUIBundle({{
            url: "{openapi_url}",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "BaseLayout"
        }});
        window.ui = ui;
    }};
    </script>
</body>
</html>
"""
    return HTMLResponse(content=swagger_html)


@router.get("/{repo_id}/versions", response_model=List[DocumentationVersionResponse], summary="List documentation versions")
def list_documentation_versions(repo_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve history of published documentation versions."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    versions = doc_db.get_documentation_versions(db, repo_id, skip=skip, limit=limit)
    return [
        DocumentationVersionResponse(
            id=v.id,
            repository_id=v.repository_id,
            commit_id=v.commit_id,
            commit_sha=v.commit.commit_sha if v.commit else None,
            version=v.version,
            openapi_json=v.openapi_json,
            validation_status=v.validation_status,
            created_at=v.created_at,
        )
        for v in versions
    ]
