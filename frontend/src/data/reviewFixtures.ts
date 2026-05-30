import type {
  AiSuggestion,
  AiSummaryStats,
  ChangedFile,
  CodeLine,
  Issue,
  PullRequestInfo,
  RiskFile,
  RiskStats,
  SummaryItem,
} from "../types/review";

export const defaultPullRequest: PullRequestInfo = {
  repository: "org/ecommerce-platform",
  visibility: "公开仓库",
  title: "feat: 支付回调重试机制与订单状态流转重构",
  description: "实现支付回调失败重试机制，优化订单状态流转逻辑，提升系统稳定性。",
  author: "李明",
  sourceBranch: "feature/payment-retry",
  targetBranch: "develop",
  createdAt: "2026-05-20 14:32",
  updatedAt: "2026-05-21 09:15",
  state: "Open",
  changedFiles: 18,
  additions: 523,
  deletions: 312,
};

export const defaultSummaryItems: SummaryItem[] = [
  { text: "新增支付回调重试机制，支持最多 3 次重试", tag: "新增功能", tone: "green" },
  { text: "重构订单状态流转逻辑，引入新的状态更新方法", tag: "重构", tone: "blue" },
  { text: "修改 payment_service.py 的支付成功回调处理流程", tag: "重构", tone: "blue" },
  { text: "补充订单不存在时的异常处理逻辑", tag: "优化", tone: "orange" },
  { text: "新增相关单元测试覆盖重试和回调失败场景", tag: "测试", tone: "violet" },
];

export const defaultRiskFiles: RiskFile[] = [
  { path: "service/payment_service.py", count: 6, high: 3, medium: 2, low: 1 },
  { path: "controller/order_controller.java", count: 4, high: 2, medium: 2, low: 0 },
  { path: "repository/order_repository.py", count: 2, high: 1, medium: 1, low: 0 },
];

export const defaultRiskStats: RiskStats = {
  high: 6,
  medium: 5,
  low: 1,
  total: 12,
};

export const defaultAiSummaryStats: AiSummaryStats = {
  riskLevel: "高风险",
  riskTone: "high",
  riskIssues: 12,
  involvedFiles: 3,
  mergeAdvice: "建议修复后合并",
};

export const defaultChangedFiles: ChangedFile[] = [
  { path: "service/payment_service.py", folder: "service", name: "payment_service.py", alerts: 6, active: true },
  { path: "service/order_service.py", folder: "service", name: "order_service.py", alerts: 3 },
  { path: "controller/order_controller.java", folder: "controller", name: "order_controller.java", alerts: 4 },
  { path: "controller/payment_controller.py", folder: "controller", name: "payment_controller.py", alerts: 2 },
  { path: "repository/order_repository.py", folder: "repository", name: "order_repository.py", alerts: 2 },
  { path: "test/test_payment_retry.py", folder: "test", name: "test_payment_retry.py", alerts: 1 },
  { path: "test/test_order_service.py", folder: "test", name: "test_order_service.py", alerts: 1 },
];

export const defaultCodeLines: CodeLine[] = [
  { line: 118, mark: " ", code: "@@ -118,15 +118,18 @@ def handle_payment_callback(self, request):" },
  { line: 119, mark: " ", code: "# 验证回调签名" },
  { line: 120, mark: " ", code: "if not self._verify_signature(request):" },
  { line: 121, mark: " ", code: "    return self._error_response(\"invalid signature\")" },
  { line: 122, mark: "-", code: "order_id = request.json[\"order_id\"]" },
  { line: 123, mark: "-", code: "payment_id = request.json[\"payment_id\"]" },
  { line: 124, mark: "-", code: "amount = request.json[\"amount\"]" },
  { line: 126, mark: "+", code: "order_id = request.json.get(\"order_id\")" },
  { line: 127, mark: "+", code: "payment_id = request.json.get(\"payment_id\")" },
  { line: 128, mark: "+", code: "amount = request.json.get(\"amount\")" },
  { line: 130, mark: "+", code: "if not order_id or not payment_id:" },
  { line: 131, mark: "+", code: "    return self._error_response(\"missing required parameters\")" },
  { line: 134, mark: " ", code: "order = self.order_service.get_order(order_id)" },
  { line: 135, mark: " ", code: "if not order:" },
  { line: 136, mark: " ", code: "    return self._error_response(\"order not found\")" },
];

export const defaultAiSuggestions: AiSuggestion[] = [
  {
    level: "高风险",
    title: "参数获取可能导致 KeyError 异常",
    line: "第122-124行",
    description: "直接读取 request.json 字段会在参数缺失时抛异常，建议统一使用 get 并增加必要性校验。",
  },
  {
    level: "中风险",
    title: "金额参数校验可以更完善",
    line: "第128-129行",
    description: "当前仅做非空校验，建议补充数值格式、精度和币种一致性检查。",
  },
];

export const defaultTopIssues: Issue[] = [
  { title: "支付回调可能重复提交", file: "payment_service.py:128", level: "high" },
  { title: "订单状态并发更新风险", file: "order_controller.java:276", level: "high" },
  { title: "权限校验可能缺失", file: "payment_controller.py:88", level: "medium" },
];
