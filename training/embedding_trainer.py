"""Embedding 模型领域自适应微调

在手册数据上微调 bge-small-zh-v1.5，提升领域检索效果。

用法:
    python training/prepare_training_data.py   # 先准备数据
    python training/embedding_trainer.py       # 开始训练
"""

import json
import math
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

import config


def load_triplets(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def train():
    """使用对比学习微调 embedding 模型"""
    triplets_path = Path(PROJECT_ROOT) / "training" / "train_triplets.json"

    if not triplets_path.exists():
        print(f"[错误] 训练数据不存在: {triplets_path}")
        print("请先运行: python training/prepare_training_data.py")
        sys.exit(1)

    triplets = load_triplets(triplets_path)
    print(f"加载 {len(triplets)} 个训练样本")

    try:
        import torch
        import torch.nn.functional as F
        from sentence_transformers import SentenceTransformer, InputExample, losses
        from torch.utils.data import DataLoader
    except ImportError as e:
        print(f"[错误] 缺少依赖: {e}")
        print("请安装: pip install sentence-transformers torch")
        sys.exit(1)

    # 加载 base 模型
    print(f"加载 base 模型: {config.EMBEDDING_MODEL}")
    model = SentenceTransformer(config.EMBEDDING_MODEL)

    # 准备训练数据（Triplet格式）
    train_examples = []
    for t in triplets:
        train_examples.append(InputExample(
            texts=[t["query"], t["positive"], t["negative"]]
        ))

    # 按 query 长度排序提升训练效率（可选，已去掉以简化）
    batch_size = 16
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)

    # Triplet loss: 让 query 与 positive 距离近，与 negative 距离远
    train_loss = losses.TripletLoss(model=model)

    # 训练参数
    num_epochs = 3
    warmup_steps = int(len(train_dataloader) * num_epochs * 0.1)
    output_path = str(PROJECT_ROOT / "training" / "finetuned_embedding_model")

    print(f"\n开始训练...")
    print(f"  样本数: {len(train_examples)}")
    print(f"  批次大小: {batch_size}")
    print(f"  迭代轮数: {num_epochs}")
    print(f"  预热步数: {warmup_steps}")
    print(f"  输出路径: {output_path}")

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=num_epochs,
        warmup_steps=warmup_steps,
        output_path=output_path,
        show_progress_bar=True,
        checkpoint_save_steps=0,
        checkpoint_path=None,
    )

    print(f"\n训练完成! 模型已保存至: {output_path}")
    print(f"\n使用微调后的模型:")
    print(f"  # 修改 config.py 中的 EMBEDDING_MODEL 为:")
    print(f'  EMBEDDING_MODEL = r"{output_path}"')
    print(f"  # 然后重新构建知识库:")
    print(f"  python data_processing/build_knowledge_base.py")


def quick_eval():
    """快速评估：对比微调前后在手册检索上的效果"""
    triplets_path = Path(PROJECT_ROOT) / "training" / "train_triplets.json"
    if not triplets_path.exists():
        return

    triplets = load_triplets(triplets_path)
    test_set = triplets[:50]
    if len(test_set) < 10:
        return

    print("\n快速评估微调效果（取前50个样本测试）...")

    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        return

    base_model = SentenceTransformer(config.EMBEDDING_MODEL)
    finetuned_path = str(PROJECT_ROOT / "training" / "finuned_embedding_model")

    models_to_eval = [("base", base_model)]
    if os.path.exists(finetuned_path):
        ft_model = SentenceTransformer(finetuned_path)
        models_to_eval.append(("finetuned", ft_model))

    for name, model_obj in models_to_eval:
        correct = 0
        for t in test_set:
            q_emb = model_obj.encode([t["query"]])
            p_emb = model_obj.encode([t["positive"]])
            n_emb = model_obj.encode([t["negative"]])
            q_emb = q_emb / np.linalg.norm(q_emb)
            p_emb = p_emb / np.linalg.norm(p_emb)
            n_emb = n_emb / np.linalg.norm(n_emb)

            pos_sim = float(np.dot(q_emb[0], p_emb[0]))
            neg_sim = float(np.dot(q_emb[0], n_emb[0]))
            if pos_sim > neg_sim:
                correct += 1

        accuracy = correct / len(test_set)
        print(f"  {name}: accuracy = {accuracy:.2%} ({correct}/{len(test_set)})")


if __name__ == "__main__":
    train()
    quick_eval()