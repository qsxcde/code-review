from typing import Any

from fastapi import HTTPException, status


def build_review_prompt(system_prompt: str | None = None) -> Any:
    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="langchain-core is not installed",
        ) from exc

    return ChatPromptTemplate.from_messages(
        [
            (
                "system", system_prompt or (
                    "你是一名资深代码审查工程师。你只分析用户提供的 PR diff，"
                    "重点关注安全、逻辑正确性、异常处理、数据一致性、并发、权限控制和测试缺失。"
                    "你的回答必须是严格 JSON，不要输出 Markdown 或额外解释。"
                    "JSON 的字段名必须保持 schema 中的英文名称，但所有字段内容必须使用中文。"
                )),
            (
                "human",
                "请返回一个严格符合以下 JSON Schema 的 JSON 对象：\n"
                "{schema}\n\n"
                "PR 数据如下：\n"
                "{pr_payload}\n\n"
                "规则：\n"
                "- 只返回 JSON，不要包含 Markdown 代码块。\n"
                "- 不要在 JSON 之外输出任何说明文字。\n"
                "- JSON 字段名保持英文，例如 summary、risks、suggestions、metrics。\n"
                "- JSON 字段值必须使用中文，severity、type 等枚举值按 schema 要求保持英文。\n"
                "- 如果没有明确风险，risks 和 suggestions 返回空数组。\n"
                "- 每个问题必须对应 diff 中的具体文件。\n"
                "- 不要输出泛泛的代码风格建议。\n"
                "- confidence 必须是 0 到 1 之间的数字。",
            ),
        ]
    )
