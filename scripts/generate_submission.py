"""
批量评估脚本：读取 question_public.csv，逐题调用 Pipeline，
生成 submission5.csv（id,ret 格式）。
使用 Qwen2.5-3B-Instruct（Ollama API）。
"""
import csv, re, os, sys, time, json
from pathlib import Path

# Fix console encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 设置 LLM 环境变量
os.environ.setdefault("USE_LLM", "true")
os.environ.setdefault("LLM_API_KEY", "ollama")
os.environ.setdefault("LLM_API_BASE", "http://localhost:11434/v1")
os.environ.setdefault("LLM_MODEL", "qwen2.5:3b")
os.environ.setdefault("LLM_TEMPERATURE", "0.5")
os.environ.setdefault("LLM_MAX_TOKENS", "256")

import importlib
import config as _cfg_mod
importlib.reload(_cfg_mod)

sys.path.insert(0, str(Path(__file__).parent.absolute()))
from engine.pipeline import CustomerServicePipeline


def parse_question_csv(path):
    """解析 question_public.csv，返回 [(id, full_question)]"""
    results = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("id,"):
            continue

        id_match = re.match(r"(\d+),", line)
        if not id_match:
            continue
        qid = int(id_match.group(1))

        all_text = line
        while i < len(lines):
            next_line = lines[i].strip()
            if not next_line:
                i += 1
                continue
            if re.match(r"^\d+,", next_line):
                break
            if next_line.startswith('"""') or next_line.startswith('"""'):
                all_text += next_line
                i += 1
            else:
                break

        all_qs = re.findall(r'"""(.*?)"""', all_text, re.DOTALL)
        if all_qs:
            full_q = " ".join(q.strip() for q in all_qs if q.strip())
        else:
            full_q = all_text.split(",", 1)[-1].strip().strip('"')

        results.append((qid, full_q))

    return results


def main():
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "data" / "question_public.csv"
    output_path = project_root / "results" / "submission5.csv"

    print("=== Initializing pipeline with Qwen2.5-3B-Instruct ===")
    t_start = time.time()

    pipeline = CustomerServicePipeline()
    pipeline.load_knowledge_base()
    print("Pipeline ready.\n")

    questions = parse_question_csv(str(csv_path))
    print(f"Total questions: {len(questions)}\n")

    results = []
    errors = []
    llm_count = 0
    cs_count = 0
    sorry_count = 0
    rule_count = 0

    # 断点续跑：读取已有 submission5.csv，跳过已处理的题
    skip_count = 0
    start_from = int(os.environ.get("START_FROM", "0"))
    if os.path.exists(str(output_path)):
        try:
            with open(str(output_path), "r", encoding="utf-8-sig") as _f:
                _reader = csv.reader(_f)
                _headers = next(_reader, None)
                for _row in _reader:
                    if len(_row) >= 2:
                        _done_id, _done_ans = int(_row[0]), _row[1]
                        results.append((_done_id, _done_ans))
                        skip_count += 1
                        if _done_ans.startswith("Sorry") or _done_ans.startswith("未找到"):
                            sorry_count += 1
                        elif any(kw in _done_ans[:20] for kw in ["您好", "你好"]):
                            cs_count += 1
                        else:
                            llm_count += 1
            print(f"Resuming: {skip_count} questions already processed, starting from Q{skip_count + 1}")
        except Exception as _e:
            print(f"Could not read existing csv, starting fresh: {_e}")
            results = []

    for idx, (qid, question) in enumerate(questions):
        if idx < skip_count:
            if qid < start_from:
                continue
        t0 = time.time()
        try:
            if len(question) > 800:
                question_trunc = question[:800]
            else:
                question_trunc = question

            answer, _ = pipeline.process(question_trunc)
            answer = answer.strip()
            if len(answer) > 2000:
                answer = answer[:2000]

            # 统计回答类型
            if answer.startswith("Sorry") or answer.startswith("未找到"):
                sorry_count += 1
            elif any(kw in answer[:20] for kw in ["您好", "你好"]):
                cs_count += 1
            else:
                llm_count += 1

        except Exception as e:
            answer = f"[ERROR] {e}"
            errors.append((qid, str(e)))

        elapsed = time.time() - t0
        results.append((qid, answer))

        # 每 10 题增量保存，防止中断丢失
        if (idx + 1) % 10 == 0:
            import csv as _csv
            with open(str(output_path), "w", encoding="utf-8-sig", newline="") as _f:
                _w = _csv.writer(_f)
                _w.writerow(["id", "ret"])
                for _qid, _ans in results:
                    _w.writerow([_qid, _ans])

        if (idx + 1) % 10 == 0 or idx == 0 or idx == len(questions) - 1:
            elapsed_total = time.time() - t_start
            try:
                msg = f'  [{idx+1}/{len(questions)}] Q{qid} ({elapsed:.1f}s, total {elapsed_total:.0f}s) -> {answer[:60]}...'
                print(msg)
            except UnicodeEncodeError:
                safe = answer[:60].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                print(f'  [{idx+1}/{len(questions)}] Q{qid} ({elapsed:.1f}s, total {elapsed_total:.0f}s) -> {safe}...')

    # 写入 submission1.csv
    with open(str(output_path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "ret"])
        for qid, answer in results:
            writer.writerow([qid, answer])

    elapsed_total = time.time() - t_start
    print(f"\n{'='*50}")
    print(f"Done! {len(results)} answers -> {output_path}")
    print(f"Total time: {elapsed_total:.0f}s ({elapsed_total/60:.1f} min)")
    print(f"  LLM-generated: {llm_count}")
    print(f"  CS template matches: {cs_count}")
    print(f"  Sorry/no-result: {sorry_count}")
    print(f"  Rule-based (estimated): {len(results) - llm_count - cs_count - sorry_count}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for qid, err in errors[:10]:
            print(f"  Q{qid}: {err}")

    # JSON 详情输出
    json_path = project_root / "results" / "submission5_detail.json"
    with open(str(json_path), "w", encoding="utf-8") as f:
        json.dump([{"id": str(qid), "question": q, "answer": a}
                    for (qid, q), (_, a) in zip(questions, results)],
                  f, ensure_ascii=False, indent=2)
    print(f"Detail -> {json_path}")

if __name__ == "__main__":
    main()
