"""
精准验证 LLM 服务方是否真的支持 streaming。
"""
import time
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

print(f"=== Testing stream ===")
print(f"BASE_URL: {settings.LLM_BASE_URL}")
print(f"MODEL: {settings.LLM_MODEL}")
print()

start = time.perf_counter()

stream = client.chat.completions.create(
    model=settings.LLM_MODEL,
    messages=[{"role": "user", "content": "请写一段 200 字的关于人工智能的科普介绍"}],
    stream=True,
)

times = []
chunks = []

for chunk in stream:
    elapsed = time.perf_counter() - start
    if chunk.choices and chunk.choices[0].delta.content:
        text = chunk.choices[0].delta.content
        times.append(elapsed)
        chunks.append(text)

total_time = time.perf_counter() - start

print(f"\n=== Summary ===")
print(f"Total chunks: {len(chunks)}")
print(f"Total time:   {total_time:.2f}s")
print(f"First chunk:  {times[0]:.3f}s   (TTFB)")
print(f"Last chunk:   {times[-1]:.3f}s")
print(f"Span:         {times[-1] - times[0]:.3f}s   ← 这个数字是关键")
print()

if times[-1] - times[0] < 0.5:
    print("❌ 服务方不真支持 streaming - 所有 chunk 在 < 0.5s 内到达")
elif times[-1] - times[0] < total_time * 0.5:
    print("⚠️  服务方半缓冲 - chunk 集中在某个时间段")
else:
    print("✓ 服务方真的在 streaming - chunk 均匀分布")

print()
print("=== Time distribution ===")
import_indices = (
    list(range(min(5, len(times))))
    + list(range(len(times)//2, min(len(times)//2 + 5, len(times))))
    + list(range(max(0, len(times) - 5), len(times)))
)
for i in sorted(set(import_indices)):
    print(f"  chunk {i+1:3d}/{len(chunks)}: {times[i]:.3f}s   {chunks[i]!r}")