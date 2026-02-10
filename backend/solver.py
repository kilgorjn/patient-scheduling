"""
CP-SAT solver for patient specialty scheduling.

Uses Google OR-Tools Constraint Programming to optimally assign
specialties to patient time slots, respecting hard constraints and
minimizing idle time / priority violations.
"""

import time
from typing import List, Dict
from pydantic import BaseModel
from ortools.sat.python import cp_model


# ---------------------------------------------------------------------------
# Pydantic models for solver input/output
# ---------------------------------------------------------------------------

class SolvePatient(BaseModel):
    name: str
    arrival_time: str  # e.g. "8:00"


class SolveSpecialty(BaseModel):
    id: str
    name: str
    duration: int = 30       # minutes (multiple of 15)
    priority: int = 0
    auto_schedule: bool = True


class PinnedSlot(BaseModel):
    patient_name: str
    time_slot: str       # e.g. "8:15"
    specialty_id: str


class SolveRequest(BaseModel):
    patients: List[SolvePatient]
    specialties: List[SolveSpecialty]
    pinned_slots: List[PinnedSlot] = []
    time_slots: List[str] = [
        "8:00", "8:15", "8:30", "8:45",
        "9:00", "9:15", "9:30", "9:45",
        "10:00", "10:15", "10:30", "10:45",
        "11:00", "11:15", "11:30", "11:45",
        "12:00", "12:15", "12:30", "12:45",
        "13:00", "13:15", "13:30", "13:45",
    ]


class SolveResultSlot(BaseModel):
    patient_name: str
    time_slot: str
    specialty_id: str
    pinned: bool = False


class SolveResponse(BaseModel):
    status: str  # "OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"
    slots: List[SolveResultSlot] = []
    solve_time_ms: int = 0
    message: str = ""


# ---------------------------------------------------------------------------
# Time-slot helpers
# ---------------------------------------------------------------------------

def time_to_index(time_str: str, time_slots: List[str]) -> int:
    """Convert a time string like '8:00' to its slot index."""
    return time_slots.index(time_str)


def index_to_time(idx: int, time_slots: List[str]) -> str:
    """Convert a slot index back to its time string."""
    return time_slots[idx]


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------

def solve_schedule(request: SolveRequest) -> SolveResponse:
    """Build and solve the CP-SAT model, returning optimized schedule slots."""
    start_time = time.time()

    time_slots = request.time_slots
    horizon = len(time_slots)
    patients = request.patients
    all_specialties = {s.id: s for s in request.specialties}

    # Separate auto vs non-auto specialties
    auto_specs = sorted(
        [s for s in request.specialties if s.auto_schedule],
        key=lambda s: s.priority
    )
    non_auto_spec_ids = {s.id for s in request.specialties if not s.auto_schedule}

    num_patients = len(patients)
    num_specs = len(auto_specs)

    # Quick exit: nothing to schedule
    if num_patients == 0 or num_specs == 0:
        pinned_result = _pinned_slots_to_result(request.pinned_slots)
        elapsed = int((time.time() - start_time) * 1000)
        return SolveResponse(status="OPTIMAL", slots=pinned_result, solve_time_ms=elapsed)

    # Build index lookups
    patient_idx: Dict[str, int] = {p.name: i for i, p in enumerate(patients)}
    spec_idx: Dict[str, int] = {s.id: i for i, s in enumerate(auto_specs)}

    # Organize pinned slots
    pinned_auto: Dict[tuple, PinnedSlot] = {}      # (patient_name, spec_id) -> slot
    pinned_non_auto: List[PinnedSlot] = []

    for ps in request.pinned_slots:
        if ps.specialty_id in non_auto_spec_ids:
            pinned_non_auto.append(ps)
        elif ps.specialty_id in spec_idx:
            pinned_auto[(ps.patient_name, ps.specialty_id)] = ps

    # -----------------------------------------------------------------------
    # Build CP-SAT model
    # -----------------------------------------------------------------------
    model = cp_model.CpModel()

    # Decision variables: one interval per (patient, auto_specialty)
    # spec_vars[p][s] = (start, end, interval)
    spec_vars = [[None] * num_specs for _ in range(num_patients)]

    for p in range(num_patients):
        p_name = patients[p].name
        arrival_idx = time_to_index(patients[p].arrival_time, time_slots)

        for s in range(num_specs):
            spec = auto_specs[s]
            dur_slots = spec.duration // 15  # 15-min resolution

            start = model.NewIntVar(0, horizon - dur_slots, f"s_{p}_{s}")
            end = model.NewIntVar(dur_slots, horizon, f"e_{p}_{s}")
            interval = model.NewFixedSizeIntervalVar(start, dur_slots, f"i_{p}_{s}")
            model.Add(end == start + dur_slots)

            # Arrival constraint
            model.Add(start >= arrival_idx)

            # Pin constraint
            pin_key = (p_name, spec.id)
            if pin_key in pinned_auto:
                pin_idx = time_to_index(pinned_auto[pin_key].time_slot, time_slots)
                model.Add(start == pin_idx)

            spec_vars[p][s] = (start, end, interval)

    # Non-auto pinned intervals (for no-overlap constraints)
    non_auto_intervals_by_patient: Dict[int, list] = {i: [] for i in range(num_patients)}
    non_auto_intervals_by_spec: Dict[str, list] = {}

    for ps in pinned_non_auto:
        if ps.patient_name not in patient_idx:
            continue
        p = patient_idx[ps.patient_name]
        slot_idx = time_to_index(ps.time_slot, time_slots)

        spec = all_specialties.get(ps.specialty_id)
        dur_slots = (spec.duration // 15) if spec else 2  # default 30 min

        name = f"na_{p}_{ps.specialty_id}_{ps.time_slot}"
        interval = model.NewFixedSizeIntervalVar(slot_idx, dur_slots, name)
        non_auto_intervals_by_patient[p].append(interval)

        if ps.specialty_id not in non_auto_intervals_by_spec:
            non_auto_intervals_by_spec[ps.specialty_id] = []
        non_auto_intervals_by_spec[ps.specialty_id].append(interval)

    # -----------------------------------------------------------------------
    # Hard constraint 1: Patient no-overlap
    # -----------------------------------------------------------------------
    for p in range(num_patients):
        patient_intervals = [spec_vars[p][s][2] for s in range(num_specs)]
        patient_intervals.extend(non_auto_intervals_by_patient.get(p, []))
        if patient_intervals:
            model.AddNoOverlap(patient_intervals)

    # -----------------------------------------------------------------------
    # Hard constraint 2: Specialty no-overlap (across patients)
    # Each specialty can only see one patient at a time.
    # -----------------------------------------------------------------------
    for s in range(num_specs):
        spec_id = auto_specs[s].id
        spec_intervals = [spec_vars[p][s][2] for p in range(num_patients)]
        # Add non-auto pinned intervals for same specialty
        spec_intervals.extend(non_auto_intervals_by_spec.get(spec_id, []))
        if len(spec_intervals) > 1:
            model.AddNoOverlap(spec_intervals)

    # -----------------------------------------------------------------------
    # Hard constraint 3: First specialty starts at patient arrival time
    # -----------------------------------------------------------------------
    for p in range(num_patients):
        arrival_idx = time_to_index(patients[p].arrival_time, time_slots)
        starts_at_arrival = []
        for s in range(num_specs):
            b = model.NewBoolVar(f"at_arr_{p}_{s}")
            model.Add(spec_vars[p][s][0] == arrival_idx).OnlyEnforceIf(b)
            starts_at_arrival.append(b)
        if starts_at_arrival:
            model.AddBoolOr(starts_at_arrival)

    # -----------------------------------------------------------------------
    # Soft objective 1: Minimize total patient span
    # -----------------------------------------------------------------------
    WEIGHT_SPAN = 100
    WEIGHT_PRIORITY = 3
    WEIGHT_MAKESPAN = 1

    patient_spans = []
    patient_max_ends = []

    for p in range(num_patients):
        all_starts = [spec_vars[p][s][0] for s in range(num_specs)]
        all_ends = [spec_vars[p][s][1] for s in range(num_specs)]

        min_start = model.NewIntVar(0, horizon, f"min_s_{p}")
        max_end = model.NewIntVar(0, horizon, f"max_e_{p}")

        model.AddMinEquality(min_start, all_starts)
        model.AddMaxEquality(max_end, all_ends)

        span = model.NewIntVar(0, horizon, f"span_{p}")
        model.Add(span == max_end - min_start)
        patient_spans.append(span)
        patient_max_ends.append(max_end)

    # -----------------------------------------------------------------------
    # Soft objective 2: Minimize priority violations (proportional)
    # -----------------------------------------------------------------------
    priority_costs = []

    for p in range(num_patients):
        for s1 in range(num_specs):
            for s2 in range(s1 + 1, num_specs):
                prio1 = auto_specs[s1].priority
                prio2 = auto_specs[s2].priority
                if prio1 == prio2:
                    continue

                if prio1 < prio2:
                    earlier_s, later_s = s1, s2
                else:
                    earlier_s, later_s = s2, s1

                delay = model.NewIntVar(0, horizon, f"pd_{p}_{earlier_s}_{later_s}")
                model.Add(delay >= spec_vars[p][earlier_s][0] - spec_vars[p][later_s][0])
                priority_costs.append(delay)

    # -----------------------------------------------------------------------
    # Soft objective 3: Minimize makespan
    # -----------------------------------------------------------------------
    makespan = model.NewIntVar(0, horizon, "makespan")
    for max_end in patient_max_ends:
        model.Add(makespan >= max_end)
    if not patient_max_ends:
        model.Add(makespan == 0)

    # -----------------------------------------------------------------------
    # Combined objective
    # -----------------------------------------------------------------------
    objective_terms = []
    for span in patient_spans:
        objective_terms.append(WEIGHT_SPAN * span)
    for pc in priority_costs:
        objective_terms.append(WEIGHT_PRIORITY * pc)
    objective_terms.append(WEIGHT_MAKESPAN * makespan)

    model.Minimize(sum(objective_terms))

    # -----------------------------------------------------------------------
    # Solve
    # -----------------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_workers = 8

    status = solver.Solve(model)
    elapsed = int((time.time() - start_time) * 1000)

    if status == cp_model.INFEASIBLE:
        return SolveResponse(
            status="INFEASIBLE",
            slots=[],
            solve_time_ms=elapsed,
            message="No feasible schedule exists for the given constraints.",
        )

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResponse(
            status="ERROR",
            slots=[],
            solve_time_ms=elapsed,
            message=f"Solver returned unexpected status: {solver.StatusName(status)}",
        )

    # -----------------------------------------------------------------------
    # Extract solution
    # -----------------------------------------------------------------------
    result_slots: List[SolveResultSlot] = []

    for p in range(num_patients):
        p_name = patients[p].name
        for s in range(num_specs):
            spec = auto_specs[s]
            start_idx = solver.Value(spec_vars[p][s][0])
            time_str = index_to_time(start_idx, time_slots)

            is_pinned = (p_name, spec.id) in pinned_auto
            result_slots.append(SolveResultSlot(
                patient_name=p_name,
                time_slot=time_str,
                specialty_id=spec.id,
                pinned=is_pinned,
            ))

    # Add non-auto pinned slots
    emitted = {(sl.patient_name, sl.time_slot) for sl in result_slots}
    for ps in pinned_non_auto:
        if (ps.patient_name, ps.time_slot) not in emitted:
            result_slots.append(SolveResultSlot(
                patient_name=ps.patient_name,
                time_slot=ps.time_slot,
                specialty_id=ps.specialty_id,
                pinned=True,
            ))

    status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
    return SolveResponse(
        status=status_str,
        slots=result_slots,
        solve_time_ms=elapsed,
        message=f"Solved in {elapsed}ms with objective value {solver.ObjectiveValue():.0f}",
    )


def _pinned_slots_to_result(pinned_slots: List[PinnedSlot]) -> List[SolveResultSlot]:
    """Convert pinned slots directly to result slots (no solver needed)."""
    return [
        SolveResultSlot(
            patient_name=ps.patient_name,
            time_slot=ps.time_slot,
            specialty_id=ps.specialty_id,
            pinned=True,
        )
        for ps in pinned_slots
    ]
