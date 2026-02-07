# Patient Scheduling Application

A simple drag-and-drop scheduling application for managing patient appointments with medical specialties and teams.

## Features

- Define medical specialties with custom colors
- Create teams composed of one or more specialties
- Drag-and-drop interface for scheduling appointments
- 30-minute appointment slots
- Save and load schedules
- Print-friendly output

## Tech Stack

- **Frontend**: Vue 3 + Vite + Vue Draggable
- **Backend**: Python FastAPI
- **Storage**: JSON files
- **Deployment**: Docker

## Quick Start with Docker

### Prerequisites
- Docker installed on your system

### Running the Application

1. Build and run the Docker container:
```bash
docker-compose up --build
```

2. Open your browser and navigate to:
```
http://localhost:8080
```

3. To stop the application:
```bash
docker-compose down
```

## Development Setup

### Prerequisites
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- npm or yarn

### Backend Development

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend server:
```bash
python app.py
```

The API will be available at `http://localhost:8080`

### Frontend Development

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

4. Build for production:
```bash
npm run build
```

## Usage Guide

### 1. Define Specialties
- Go to the "Manage Specialties" tab
- Add specialty types (e.g., MD, OT, Speech)
- Assign a color to each specialty

### 2. Create Teams
- Go to the "Manage Teams" tab
- Create teams by selecting one or more specialties
- Teams represent 30-minute appointment blocks

### 3. Build Schedule
- Go to the "Schedule" tab
- Add patient names in the left column
- Drag team blocks from the palette on the left into time slots
- Double-click a scheduled team to remove it

### 4. Save/Print
- Click "Save Schedule" to save your work
- Click "Print Schedule" for a print-friendly view

## API Endpoints

### Specialties
- `GET /api/specialties` - Get all specialties
- `POST /api/specialties` - Create a specialty
- `DELETE /api/specialties/{id}` - Delete a specialty

### Teams
- `GET /api/teams` - Get all teams
- `POST /api/teams` - Create a team
- `DELETE /api/teams/{id}` - Delete a team

### Schedules
- `GET /api/schedules` - Get all schedules
- `POST /api/schedules` - Create a schedule
- `GET /api/schedules/{id}` - Get a specific schedule
- `DELETE /api/schedules/{id}` - Delete a schedule

## Project Structure

```
patient-scheduling/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   └── data/              # JSON storage
│       ├── specialties.json
│       ├── teams.json
│       └── schedules.json
├── frontend/
│   ├── src/
│   │   ├── components/    # Vue components
│   │   ├── App.vue       # Main app component
│   │   └── main.js       # Entry point
│   ├── package.json      # Node dependencies
│   └── vite.config.js    # Vite configuration
├── Dockerfile            # Docker build configuration
├── docker-compose.yml    # Docker Compose configuration
└── README.md            # This file
```

## Data Persistence

Schedule data is stored in JSON files in the `backend/data` directory. When running with Docker, this directory is mounted as a volume to persist data between container restarts.

## License

This project is open source and available for use.
