from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import typer
from typing import Dict, Optional
from mermaid_agent import mermaid_agent
from mermaid_agent.modules.typings import OneShotMermaidParams, IterateMermaidParams, MermaidAgentResponse
from mermaid_agent.modules.utils import current_date_time_str
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi import Request
from datetime import datetime
import json

app = FastAPI()

# In-memory storage for files
file_store: Dict[str, Dict] = {}

class MermaidRequest(BaseModel):
    prompt: str
    output_filename: str

class UpdateRequest(BaseModel):
    change_prompt: str

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins; restrict in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Mount the static files
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
app.mount("/sessions", StaticFiles(directory="sessions", html=True), name="static")

@app.post("/generate-mermaid")
async def generate_mermaid(request: MermaidRequest):
    """
    Endpoint to generate a Mermaid diagram from a prompt.
    """
    try:
        # Create a unique identifier and filename
        identifier = str(uuid.uuid4())
        filename = f"{request.output_filename}_{current_date_time_str()}.png"
        
        # Prepare parameters and generate diagram
        params = OneShotMermaidParams(prompt=request.prompt, output_file=filename)
        response: MermaidAgentResponse = mermaid_agent.one_shot_mermaid_agent(params)
        
        if response.img:
            # Save metadata in the file store
            file_store[identifier] = {
                "prompt": request.prompt,
                "current_mermaid": response.mermaid,
                "output_filename": filename,
            }
            return {"status": "success", "identifier": identifier, "filename": filename}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate Mermaid diagram.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/iframe", response_class=HTMLResponse)
async def iframe(imgsrc: str):
    """
    Returns a dynamic HTML page that redirects the user to the static path using client-side JavaScript.
    """
    try:
        # Split the imgsrc to extract the session_id
        parts = imgsrc.split("_output_")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid imgsrc format.")
        
        session_id = parts[1].split(".")[0]  # Extract session ID
        static_url = f"/static/?session_id={session_id}"

        # Return HTML with client-side JavaScript redirection
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Redirecting...</title>
            <script>
                // Redirect to the static URL from the client side
                window.location.href = "{static_url}";
            </script>
        </head>
        <body>
            <p>If you are not redirected automatically, <a href="{static_url}">click here</a>.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Utility functions
def build_file_path(filename: str) -> str:
    return os.path.join("sessions", filename)

def current_date_time_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

@app.post("/iterative-mermaid")
async def iterative_mermaid(identifier: Optional[str] = None, request: Request = None):
    """
    Endpoint to generate or update a Mermaid diagram iteratively.
    """
    # Extract the request data
    req_data = await request.json()
    prompt = req_data.get("prompt")
    session_id = req_data.get("session_id")
    current_date = current_date_time_str()
    output_file = f"output_{session_id if session_id else 'iter_session_' + current_date}.png"

    # Validate the prompt
    if not prompt or not prompt.strip():
        return {"error": "Prompt is required"}

    # Determine the session directory
    if session_id:
        session_dir = build_file_path(session_id)
        if not os.path.exists(session_dir):
            return {"error": "Session ID not found"}
    else:
        session_dir = build_file_path(f"iter_session_{current_date}")
        os.makedirs(session_dir, exist_ok=True)

    # Log the parameters
    print(f"Prompt: {prompt}")
    print(f"Output file: {output_file}")
    print(f"Session directory: {session_dir}")

    # Simulate MermaidAgentResponse (Replace with actual Mermaid agent logic)
    response = mermaid_agent.one_shot_mermaid_agent(
        OneShotMermaidParams(prompt=prompt, output_file=output_file)
    )
    if not response.img:
        return {"error": "Failed to generate Mermaid chart"}

    print(f"BUILT one shot mermaid chart: {response}")

    # Save the initial chart if this is a new session
    if not session_id:
        initial_output_file = os.path.join(session_dir, f"iteration_0_{output_file}")
        response.img.save(initial_output_file)

    # Iterate to refine the Mermaid chart
    iterate_params = IterateMermaidParams(
        change_prompt="",
        base_prompt=prompt,
        current_mermaid_chart=response.mermaid,
        current_mermaid_img=response.img,
        output_file=output_file,
    )

    change_prompt = req_data.get("change_prompt")
    prompt_logger_file = os.path.join(session_dir, "prompt.json")
    # Define iteration_count based on session files
    iteration_files = [f for f in os.listdir(session_dir) if f.startswith("iteration_")]
    iteration_count = len(iteration_files) if change_prompt else 0
    if change_prompt:
        iterate_params.change_prompt = change_prompt
        response = mermaid_agent.iterate_mermaid_agent(iterate_params)
        iterate_params.current_mermaid_chart = response.mermaid

        if response.img:
            iteration_output_file = os.path.join(session_dir, f"iteration_{iteration_count}_{output_file}")
            response.img.save(iteration_output_file)
    
    data = {
        "prompt": prompt,
        "iterations": iteration_count
    }

    with open(prompt_logger_file, 'w') as json_file:
        json.dump(data, json_file, indent=4)

    return {
        "message": "Mermaid chart iteration completed",
        "iterations": iteration_count,
        "session_id": os.path.basename(session_dir)
    }
######

# PowerShell example to initiate the Mermaid chart generation
# to initiate new request:
# $body = @{ "prompt" = "show primary colors"; } | ConvertTo-Json -Depth 10
# Invoke-RestMethod -Uri "http://localhost:8000/iterative-mermaid" -Method POST -Body $body -ContentType "application/json"

######

# to iterate [change_prompt is needed]:
# $body = @"
# {
#     "session_id": "iter_session_20250103_201120",
#     "change_prompt": "also show combination results",
#     "prompt": "show primary colors"
# }
# "@
# Invoke-RestMethod -Uri "http://localhost:8000/iterative-mermaid" -Method POST -Body $body -ContentType "application/json"