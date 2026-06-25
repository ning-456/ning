"""知识库构建入口 - 完全本地化（修复图片映射：按 <PIC> 位置顺序对应）"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MANUAL_DIR, ILLUSTRATION_DIR, KNOWLEDGE_BASE_DIR,
    CHROMA_DB_PATH, IMAGE_INDEX_PATH, TEXT_IMAGE_MAPPING_PATH,
    CHUNK_MIN_CHARS, CHUNK_MAX_CHARS, CHUNK_OVERLAP_CHARS,
)
from data_processing.text_cleaner import extract_chinese_manuals, clean_text
from data_processing.text_chunker import chunk_all_manuals
from data_processing.image_encoder import build_image_index, load_image_index


def build_text_image_mapping(chunks: list, image_index: dict,
                             manual_dir: str = MANUAL_DIR,
                             output_path: str = None) -> list:
    """建立文本块到图片的映射（顺序映射：按<PIC>在手册中的出现顺序分配图片）

    修复：原始代码使用字符位置匹配，但清洗后文本位置偏移导致映射失效。
    改用顺序分配：对每个手册按chunk顺序，依次分配图片列表中的图片。
    """
    # 读取每本手册的图片列表
    manual_images = {}
    for fname in sorted(os.listdir(manual_dir)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(manual_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) >= 1:
                img_list = data[1] if len(data) > 1 and isinstance(data[1], list) else []
                manual_images[fname.replace(".txt", "")] = {"all_images": img_list}
        except Exception:
            pass

    # 按手册分组chunks（保持原顺序）
    from collections import OrderedDict
    source_chunks = OrderedDict()
    for chunk in chunks:
        src = chunk.get("source", "")
        if src not in source_chunks:
            source_chunks[src] = []
        source_chunks[src].append(chunk)

    # 为每个手册维护图片分配指针
    img_cursor = {}
    for src in source_chunks:
        img_cursor[src] = 0

    result = []
    total_pics = 0
    total_mapped = 0

    for chunk in chunks:
        source = chunk.get("source", "")
        chunk_text = chunk.get("text", "")

        # 统计该chunk中的<PIC>数量
        num_pics = len(list(re.finditer(r"<PIC>", chunk_text)))
        total_pics += num_pics

        image_ids = []
        if source in manual_images and num_pics > 0:
            all_imgs = manual_images[source]["all_images"]
            cursor = img_cursor[source]
            for i in range(num_pics):
                idx = cursor + i
                if idx < len(all_imgs):
                    img_id = all_imgs[idx]
                    if img_id in image_index and img_id not in image_ids:
                        image_ids.append(img_id)
                # 超出范围的直接跳过（不阻塞构建）
            img_cursor[source] = cursor + num_pics
            total_mapped += len(image_ids)

        result.append({
            "chunk_id": chunk["chunk_id"],
            "text": chunk_text,
            "source": source,
            "image_ids": image_ids,
        })

    print(f"  图文匹配: {total_mapped}/{total_pics} 图片已关联 ({sum(len(r['image_ids']) for r in result)} 个唯一)")

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  图文映射已保存: {output_path}")
    return result

def build_vector_store(chunks_with_images: list, chroma_db_path: str,
                       embedding_model_name: str = ""):
    from engine.rag.knowledge_base import KnowledgeBase
    kb = KnowledgeBase(chroma_db_path)
    kb.build(chunks_with_images)
    return kb


def main():
    print("=" * 60)
    print("多模态客服智能体 - 知识库构建（修复图片映射版）")
    print("=" * 60)

    print("\n[1/5] 提取并清洗手册文本...")
    manuals = extract_chinese_manuals(MANUAL_DIR)
    print(f"  {len(manuals)} 份中文手册已加载")

    print("\n[2/5] 文本分块...")
    chunks = chunk_all_manuals(manuals,
                               min_chars=CHUNK_MIN_CHARS,
                               max_chars=CHUNK_MAX_CHARS,
                               overlap=CHUNK_OVERLAP_CHARS)
    print(f"  共 {len(chunks)} 个文本块")

    print("\n[3/5] 图片编码与索引...")
    if os.path.exists(IMAGE_INDEX_PATH):
        print("  图片索引已存在，加载中...")
        image_index = load_image_index(IMAGE_INDEX_PATH)
        print(f"  {len(image_index)} 张图片已索引")
    else:
        image_index = build_image_index(ILLUSTRATION_DIR, IMAGE_INDEX_PATH)

    print("\n[4/5] 图文绑定（按位置映射）...")
    chunks_with_images = build_text_image_mapping(chunks, image_index, MANUAL_DIR, TEXT_IMAGE_MAPPING_PATH)

    print("\n[5/5] 构建语义向量索引...")
    build_vector_store(chunks_with_images, CHROMA_DB_PATH)

    print("\n" + "=" * 60)
    print("知识库构建完成!")
    print(f"  手册: {len(manuals)} 份")
    print(f"  文本块: {len(chunks)} 个")
    print(f"  图片: {len(image_index)} 张")
    print("=" * 60)


if __name__ == "__main__":
    main()
