from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path

app = FastAPI(title="Patient Scheduling API")

# CORS middleware for Vue frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Data models
class Specialty(BaseModel):
    id: str
    name: str
    color: str

class Team(BaseModel):
    id: str
    name: str
    specialty_ids: List[str]
    duration: int = 30  # minutes

class ScheduleSlot(BaseModel):
    patient_name: str
    time_slot: str
    team_id: str

class Patient(BaseModel):
    name: str
    arrival_time: str

class Schedule(BaseModel):
    id: str
    name: str
    slots: List[ScheduleSlot]
    patients: Optional[List[Patient]] = None
    created_at: str

# Helper functions for JSON storage
def load_data(filename: str):
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return []

def save_data(filename: str, data):
    filepath = DATA_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

# API Routes

@app.get("/api/")
async def root():
    return {"message": "Patient Scheduling API", "version": "1.0"}

# Specialties endpoints
@app.get("/api/specialties", response_model=List[Specialty])
async def get_specialties():
    return load_data("specialties.json")

@app.post("/api/specialties", response_model=Specialty)
async def create_specialty(specialty: Specialty):
    specialties = load_data("specialties.json")
    specialties.append(specialty.dict())
    save_data("specialties.json", specialties)
    return specialty

@app.delete("/api/specialties/{specialty_id}")
async def delete_specialty(specialty_id: str):
    specialties = load_data("specialties.json")
    specialties = [s for s in specialties if s["id"] != specialty_id]
    save_data("specialties.json", specialties)
    return {"message": "Specialty deleted"}

# Teams endpoints
@app.get("/api/teams", response_model=List[Team])
async def get_teams():
    return load_data("teams.json")

@app.post("/api/teams", response_model=Team)
async def create_team(team: Team):
    teams = load_data("teams.json")
    teams.append(team.dict())
    save_data("teams.json", teams)
    return team

@app.delete("/api/teams/{team_id}")
async def delete_team(team_id: str):
    teams = load_data("teams.json")
    teams = [t for t in teams if t["id"] != team_id]
    save_data("teams.json", teams)
    return {"message": "Team deleted"}

# Schedules endpoints
@app.get("/api/schedules", response_model=List[Schedule])
async def get_schedules():
    return load_data("schedules.json")

@app.post("/api/schedules", response_model=Schedule)
async def create_schedule(schedule: Schedule):
    schedules = load_data("schedules.json")
    schedules.append(schedule.dict())
    save_data("schedules.json", schedules)
    return schedule

@app.get("/api/schedules/{schedule_id}", response_model=Schedule)
async def get_schedule(schedule_id: str):
    schedules = load_data("schedules.json")
    for schedule in schedules:
        if schedule["id"] == schedule_id:
            return schedule
    raise HTTPException(status_code=404, detail="Schedule not found")

@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    schedules = load_data("schedules.json")
    schedules = [s for s in schedules if s["id"] != schedule_id]
    save_data("schedules.json", schedules)
    return {"message": "Schedule deleted"}

# Serve Vue static files (for production)
# Mount this after API routes to avoid conflicts
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
else:
    print(f"Warning: Frontend dist folder not found at {FRONTEND_DIST}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
