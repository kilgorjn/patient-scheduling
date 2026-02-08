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
      <button @click="addSpecialty">Add Specialty</button>
    </div>

    <div class="specialty-list">
      <div
        v-for="specialty in specialties"
        :key="specialty.id"
        class="specialty-item"
        :style="{ backgroundColor: specialty.color }">
        <span class="specialty-name">{{ specialty.name }}</span>
        <button @click="deleteSpecialty(specialty.id)" class="delete-btn">×</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'SpecialtyManager',
  props: {
    activeTab: String
  },
  setup(props) {
    const specialties = ref([])
    const newSpecialty = ref({
      name: '',
      color: '#4CAF50'
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
          color: newSpecialty.value.color
        }
        await axios.post('/api/specialties', specialty)
        await loadSpecialties()
        newSpecialty.value.name = ''
        newSpecialty.value.color = '#4CAF50'
      } catch (error) {
        console.error('Error adding specialty:', error)
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
}

.form input {
  flex: 1;
}

.specialty-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.specialty-item {
  padding: 15px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: white;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}

.specialty-name {
  font-weight: bold;
  font-size: 16px;
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
