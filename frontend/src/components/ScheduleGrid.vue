<template>
  <div class="container">
    <h2>Schedule</h2>

    <div class="toolbar">
      <button @click="addPatient">Add Patient</button>
      <button @click="clearSchedule">Clear Schedule</button>
      <button @click="saveSchedule">Save Schedule</button>
      <button @click="openLoadModal">Load Schedule</button>
      <button @click="autoSchedule" :disabled="isAutoScheduling">
        {{ isAutoScheduling ? 'Solving...' : 'Auto Schedule' }}
      </button>
      <span v-if="autoScheduleError" class="auto-schedule-error">{{ autoScheduleError }}</span>
      <button @click="printSchedule">Print Schedule</button>
    </div>

    <!-- Solver Progress Indicator -->
    <div v-if="isAutoScheduling" class="solver-progress">
      <div class="progress-bar-container">
        <div class="progress-bar-fill"></div>
      </div>
      <div class="progress-message">Optimizing schedule... (may take up to 30 seconds)</div>
    </div>

    <!-- Load Schedule Modal -->
    <div v-if="showLoadModal" class="modal-overlay" @click.self="showLoadModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Load Schedule</h3>
          <button @click="showLoadModal = false" class="modal-close">&times;</button>
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
      <!-- Specialty palette -->
      <div class="specialty-palette">
        <h3>Specialties</h3>
        <div v-for="spec in specialties" :key="spec.id" class="specialty-block">
          <div
            class="specialty-content"
            draggable="true"
            @dragstart="onDragStart($event, spec)"
            :style="{ borderLeft: '4px solid ' + spec.color }">
            <div class="specialty-name-row">
              <strong>{{ spec.name }}</strong>
              <span class="palette-duration">{{ spec.duration }}m</span>
              <span
                class="palette-auto-indicator"
                :class="{ 'auto-off': spec.auto_schedule === false }"
                title="Auto-schedule">&#x2699;</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Schedule grid -->
      <div class="schedule-grid-container">
        <div class="schedule-grid-scroll-wrapper">
          <table class="schedule-grid">
          <thead>
            <tr>
              <th class="patient-header">Patient</th>
              <th
                v-for="timeSlot in timeSlots"
                :key="timeSlot"
                :class="['time-header', { 'print-hide': !shouldShowInPrint(timeSlot) }]">
                {{ timeSlot }}
              </th>
              <th class="actions-header"></th>
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
                <select
                  :value="patient.arrivalTime"
                  @change="onArrivalTimeChange(patient, $event.target.value)"
                  class="arrival-select">
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
                  'span-continuation-cell': getEntryForSlot(patient.name, timeSlot)?.spanContinuation,
                  'before-arrival': isBeforeArrival(patient, timeSlot),
                  'print-hide': !shouldShowInPrint(timeSlot)
                }"
                @dragover="onDragOver($event, patient, timeSlot)"
                @drop="onDrop($event, patient.name, timeSlot, patient)">
                <div
                  v-if="getEntryForSlot(patient.name, timeSlot) && !getEntryForSlot(patient.name, timeSlot).spanContinuation"
                  class="scheduled-specialty"
                  :class="{
                    'double-booked-entry': isDoubleBooked(patient.name, timeSlot),
                    'duplicate-entry': isDuplicateSpecialty(patient.name, timeSlot),
                    'pinned-entry': getEntryForSlot(patient.name, timeSlot)?.pinned,
                    'before-arrival-entry': isEntryBeforeArrival(patient.name, timeSlot)
                  }"
                  :style="getSpecialtyStyle(patient.name, timeSlot)"
                  :draggable="!getEntryForSlot(patient.name, timeSlot)?.pinned"
                  @dragstart="onGridDragStart($event, patient.name, timeSlot)"
                  @dblclick="removeEntry(patient.name, timeSlot)">
                  <span
                    v-if="isEntryBeforeArrival(patient.name, timeSlot)"
                    class="warning-icon"
                    title="Scheduled before patient arrival">&#x26A0;</span>
                  <span
                    class="pin-btn"
                    :class="{ 'is-pinned': getEntryForSlot(patient.name, timeSlot)?.pinned }"
                    @click.stop="togglePin(patient.name, timeSlot)"
                    :title="getEntryForSlot(patient.name, timeSlot)?.pinned ? 'Unpin' : 'Pin'">&#x1F4CC;</span>
                  {{ getEntryForSlot(patient.name, timeSlot).name }}
                </div>
              </td>
              <td class="actions-cell">
                <button
                  @click="printPatientChecklist(patient)"
                  class="print-patient-btn"
                  title="Print patient checklist">
                  &#x1F4C4;
                </button>
                <button
                  @click="deletePatient(rowIndex, patient.name)"
                  class="delete-patient-btn"
                  title="Delete patient">
                  &times;
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </div>

    <!-- Patient Checklist for Printing (hidden by default) -->
    <div class="patient-checklist" v-if="checklistPatient">
      <div class="checklist-header">
        <h2>{{ checklistPatient.name }}</h2>
        <p class="date-info">Date: _________________</p>
      </div>
      <table class="checklist-table">
        <thead>
          <tr>
            <th class="checkbox-col">Done</th>
            <th class="time-col">Time</th>
            <th class="specialty-col">Appointment</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in checklistItems" :key="index">
            <td class="checkbox-col">
              <div class="checkbox-box">☐</div>
            </td>
            <td class="time-col">{{ item.time }}</td>
            <td class="specialty-col">{{ item.specialty }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'ScheduleGrid',
  props: {
    activeTab: String
  },
  setup(props) {
    const specialties = ref([])
    // Default to Patient 1, Patient 2, ...
    const defaultPatientCount = 5
    const patients = ref(
      Array.from({ length: defaultPatientCount }, (_, i) => ({
        name: `Patient ${i + 1}`,
        arrivalTime: '8:00'
      }))
    )

    // Time slot configuration
    const BASE_START_TIME = '8:00'
    const BASE_END_TIME = '13:45'
    const MAX_END_TIME = '17:00'

    // Time utility functions
    const timeToMinutes = (timeStr) => {
      const [h, m] = timeStr.split(':').map(Number)
      return h * 60 + m
    }

    const minutesToTime = (minutes) => {
      const h = Math.floor(minutes / 60)
      const m = minutes % 60
      return `${h}:${String(m).padStart(2, '0')}`
    }

    const generateTimeSlots = (startTime, endTime) => {
      const slots = []
      const startMin = timeToMinutes(startTime)
      const endMin = timeToMinutes(endTime)

      for (let min = startMin; min <= endMin; min += 15) {
        slots.push(minutesToTime(min))
      }
      return slots
    }

    const extendTimeSlots = (newEndTime) => {
      timeSlots.value = generateTimeSlots(BASE_START_TIME, newEndTime)
    }

    const detectRequiredTimeRange = (slots) => {
      if (!slots || slots.length === 0) return null

      let maxEndIdx = -1

      for (const slot of slots) {
        const spec = specialties.value.find(s => s.id === slot.specialty_id)
        const numSlots = spec ? Math.max(1, Math.round((spec.duration || 30) / 15)) : 2
        const startIdx = timeSlots.value.indexOf(slot.time_slot)

        if (startIdx < 0) continue

        const endIdx = startIdx + numSlots
        maxEndIdx = Math.max(maxEndIdx, endIdx)
      }

      // Check if we need more slots
      if (maxEndIdx > timeSlots.value.length) {
        // Calculate needed end time (round up to next quarter hour)
        const lastTime = timeSlots.value[timeSlots.value.length - 1]
        const lastMin = timeToMinutes(lastTime)
        const neededMin = lastMin + ((maxEndIdx - timeSlots.value.length) * 15)
        const roundedMin = Math.min(timeToMinutes(MAX_END_TIME), neededMin)

        return {
          endTime: minutesToTime(roundedMin),
          needsExtension: true
        }
      }
      return null
    }

    // Dynamic time slots - default to base range, extends if needed
    const timeSlots = ref(generateTimeSlots(BASE_START_TIME, BASE_END_TIME))
    const schedule = ref({})
    const draggedSpecialty = ref(null)
    const dragSourceKey = ref(null)
    const showLoadModal = ref(false)
    const savedSchedules = ref([])
    const isAutoScheduling = ref(false)
    const autoScheduleError = ref('')
    const checklistPatient = ref(null)
    const checklistItems = ref([])

    const loadSpecialties = async () => {
      try {
        const response = await axios.get('/api/specialties')
        specialties.value = response.data
      } catch (error) {
        console.error('Error loading specialties:', error)
      }
    }

    // How many 15-min slots a specialty occupies
    const durationSlots = (spec) => {
      return Math.max(1, Math.round((spec.duration || 30) / 15))
    }

    // Get N consecutive time slots starting at startSlot
    const getConsecutiveSlots = (startSlot, count) => {
      const idx = timeSlots.value.indexOf(startSlot)
      if (idx < 0 || idx + count > timeSlots.value.length) return null
      return timeSlots.value.slice(idx, idx + count)
    }

    const isBeforeArrival = (patient, timeSlot) => {
      if (!patient.arrivalTime) return false
      const arrivalIdx = timeSlots.value.indexOf(patient.arrivalTime)
      const slotIdx = timeSlots.value.indexOf(timeSlot)
      return slotIdx < arrivalIdx
    }

    const isEntryBeforeArrival = (patientName, timeSlot) => {
      const patient = patients.value.find(p => p.name === patientName)
      if (!patient) return false
      return isBeforeArrival(patient, timeSlot)
    }

    const onDragOver = (event, patient, timeSlot) => {
      if (!isBeforeArrival(patient, timeSlot)) {
        event.preventDefault()
      }
    }

    const addPatient = () => {
      patients.value.push({ name: '', arrivalTime: '8:00' })
    }

    const deletePatient = (index, patientName) => {
      const displayName = patientName || `Patient ${index + 1}`
      const confirmed = confirm(`Are you sure you want to delete ${displayName}? This will remove all their scheduled appointments.`)

      if (!confirmed) return

      const patient = patients.value[index]

      // Remove all schedule entries for this patient
      const newSchedule = {}
      for (const [key, entry] of Object.entries(schedule.value)) {
        const lastDash = key.lastIndexOf('-')
        const keyPatientName = key.substring(0, lastDash)

        if (keyPatientName !== patient.name) {
          newSchedule[key] = entry
        }
      }
      schedule.value = newSchedule

      // Remove the patient from the list
      patients.value.splice(index, 1)
    }

    const onArrivalTimeChange = (patient, newArrivalTime) => {
      // Just update the arrival time - validation is handled visually
      patient.arrivalTime = newArrivalTime
    }

    const clearSchedule = () => {
      // Remove all non-pinned entries from the schedule
      const newSchedule = {}
      for (const [key, entry] of Object.entries(schedule.value)) {
        if (entry.pinned) {
          newSchedule[key] = entry
        }
      }
      schedule.value = newSchedule
    }

    const onDragStart = (event, spec) => {
      draggedSpecialty.value = spec
      dragSourceKey.value = null
      event.dataTransfer.effectAllowed = 'copy'
    }

    const onGridDragStart = (event, patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      const entry = schedule.value[key]

      // Block drag on pinned entries
      if (entry && entry.pinned) {
        event.preventDefault()
        return
      }

      // Find the specialty from our list to get full data
      const spec = specialties.value.find(s => s.id === entry.specialty_id)
      draggedSpecialty.value = spec || entry
      dragSourceKey.value = key
      event.dataTransfer.effectAllowed = 'move'
    }

    // Clear all slots occupied by a specialty entry starting at the given key
    const clearEntrySlots = (key) => {
      const entry = schedule.value[key]
      if (!entry) return

      const lastDash = key.lastIndexOf('-')
      const patientName = key.substring(0, lastDash)
      const startSlot = key.substring(lastDash + 1)

      // Find the specialty to know how many slots to clear
      const spec = specialties.value.find(s => s.id === entry.specialty_id)
      const numSlots = spec ? durationSlots(spec) : 1

      const slots = getConsecutiveSlots(startSlot, numSlots)
      if (slots) {
        for (const slot of slots) {
          delete schedule.value[`${patientName}-${slot}`]
        }
      } else {
        // Fallback: just delete the one slot
        delete schedule.value[key]
      }
    }

    const onDrop = (event, patientName, timeSlot, patient) => {
      if (!draggedSpecialty.value) return

      // Block drops on before-arrival cells
      if (patient && isBeforeArrival(patient, timeSlot)) {
        draggedSpecialty.value = null
        dragSourceKey.value = null
        return
      }

      const spec = draggedSpecialty.value
      const numSlots = durationSlots(spec)

      // Check if the specialty fits starting at this slot
      const slots = getConsecutiveSlots(timeSlot, numSlots)
      if (!slots) {
        draggedSpecialty.value = null
        dragSourceKey.value = null
        return
      }

      // Block drops onto pinned entries
      for (const slot of slots) {
        const existingKey = `${patientName}-${slot}`
        const existing = schedule.value[existingKey]
        if (existing && existing.pinned) {
          draggedSpecialty.value = null
          dragSourceKey.value = null
          return
        }
      }

      // Determine if this is a new placement from palette (pin it) or a move within grid (preserve state)
      const isNewPlacement = !dragSourceKey.value

      // Remove from old position if moving within the grid
      if (dragSourceKey.value) {
        clearEntrySlots(dragSourceKey.value)
      }

      // Clear any existing entries in the target slots
      for (const slot of slots) {
        const existingKey = `${patientName}-${slot}`
        const existing = schedule.value[existingKey]
        if (existing && !existing.spanContinuation) {
          clearEntrySlots(existingKey)
        } else if (existing && existing.spanContinuation) {
          // Clear the parent span start too
          const parentKey = `${patientName}-${existing.spanStartSlot}`
          clearEntrySlots(parentKey)
        }
      }

      // Place the specialty (pinned if dragged from palette, unpinned if moved within grid)
      const startKey = `${patientName}-${slots[0]}`
      schedule.value[startKey] = {
        specialty_id: spec.id,
        name: spec.name,
        color: spec.color,
        duration: spec.duration,
        pinned: isNewPlacement,
        spanStart: numSlots > 1,
      }

      // Place continuation cells for multi-slot specialties
      for (let i = 1; i < numSlots; i++) {
        const contKey = `${patientName}-${slots[i]}`
        schedule.value[contKey] = {
          specialty_id: spec.id,
          name: spec.name,
          color: spec.color,
          duration: spec.duration,
          pinned: isNewPlacement,
          spanContinuation: true,
          spanStartSlot: slots[0],
        }
      }

      draggedSpecialty.value = null
      dragSourceKey.value = null
    }

    const getEntryForSlot = (patientName, timeSlot) => {
      return schedule.value[`${patientName}-${timeSlot}`]
    }

    const removeEntry = (patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      const entry = schedule.value[key]
      if (!entry) return
      if (entry.pinned) return
      clearEntrySlots(key)
    }

    const togglePin = (patientName, timeSlot) => {
      const key = `${patientName}-${timeSlot}`
      const entry = schedule.value[key]
      if (!entry) return

      const newPinned = !entry.pinned
      entry.pinned = newPinned

      // Also pin/unpin all continuation cells
      const spec = specialties.value.find(s => s.id === entry.specialty_id)
      const numSlots = spec ? durationSlots(spec) : 1
      const slots = getConsecutiveSlots(timeSlot, numSlots)
      if (slots) {
        for (let i = 1; i < slots.length; i++) {
          const contEntry = schedule.value[`${patientName}-${slots[i]}`]
          if (contEntry) {
            contEntry.pinned = newPinned
          }
        }
      }
    }

    // Detect double-booked specialties: same specialty scheduled for 2+ patients at the same time
    const doubleBookedSlots = computed(() => {
      const conflicts = new Set()
      for (const timeSlot of timeSlots.value) {
        const specsAtTime = []
        for (const patient of patients.value) {
          const key = `${patient.name}-${timeSlot}`
          const entry = schedule.value[key]
          if (entry) {
            specsAtTime.push({ key, specId: entry.specialty_id })
          }
        }
        const specCounts = {}
        for (const item of specsAtTime) {
          if (!specCounts[item.specId]) specCounts[item.specId] = []
          specCounts[item.specId].push(item.key)
        }
        for (const keys of Object.values(specCounts)) {
          if (keys.length > 1) {
            keys.forEach(k => conflicts.add(k))
          }
        }
      }
      return conflicts
    })

    const isDoubleBooked = (patientName, timeSlot) => {
      return doubleBookedSlots.value.has(`${patientName}-${timeSlot}`)
    }

    // Detect duplicate specialties: same specialty scheduled more than once for the same patient
    const duplicateSpecialtySlots = computed(() => {
      const duplicates = new Set()
      for (const patient of patients.value) {
        const specEntries = []
        for (const timeSlot of timeSlots.value) {
          const key = `${patient.name}-${timeSlot}`
          const entry = schedule.value[key]
          if (entry && !entry.spanContinuation) {
            specEntries.push({ key, specId: entry.specialty_id })
          }
        }
        const specCounts = {}
        for (const item of specEntries) {
          if (!specCounts[item.specId]) specCounts[item.specId] = []
          specCounts[item.specId].push(item.key)
        }
        for (const keys of Object.values(specCounts)) {
          if (keys.length > 1) {
            keys.forEach(k => duplicates.add(k))
          }
        }
      }
      return duplicates
    })

    const isDuplicateSpecialty = (patientName, timeSlot) => {
      return duplicateSpecialtySlots.value.has(`${patientName}-${timeSlot}`)
    }

    const getSpecialtyStyle = (patientName, timeSlot) => {
      const entry = getEntryForSlot(patientName, timeSlot)
      if (!entry) return {}

      const spec = specialties.value.find(s => s.id === entry.specialty_id)
      const color = spec ? spec.color : (entry.color || '#cccccc')
      const numSlots = spec ? durationSlots(spec) : 1

      const style = {
        backgroundColor: color,
      }

      // For multi-slot specialties, span across columns
      if (numSlots > 1) {
        // Use calc() to span across cell borders
        style.width = `calc(${numSlots * 100}% + ${numSlots - 1}px)`
        style.position = 'relative'
        style.zIndex = '2'
      }

      return style
    }

    // Reconstruct schedule object from flat slot list
    const reconstructScheduleFromSlots = (slots) => {
      const newSchedule = {}
      for (const slot of slots) {
        const key = `${slot.patient_name}-${slot.time_slot}`
        const pinned = !!slot.pinned

        const spec = specialties.value.find(s => s.id === slot.specialty_id)
        if (!spec) continue

        const numSlots = durationSlots(spec)

        // Only create entries from the start slot (solver only emits start slots)
        if (newSchedule[key]?.spanContinuation) continue

        const consecutiveSlots = getConsecutiveSlots(slot.time_slot, numSlots)
        if (!consecutiveSlots) continue

        newSchedule[key] = {
          specialty_id: spec.id,
          name: spec.name,
          color: spec.color,
          duration: spec.duration,
          pinned,
          spanStart: numSlots > 1,
        }

        for (let i = 1; i < consecutiveSlots.length; i++) {
          const contKey = `${slot.patient_name}-${consecutiveSlots[i]}`
          newSchedule[contKey] = {
            specialty_id: spec.id,
            name: spec.name,
            color: spec.color,
            duration: spec.duration,
            pinned,
            spanContinuation: true,
            spanStartSlot: slot.time_slot,
          }
        }
      }
      return newSchedule
    }

    const autoSchedule = async () => {
      isAutoScheduling.value = true
      autoScheduleError.value = ''

      try {
        // Collect pinned slots from current schedule (only start slots, not continuations)
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
            specialty_id: entry.specialty_id,
          })
        }

        const solveRequest = {
          patients: patients.value.map(p => ({
            name: p.name,
            arrival_time: p.arrivalTime || '8:00'
          })),
          specialties: specialties.value.map(s => ({
            id: s.id,
            name: s.name,
            duration: s.duration || 30,
            priority: s.priority || 0,
            auto_schedule: s.auto_schedule !== false,
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

        // Check if we need to extend time range
        const neededRange = detectRequiredTimeRange(result.slots)
        if (neededRange?.needsExtension) {
          extendTimeSlots(neededRange.endTime)
          // Reconstruct with extended slots
          schedule.value = reconstructScheduleFromSlots(result.slots)
        }

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
        // Only save start slots (not continuations) — reconstruct will rebuild them
        const slots = []
        for (const [key, entry] of Object.entries(schedule.value)) {
          if (entry.spanContinuation) continue
          const lastDash = key.lastIndexOf('-')
          const patientName = key.substring(0, lastDash)
          const timeSlot = key.substring(lastDash + 1)
          slots.push({
            patient_name: patientName,
            time_slot: timeSlot,
            specialty_id: entry.specialty_id,
            pinned: !!entry.pinned,
          })
        }

        const scheduleData = {
          id: Date.now().toString(),
          name: `Schedule ${new Date().toLocaleString()}`,
          slots,
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

    // Calculate last appointment time for print optimization
    const getLastAppointmentSlot = () => {
      let maxSlotIndex = -1

      for (const [key, entry] of Object.entries(schedule.value)) {
        if (entry.spanContinuation) continue
        const lastDash = key.lastIndexOf('-')
        const timeSlot = key.substring(lastDash + 1)
        const slotIndex = timeSlots.value.indexOf(timeSlot)

        if (slotIndex >= 0) {
          // Find the specialty to get duration
          const spec = specialties.value.find(s => s.id === entry.specialty_id)
          const numSlots = spec ? Math.max(1, Math.round((spec.duration || 30) / 15)) : 2
          const endSlotIndex = slotIndex + numSlots
          maxSlotIndex = Math.max(maxSlotIndex, endSlotIndex)
        }
      }

      // Add 30-minute buffer (2 slots of 15 minutes each)
      const bufferSlots = 2
      const printCutoff = maxSlotIndex + bufferSlots

      return printCutoff < timeSlots.value.length ? printCutoff : timeSlots.value.length
    }

    const shouldShowInPrint = (timeSlot) => {
      const slotIndex = timeSlots.value.indexOf(timeSlot)
      const cutoff = getLastAppointmentSlot()
      return slotIndex < cutoff
    }

    const printSchedule = () => {
      window.print()
    }

    const printPatientChecklist = (patient) => {
      // Get all appointments for this patient
      const appointments = []

      for (const [key, entry] of Object.entries(schedule.value)) {
        if (entry.spanContinuation) continue

        const lastDash = key.lastIndexOf('-')
        const patientName = key.substring(0, lastDash)
        const timeSlot = key.substring(lastDash + 1)

        if (patientName === patient.name) {
          const specialty = specialties.value.find(s => s.id === entry.specialty_id)
          if (specialty) {
            appointments.push({
              time: timeSlot,
              specialty: specialty.name,
              timeIndex: timeSlots.value.indexOf(timeSlot)
            })
          }
        }
      }

      // Sort by time
      appointments.sort((a, b) => a.timeIndex - b.timeIndex)

      // Set checklist data
      checklistPatient.value = patient
      checklistItems.value = appointments

      // Wait for DOM update, then print
      setTimeout(() => {
        window.print()
        // Clear checklist after printing
        setTimeout(() => {
          checklistPatient.value = null
          checklistItems.value = []
        }, 100)
      }, 100)
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
          const names = [...new Set(saved.slots.map(s => s.patient_name))]
          patients.value = names.map(name => ({ name, arrivalTime: '8:00' }))
        }

        schedule.value = reconstructScheduleFromSlots(saved.slots)

        // Check if loaded schedule needs extended time range
        const neededRange = detectRequiredTimeRange(saved.slots)
        if (neededRange?.needsExtension) {
          extendTimeSlots(neededRange.endTime)
          schedule.value = reconstructScheduleFromSlots(saved.slots)
        }

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
        loadSpecialties()
      }
    })

    onMounted(() => {
      loadSpecialties()
    })

    return {
      specialties,
      patients,
      timeSlots,
      schedule,
      addPatient,
      deletePatient,
      onArrivalTimeChange,
      clearSchedule,
      autoSchedule,
      isBeforeArrival,
      isEntryBeforeArrival,
      onDragOver,
      onDragStart,
      onGridDragStart,
      onDrop,
      getEntryForSlot,
      removeEntry,
      togglePin,
      isDoubleBooked,
      isDuplicateSpecialty,
      getSpecialtyStyle,
      saveSchedule,
      printSchedule,
      printPatientChecklist,
      shouldShowInPrint,
      checklistPatient,
      checklistItems,
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

.solver-progress {
  background: #e3f2fd;
  border: 2px solid #2196F3;
  border-radius: 8px;
  padding: 15px 20px;
  margin-bottom: 20px;
  animation: pulse 2s ease-in-out infinite;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: #bbdefb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #2196F3, #1976D2, #2196F3);
  background-size: 200% 100%;
  animation: progress-slide 1.5s linear infinite;
  border-radius: 4px;
}

.progress-message {
  color: #1565C0;
  font-size: 13px;
  font-weight: 500;
  text-align: center;
}

@keyframes pulse {
  0%, 100% {
    background-color: #e3f2fd;
  }
  50% {
    background-color: #bbdefb;
  }
}

@keyframes progress-slide {
  0% {
    background-position: 0% 0%;
  }
  100% {
    background-position: 200% 0%;
  }
}

.schedule-wrapper {
  display: flex;
  gap: 20px;
}

.specialty-palette {
  flex-shrink: 0;
  width: 210px;
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  max-height: 600px;
  overflow-y: auto;
}

.specialty-palette h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
}

.specialty-block {
  background: white;
  border: 2px solid #ddd;
  border-radius: 6px;
  padding: 6px 8px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.specialty-block:hover {
  border-color: #4CAF50;
  transform: translateY(-1px);
  box-shadow: 0 3px 6px rgba(0,0,0,0.1);
}

.specialty-content {
  flex: 1;
  cursor: move;
  padding: 4px 6px;
  border-radius: 3px;
}

.specialty-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.specialty-name-row strong {
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.palette-duration {
  font-size: 10px;
  color: #666;
  background: #eee;
  padding: 1px 4px;
  border-radius: 3px;
  flex-shrink: 0;
}

.palette-auto-indicator {
  font-size: 16px;
  color: #4CAF50;
  flex-shrink: 0;
}

.palette-auto-indicator.auto-off {
  color: #f44336;
}

.schedule-grid-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.schedule-grid-scroll-wrapper {
  overflow-x: auto;
  overflow-y: visible;
}

.schedule-grid {
  border-collapse: collapse;
  background: white;
  table-layout: auto;
  width: max-content;
}

/* Sticky patient column */
.patient-header,
.patient-cell {
  position: sticky;
  left: 0;
  z-index: 5;
  background: white;
  box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}

/* Sticky time header row */
.schedule-grid thead th {
  position: sticky;
  top: 0;
  z-index: 10;
}

/* Corner cell (patient header is both sticky left and top) */
.patient-header {
  z-index: 11;
}

/* Actions column sticky on right */
.actions-header,
.actions-cell {
  position: sticky;
  right: 0;
  z-index: 5;
  background: #f5f5f5;
  box-shadow: -2px 0 4px rgba(0,0,0,0.1);
}

.schedule-grid th,
.schedule-grid td {
  border: 1px solid #ddd;
  padding: 4px 2px;
  text-align: center;
  min-width: 52px;
  max-width: 52px;
}

.schedule-grid th {
  background-color: #4CAF50;
  color: white;
  font-weight: bold;
  position: sticky;
  top: 0;
  z-index: 10;
}

.time-header {
  font-size: 11px;
  white-space: nowrap;
}

.patient-header {
  min-width: 160px !important;
  max-width: 160px !important;
  width: 160px !important;
}

.patient-cell {
  background-color: #e8f5e9;
  font-weight: bold;
  min-width: 160px !important;
  max-width: 160px !important;
  width: 160px !important;
}

.patient-input {
  width: 100%;
  border: none;
  background: transparent;
  font-weight: bold;
  text-align: center;
  font-size: 12px;
}

.arrival-select {
  width: 100%;
  border: none;
  background: transparent;
  font-size: 10px;
  color: #666;
  text-align: center;
  cursor: pointer;
}

.actions-header {
  min-width: 40px !important;
  max-width: 40px !important;
  width: 40px !important;
}

.actions-cell {
  background-color: #f5f5f5;
  text-align: center;
  vertical-align: middle;
  min-width: 40px !important;
  max-width: 40px !important;
  width: 40px !important;
}

.print-patient-btn {
  background: #2196F3;
  border: none;
  border-radius: 4px;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  color: white;
  line-height: 1;
  padding: 0;
  opacity: 0.8;
  margin-bottom: 4px;
}

.print-patient-btn:hover {
  opacity: 1;
  background: #1976D2;
}

.delete-patient-btn {
  background: #f44336;
  border: none;
  border-radius: 4px;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 18px;
  color: white;
  line-height: 1;
  padding: 0;
  opacity: 0.8;
}

.delete-patient-btn:hover {
  opacity: 1;
  background: #d32f2f;
}

.schedule-cell {
  min-height: 50px;
  position: relative;
  vertical-align: middle;
  overflow: visible;
}

.scheduled-specialty {
  padding: 4px 2px;
  border-radius: 3px;
  color: white;
  font-weight: bold;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
  cursor: pointer;
  font-size: 11px;
  word-wrap: break-word;
  position: relative;
  white-space: nowrap;
  overflow: visible;
  box-sizing: border-box;
}

.scheduled-specialty:hover {
  opacity: 0.85;
}

.span-continuation-cell {
  padding: 0;
  border-left: none;
}

.before-arrival {
  background-color: #e0e0e0;
  cursor: not-allowed;
}

.double-booked-cell {
  background-color: #fff3cd;
}

.double-booked-entry {
  outline: 3px solid red;
  outline-offset: -2px;
}

.duplicate-entry {
  outline: 3px solid orange;
  outline-offset: -2px;
}

.before-arrival-entry {
  outline: 3px solid #ffc107;
  outline-offset: -2px;
  filter: brightness(0.9);
}

.warning-icon {
  position: absolute;
  top: 1px;
  left: 1px;
  font-size: 10px;
  color: #ffc107;
  line-height: 1;
  z-index: 3;
  text-shadow: 0px 0px 2px rgba(0,0,0,0.8);
}

.pin-btn {
  position: absolute;
  top: 1px;
  right: 1px;
  font-size: 8px;
  cursor: pointer;
  opacity: 0.3;
  line-height: 1;
  z-index: 3;
}

.pin-btn:hover {
  opacity: 0.7;
}

.pin-btn.is-pinned {
  opacity: 1;
}

.pinned-entry {
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

/* Patient Checklist Styles */
.patient-checklist {
  display: none; /* Hidden by default in screen view */
}

.checklist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.checklist-header h2 {
  font-size: 18px;
  margin: 0;
  color: #4CAF50;
  font-weight: bold;
}

.date-info {
  font-size: 12px;
  color: #333;
  margin: 0;
  font-weight: normal;
}

.checklist-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 0;
}

.checklist-table thead th {
  background-color: #4CAF50;
  color: white;
  padding: 8px;
  text-align: left;
  border: 1px solid #333;
  font-size: 13px;
}

.checklist-table tbody tr {
  border-bottom: 1px solid #ddd;
}

.checklist-table tbody tr:hover {
  background-color: #f5f5f5;
}

.checklist-table tbody td {
  padding: 8px;
  border: 1px solid #ddd;
  font-size: 12px;
}

.checkbox-col {
  width: 50px;
  text-align: center;
}

.checkbox-box {
  font-size: 24px;
  line-height: 1;
  color: #333;
}

.time-col {
  width: 80px;
  font-weight: bold;
  color: #333;
}

.specialty-col {
  color: #555;
}

@media print {
  /* Default: Hide UI elements for main schedule printing */
  .toolbar,
  .specialty-palette,
  .actions-header,
  .actions-cell,
  .print-hide {
    display: none;
  }

  .schedule-wrapper {
    display: block;
  }

  .schedule-grid-container,
  .schedule-grid-scroll-wrapper {
    overflow: visible;
    width: 100%;
  }

  .schedule-grid {
    table-layout: fixed;
    width: 100%;
    font-size: 8px;
  }

  .schedule-grid th,
  .schedule-grid td {
    padding: 1px 0px;
    border: 1px solid #999;
  }

  /* Time headers - ultra-narrow vertical text */
  .time-header {
    font-size: 7px;
    writing-mode: vertical-rl;
    text-orientation: mixed;
    min-width: 16px !important;
    max-width: 16px !important;
    width: 16px !important;
    padding: 1px 0px;
  }

  /* Patient column - narrower */
  .patient-header,
  .patient-cell {
    min-width: 65px !important;
    max-width: 65px !important;
    width: 65px !important;
    font-size: 8px;
  }

  .patient-input,
  .arrival-select {
    font-size: 7px;
    padding: 0px;
  }

  /* Specialty badges - smaller */
  .scheduled-specialty {
    font-size: 6px;
    padding: 1px 0px;
    white-space: normal;
    word-break: break-word;
    line-height: 1.1;
  }

  /* Preserve colors */
  .scheduled-specialty,
  .schedule-grid th,
  .patient-cell,
  .before-arrival-entry,
  .double-booked-entry {
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }

  /* Page settings - narrower margins */
  @page {
    size: landscape;
    margin: 0.2in;
  }

  tbody tr {
    page-break-inside: avoid;
  }

  /* Patient Checklist Print Styles */
  /* Position checklist to cover entire page */
  .patient-checklist {
    display: block !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: white !important;
    z-index: 999999 !important;
    padding: 0.3in !important;
    margin: 0 !important;
  }

  /* Checklist print formatting */
  .checklist-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .checklist-header h2 {
    font-size: 16px;
    margin: 0;
  }

  .date-info {
    font-size: 11px;
    margin: 0;
  }

  .checklist-table {
    width: 100%;
    page-break-inside: avoid;
  }

  .checklist-table thead th {
    background-color: #4CAF50 !important;
    color: white !important;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
    font-size: 12px;
    padding: 6px 8px;
  }

  .checklist-table tbody td {
    font-size: 11px;
    padding: 6px 8px;
    border: 1px solid #333;
  }

  .checkbox-box {
    font-size: 20px;
    font-weight: bold;
  }

  /* Portrait orientation for patient checklist */
  body:has(.patient-checklist) {
    @page {
      size: portrait;
      margin: 0.3in;
    }
  }
}
</style>
