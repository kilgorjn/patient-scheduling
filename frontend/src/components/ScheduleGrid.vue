<template>
  <div class="container">
    <h2>Schedule</h2>

    <div class="toolbar">
      <button @click="addPatient">Add Patient</button>
      <button @click="saveSchedule">Save Schedule</button>
      <button @click="printSchedule">Print Schedule</button>
    </div>

    <div class="schedule-wrapper">
      <!-- Team palette -->
      <div class="team-palette">
        <h3>Teams</h3>
        <div
          v-for="team in teams"
          :key="team.id"
          class="team-block"
          draggable="true"
          @dragstart="onDragStart($event, team)">
          <div class="team-content">
            <strong>{{ team.name }}</strong>
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
                    'span-continuation': getTeamForSlot(patient.name, timeSlot)?.spanContinuation
                  }"
                  :style="getTeamStyle(getTeamForSlot(patient.name, timeSlot))"
                  draggable="true"
                  @dragstart="onGridDragStart($event, patient.name, timeSlot)"
                  @dblclick="removeTeam(patient.name, timeSlot)">
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
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'ScheduleGrid',
  setup() {
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

      if (entry.spanContinuation) {
        // Clicked on continuation - remove the start cell too
        const startKey = `${patientName}-${entry.spanStartSlot}`
        delete schedule.value[startKey]
        delete schedule.value[key]
      } else {
        clearTeamSlots(key)
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

    const saveSchedule = async () => {
      try {
        const scheduleData = {
          id: Date.now().toString(),
          name: `Schedule ${new Date().toLocaleString()}`,
          slots: Object.entries(schedule.value).map(([key, team]) => {
            const [patientName, timeSlot] = key.split('-')
            return {
              patient_name: patientName,
              time_slot: timeSlot,
              team_id: team.id
            }
          }),
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
      isBeforeArrival,
      onDragOver,
      getNextTimeSlot,
      onDragStart,
      onGridDragStart,
      onDrop,
      getTeamForSlot,
      removeTeam,
      isDoubleBooked,
      isDuplicateTeam,
      getSpecialtyColor,
      getTeamStyle,
      saveSchedule,
      printSchedule
    }
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
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
  padding: 10px;
  margin-bottom: 10px;
  cursor: move;
  transition: all 0.2s;
}

.team-block:hover {
  border-color: #4CAF50;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
}
</style>
