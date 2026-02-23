<template>
  <div class="form-group">
    <label v-if="field.label">{{ field.label }} <span v-if="field.required" class="required">*</span></label>

    <!-- Text input -->
    <va-input
      v-if="field.type === 'text'"
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event)"
      :placeholder="field.placeholder"
    />

    <!-- Number input -->
    <va-input
      v-else-if="field.type === 'number'"
      type="number"
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event ? Number($event) : null)"
      :placeholder="field.placeholder"
    />

    <!-- Select -->
    <va-select
      v-else-if="field.type === 'select'"
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event)"
      :options="field.options || []"
      :placeholder="field.placeholder || 'Selecione'"
      clearable
    />

    <!-- Textarea -->
    <va-textarea
      v-else-if="field.type === 'textarea'"
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event)"
      :placeholder="field.placeholder"
      :min-rows="3"
      autosize
    />

    <!-- Boolean (checkbox) -->
    <va-checkbox
      v-else-if="field.type === 'boolean'"
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event)"
      :label="field.placeholder"
    />

    <!-- Date -->
    <va-date-input
      v-else-if="field.type === 'date'"
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event)"
      :placeholder="field.placeholder"
    />

    <!-- Fallback to text -->
    <va-input
      v-else
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event)"
      :placeholder="field.placeholder"
    />
  </div>
</template>

<script setup>
defineProps({
  field: {
    type: Object,
    required: true
  },
  modelValue: {
    default: null
  }
})

defineEmits(['update:modelValue'])
</script>

<style lang="scss" scoped>
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    font-weight: 500;
    color: var(--text-dark);
    font-size: 0.875rem;

    .required {
      color: var(--danger-color, #ef4444);
    }
  }
}
</style>
