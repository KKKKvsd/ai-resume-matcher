"""
app/schemas/keyword.py

结构化关键词输出 schema。
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


KeywordSource = Literal["rule", "llm", "merged"]
KeywordImportance = Literal["required", "preferred", "nice_to_have"]


class KeywordItem(BaseModel):
    """单个关键词的结构化表示。"""
    name: str = Field(..., description="标准化后的关键词名称。")
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(default="general")
    importance: KeywordImportance = Field(default="preferred")
    source: KeywordSource = Field(default="rule")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class KeywordExtractionResult(BaseModel):
    """关键词抽取的最终结果。"""
    keywords: list[KeywordItem] = Field(default_factory=list)
    total: int = 0
    rule_only: int = 0
    llm_only: int = 0
    merged: int = 0
    mode: Literal["hybrid", "rule_only", "llm_only"] = "hybrid"
    warnings: list[str] = Field(default_factory=list)

    def to_legacy_list(self) -> list[str]:
        """
        向后兼容:旧代码需要 list[str]。
        按重要度排序,required 优先。
        """
        priority = {"required": 0, "preferred": 1, "nice_to_have": 2}
        sorted_items = sorted(
            self.keywords,
            key=lambda item: (priority.get(item.importance, 3), item.name.lower()),
        )
        return [item.name for item in sorted_items]