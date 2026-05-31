import { reactive } from "vue";
import { phaseLabel } from "../utils/progressLabels";
import type { ProgressState, ReviewProgressEvent } from "../types/review";

export const useAnalysisProgress = () => {
  const progressState = reactive<ProgressState>({
    percent: 0,
    currentPhase: "",
    reconnecting: false,
    agents: {
      "[安全]": "idle",
      "[性能]": "idle",
      "[风格]": "idle",
    },
    agentRisks: {},
  });

  const resetProgress = () => {
    progressState.percent = 0;
    progressState.currentPhase = "";
    progressState.reconnecting = false;
    progressState.agents["[安全]"] = "idle";
    progressState.agents["[性能]"] = "idle";
    progressState.agents["[风格]"] = "idle";
    progressState.agentRisks = {};
  };

  const updateProgress = (event: ReviewProgressEvent) => {
    progressState.reconnecting = event.message === "重新连接中...";
    if (event.percent !== undefined) progressState.percent = event.percent;

    const nextLabel = phaseLabel(event.event, event.phase, event.agent);
    progressState.currentPhase = event.message || nextLabel || progressState.currentPhase;

    if (event.agent) {
      if (event.event === "agent_done") progressState.agents[event.agent] = "done";
      else if (event.event === "agent_error") progressState.agents[event.agent] = "error";
      else if (event.event === "agent_skipped") progressState.agents[event.agent] = "skipped";
      else progressState.agents[event.agent] = "running";

      if (event.event === "agent_done") {
        progressState.agentRisks[event.agent] = {
          risks: event.risks || 0,
          high: event.high || 0,
        };
      }
    }
  };

  return {
    progressState,
    resetProgress,
    updateProgress,
  };
};
