"""
CP-SAT solver for patient team scheduling.

Uses Google OR-Tools Constraint Programming to optimally assign
teams to patient time slots, respecting hard constraints and
minimizing idle time / priority violations.
"""

import time
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel
from ortools.sat.python import cp_model


# ---------------------------------------------------------------------------
# Pydantic models for solver input/output
# ---------------------------------------------------------------------------

class SolvePatient(BaseModel):
    name: str
    arrival_time: str  # e.g. "8:00"


class SolveTeam(BaseModel):
    id: str
    name: str
    specialty_ids: List[str]
    duration: int = 30
    priority: int = 0
    auto_schedule: bool = True
    capacity: int = 1


class SolveSpecialty(BaseModel):
    id: str
    name: str


class PinnedSlot(BaseModel):
    patient_name: str
    time_slot: str
    team_id: str
    is_split: bool = False
    original_team_id: Optional[str] = None
    split_specialty_id: Optional[str] = None


class SolveRequest(BaseModel):
    patients: List[SolvePatient]
    teams: List[SolveTeam]
    specialties: List[SolveSpecialty]
    pinned_slots: List[PinnedSlot] = []
    time_slots: List[str] = [
        "8:00", "8:30", "9:00", "9:30", "10:00", "10:30",
        "11:00", "11:30", "12:00", "12:30", "13:00", "13:30",
    ]


class SolveResultSlot(BaseModel):
    patient_name: str
    time_slot: str
    team_id: str
    pinned: bool = False
    is_split: bool = False
    original_team_id: Optional[str] = None
    split_specialty_id: Optional[str] = None


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
    auto_teams = [t for t in request.teams if t.auto_schedule]
    non_auto_teams = {t.id: t for t in request.teams if not t.auto_schedule}
    num_patients = len(patients)
    num_teams = len(auto_teams)

    # Quick exit: nothing to schedule
    if num_patients == 0 or num_teams == 0:
        pinned_result = _pinned_slots_to_result(request.pinned_slots)
        elapsed = int((time.time() - start_time) * 1000)
        return SolveResponse(status="OPTIMAL", slots=pinned_result, solve_time_ms=elapsed)

    # Build index lookups
    patient_idx: Dict[str, int] = {p.name: i for i, p in enumerate(patients)}
    team_idx: Dict[str, int] = {t.id: i for i, t in enumerate(auto_teams)}

    # Organize pinned slots by (patient_name, team_id) for auto teams
    # and collect non-auto pinned slots separately
    pinned_auto: Dict[Tuple[str, str], PinnedSlot] = {}
    pinned_auto_splits: Dict[Tuple[str, str, str], PinnedSlot] = {}
    pinned_non_auto: List[PinnedSlot] = []

    for ps in request.pinned_slots:
        if ps.team_id in non_auto_teams or (ps.original_team_id and ps.original_team_id in non_auto_teams):
            pinned_non_auto.append(ps)
        elif ps.is_split and ps.original_team_id and ps.split_specialty_id:
            pinned_auto_splits[(ps.patient_name, ps.original_team_id, ps.split_specialty_id)] = ps
        else:
            # Whole-team pinned slot — use the real team_id
            real_team_id = ps.team_id
            # For split entries the team_id is "split_X_Y", use original_team_id
            if ps.original_team_id and ps.original_team_id in team_idx:
                real_team_id = ps.original_team_id
            pinned_auto[(ps.patient_name, real_team_id)] = ps

    # -----------------------------------------------------------------------
    # Build CP-SAT model
    # -----------------------------------------------------------------------
    model = cp_model.CpModel()

    # Storage for interval variables
    # whole_vars[p][t] = (start, end, interval, present)
    whole_vars: List[List[Optional[Tuple]]] = [[None] * num_teams for _ in range(num_patients)]
    # split_vars[p][t][spec_id] = (start, end, interval, present)
    split_vars: List[List[Dict]] = [[{} for _ in range(num_teams)] for _ in range(num_patients)]
    # For multi-specialty teams: mode selector
    # whole_mode[p][t] = BoolVar (1 = whole, 0 = split)
    whole_mode: List[List[Optional[object]]] = [[None] * num_teams for _ in range(num_patients)]
    # Track mode type: 'whole' (always whole), 'split' (always split), 'var' (solver decides)
    mode_types: List[List[str]] = [['whole'] * num_teams for _ in range(num_patients)]

    # Non-auto pinned intervals (for no-overlap constraints)
    non_auto_intervals_by_patient: Dict[int, List] = {i: [] for i in range(num_patients)}
    non_auto_intervals_by_spec: Dict[str, List] = {}

    # Create fixed intervals for non-auto pinned slots
    for ps in pinned_non_auto:
        if ps.patient_name not in patient_idx:
            continue
        p = patient_idx[ps.patient_name]
        slot_idx = time_to_index(ps.time_slot, time_slots)

        # Determine duration: look up the team
        team_id = ps.original_team_id or ps.team_id
        dur = 1  # default 30 min
        if team_id in non_auto_teams:
            # For split entries, duration is always 1 slot
            if not ps.is_split:
                dur = non_auto_teams[team_id].duration // 30

        end_idx = slot_idx + dur
        name = f"na_{ps.patient_name}_{ps.team_id}_{ps.time_slot}"
        interval = model.NewFixedSizeIntervalVar(slot_idx, dur, name)
        non_auto_intervals_by_patient[p].append(interval)

        # Track specialty usage for no-overlap
        if ps.is_split and ps.split_specialty_id:
            spec = ps.split_specialty_id
            if spec not in non_auto_intervals_by_spec:
                non_auto_intervals_by_spec[spec] = []
            non_auto_intervals_by_spec[spec].append(interval)
        elif team_id in non_auto_teams:
            for spec in non_auto_teams[team_id].specialty_ids:
                if spec not in non_auto_intervals_by_spec:
                    non_auto_intervals_by_spec[spec] = []
                non_auto_intervals_by_spec[spec].append(interval)

    # -----------------------------------------------------------------------
    # Create decision variables for each (patient, auto_team) pair
    # -----------------------------------------------------------------------
    for p in range(num_patients):
        p_name = patients[p].name
        arrival_idx = time_to_index(patients[p].arrival_time, time_slots)

        for t in range(num_teams):
            team = auto_teams[t]
            dur_slots = team.duration // 30
            t_id = team.id
            is_splittable = len(team.specialty_ids) >= 2

            pinned_key = (p_name, t_id)
            is_pinned_whole = pinned_key in pinned_auto

            # Check if any specialties are pinned as splits
            pinned_split_specs = {}
            for spec in team.specialty_ids:
                key = (p_name, t_id, spec)
                if key in pinned_auto_splits:
                    pinned_split_specs[spec] = pinned_auto_splits[key]

            # Determine if this pair is forced into a specific mode
            force_whole = is_pinned_whole
            force_split = len(pinned_split_specs) > 0

            if is_splittable and not force_whole and not force_split:
                # Mode selector: 1 = whole, 0 = split
                mode_var = model.NewBoolVar(f"mode_{p}_{t}")
                whole_mode[p][t] = mode_var
                mode_types[p][t] = 'var'
            elif is_splittable:
                # Force mode based on pinned state
                mode_var = model.NewConstant(1 if force_whole else 0)
                whole_mode[p][t] = mode_var
                mode_types[p][t] = 'whole' if force_whole else 'split'
            else:
                # Single specialty: always whole mode
                mode_var = model.NewConstant(1)
                whole_mode[p][t] = mode_var
                mode_types[p][t] = 'whole'

            # --- Whole-mode interval ---
            w_start = model.NewIntVar(0, horizon - dur_slots, f"ws_{p}_{t}")
            w_end = model.NewIntVar(dur_slots, horizon, f"we_{p}_{t}")

            if is_splittable:
                w_present = mode_var  # present only in whole mode
                w_interval = model.NewOptionalIntervalVar(
                    w_start, dur_slots, w_end, w_present, f"wi_{p}_{t}"
                )
            else:
                # Single-specialty team: always present
                w_present = model.NewConstant(1)
                w_interval = model.NewFixedSizeIntervalVar(
                    w_start, dur_slots, f"wi_{p}_{t}"
                )
                model.Add(w_end == w_start + dur_slots)

            # Arrival constraint for whole mode
            if is_splittable:
                model.Add(w_start >= arrival_idx).OnlyEnforceIf(mode_var)
            else:
                model.Add(w_start >= arrival_idx)

            # Pin whole-mode start if applicable
            if is_pinned_whole:
                pin_idx = time_to_index(pinned_auto[pinned_key].time_slot, time_slots)
                model.Add(w_start == pin_idx)

            whole_vars[p][t] = (w_start, w_end, w_interval, w_present)

            # --- Split-mode intervals (one per specialty) ---
            if is_splittable:
                not_mode = mode_var.Not()
                for spec in team.specialty_ids:
                    s_start = model.NewIntVar(0, horizon - 1, f"ss_{p}_{t}_{spec}")
                    s_end = model.NewIntVar(1, horizon, f"se_{p}_{t}_{spec}")
                    s_present = not_mode  # present only in split mode
                    s_interval = model.NewOptionalIntervalVar(
                        s_start, 1, s_end, s_present, f"si_{p}_{t}_{spec}"
                    )

                    # Arrival constraint for split mode
                    model.Add(s_start >= arrival_idx).OnlyEnforceIf(not_mode)

                    # Pin split-mode start if applicable
                    if spec in pinned_split_specs:
                        pin_idx = time_to_index(pinned_split_specs[spec].time_slot, time_slots)
                        model.Add(s_start == pin_idx)

                    split_vars[p][t][spec] = (s_start, s_end, s_interval, s_present)

    # -----------------------------------------------------------------------
    # Hard constraint 1: Patient no-overlap
    # -----------------------------------------------------------------------
    for p in range(num_patients):
        patient_intervals = []
        for t in range(num_teams):
            if whole_vars[p][t]:
                patient_intervals.append(whole_vars[p][t][2])  # interval
            for spec, sv in split_vars[p][t].items():
                patient_intervals.append(sv[2])  # interval
        # Add non-auto pinned intervals for this patient
        patient_intervals.extend(non_auto_intervals_by_patient.get(p, []))
        if patient_intervals:
            model.AddNoOverlap(patient_intervals)

    # -----------------------------------------------------------------------
    # Hard constraint 2: Team no-overlap (across patients)
    # -----------------------------------------------------------------------
    for t in range(num_teams):
        team = auto_teams[t]
        team_intervals = []
        for p in range(num_patients):
            if whole_vars[p][t]:
                team_intervals.append(whole_vars[p][t][2])
            # In split mode, each specialty is a separate resource,
            # handled by specialty no-overlap below. But whole-mode
            # intervals still need team-level no-overlap.
        # For whole-mode intervals only, they must not overlap across patients
        # (each whole interval uses the full team as a resource)
        if len(team_intervals) > 1:
            if team.capacity == 1:
                model.AddNoOverlap(team_intervals)
            else:
                # Cumulative constraint for teams with capacity > 1
                demands = [1] * len(team_intervals)
                model.AddCumulative(team_intervals, demands, team.capacity)

    # -----------------------------------------------------------------------
    # Hard constraint 3: Specialty no-overlap (across patients)
    # Each specialty can only serve one patient at a time.
    # This covers both whole-mode (team uses all its specialties)
    # and split-mode (individual specialty intervals).
    # -----------------------------------------------------------------------
    # Collect all intervals that use each specialty
    spec_intervals: Dict[str, List] = {}
    for t in range(num_teams):
        team = auto_teams[t]
        for spec in team.specialty_ids:
            if spec not in spec_intervals:
                spec_intervals[spec] = []
            for p in range(num_patients):
                # Whole-mode interval uses this specialty
                if whole_vars[p][t]:
                    spec_intervals[spec].append(whole_vars[p][t][2])
                # Split-mode interval for this specific specialty
                if spec in split_vars[p][t]:
                    spec_intervals[spec].append(split_vars[p][t][spec][2])

    # Add non-auto pinned specialty intervals
    for spec, intervals in non_auto_intervals_by_spec.items():
        if spec not in spec_intervals:
            spec_intervals[spec] = []
        spec_intervals[spec].extend(intervals)

    for spec, intervals in spec_intervals.items():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)

    # -----------------------------------------------------------------------
    # Soft objective 1: Minimize total patient span (idle time proxy)
    # span[p] = max_end[p] - min_start[p]
    # -----------------------------------------------------------------------
    WEIGHT_SPAN = 10
    WEIGHT_PRIORITY = 15
    WEIGHT_MAKESPAN = 1

    patient_spans = []
    patient_max_ends = []

    for p in range(num_patients):
        arrival_idx = time_to_index(patients[p].arrival_time, time_slots)

        # Collect all (start, end, present) for this patient's active intervals
        all_starts = []
        all_ends = []
        all_present = []

        for t in range(num_teams):
            if whole_vars[p][t]:
                ws, we, _, wp = whole_vars[p][t]
                all_starts.append((ws, wp))
                all_ends.append((we, wp))
            for spec, sv in split_vars[p][t].items():
                ss, se, _, sp = sv
                all_starts.append((ss, sp))
                all_ends.append((se, sp))

        if not all_starts:
            continue

        # min_start: the earliest start among present intervals
        min_start = model.NewIntVar(0, horizon, f"min_s_{p}")
        # max_end: the latest end among present intervals
        max_end = model.NewIntVar(0, horizon, f"max_e_{p}")

        # min_start <= each present start, and equals at least one of them
        # Use: min_start <= s (when present), and min_start >= arrival_idx
        # Then minimize span which pushes min_start up
        for s, pres in all_starts:
            if isinstance(pres, int) or (hasattr(pres, 'index') and pres.index == -1):
                # Constant True
                model.Add(min_start <= s)
            else:
                # For optional: if present, min_start <= s
                model.Add(min_start <= s).OnlyEnforceIf(pres)
        model.Add(min_start >= arrival_idx)

        for e, pres in all_ends:
            if isinstance(pres, int) or (hasattr(pres, 'index') and pres.index == -1):
                model.Add(max_end >= e)
            else:
                model.Add(max_end >= e).OnlyEnforceIf(pres)

        span = model.NewIntVar(0, horizon, f"span_{p}")
        model.Add(span == max_end - min_start)
        patient_spans.append(span)
        patient_max_ends.append(max_end)

    # -----------------------------------------------------------------------
    # Compute effective start for each (patient, team) pair.
    # whole mode → whole_start; split mode → min(split_starts)
    # -----------------------------------------------------------------------
    effective_starts: List[List[Optional[object]]] = [[None] * num_teams for _ in range(num_patients)]

    for p in range(num_patients):
        for t in range(num_teams):
            team = auto_teams[t]
            mt = mode_types[p][t]

            if mt == 'whole':
                # Always whole mode — effective start is the whole start
                effective_starts[p][t] = whole_vars[p][t][0]
            elif mt == 'split':
                # Always split mode — effective start is min of split starts
                split_starts = [split_vars[p][t][spec][0]
                                for spec in team.specialty_ids
                                if spec in split_vars[p][t]]
                if split_starts:
                    eff = model.NewIntVar(0, horizon, f"eff_{p}_{t}")
                    model.AddMinEquality(eff, split_starts)
                    effective_starts[p][t] = eff
            else:
                # Variable mode (BoolVar) — conditional on solver choice
                mode = whole_mode[p][t]
                ws = whole_vars[p][t][0]
                split_starts = [split_vars[p][t][spec][0]
                                for spec in team.specialty_ids
                                if spec in split_vars[p][t]]

                eff = model.NewIntVar(0, horizon, f"eff_{p}_{t}")
                # Whole mode: eff == whole_start
                model.Add(eff == ws).OnlyEnforceIf(mode)
                # Split mode: eff <= each split start (upper bound = min)
                for ss in split_starts:
                    model.Add(eff <= ss).OnlyEnforceIf(mode.Not())
                # Split mode tightness: eff >= at least one split start
                min_sels = []
                for i, ss in enumerate(split_starts):
                    sel = model.NewBoolVar(f"msel_{p}_{t}_{i}")
                    model.Add(eff >= ss).OnlyEnforceIf(sel, mode.Not())
                    min_sels.append(sel)
                if min_sels:
                    model.AddBoolOr(min_sels).OnlyEnforceIf(mode.Not())

                effective_starts[p][t] = eff

    # -----------------------------------------------------------------------
    # Hard constraint 4: First team starts at patient arrival time
    # At least one team must begin seeing the patient exactly when they arrive.
    # -----------------------------------------------------------------------
    for p in range(num_patients):
        arrival_idx = time_to_index(patients[p].arrival_time, time_slots)
        starts_at_arrival = []
        for t in range(num_teams):
            es = effective_starts[p][t]
            if es is None:
                continue
            b = model.NewBoolVar(f"at_arrival_{p}_{t}")
            model.Add(es == arrival_idx).OnlyEnforceIf(b)
            starts_at_arrival.append(b)
        if starts_at_arrival:
            model.AddBoolOr(starts_at_arrival)

    # -----------------------------------------------------------------------
    # Soft objective 2: Minimize priority ordering violations (proportional)
    # For each patient, penalize when a higher-priority team (lower number)
    # starts after a lower-priority team. Penalty is proportional to the
    # number of slots the higher-priority team is delayed past the lower.
    # -----------------------------------------------------------------------
    priority_costs = []

    for p in range(num_patients):
        for t1 in range(num_teams):
            for t2 in range(t1 + 1, num_teams):
                prio1 = auto_teams[t1].priority
                prio2 = auto_teams[t2].priority
                if prio1 == prio2:
                    continue

                # We want the lower-priority-number team to start first
                if prio1 < prio2:
                    earlier_t, later_t = t1, t2
                else:
                    earlier_t, later_t = t2, t1

                es = effective_starts[p][earlier_t]
                ls = effective_starts[p][later_t]
                if es is None or ls is None:
                    continue

                # delay = max(0, es - ls): how many slots the higher-priority
                # team starts after the lower-priority team.
                # Since delay >= 0 (domain) and is minimized in the objective,
                # it settles to exactly max(0, es - ls) when constrained.
                delay = model.NewIntVar(0, horizon, f"pdelay_{p}_{earlier_t}_{later_t}")
                model.Add(delay >= es - ls)
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
    solver.parameters.max_time_in_seconds = 5.0
    solver.parameters.num_workers = 4

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
    result_slots = _extract_solution(
        solver, whole_vars, split_vars, whole_mode,
        patients, auto_teams, time_slots, request.pinned_slots,
    )

    status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
    return SolveResponse(
        status=status_str,
        slots=result_slots,
        solve_time_ms=elapsed,
        message=f"Solved in {elapsed}ms with objective value {solver.ObjectiveValue():.0f}",
    )


def _extract_solution(
    solver,
    whole_vars,
    split_vars,
    whole_mode,
    patients,
    auto_teams,
    time_slots,
    pinned_slots,
) -> List[SolveResultSlot]:
    """Convert solver variable values back to SolveResultSlot objects."""
    result: List[SolveResultSlot] = []
    num_patients = len(patients)
    num_teams = len(auto_teams)

    # Track which (patient, time_slot) are emitted to avoid duplicates from pinned
    emitted = set()

    for p in range(num_patients):
        p_name = patients[p].name
        for t in range(num_teams):
            team = auto_teams[t]
            mode = whole_mode[p][t]

            # Determine if whole mode is active
            if isinstance(mode, int):
                is_whole = mode == 1
            elif hasattr(mode, 'index') and mode.index == -1:
                # Constant
                is_whole = True
            else:
                is_whole = solver.Value(mode) == 1

            if is_whole and whole_vars[p][t]:
                w_start, w_end, _, _ = whole_vars[p][t]
                start_idx = solver.Value(w_start)
                time_str = index_to_time(start_idx, time_slots)

                # Check if this was pinned
                is_pinned = False
                for ps in pinned_slots:
                    real_id = ps.original_team_id or ps.team_id
                    if (ps.patient_name == p_name and real_id == team.id
                            and not ps.is_split):
                        is_pinned = True
                        break

                slot = SolveResultSlot(
                    patient_name=p_name,
                    time_slot=time_str,
                    team_id=team.id,
                    pinned=is_pinned,
                )
                result.append(slot)
                emitted.add((p_name, time_str))
            else:
                # Split mode
                for spec in team.specialty_ids:
                    if spec not in split_vars[p][t]:
                        continue
                    s_start, _, _, _ = split_vars[p][t][spec]
                    start_idx = solver.Value(s_start)
                    time_str = index_to_time(start_idx, time_slots)

                    # Check if this specific split was pinned
                    is_pinned = False
                    for ps in pinned_slots:
                        if (ps.patient_name == p_name and ps.is_split
                                and ps.original_team_id == team.id
                                and ps.split_specialty_id == spec):
                            is_pinned = True
                            break

                    slot = SolveResultSlot(
                        patient_name=p_name,
                        time_slot=time_str,
                        team_id=f"split_{team.id}_{spec}",
                        pinned=is_pinned,
                        is_split=True,
                        original_team_id=team.id,
                        split_specialty_id=spec,
                    )
                    result.append(slot)
                    emitted.add((p_name, time_str))

    # Add non-auto pinned slots that weren't part of the solver
    for ps in pinned_slots:
        team_id = ps.original_team_id or ps.team_id
        # Check if this is a non-auto team
        is_auto = any(t.id == team_id for t in auto_teams)
        if not is_auto:
            if (ps.patient_name, ps.time_slot) not in emitted:
                result.append(SolveResultSlot(
                    patient_name=ps.patient_name,
                    time_slot=ps.time_slot,
                    team_id=ps.team_id,
                    pinned=True,
                    is_split=ps.is_split,
                    original_team_id=ps.original_team_id,
                    split_specialty_id=ps.split_specialty_id,
                ))
                emitted.add((ps.patient_name, ps.time_slot))

    return result


def _pinned_slots_to_result(pinned_slots: List[PinnedSlot]) -> List[SolveResultSlot]:
    """Convert pinned slots directly to result slots (no solver needed)."""
    return [
        SolveResultSlot(
            patient_name=ps.patient_name,
            time_slot=ps.time_slot,
            team_id=ps.team_id,
            pinned=True,
            is_split=ps.is_split,
            original_team_id=ps.original_team_id,
            split_specialty_id=ps.split_specialty_id,
        )
        for ps in pinned_slots
    ]
