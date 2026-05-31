import { ref } from "vue";
import { ElMessage } from "element-plus";
import { submitReviewFeedback } from "../api/historyApi";
import type { FeedbackRating } from "../types/review";

export const useReviewFeedback = (
  apiBaseUrl: string,
  getAccessToken: () => string,
) => {
  const currentRecordId = ref<number | null>(null);
  const feedbackState = ref<Record<string, FeedbackRating>>({});

  const setRecordId = (id: number | null) => {
    currentRecordId.value = id;
  };

  const sendFeedback = async (riskIndex: number, rating: FeedbackRating) => {
    if (!currentRecordId.value) return;

    await submitReviewFeedback(apiBaseUrl, getAccessToken(), currentRecordId.value, riskIndex, rating);
    feedbackState.value[`${currentRecordId.value}-${riskIndex}`] = rating;
    ElMessage.success("反馈已提交");
  };

  return {
    feedbackState,
    setRecordId,
    sendFeedback,
  };
};
