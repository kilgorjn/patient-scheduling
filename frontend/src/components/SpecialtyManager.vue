<template>
  <div class="container">
    <h2>Manage Specialties</h2>

    <div class="form">
      <input
        v-model="newSpecialty.name"
        placeholder="Specialty name (e.g., MD, OT)"
        @keyup.enter="addSpecialty"
      />
      <input
        v-model="newSpecialty.color"
        type="color"
      />
      <select v-model="newSpecialty.duration">
        <option :value="15">15 min</option>
        <option :value="30">30 min</option>
        <option :value="45">45 min</option>
        <option :value="60">60 min</option>
      </select>
      <button @click="addSpecialty">Add Specialty</button>
    </div>

    <div class="specialty-list">
      <draggable
        v-model="specialties"
        item-key="id"
        handle=".reorder-handle"
        @end="onReorder">
        <template #item="{ element: specialty, index }">
          <div
            class="specialty-item"
            :style="{ backgroundColor: specialty.color }">
            <span class="reorder-handle" title="Drag to reorder priority">&#x2630;</span>
            <span class="priority-badge">{{ index }}</span>
            <span class="specialty-name">{{ specialty.name }}</span>
            <input
              type="color"
              :value="specialty.color"
              @input="updateField(specialty, 'color', $event.target.value)"
              class="color-picker"
              @click.stop
              title="Change color"
            />
            <select
              :value="specialty.duration || 30"
              @change="updateField(specialty, 'duration', parseInt($event.target.value))"
              class="duration-select"
              @click.stop>
              <option :value="15">15m</option>
              <option :value="30">30m</option>
              <option :value="45">45m</option>
              <option :value="60">60m</option>
            </select>
            <span
              class="auto-toggle"
              :class="{ 'auto-off': specialty.auto_schedule === false }"
              @click.stop="updateField(specialty, 'auto_schedule', !specialty.auto_schedule)"
              :title="specialty.auto_schedule !== false ? 'Auto-schedule ON (click to disable)' : 'Auto-schedule OFF (click to enable)'">
              &#x2699;
            </span>
            <button @click="deleteSpecialty(specialty.id)" class="delete-btn">&times;</button>
          </div>
        </template>
      </draggable>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import draggable from 'vuedraggable'

export default {
  name: 'SpecialtyManager',
  components: { draggable },
  props: {
    activeTab: String
  },
  setup(props) {
    const specialties = ref([])
    const newSpecialty = ref({
      name: '',
      color: '#4CAF50',
      duration: 30
    })

    const loadSpecialties = async () => {
      try {
        const response = await axios.get('/api/specialties')
        specialties.value = response.data
      } catch (error) {
        console.error('Error loading specialties:', error)
      }
    }

    const addSpecialty = async () => {
      if (!newSpecialty.value.name) return

      try {
        const specialty = {
          id: Date.now().toString(),
          name: newSpecialty.value.name,
          color: newSpecialty.value.color,
          duration: newSpecialty.value.duration,
          auto_schedule: true
        }
        await axios.post('/api/specialties', specialty)
        await loadSpecialties()
        newSpecialty.value.name = ''
        newSpecialty.value.color = '#4CAF50'
        newSpecialty.value.duration = 30
      } catch (error) {
        console.error('Error adding specialty:', error)
      }
    }

    const updateField = async (specialty, field, value) => {
      try {
        const updated = { ...specialty, [field]: value }
        await axios.put(`/api/specialties/${specialty.id}`, updated)
        await loadSpecialties()
      } catch (error) {
        console.error('Error updating specialty:', error)
      }
    }

    const onReorder = async () => {
      try {
        const items = specialties.value.map((s, i) => ({
          id: s.id,
          priority: i
        }))
        await axios.put('/api/specialties/reorder', items)
        await loadSpecialties()
      } catch (error) {
        console.error('Error reordering specialties:', error)
      }
    }

    const deleteSpecialty = async (id) => {
      try {
        await axios.delete(`/api/specialties/${id}`)
        await loadSpecialties()
      } catch (error) {
        console.error('Error deleting specialty:', error)
      }
    }

    watch(() => props.activeTab, (tab) => {
      if (tab === 'specialties') loadSpecialties()
    })

    onMounted(() => {
      loadSpecialties()
    })

    return {
      specialties,
      newSpecialty,
      addSpecialty,
      updateField,
      onReorder,
      deleteSpecialty
    }
  }
}
</script>

<style scoped>
.form {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
}

.form input[type="text"] {
  flex: 1;
}

.form input[type="color"] {
  width: 50px;
  height: 36px;
  border: 2px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  padding: 2px;
}

.form input[type="color"]:hover {
  border-color: #4CAF50;
}

.form select {
  padding: 6px;
}

.specialty-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.specialty-item {
  padding: 10px 14px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}

.reorder-handle {
  cursor: grab;
  font-size: 16px;
  opacity: 0.7;
  user-select: none;
}

.reorder-handle:hover {
  opacity: 1;
}

.priority-badge {
  background: rgba(0,0,0,0.25);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: bold;
  min-width: 18px;
  text-align: center;
}

.specialty-name {
  font-weight: bold;
  font-size: 16px;
  flex: 1;
}

.color-picker {
  width: 32px;
  height: 24px;
  border: 2px solid rgba(255,255,255,0.5);
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
  background: none;
}

.color-picker:hover {
  border-color: rgba(255,255,255,0.8);
}

.duration-select {
  background: rgba(255,255,255,0.25);
  border: 1px solid rgba(255,255,255,0.4);
  border-radius: 4px;
  color: white;
  padding: 2px 4px;
  font-size: 12px;
  cursor: pointer;
}

.duration-select option {
  color: #333;
  background: white;
}

.auto-toggle {
  cursor: pointer;
  font-size: 20px;
  color: #4CAF50;
  opacity: 0.9;
}

.auto-toggle:hover {
  opacity: 1;
}

.auto-toggle.auto-off {
  color: #f44336;
  opacity: 1;
}

.delete-btn {
  background: rgba(255, 255, 255, 0.3);
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 20px;
  color: white;
}

.delete-btn:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>
