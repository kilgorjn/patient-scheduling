from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path
from solver import SolveRequest, SolveResponse, solve_schedule

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
    duration: int = 30       # minutes (multiple of 15)
    priority: int = 0        # lower = higher priority
    auto_schedule: bool = True

class SpecialtyReorderItem(BaseModel):
    id: str
    priority: int

class ScheduleSlot(BaseModel):
    patient_name: str
    time_slot: str
    specialty_id: str
    pinned: bool = False

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
    return {"message": "Patient Scheduling API", "version": "2.0"}

# Specialties endpoints
@app.get("/api/specialties", response_model=List[Specialty])
async def get_specialties():
    specialties = load_data("specialties.json")
    return sorted(specialties, key=lambda s: s.get("priority", 0))

@app.post("/api/specialties", response_model=Specialty)
async def create_specialty(specialty: Specialty):
    specialties = load_data("specialties.json")
    max_priority = max((s.get("priority", 0) for s in specialties), default=-1)
    spec_dict = specialty.dict()
    spec_dict["priority"] = max_priority + 1
    specialties.append(spec_dict)
    save_data("specialties.json", specialties)
    return Specialty(**spec_dict)

@app.put("/api/specialties/reorder")
async def reorder_specialties(items: List[SpecialtyReorderItem]):
    specialties = load_data("specialties.json")
    priority_map = {item.id: item.priority for item in items}
    for spec in specialties:
        if spec["id"] in priority_map:
            spec["priority"] = priority_map[spec["id"]]
    save_data("specialties.json", specialties)
    return {"message": "Specialties reordered"}

@app.put("/api/specialties/{specialty_id}", response_model=Specialty)
async def update_specialty(specialty_id: str, specialty: Specialty):
    specialties = load_data("specialties.json")
    for i, s in enumerate(specialties):
        if s["id"] == specialty_id:
            updated = specialty.dict()
            updated["id"] = specialty_id
            specialties[i] = updated
            save_data("specialties.json", specialties)
            return Specialty(**updated)
    raise HTTPException(status_code=404, detail="Specialty not found")

@app.delete("/api/specialties/{specialty_id}")
async def delete_specialty(specialty_id: str):
    specialties = load_data("specialties.json")
    specialties = [s for s in specialties if s["id"] != specialty_id]
    save_data("specialties.json", specialties)
    return {"message": "Specialty deleted"}

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

# Solver endpoint
@app.post("/api/solve", response_model=SolveResponse)
async def solve(request: SolveRequest):
    try:
        return solve_schedule(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")

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
