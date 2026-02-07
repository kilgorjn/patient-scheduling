<template>
  <div id="app">
    <h1>Patient Scheduling</h1>

    <div class="tabs">
      <button
        @click="activeTab = 'schedule'"
        :class="{ active: activeTab === 'schedule' }">
        Schedule
      </button>
      <button
        @click="activeTab = 'specialties'"
        :class="{ active: activeTab === 'specialties' }">
        Manage Specialties
      </button>
      <button
        @click="activeTab = 'teams'"
        :class="{ active: activeTab === 'teams' }">
        Manage Teams
      </button>
    </div>

    <div v-if="activeTab === 'schedule'">
      <ScheduleGrid />
    </div>

    <div v-if="activeTab === 'specialties'">
      <SpecialtyManager />
    </div>

    <div v-if="activeTab === 'teams'">
      <TeamManager />
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import ScheduleGrid from './components/ScheduleGrid.vue'
import SpecialtyManager from './components/SpecialtyManager.vue'
import TeamManager from './components/TeamManager.vue'

export default {
  name: 'App',
  components: {
    ScheduleGrid,
    SpecialtyManager,
    TeamManager
  },
  setup() {
    const activeTab = ref('schedule')

    return {
      activeTab
    }
  }
}
</script>

<style scoped>
.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tabs button {
  background-color: #e0e0e0;
  color: #333;
}

.tabs button.active {
  background-color: #4CAF50;
  color: white;
}

.tabs button:hover {
  background-color: #d0d0d0;
}

.tabs button.active:hover {
  background-color: #45a049;
}
</style>
