<script setup lang="ts">
import { AlertTriangle, Ban, Loader2, Play } from "lucide-vue-next";

defineProps<{
  modelValue: string;
  loading: boolean;
  canSubmit: boolean;
  errorMessage: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  submit: [];
  cancel: [];
}>();
</script>

<template>
  <form class="input-band" @submit.prevent="emit('submit')">
    <label class="input-label" for="pr-url">GitHub PR URL</label>
    <div class="input-row">
      <input
        id="pr-url"
        :value="modelValue"
        type="url"
        placeholder="https://github.com/owner/repo/pull/123"
        autocomplete="off"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <button class="primary-button" type="submit" :disabled="!canSubmit">
        <Loader2 v-if="loading" class="spin" :size="18" />
        <Play v-else :size="18" />
        <span>{{ loading ? "分析中" : "开始分析" }}</span>
      </button>
      <button
        v-if="loading"
        class="cancel-button"
        type="button"
        @click="emit('cancel')"
      >
        <Ban :size="18" />
        <span>取消</span>
      </button>
    </div>
    <p v-if="errorMessage" class="error-text">
      <AlertTriangle :size="16" />
      {{ errorMessage }}
    </p>
  </form>
</template>
