"""直接用 requests 测后端 SSE 是不是真 streaming"""
import requests
import time

# 改成你登录后拿到的 token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJjc3lAZXhhbXBsZS5jb20iLCJleHAiOjE3Nzc3NjM1MDV9.1hrbuWC-qtvuqQ1-cT-5-oPIlTvrHXZ4CGh0C2gZJU0"

start = time.perf_counter()

r = requests.post(
    "http://127.0.0.1:8000/api/v1/match/agent/stream",
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    },
    json={"query": "请详细分析我的简历适合哪些岗位,至少 200 字"},
    stream=True,  # 关键:让 requests 不缓冲整个响应
    timeout=120,
)

print(f"Status: {r.status_code}")
print(f"Headers: {dict(r.headers)}")
print()
print("=== Events ===")

event_count = 0
for line in r.iter_lines(decode_unicode=True):
    elapsed = time.perf_counter() - start
    if line and line.startswith("data: "):
        event_count += 1
        # 只显示前 50 字
        preview = line[:80]
        print(f"[{elapsed:6.2f}s] event {event_count}: {preview}")

print(f"\nTotal events: {event_count}")
print(f"Total time: {time.perf_counter() - start:.2f}s")