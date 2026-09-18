<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import TierLadder from '../components/TierLadder.vue'
import SegmentTable from '../components/SegmentTable.vue'

const sides = [
  { key: 'left', label: '左侧' },
  { key: 'right', label: '右侧' },
]
const accounts = ref([])
const form = reactive({
  left: { account_id: null, kwh: 120, peak: false },
  right: { account_id: null, kwh: 400, peak: true },
})
const persist = ref(false)
const result = ref(null)
const error = ref('')
const busy = ref(false)

onMounted(async () => {
  accounts.value = (await getJSON('/api/accounts')).items
  if (accounts.value.length) {
    form.left.account_id = accounts.value[0].id
    form.right.account_id = accounts.value[accounts.value.length - 1].id
  }
})

const accountName = (id) => accounts.value.find((a) => a.id === id)?.name ?? `#${id}`

const maxTotal = computed(() =>
  result.value ? Math.max(result.value.left.total, result.value.right.total, 0) : 0
)
const barWidth = (total) => (maxTotal.value > 0 ? `${(total / maxTotal.value) * 100}%` : '0%')
const deltaHint = computed(() => {
  if (!result.value) return ''
  const d = result.value.delta
  if (d > 0) return '右侧更高'
  if (d < 0) return '左侧更高'
  return '两侧持平'
})

const run = async () => {
  error.value = ''
  busy.value = true
  try {
    result.value = await postJSON('/api/dual', {
      left: { ...form.left },
      right: { ...form.right },
      persist: persist.value,
    })
  } catch (e) {
    result.value = null
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <div class="page work">
    <h1>测算工作台</h1>
    <p class="muted">双户并列试算：一次请求对比两个户号的分段账单与合计差值。</p>

    <div class="dual-forms">
      <div class="panel" v-for="side in sides" :key="side.key">
        <h3>{{ side.label }}</h3>
        <div class="form-col">
          <label>户号
            <select v-model.number="form[side.key].account_id">
              <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}（#{{ a.id }}）</option>
            </select>
          </label>
          <label>电量(kWh) <input type="number" v-model.number="form[side.key].kwh" min="0" step="1" /></label>
          <label><input type="checkbox" v-model="form[side.key].peak" /> 尖峰系数</label>
        </div>
      </div>
    </div>

    <div class="panel action-row">
      <label><input type="checkbox" v-model="persist" /> 写入运行记录（persist）</label>
      <button @click="run" :disabled="busy">{{ busy ? '试算中…' : persist ? '试算并入库' : '试算' }}</button>
      <span v-if="!persist" class="muted">默认仅试算，不写运行记录</span>
    </div>

    <p v-if="error" class="panel error">{{ error }}</p>

    <template v-if="result">
      <div class="panel">
        <h3>差值条</h3>
        <div class="bar-row" v-for="side in sides" :key="side.key">
          <span class="bar-label">{{ side.label }} · {{ accountName(result[side.key].account_id) }}</span>
          <div class="bar"><div class="fill" :class="side.key" :style="{ width: barWidth(result[side.key].total) }"></div></div>
          <span class="bar-val">¥{{ result[side.key].total }}</span>
        </div>
        <p class="delta-line">右侧 − 左侧 = <strong>¥{{ result.delta }}</strong> <span class="muted">{{ deltaHint }}</span></p>
        <p v-if="result.run_ids" class="muted">
          已入库：左侧 #{{ result.run_ids.left }} · 右侧 #{{ result.run_ids.right }}
          <router-link to="/history">查看测算记录</router-link>
        </p>
        <p v-else class="muted">仅试算，未写入运行记录</p>
      </div>

      <div class="dual-results">
        <div class="panel" v-for="side in sides" :key="side.key">
          <h3>{{ side.label }} · {{ accountName(result[side.key].account_id) }}</h3>
          <p>
            合计 <span class="hero-num-sm">¥{{ result[side.key].total }}</span>
            <span class="muted">
              {{ result[side.key].kwh }} kWh<template v-if="result[side.key].peak"> · 尖峰 ×{{ result[side.key].peak_factor }}</template>
            </span>
          </p>
          <TierLadder :segments="result[side.key].segments" />
          <SegmentTable :rows="result[side.key].segments" />
        </div>
      </div>
    </template>
  </div>
</template>
<style scoped>
.dual-forms, .dual-results { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 820px) { .dual-forms, .dual-results { grid-template-columns: 1fr; } }
.form-col { display: flex; flex-direction: column; gap: 0.6rem; align-items: flex-start; }
select { background: #0d1612; border: 1px solid var(--muted); color: var(--text); padding: 0.35rem 0.5rem; border-radius: 6px; margin-left: 0.35rem; }
input[type=number] { width: 7rem; margin-left: 0.35rem; }
.action-row { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; }
button:disabled { opacity: 0.6; cursor: default; }
.error { border: 1px solid #d96a6a; color: #f0a8a8; }
.bar-row { display: flex; align-items: center; gap: 0.6rem; margin: 0.35rem 0; }
.bar-label { width: 10rem; font-size: 0.85rem; color: var(--muted); }
.bar { flex: 1; height: 14px; background: #0d1612; border-radius: 7px; overflow: hidden; }
.fill { height: 100%; }
.fill.left { background: var(--accent); }
.fill.right { background: #d9a441; }
.bar-val { width: 6rem; text-align: right; }
.delta-line { margin-top: 0.6rem; }
.hero-num-sm { font-size: 1.6rem; font-weight: 700; color: var(--accent); }
</style>
