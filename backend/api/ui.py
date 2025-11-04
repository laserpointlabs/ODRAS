"""
UI Routes Module

Handles serving HTML files for the ODRAS application UI.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])


@router.get("/", response_class=HTMLResponse)
def ui_root():
    """Serve the main ODRAS application UI at root URL"""
    try:
        with open("frontend/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback to app.html if index.html doesn't exist
        try:
            with open("frontend/app.html", "r") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(content="<h1>App not found</h1>", status_code=404)


@router.get("/app", response_class=HTMLResponse)
def ui_restart():
    """Serve the main ODRAS application UI (alias for root)"""
    try:
        with open("frontend/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback to app.html if index.html doesn't exist
        try:
            with open("frontend/app.html", "r") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(content="<h1>App not found</h1>", status_code=404)


@router.get("/ontology-editor", response_class=HTMLResponse)
def ontology_editor():
    """Serve the ontology editor UI"""
    try:
        with open("frontend/ontology-editor.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Ontology editor not found</h1>", status_code=404)


@router.get("/session-intelligence-demo", response_class=HTMLResponse)
def session_intelligence_demo():
    """Serve the session intelligence demo UI"""
    try:
        with open("frontend/session-intelligence-demo.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Session intelligence demo not found</h1>", status_code=404)


@router.get("/cqmt-workbench", response_class=HTMLResponse)
def cqmt_workbench():
    """Serve the CQ/MT workbench UI"""
    try:
        with open("frontend/cqmt-workbench.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>CQ/MT workbench not found</h1>", status_code=404)

