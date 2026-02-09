<template>
  <div class="container">
    <h2>Schedule</h2>

    <div class="toolbar">
      <button @click="addPatient">Add Patient</button>
      <button @click="saveSchedule">Save Schedule</button>
      <button @click="openLoadModal">Load Schedule</button>
      <button @click="autoSchedule" :disabled="isAutoScheduling">
        {{ isAutoScheduling ? 'Solving...' : 'Auto Schedule' }}
      </button>
      <span v-if="autoScheduleError" class="auto-schedule-error">{{ autoScheduleError }}</span>
      <button @click="printSchedule">Print Schedule</button>
    </div>

    <!-- Load Schedule Modal -->
    <div v-if="showLoadModal" class="modal-overlay" @click.self="showLoadModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Load Schedule</h3>
          <button @click="showLoadModal = false" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div v-if="savedSchedules.length === 0" class="no-schedules">
            No saved schedules found.
          </div>
          <div v-for="s in savedSchedules" :key="s.id" class="saved-schedule-item">
            <div class="saved-schedule-info">
              <strong>{{ s.name }}</strong>
              <span class="saved-schedule-date">{{ new Date(s.created_at).toLocaleString() }}</span>
              <span class="saved-schedule-detail">{{ s.slots.length }} slots</span>
            </div>
            <div class="saved-schedule-actions">
              <button @click="loadScheduleById(s.id)" class="load-btn">Load</button>
              <button @click="deleteSavedSchedule(s.id)" class="delete-schedule-btn">Delete</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="schedule-wrapper">
      <!-- Team palette -->
      <div class="team-palette">
        <h3>Teams</h3>
        <draggable
          v-model="teams"
          item-key="id"
          handle=".palette-reorder-handle"
          @end="onPaletteReorder">
          <template #item="{ element: team }">
            <div class="team-block">
              <span class="palette-reorder-handle" title="Drag to reorder">&#x2630;</span>
              <div
                class="team-content"
                draggable="true"
                @dragstart="onDragStart($event, team)">
                <div class="team-name-row">
                  <strong>{{ team.name }}</strong>
                  <span
                    class="palette-auto-indicator"
                    :class="{ 'auto-off': team.auto_schedule === false }"
                    title="Auto-schedule">&#x2699;</span>
                </div>
                <div class="team-specialties-mini">
                  <span
                    v-for="specialtyId in team.specialty_ids"
                    :key="specialtyId"
                    class="specialty-dot"
                    :style="{ backgroundColor: getSpecialtyColor(specialtyId) }">
                  </span>
                </div>
              </div>
            </div>
          </template>
        </draggable>
      </div>

      <!-- Schedule grid -->
      <div class="schedule-grid-container">
        <table class="schedule-grid">
          <thead>
            <tr>
              <th class="patient-header">Patient</th>
              <th v-for="timeSlot in timeSlots" :key="timeSlot">
                {{ timeSlot }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(patient, rowIndex) in patients" :key="rowIndex">
              <td class="patient-cell">
                <input
                  v-model="patient.name"
                  placeholder="Patient name"
                  class="patient-input"
                />
                <select v-model="patient.arrivalTime" class="arrival-select">
                  <option value="">Arrival...</option>
                  <option v-for="slot in timeSlots" :key="slot" :value="slot">{{ slot }}</option>
                </select>
              </td>
              <td
                v-for="timeSlot in timeSlots"
                :key="timeSlot"
                class="schedule-cell"
                :class="{
                  'double-booked-cell': isDoubleBooked(patient.name, timeSlot),
                  'span-start-cell': getTeamForSlot(patient.name, timeSlot)?.spanStart,
                  'span-continuation-cell': getTeamForSlot(patient.name, timeSlot)?.spanContinuation,
                  'before-arrival': isBeforeArrival(patient, timeSlot)
                }"
                @dragover="onDragOver($event, patient, timeSlot)"
                @drop="onDrop($event, patient.name, timeSlot, patient)">
                <div
                  v-if="getTeamForSlot(patient.name, timeSlot)"
                  class="scheduled-team"
                  :class="{
                    'double-booked-team': isDoubleBooked(patient.name, timeSlot),
                    'duplicate-team': isDuplicateTeam(patient.name, timeSlot),
                    'span-continuation': getTeamForSlot(patient.name, timeSlot)?.spanContinuation,
                    'pinned-team': getTeamForSlot(patient.name, timeSlot)?.pinned
                  }"
                  :style="getTeamStyle(getTeamForSlot(patient.name, timeSlot))"
                  :draggable="!getTeamForSlot(patient.name, timeSlot)?.pinned"
                  @dragstart="onGridDragStart($event, patient.name, timeSlot)"
                  @dblclick="removeTeam(patient.name, timeSlot)">
                  <span
                    v-if="!getTeamForSlot(patient.name, timeSlot)?.spanContinuation"
                    class="pin-btn"
                    :class="{ 'is-pinned': getTeamForSlot(patient.name, timeSlot)?.pinned }"
                    @click.stop="togglePin(patient.name, timeSlot)"
                    :title="getTeamForSlot(patient.name, timeSlot)?.pinned ? 'Unpin' : 'Pin'">&#x1F4CC;</span>
                  {{ getTeamForSlot(patient.name, timeSlot)?.spanContinuation ? '' : getTeamForSlot(patient.name, timeSlot).name }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'
import draggable from 'vuedraggable'

export default {
  name: 'ScheduleGrid',
  components: { draggable },
  props: {
    activeTab: String
  },
  setup(props) {
    const teams = ref([])
    const specialties = ref([])
    const patients = ref([
      { name: 'Handerson', arrivalTime: '8:00' },
      { name: 'Wilson', arrivalTime: '8:00' },
      { name: 'Goodeum', arrivalTime: '8:00' },
      { name: 'Martin', arrivalTime: '8:00' },
      { name: 'Leach', arrivalTime: '8:00' }
    ])
    const timeSlots = ref([
      '8:00', '8:30', '9:00', '9:30', '10:00', '10:30',
      '11:00', '11:30', '12:00', '12:30', '13:00', '13:30'
    ])
    const schedule = ref({})
    const draggedTeam = ref(null)
    const dragSourceKey = ref(null)
    const showLoadModal = ref(false)
    const savedSchedules = ref([])
    const isAutoScheduling = ref(false)
    const autoScheduleError = ref('')

    const loadTeams = async () => {
      try {
        const response = await axios.get('/api/teams')
        teams.value = response.data
      } catch (error) {
        console.error('Error loading teams:', error)
      }
    }

    const loadSpecialties = async () => {
      try {
        const response = await axios.get('/api/specialties')
        specialties.value = response.data
      } catch (error) {
        console.error('Error loading specialties:', error)
      }
    }

    const getNextTimeSlot = (timeSlot) => {
      const idx = timeSlots.value.indexOf(timeSlot)
      if (idx >= 0 && idx < timeSlots.value.length - 1) {
        return timeSlots.value[idx + 1]
      }
      return null
    }

    const isBeforeArrival = (patient, timeSlot) => {
      if (!patient.arrivalTime) return false
      const arrivalIdx = timeSlots.value.indexOf(patient.arrivalTime)
      const slotIdx = timeSlots.value.indexOf(timeSlot)
      return slotIdx < arrivalIdx
    }

    const onDragOver = (event, patient, timeSlot) => {
      if (!isBeforeArrival(patient, timeSlot)) {
        event.preventDefault()
      }
    }

    const addPatient = () => {
      patients.value.push({ name: '', arrivalTime: '8:00' })
    }

    const onDragStart = (event, team) => {
      draggedTeam.value = team
      dragSourceKey.value = null
      event.dataTransfer.effectAllowed = 'copy'
    }

    const onGridDragStart = (event, patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      const entry = schedule.value[key]

      // Block drag on pinned teams
      if (entry && entry.pinned) {
        event.preventDefault()
        return
      }
      if (entry && entry.spanContinuation) {
        const startEntry = schedule.value[`${patientName}-${entry.spanStartSlot}`]
        if (startEntry && startEntry.pinned) {
          event.preventDefault()
          return
        }
      }

      // If dragging a continuation cell, find the start cell instead
      if (entry && entry.spanContinuation) {
        draggedTeam.value = { ...entry, spanContinuation: undefined, spanStart: undefined }
        dragSourceKey.value = `${patientName}-${entry.spanStartSlot}`
      } else {
        draggedTeam.value = { ...entry, spanContinuation: undefined, spanStart: undefined }
        dragSourceKey.value = key
      }
      event.dataTransfer.effectAllowed = 'move'
    }

    const clearTeamSlots = (key) => {
      const entry = schedule.value[key]
      if (!entry) return
      // Remove the main slot
      delete schedule.value[key]
      // If it's a span start, also remove the continuation
      if (entry.spanStart) {
        const patientName = key.substring(0, key.lastIndexOf('-'))
        const contKey = `${patientName}-${entry.spanNextSlot}`
        delete schedule.value[contKey]
      }
    }

    const onDrop = (event, patientName, timeSlot, patient) => {
      if (!draggedTeam.value) return

      // Block drops on before-arrival cells
      if (patient && isBeforeArrival(patient, timeSlot)) {
        draggedTeam.value = null
        dragSourceKey.value = null
        return
      }

      // Block drops onto pinned teams
      const existingEntry = schedule.value[`${patientName}-${timeSlot}`]
      if (existingEntry && existingEntry.pinned) {
        draggedTeam.value = null
        dragSourceKey.value = null
        return
      }

      const team = draggedTeam.value
      const is60Min = team.duration === 60

      // Check if 60-min team fits (not at the last slot)
      if (is60Min && !getNextTimeSlot(timeSlot)) {
        draggedTeam.value = null
        dragSourceKey.value = null
        return
      }

      // Remove from old position if moving within the grid
      if (dragSourceKey.value) {
        clearTeamSlots(dragSourceKey.value)
      }

      if (is60Min) {
        const nextSlot = getNextTimeSlot(timeSlot)
        const key = `${patientName}-${timeSlot}`
        const nextKey = `${patientName}-${nextSlot}`
        schedule.value[key] = { ...team, spanStart: true, spanNextSlot: nextSlot }
        schedule.value[nextKey] = { ...team, spanContinuation: true, spanStartSlot: timeSlot }
      } else {
        const key = `${patientName}-${timeSlot}`
        schedule.value[key] = { ...team }
      }

      draggedTeam.value = null
      dragSourceKey.value = null
    }

    const getTeamForSlot = (patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      return schedule.value[key]
    }

    const removeTeam = (patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      const entry = schedule.value[key]
      if (!entry) return
      if (entry.pinned) return
      if (entry.spanContinuation) {
        const startEntry = schedule.value[`${patientName}-${entry.spanStartSlot}`]
        if (startEntry && startEntry.pinned) return
      }

      if (entry.spanContinuation) {
        const startKey = `${patientName}-${entry.spanStartSlot}`
        delete schedule.value[startKey]
        delete schedule.value[key]
      } else {
        clearTeamSlots(key)
      }
    }

    const togglePin = (patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      const entry = schedule.value[key]
      if (!entry) return

      const newPinned = !entry.pinned
      entry.pinned = newPinned

      // Also pin/unpin the span partner for 60-min teams
      if (entry.spanStart) {
        const contKey = `${patientName}-${entry.spanNextSlot}`
        if (schedule.value[contKey]) {
          schedule.value[contKey].pinned = newPinned
        }
      }
      if (entry.spanContinuation) {
        const startKey = `${patientName}-${entry.spanStartSlot}`
        if (schedule.value[startKey]) {
          schedule.value[startKey].pinned = newPinned
        }
      }
    }

    // Detect double-booked teams: same team scheduled for 2+ patients at the same time
    const doubleBookedSlots = computed(() => {
      const conflicts = new Set()
      for (const timeSlot of timeSlots.value) {
        const teamsAtTime = []
        for (const patient of patients.value) {
          const key = `${patient.name}-${timeSlot}`
          const team = schedule.value[key]
          if (team) {
            teamsAtTime.push({ key, teamId: team.id })
          }
        }
        // Find teams that appear more than once in this time slot
        const teamCounts = {}
        for (const entry of teamsAtTime) {
          if (!teamCounts[entry.teamId]) teamCounts[entry.teamId] = []
          teamCounts[entry.teamId].push(entry.key)
        }
        for (const keys of Object.values(teamCounts)) {
          if (keys.length > 1) {
            keys.forEach(k => {
              conflicts.add(k)
              // Also mark the span partner if it exists
              const entry = schedule.value[k]
              if (entry) {
                const patientName = k.substring(0, k.lastIndexOf('-'))
                if (entry.spanStart) conflicts.add(`${patientName}-${entry.spanNextSlot}`)
                if (entry.spanContinuation) conflicts.add(`${patientName}-${entry.spanStartSlot}`)
              }
            })
          }
        }
      }
      return conflicts
    })

    const isDoubleBooked = (patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      return doubleBookedSlots.value.has(key)
    }

    // Detect duplicate teams: same team scheduled more than once for the same patient
    const duplicateTeamSlots = computed(() => {
      const duplicates = new Set()
      for (const patient of patients.value) {
        // Collect all team IDs for this patient (skip continuation cells)
        const teamEntries = []
        for (const timeSlot of timeSlots.value) {
          const key = `${patient.name}-${timeSlot}`
          const team = schedule.value[key]
          if (team && !team.spanContinuation) {
            teamEntries.push({ key, teamId: team.id })
          }
        }
        // Find teams that appear more than once
        const teamCounts = {}
        for (const entry of teamEntries) {
          if (!teamCounts[entry.teamId]) teamCounts[entry.teamId] = []
          teamCounts[entry.teamId].push(entry.key)
        }
        for (const keys of Object.values(teamCounts)) {
          if (keys.length > 1) {
            keys.forEach(k => {
              duplicates.add(k)
              // Also mark span partner
              const entry = schedule.value[k]
              if (entry && entry.spanStart) {
                duplicates.add(`${patient.name}-${entry.spanNextSlot}`)
              }
            })
          }
        }
      }
      return duplicates
    })

    const isDuplicateTeam = (patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      return duplicateTeamSlots.value.has(key)
    }

    const getSpecialtyColor = (id) => {
      const specialty = specialties.value.find(s => s.id === id)
      return specialty ? specialty.color : '#cccccc'
    }

    const getTeamStyle = (team) => {
      if (!team || !team.specialty_ids || team.specialty_ids.length === 0) {
        return { backgroundColor: '#cccccc' }
      }

      // Use the first specialty's color for simplicity
      const firstColor = getSpecialtyColor(team.specialty_ids[0])

      // If multiple specialties, create a gradient
      if (team.specialty_ids.length > 1) {
        const colors = team.specialty_ids.map(id => getSpecialtyColor(id))
        return {
          background: `linear-gradient(135deg, ${colors.join(', ')})`
        }
      }

      return { backgroundColor: firstColor }
    }

    // Reconstruct schedule object from flat slot list (shared by autoSchedule and loadScheduleById)
    const reconstructScheduleFromSlots = (slots) => {
      const newSchedule = {}
      for (const slot of slots) {
        const key = `${slot.patient_name}-${slot.time_slot}`
        const pinned = !!slot.pinned

        if (slot.is_split && slot.split_specialty_id) {
          const specialty = specialties.value.find(s => s.id === slot.split_specialty_id)
          const originalTeam = teams.value.find(t => t.id === slot.original_team_id)
          newSchedule[key] = {
            id: slot.team_id,
            name: specialty ? specialty.name : 'Unknown',
            specialty_ids: [slot.split_specialty_id],
            duration: 30,
            pinned,
            isSplit: true,
            originalTeamId: slot.original_team_id,
            originalTeamName: originalTeam ? originalTeam.name : 'Unknown',
            splitSpecialtyId: slot.split_specialty_id
          }
          continue
        }

        const team = teams.value.find(t => t.id === slot.team_id)
        if (!team) continue

        if (team.duration === 60) {
          const nextSlot = getNextTimeSlot(slot.time_slot)
          if (nextSlot && !newSchedule[key]?.spanContinuation) {
            newSchedule[key] = { ...team, spanStart: true, spanNextSlot: nextSlot, pinned }
            newSchedule[`${slot.patient_name}-${nextSlot}`] = { ...team, spanContinuation: true, spanStartSlot: slot.time_slot, pinned }
          }
        } else {
          newSchedule[key] = { ...team, pinned }
        }
      }
      return newSchedule
    }

    const autoSchedule = async () => {
      isAutoScheduling.value = true
      autoScheduleError.value = ''

      try {
        // Collect pinned slots from current schedule
        const pinnedSlots = []
        for (const [key, entry] of Object.entries(schedule.value)) {
          if (!entry.pinned) continue
          if (entry.spanContinuation) continue

          const lastDash = key.lastIndexOf('-')
          const patientName = key.substring(0, lastDash)
          const timeSlot = key.substring(lastDash + 1)

          pinnedSlots.push({
            patient_name: patientName,
            time_slot: timeSlot,
            team_id: entry.isSplit ? entry.id : entry.id,
            is_split: !!entry.isSplit,
            original_team_id: entry.originalTeamId || null,
            split_specialty_id: entry.splitSpecialtyId || null,
          })
        }

        const solveRequest = {
          patients: patients.value.map(p => ({
            name: p.name,
            arrival_time: p.arrivalTime || '8:00'
          })),
          teams: teams.value.map(t => ({
            id: t.id,
            name: t.name,
            specialty_ids: t.specialty_ids,
            duration: t.duration || 30,
            priority: t.priority || 0,
            auto_schedule: t.auto_schedule !== false,
            capacity: t.capacity || 1,
          })),
          specialties: specialties.value.map(s => ({
            id: s.id,
            name: s.name,
          })),
          pinned_slots: pinnedSlots,
          time_slots: timeSlots.value,
        }

        const response = await axios.post('/api/solve', solveRequest)
        const result = response.data

        if (result.status === 'INFEASIBLE') {
          autoScheduleError.value = 'No feasible schedule found. Try removing some constraints.'
          return
        }

        if (result.status === 'ERROR') {
          autoScheduleError.value = result.message || 'Solver encountered an error.'
          return
        }

        schedule.value = reconstructScheduleFromSlots(result.slots)
        console.log('Solver result:', result.status, `(${result.solve_time_ms}ms)`, result.message)
        console.log('Schedule JSON:', JSON.stringify(schedule.value, null, 2))
      } catch (error) {
        console.error('Auto-schedule error:', error)
        autoScheduleError.value = error.response?.data?.detail || 'Failed to connect to solver.'
      } finally {
        isAutoScheduling.value = false
      }
    }

    const saveSchedule = async () => {
      try {
        const scheduleData = {
          id: Date.now().toString(),
          name: `Schedule ${new Date().toLocaleString()}`,
          slots: Object.entries(schedule.value).map(([key, team]) => {
            const lastDash = key.lastIndexOf('-')
            const patientName = key.substring(0, lastDash)
            const timeSlot = key.substring(lastDash + 1)
            return {
              patient_name: patientName,
              time_slot: timeSlot,
              team_id: team.id,
              pinned: !!team.pinned,
              is_split: !!team.isSplit,
              original_team_id: team.originalTeamId || null,
              split_specialty_id: team.splitSpecialtyId || null
            }
          }),
          patients: patients.value.map(p => ({
            name: p.name,
            arrival_time: p.arrivalTime
          })),
          created_at: new Date().toISOString()
        }

        await axios.post('/api/schedules', scheduleData)
        alert('Schedule saved successfully!')
      } catch (error) {
        console.error('Error saving schedule:', error)
        alert('Error saving schedule')
      }
    }

    const printSchedule = () => {
      window.print()
    }

    const onPaletteReorder = async () => {
      const reorderData = teams.value.map((t, i) => ({ id: t.id, priority: i }))
      try {
        await axios.put('/api/teams/reorder', reorderData)
      } catch (error) {
        console.error('Error reordering teams:', error)
        await loadTeams()
      }
    }

    const openLoadModal = async () => {
      try {
        const response = await axios.get('/api/schedules')
        savedSchedules.value = response.data
      } catch (error) {
        console.error('Error loading saved schedules:', error)
      }
      showLoadModal.value = true
    }

    const loadScheduleById = async (id) => {
      try {
        const response = await axios.get(`/api/schedules/${id}`)
        const saved = response.data

        // Restore patients
        if (saved.patients && saved.patients.length > 0) {
          patients.value = saved.patients.map(p => ({
            name: p.name,
            arrivalTime: p.arrival_time
          }))
        } else {
          // Backward compat: extract patient names from slots
          const names = [...new Set(saved.slots.map(s => s.patient_name))]
          patients.value = names.map(name => ({ name, arrivalTime: '8:00' }))
        }

        schedule.value = reconstructScheduleFromSlots(saved.slots)
        showLoadModal.value = false
      } catch (error) {
        console.error('Error loading schedule:', error)
        alert('Error loading schedule')
      }
    }

    const deleteSavedSchedule = async (id) => {
      try {
        await axios.delete(`/api/schedules/${id}`)
        savedSchedules.value = savedSchedules.value.filter(s => s.id !== id)
      } catch (error) {
        console.error('Error deleting schedule:', error)
      }
    }

    watch(() => props.activeTab, (tab) => {
      if (tab === 'schedule') {
        loadTeams()
        loadSpecialties()
      }
    })

    onMounted(() => {
      loadTeams()
      loadSpecialties()
    })

    return {
      teams,
      specialties,
      patients,
      timeSlots,
      schedule,
      addPatient,
      autoSchedule,
      isBeforeArrival,
      onDragOver,
      getNextTimeSlot,
      onDragStart,
      onGridDragStart,
      onDrop,
      getTeamForSlot,
      removeTeam,
      togglePin,
      isDoubleBooked,
      isDuplicateTeam,
      getSpecialtyColor,
      getTeamStyle,
      saveSchedule,
      printSchedule,
      onPaletteReorder,
      showLoadModal,
      savedSchedules,
      openLoadModal,
      loadScheduleById,
      deleteSavedSchedule,
      isAutoScheduling,
      autoScheduleError
    }
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
}

.auto-schedule-error {
  color: #cc0000;
  font-size: 13px;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.schedule-wrapper {
  display: flex;
  gap: 20px;
}

.team-palette {
  flex-shrink: 0;
  width: 200px;
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  max-height: 600px;
  overflow-y: auto;
}

.team-palette h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
}

.team-block {
  background: white;
  border: 2px solid #ddd;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.team-block:hover {
  border-color: #4CAF50;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.palette-reorder-handle {
  cursor: grab;
  color: #999;
  font-size: 14px;
  flex-shrink: 0;
  user-select: none;
  padding: 2px;
}

.palette-reorder-handle:hover {
  color: #666;
}

.palette-reorder-handle:active {
  cursor: grabbing;
}

.team-content {
  flex: 1;
  cursor: move;
}

.team-name-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 5px;
}

.team-name-row strong {
  font-size: 14px;
}

.palette-auto-indicator {
  font-size: 11px;
  color: #4CAF50;
  flex-shrink: 0;
}

.palette-auto-indicator.auto-off {
  color: #ccc;
}

.team-content strong {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
}

.team-specialties-mini {
  display: flex;
  gap: 4px;
}

.specialty-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(0,0,0,0.2);
}

.schedule-grid-container {
  flex: 1;
  overflow-x: auto;
}

.schedule-grid {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.schedule-grid th,
.schedule-grid td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: center;
  min-width: 80px;
}

.schedule-grid th {
  background-color: #4CAF50;
  color: white;
  font-weight: bold;
  position: sticky;
  top: 0;
  z-index: 10;
}

.patient-header {
  min-width: 120px;
}

.patient-cell {
  background-color: #e8f5e9;
  font-weight: bold;
}

.patient-input {
  width: 100%;
  border: none;
  background: transparent;
  font-weight: bold;
  text-align: center;
}

.arrival-select {
  width: 100%;
  border: none;
  background: transparent;
  font-size: 11px;
  color: #666;
  text-align: center;
  cursor: pointer;
}

.schedule-cell {
  min-height: 60px;
  position: relative;
  vertical-align: middle;
}

.scheduled-team {
  padding: 8px;
  border-radius: 4px;
  color: white;
  font-weight: bold;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
  cursor: pointer;
  font-size: 12px;
  word-wrap: break-word;
}

.scheduled-team:hover {
  opacity: 0.8;
}

.span-start-cell {
  border-right: none;
}

.span-continuation-cell {
  border-left: none;
}

.span-start-cell .scheduled-team {
  border-radius: 4px 0 0 4px;
}

.span-continuation .scheduled-team,
.span-continuation {
  border-radius: 0 4px 4px 0;
  min-height: 32px;
}

.before-arrival {
  background-color: #e0e0e0;
  cursor: not-allowed;
}

.double-booked-cell {
  background-color: #fff3cd;
}

.double-booked-team {
  outline: 3px solid red;
  outline-offset: -2px;
}

.duplicate-team {
  outline: 3px solid orange;
  outline-offset: -2px;
}

.scheduled-team {
  position: relative;
}

.pin-btn {
  position: absolute;
  top: 1px;
  right: 2px;
  font-size: 10px;
  cursor: pointer;
  opacity: 0.3;
  line-height: 1;
  z-index: 1;
}

.pin-btn:hover {
  opacity: 0.7;
}

.pin-btn.is-pinned {
  opacity: 1;
}

.pinned-team {
  outline: 2px dashed rgba(255,255,255,0.7);
  outline-offset: -3px;
  cursor: default;
}


.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #ddd;
}

.modal-header h3 {
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  line-height: 1;
}

.modal-body {
  padding: 15px 20px;
  overflow-y: auto;
}

.no-schedules {
  text-align: center;
  color: #999;
  padding: 20px;
}

.saved-schedule-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  margin-bottom: 8px;
}

.saved-schedule-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.saved-schedule-date {
  font-size: 12px;
  color: #666;
}

.saved-schedule-detail {
  font-size: 11px;
  color: #999;
}

.saved-schedule-actions {
  display: flex;
  gap: 8px;
}

.load-btn {
  background: #4CAF50;
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.load-btn:hover {
  background: #45a049;
}

.delete-schedule-btn {
  background: #ff4444;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.delete-schedule-btn:hover {
  background: #cc0000;
}

@media print {
  .toolbar,
  .team-palette {
    display: none;
  }

  .schedule-wrapper {
    display: block;
  }

  .schedule-grid-container {
    overflow: visible;
  }

  .scheduled-team,
  .schedule-grid th,
  .patient-cell,
  .before-arrival,
  .double-booked-cell {
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }
}
</style>
