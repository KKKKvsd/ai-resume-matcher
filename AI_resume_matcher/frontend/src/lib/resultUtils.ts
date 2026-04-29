export function safeArray(value: unknown): string[] {
  if (!value) return [];

  if (Array.isArray(value)) {
    return value.map((item) => {
      if (typeof item === "string") return item;
      return safeStringify(item);
    });
  }

  if (typeof value === "string") {
    const trimmed = value.trim();

    if (!trimmed) return [];

    try {
      const parsed = JSON.parse(trimmed);

      if (Array.isArray(parsed)) {
        return parsed.map((item) => {
          if (typeof item === "string") return item;
          return safeStringify(item);
        });
      }

      return [safeStringify(parsed)];
    } catch {
      return trimmed
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }

  return [safeStringify(value)];
}

export function safeEvidence(value: unknown): unknown[] {
  if (!value) return [];

  if (Array.isArray(value)) return value;

  if (typeof value === "string") {
    const trimmed = value.trim();

    if (!trimmed) return [];

    try {
      const parsed = JSON.parse(trimmed);
      return Array.isArray(parsed) ? parsed : [parsed];
    } catch {
      return [trimmed];
    }
  }

  return [value];
}

export function safeStringify(value: unknown): string {
  if (typeof value === "string") return value;

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function formatDate(value?: string) {
  if (!value) return "-";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function getScoreLabel(score: number | null | undefined) {
  if (score === null || score === undefined) return "暂无评分";
  if (score >= 85) return "高度匹配";
  if (score >= 70) return "较匹配";
  if (score >= 50) return "一般匹配";
  return "匹配度偏低";
}