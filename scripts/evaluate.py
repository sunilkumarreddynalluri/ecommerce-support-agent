"""Run the benchmark. Add more cases to eval/test_cases.json (aim for 40-50).
Usage: python -m scripts.evaluate
Each case runs on a fresh conversation thread.
"""
import json
import time
import uuid

from app.agent import chat

cases = json.load(open("eval/test_cases.json"))
results = []
tool_ok = text_ok = full_ok = 0
t0 = time.time()

for c in cases:
    start = time.time()
    reply, tools = chat(c["message"], uuid.uuid4().hex)
    used = set(tools)
    t_pass = bool(
        set(c.get("expect_all", [])) <= used
        and (not c.get("expect_any") or (used & set(c["expect_any"])))
        and not (used & set(c.get("forbid", [])))
    )
    x_pass = bool((not c.get("contains")) or any(k.lower() in reply.lower() for k in c["contains"]))
    tool_ok += t_pass
    text_ok += x_pass
    full_ok += t_pass and x_pass
    results.append({"id": c["id"], "tool_pass": t_pass, "text_pass": x_pass,
                    "tools": tools, "reply": reply, "seconds": round(time.time() - start, 2)})
    print(f"#{c['id']:>2} tools={'OK ' if t_pass else 'BAD'} text={'OK ' if x_pass else 'BAD'} used={tools}")
    if not (t_pass and x_pass):
        print(f"     reply: {reply[:200]}")

n = len(cases)
print(f"\nTool-selection accuracy : {tool_ok}/{n} = {tool_ok / n:.0%}")
print(f"Answer-content accuracy : {text_ok}/{n} = {text_ok / n:.0%}")
print(f"Fully correct           : {full_ok}/{n} = {full_ok / n:.0%}")
print(f"Avg latency/case        : {(time.time() - t0) / n:.1f}s")
json.dump(results, open("eval/results.json", "w"), indent=2)