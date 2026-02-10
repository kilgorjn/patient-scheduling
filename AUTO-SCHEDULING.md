# Feature- Auto Schedule

as a user, I want to ability to click and 'auto schedule' button, in which the system automatically schedules the teams to the patients.

## Team is enabled for auto-scheduling
Auto Scheduling will use the Teams list to fill in a patients schedule. However, some teams should not be included in auto-Scheduling.  A team should be able to be designated as 'available for autoscheduling', and there should be an indicator/icon to represent the auto-scheduling state. (perhaps a gear icon, and the same icon with a line through it for disabled).

## Prefilled slots
A user can prefill a slot with a team and pin the slot so that it is read-only.  The auto-scheduler should take this into account and not change that slot.

## Patient Team Slot Duplicates
A team should only be booked for a patient once.  There should be no team seeing patient more than once a day.

## Team Conflict
A team can only see one patient at a time.  

## Team Priority
The teams are prioritized from top to bottom.  The auto-scheduler should respect that as much as possible.  For example, if 2 patients arrive at the same time (8:00 as an example), the system should schedule the first patient's first slot with the #1 priority team, and the second patients first slot with the #2 priority.


## Minimal Empty Gaps in Schedule
The algorithm should minimize empty gaps in a patients schedule as much as possible.
If there are no solutions, perhaps a team with multiple specialties could be split up to fill the gaps.  



# Patient Team Scheduling System --- Requirements & Design Summary (Update)

## 1. Overview

The system will generate optimized daily schedules for hospital patients
who must be seen by multiple care teams.

Each patient is placed in a room and visited sequentially by teams
(e.g., MD, RN, specialists). The scheduler must:

-   Respect fixed appointment arrival times
-   Avoid team conflicts
-   Avoid patient conflicts
-   Work around fixed external appointments
-   Minimize patient idle time
-   Prefer clinically prioritized team orderings

The schedule is solved algorithmically and exposed via an API for
browser visualization.

------------------------------------------------------------------------

## 2. Problem Classification

This is a constrained optimization scheduling problem equivalent to:

-   Job‑shop scheduling
-   With release times (appointment arrivals)
-   Resource constraints (teams)
-   No‑overlap constraints (patients & teams)
-   Fixed‑time operations (external appointments)
-   Soft precedence rules (priority ordering)
-   Idle‑time minimization objective

The problem is NP‑hard and requires an optimization solver rather than
heuristic‑only logic.

------------------------------------------------------------------------

## 3. Entities

### 3.1 Patients

-   Arrive at a fixed appointment time
-   Must see all required teams (currently all teams)
-   Can only meet one team at a time
-   Cannot begin visits before arrival
-   May have fixed external appointments
-   Idle gaps should be minimized but may occur if unavoidable

### 3.2 Teams

Examples:

-   MD
-   RN
-   Specialists
-   Care coordinators

Attributes:

  Attribute       Description
  --------------- ------------------------------------------------
  Duration        Visit length (30 or 60 minutes typical)
  Priority Rank   Preferred order of visit
  Capacity        Number of patients team can see simultaneously

Capacity \> 1 models "team can split".

### 3.3 External / Fixed Blocks

Some patients have fixed-time appointments with outside teams:

-   Start time fixed
-   Duration fixed
-   Cannot be moved
-   Other visits must schedule around them

------------------------------------------------------------------------

## 4. Scheduling Constraints

### 4.1 Patient Constraints

-   Cannot overlap visits
-   Cannot overlap fixed external blocks
-   Cannot start before appointment arrival
-   Must see each team exactly once

### 4.2 Team Constraints

-   Cannot see multiple patients simultaneously beyond capacity
-   Capacity defaults to 1
-   Higher capacity models split teams

### 4.3 Visit Durations

-   Typically 30 or 60 minutes
-   Configurable per team

### 4.4 External Appointment Constraints

-   Fixed start/end times
-   Non-movable
-   Treated as blocking intervals

------------------------------------------------------------------------

## 5. Ordering & Priority Rules

Some teams have preferred ordering.

  Priority   Team
  ---------- --------------
  0          MD
  1          RN
  2          Specialist A

Rules:

-   Preferred order should be followed when feasible
-   If conflicts occur, solver may reorder
-   Priority violations should incur penalties

This is a soft constraint, not hard precedence.

------------------------------------------------------------------------

## 6. Idle Time (Gap) Rules

Definition:\
Idle time = time between consecutive patient visits where no activity
occurs.

Rules:

-   Idle time is allowed if unavoidable
-   Idle time should be minimized
-   Fixed external appointments may create unavoidable gaps
-   Teams with capacity \>1 may reduce gaps

Optimization goal: minimize total idle time across all patients.

------------------------------------------------------------------------

## 7. Optimization Objectives

Primary objective:

1.  Minimize total patient idle time

Secondary objectives:

2.  Minimize patient total time in hospital\
3.  Minimize clinic makespan (end of day)\
4.  Minimize priority violations

Objectives may be weighted.

------------------------------------------------------------------------

## 8. Scale Assumptions

Current target:

-   \~5 patients/day
-   \~8 teams
-   \~40 visits total

This scale is well within exact solver capability.

------------------------------------------------------------------------

## 9. Solver Technology

Selected approach: Constraint Programming (CP‑SAT)\
Tool: Google OR‑Tools\
Language: Python

Rationale:

-   Native interval scheduling support
-   Resource constraints
-   Fixed-time blocks
-   Optimization objectives
-   Efficient at this scale

------------------------------------------------------------------------

## 10. System Architecture

Browser UI → Scheduling API (FastAPI) → Solver Engine (OR‑Tools CP‑SAT)
→ Optimized Schedule → JSON Response → Visualization

------------------------------------------------------------------------

## 11. API Endpoint

POST /solve

Responsibilities:

-   Accept scheduling inputs
-   Invoke solver
-   Return optimized schedules
-   Return infeasible status if unsolvable

------------------------------------------------------------------------

## 12. Input Data Model (Example)

``` json
{
  "day_start": "08:00",
  "day_end": "17:00",
  "patients": [
    { "id": "P1", "appointment_time": "08:00" }
  ],
  "teams": [
    {
      "id": "MD",
      "duration_minutes": 60,
      "priority_rank": 0,
      "capacity": 1
    }
  ],
  "fixed_blocks": [
    {
      "patient_id": "P1",
      "start_time": "10:00",
      "duration_minutes": 60,
      "label": "Radiology"
    }
  ]
}
```

------------------------------------------------------------------------

## 13. Output Data Model (Example)

``` json
{
  "status": "OPTIMAL",
  "visits": [
    {
      "patient_id": "P1",
      "team_id": "MD",
      "start_time": "08:00",
      "end_time": "09:00"
    }
  ]
}
```

------------------------------------------------------------------------

## 14. Visualization Requirements

-   Patient timeline view
-   Gantt chart layout
-   Idle gap highlighting
-   Priority violation indicators
-   Team utilization view (optional)

------------------------------------------------------------------------

## 15. Non‑Functional Requirements

  Category          Requirement
  ----------------- ------------------------------
  Performance       Solve \< 5 seconds
  Determinism       Same input → same output
  Extensibility     Support more teams/patients
  Observability     Log infeasible cases
  Configurability   Adjustable objective weights

------------------------------------------------------------------------

## 16. Future Enhancements

-   Optional teams
-   Multiple rooms
-   Staff shifts
-   Breaks
-   Overtime penalties
-   Real-time rescheduling
-   Analytics dashboards

------------------------------------------------------------------------
