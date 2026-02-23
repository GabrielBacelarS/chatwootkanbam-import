<template>
  <div class="chips-input" :class="{ 'chips-input--focused': isFocused }">
    <label v-if="label" class="chips-label">{{ label }}</label>
    <div class="chips-container" @click="focusInput">
      <va-chip
        v-for="(chip, index) in modelValue"
        :key="index"
        closeable
        size="small"
        color="primary"
        @update:modelValue="removeChip(index)"
      >
        {{ chip }}
      </va-chip>
      <input
        ref="inputRef"
        v-model="inputValue"
        type="text"
        class="chips-input-field"
        :placeholder="modelValue.length === 0 ? placeholder : ''"
        @keydown.enter.prevent="addChip"
        @keydown.backspace="handleBackspace"
        @focus="isFocused = true"
        @blur="handleBlur"
      />
    </div>
    <small v-if="hint" class="chips-hint">{{ hint }}</small>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: 'Digite e pressione Enter'
  },
  hint: {
    type: String,
    default: ''
  },
  separator: {
    type: String,
    default: ','
  }
})

const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)
const inputValue = ref('')
const isFocused = ref(false)

const focusInput = () => {
  inputRef.value?.focus()
}

const addChip = () => {
  const value = inputValue.value.trim()
  if (value && !props.modelValue.includes(value)) {
    emit('update:modelValue', [...props.modelValue, value])
    inputValue.value = ''
  }
}

const removeChip = (index) => {
  const newValue = [...props.modelValue]
  newValue.splice(index, 1)
  emit('update:modelValue', newValue)
}

const handleBackspace = () => {
  if (inputValue.value === '' && props.modelValue.length > 0) {
    removeChip(props.modelValue.length - 1)
  }
}

const handleBlur = () => {
  isFocused.value = false
  // Add chip on blur if there's text
  if (inputValue.value.trim()) {
    addChip()
  }
}
</script>

<style lang="scss" scoped>
.chips-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.chips-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-dark);
}

.chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  min-height: 42px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-card);
  cursor: text;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--primary-color);
  }

  .chips-input--focused & {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
  }
}

.chips-input-field {
  flex: 1;
  min-width: 100px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.875rem;
  color: var(--text-color);
  padding: 0.25rem 0;

  &::placeholder {
    color: var(--text-muted);
  }
}

.chips-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
}
</style>
