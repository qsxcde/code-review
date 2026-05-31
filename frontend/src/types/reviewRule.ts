export type ReviewRuleCategory = "security" | "performance" | "style" | "custom";

export interface RuleFileFilters {
  include: string[];
  exclude: string[];
}

export interface ReviewRule {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  category: ReviewRuleCategory;
  prompt_content: string;
  file_filters: RuleFileFilters | null;
  is_enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface ReviewRuleListResponse {
  items: ReviewRule[];
  total: number;
}

export interface ReviewRulePayload {
  name: string;
  description?: string | null;
  category: ReviewRuleCategory;
  prompt_content: string;
  file_filters?: RuleFileFilters | null;
  priority: number;
}

export type ReviewRuleUpdatePayload = Partial<ReviewRulePayload> & {
  is_enabled?: boolean;
};
