<template>
  <div class="container">
    <h2>Manage Teams</h2>

    <div class="form">
      <input
        v-model="newTeam.name"
        placeholder="Team name"
        @keyup.enter="addTeam"
      />
      <div class="duration-selector">
        <label>Duration:</label>
        <div class="duration-options">
          <label>
            <input type="radio" :value="30" v-model="newTeam.duration" />
            30 minutes
          </label>
          <label>
            <input type="radio" :value="60" v-model="newTeam.duration" />
            60 minutes
          </label>
        </div>
      </div>
      <div class="specialty-selector">
        <label>Select Specialties:</label>
        <div class="specialty-checkboxes">
          <label v-for="specialty in specialties" :key="specialty.id">
            <input
              type="checkbox"
              :value="specialty.id"
              v-model="newTeam.specialty_ids"
            />
            <span :style="{ color: specialty.color }">{{ specialty.name }}</span>
          </label>
        </div>
      </div>
      <button @click="addTeam" :disabled="!canAddTeam">Add Team</button>
    </div>

    <draggable
      v-model="teams"
      item-key="id"
      handle=".drag-handle"
      class="team-list"
      @end="onDragEnd">
      <template #item="{ element: team, index }">
        <div class="team-item">
          <div class="drag-handle" title="Drag to reorder">
            <span class="priority-number">{{ index + 1 }}</span>
            <span class="drag-icon">&#x2630;</span>
          </div>
          <div class="team-details">
            <div class="team-header">
              <h3>{{ team.name }}</h3>
              <button
                @click="toggleAutoSchedule(team)"
                class="auto-schedule-btn"
                :title="team.auto_schedule !== false ? 'Disable auto-schedule' : 'Enable auto-schedule'">
                <span :class="team.auto_schedule !== false ? 'auto-on' : 'auto-off'">&#x2699;</span>
              </button>
              <button @click="deleteTeam(team.id)" class="delete-btn">×</button>
            </div>
            <div class="team-specialties">
              <span
                v-for="specialtyId in team.specialty_ids"
                :key="specialtyId"
                class="specialty-badge"
                :style="{ backgroundColor: getSpecialtyColor(specialtyId) }">
                {{ getSpecialtyName(specialtyId) }}
              </span>
            </div>
            <div class="team-duration">Duration: {{ team.duration }} minutes</div>
          </div>
        </div>
      </template>
    </draggable>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'
import draggable from 'vuedraggable'

export default {
  name: 'TeamManager',
  components: { draggable },
  props: {
    activeTab: String
  },
  setup(props) {
    const teams = ref([])
    const specialties = ref([])
    const newTeam = ref({
      name: '',
      specialty_ids: [],
      duration: 30
    })

    const canAddTeam = computed(() => {
      return newTeam.value.name && newTeam.value.specialty_ids.length > 0
    })

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

    const addTeam = async () => {
      if (!canAddTeam.value) return

      try {
        const team = {
          id: Date.now().toString(),
          name: newTeam.value.name,
          specialty_ids: [...newTeam.value.specialty_ids],
          duration: newTeam.value.duration
        }
        await axios.post('/api/teams', team)
        await loadTeams()
        newTeam.value.name = ''
        newTeam.value.specialty_ids = []
        newTeam.value.duration = 30
      } catch (error) {
        console.error('Error adding team:', error)
      }
    }

    const toggleAutoSchedule = async (team) => {
      try {
        const updated = { ...team, auto_schedule: team.auto_schedule === false ? true : false }
        await axios.put(`/api/teams/${team.id}`, updated)
        await loadTeams()
      } catch (error) {
        console.error('Error updating team:', error)
      }
    }

    const deleteTeam = async (id) => {
      try {
        await axios.delete(`/api/teams/${id}`)
        await loadTeams()
      } catch (error) {
        console.error('Error deleting team:', error)
      }
    }

    const getSpecialtyName = (id) => {
      const specialty = specialties.value.find(s => s.id === id)
      return specialty ? specialty.name : 'Unknown'
    }

    const getSpecialtyColor = (id) => {
      const specialty = specialties.value.find(s => s.id === id)
      return specialty ? specialty.color : '#cccccc'
    }

    const onDragEnd = async () => {
      const reorderData = teams.value.map((t, i) => ({ id: t.id, priority: i }))
      try {
        await axios.put('/api/teams/reorder', reorderData)
      } catch (error) {
        console.error('Error reordering teams:', error)
        await loadTeams()
      }
    }

    watch(() => props.activeTab, (tab) => {
      if (tab === 'teams') {
        loadSpecialties()
        loadTeams()
      }
    })

    onMounted(() => {
      loadSpecialties()
      loadTeams()
    })

    return {
      teams,
      specialties,
      newTeam,
      canAddTeam,
      addTeam,
      toggleAutoSchedule,
      deleteTeam,
      onDragEnd,
      getSpecialtyName,
      getSpecialtyColor
    }
  }
}
</script>

<style scoped>
.form {
  margin-bottom: 20px;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
}

.form input {
  width: 100%;
  margin-bottom: 15px;
}

.duration-selector {
  margin-bottom: 15px;
}

.duration-selector > label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

.duration-options {
  display: flex;
  gap: 20px;
}

.duration-options label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: normal;
}

.specialty-selector {
  margin-bottom: 15px;
}

.specialty-selector label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

.specialty-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.specialty-checkboxes label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: normal;
}

.team-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 600px;
}

.team-item {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 12px 15px;
  background: white;
  display: flex;
  align-items: center;
  gap: 15px;
}

.drag-handle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  cursor: grab;
  padding: 4px 8px;
  border-radius: 4px;
  user-select: none;
}

.drag-handle:hover {
  background: #f0f0f0;
}

.drag-handle:active {
  cursor: grabbing;
}

.priority-number {
  font-weight: bold;
  font-size: 14px;
  color: #666;
  min-width: 20px;
  text-align: center;
}

.drag-icon {
  font-size: 16px;
  color: #999;
  line-height: 1;
}

.sortable-ghost {
  opacity: 0.4;
  background: #e8f5e9;
}

.team-details {
  flex: 1;
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.team-header h3 {
  margin: 0;
  font-size: 18px;
}

.team-specialties {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.specialty-badge {
  padding: 4px 12px;
  border-radius: 12px;
  color: white;
  font-size: 12px;
  font-weight: bold;
  text-shadow: 1px 1px 1px rgba(0,0,0,0.2);
}

.team-duration {
  font-size: 12px;
  color: #666;
}

.auto-schedule-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 2px 4px;
  line-height: 1;
}

.auto-schedule-btn .auto-on {
  color: #4CAF50;
}

.auto-schedule-btn .auto-off {
  color: #ccc;
  position: relative;
}

.auto-schedule-btn .auto-off::after {
  content: '';
  position: absolute;
  top: 50%;
  left: -1px;
  right: -1px;
  height: 2px;
  background: #999;
  transform: rotate(-45deg);
}

.delete-btn {
  background: #ff4444;
  border: none;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 20px;
  color: white;
}

.delete-btn:hover {
  background: #cc0000;
}
</style>
