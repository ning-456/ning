"""批量评估脚本 - 读取赛题并生成提交文件"""

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

import config
from engine.pipeline import CustomerServicePipeline


def load_questions(csv_path: str) -> list[dict]:
    questions = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return questions
        id_idx = header.index("id")
        q_idx = header.index("question")
        for row in reader:
            if len(row) <= max(id_idx, q_idx):
                continue
            questions.append({"id": row[id_idx].strip(), "question": row[q_idx].strip()})
    return questions


def parse_question(text: str) -> str:
    import re
    text = text.strip().strip("\"").strip("'")
    text = text.replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", text).strip()


def main():
    parser = argparse.ArgumentParser(description="批量评估客服智能体")
    parser.add_argument("--input", default=str(config.QUESTION_CSV_PATH))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "submission_result.csv"))
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    all_q = load_questions(args.input)
    target = [q for q in all_q if args.start <= int(q["id"]) <= (args.end or 9999)]
    print(f"处理 {len(target)} 道题...")

    pipeline = CustomerServicePipeline()
    pipeline.load_knowledge_base()

    results = []
    total = len(target)
    start_time = time.time()

    for idx, item in enumerate(target, 1):
        q = parse_question(item["question"])
        print(f"  [{idx}/{total}] 题#{item['id']} ... ", end="")
        try:
            t0 = time.time()
            answer, _ = pipeline.process(q)
            results.append({"id": item["id"], "ret": answer})
            print(f"完成 ({time.time()-t0:.2f}s)")
        except Exception as e:
            results.append({"id": item["id"], "ret": f"处理异常: {e}"})
            print(f"失败: {e}")

    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "ret"])
        for r in results:
            w.writerow([r["id"], r["ret"]])

    elapsed = time.time() - start_time
    print(f"\n完成! 总耗时:{elapsed:.2f}s 输出:{args.output}")

if __name__ == "__main__":
    main()