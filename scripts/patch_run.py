"""补跑脚本"""
import csv, re, os, sys, time
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("USE_LLM", "true")
os.environ.setdefault("LLM_API_KEY", "ollama")
os.environ.setdefault("LLM_API_BASE", "http://localhost:11434/v1")
os.environ.setdefault("LLM_MODEL", "qwen2.5:3b")
os.environ.setdefault("LLM_TEMPERATURE", "0.3")
os.environ.setdefault("LLM_MAX_TOKENS", "256")

import importlib
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
import config as _cfg
importlib.reload(_cfg)
from engine.pipeline import CustomerServicePipeline

REDO_IDS = {241, 242, 244, 245, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 271, 272, 273, 274, 276, 279, 290, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436}

root = Path(__file__).parent.parent.absolute()
out = root / "results" / "submission3.csv"
existing = {}
if out.exists():
    with open(out, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if row: existing[int(row[0])] = row[1]

qs = {}
with open(root / "data" / "question_public.csv", "r", encoding="utf-8") as f:
    for line in f:
        m = re.match(r"(\d+),", line.strip())
        if m:
            qid = int(m.group(1))
            qs[qid] = line.strip().split(",", 1)[-1].strip(chr(34)).strip()

print("=== Patch run:", len(REDO_IDS), "questions ===")
t0 = time.time()
pl = CustomerServicePipeline()
pl.load_knowledge_base()

new = {}
for idx, qid in enumerate(sorted(REDO_IDS)):
    q = qs.get(qid, "")
    if not q: continue
    if len(q) > 800: q = q[:800]
    t1 = time.time()
    try:
        ans, _ = pl.process(q)
        ans = ans.strip()[:2000]
    except Exception as e:
        ans = "[ERROR] " + str(e)
    new[qid] = ans
    t = time.time() - t1
    tt = time.time() - t0
    tag = "OK" if "Sorry" not in ans else "NO"
    sq = q[:40].encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    sa = ans[:50].encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    print(f"  [{idx+1}/{len(REDO_IDS)}] Q{qid} ({t:.0f}s) [{tag}] {sq} -> {sa}")
    if (idx+1) % 10 == 0 or idx == len(REDO_IDS)-1:
        merged = dict(existing)
        merged.update(new)
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "ret"])
            for qid2 in sorted(merged):
                w.writerow([qid2, merged[qid2]])

tt = time.time() - t0
merged = dict(existing)
merged.update(new)
print(f"Done: {len(new)} in {tt:.0f}s, total: {len(merged)}/400")