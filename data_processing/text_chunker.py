"""文本分块模块 - 按 # 标题分块，追踪字符位置"""

import re
from typing import List, Dict


def chunk_text(text: str, source: str = "", min_chars: int = 200,
               max_chars: int = 800, overlap: int = 50) -> List[Dict]:
    """将单篇手册按 # 标题分块，追踪字符位置用于图片映射"""
    if not text.strip():
        return []

    # 按 # 标题分割
    sections = re.split(r'(^#\s+.+?$)', text, flags=re.MULTILINE)
    # 合并标题和内容
    merged = []
    i = 0
    while i < len(sections):
        if sections[i].startswith("#"):
            heading = sections[i]
            content = sections[i + 1].strip() if i + 1 < len(sections) else ""
            merged.append(f"{heading}\n{content}")
            i += 2
        else:
            if sections[i].strip():
                merged.append(sections[i].strip())
            i += 1

    chunks = []
    chunk_index = 0
    char_pos = 0  # 当前在原文中的位置

    for section in merged:
        if not section.strip():
            char_pos += len(section) + 1
            continue

        start_pos = char_pos
        section_len = len(section)

        if len(section) <= max_chars and len(section) >= min_chars:
            chunk_id = f"{source}_{chunk_index:04d}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": section.strip(),
                "source": source,
                "start_char": start_pos,
                "end_char": start_pos + len(section.strip()),
            })
            chunk_index += 1
            char_pos += section_len + 1
            continue

        if len(section) > max_chars:
            # 按子标题拆分
            sub_sections = re.split(r'\n(?=#\s)', section)
            for sub in sub_sections:
                sub = sub.strip()
                if not sub:
                    continue
                sub_start = text.find(sub, start_pos)
                if sub_start < 0:
                    sub_start = char_pos
                if len(sub) <= max_chars:
                    chunk_id = f"{source}_{chunk_index:04d}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "text": sub,
                        "source": source,
                        "start_char": sub_start,
                        "end_char": sub_start + len(sub),
                    })
                    chunk_index += 1
                else:
                    # 按句子拆分
                    sentences = re.split(r'(?<=[。！？.!?])\s*', sub)
                    temp = ""
                    temp_start = sub_start
                    for sent in sentences:
                        if not sent.strip():
                            continue
                        if len(temp) + len(sent) > max_chars and len(temp) >= min_chars:
                            chunk_id = f"{source}_{chunk_index:04d}"
                            chunks.append({
                                "chunk_id": chunk_id,
                                "text": temp.strip(),
                                "source": source,
                                "start_char": temp_start,
                                "end_char": temp_start + len(temp.strip()),
                            })
                            chunk_index += 1
                            temp_start = text.find(sent[:10], sub_start)
                            temp = sent
                        else:
                            temp += sent
                    if temp.strip():
                        chunk_id = f"{source}_{chunk_index:04d}"
                        chunks.append({
                            "chunk_id": chunk_id,
                            "text": temp.strip(),
                            "source": source,
                            "start_char": temp_start,
                            "end_char": temp_start + len(temp.strip()),
                        })
                        chunk_index += 1
            char_pos += section_len + 1
            continue

        # 短内容合并到前一块
        if chunks:
            chunks[-1]["text"] += "\n\n" + section
            chunks[-1]["end_char"] = start_pos + len(section.strip())
            # 合并短内容时start_char不变,end_char扩展至追加内容的末尾
        else:
            chunk_id = f"{source}_{chunk_index:04d}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": section.strip(),
                "source": source,
                "start_char": start_pos,
                "end_char": start_pos + len(section.strip()),
            })
            chunk_index += 1
        char_pos += section_len + 1

    return chunks


def chunk_all_manuals(manuals: Dict[str, str], min_chars: int = 200,
                      max_chars: int = 800, overlap: int = 50) -> List[Dict]:
    all_chunks = []
    for source_name, text in manuals.items():
        chunks = chunk_text(text, source=source_name,
                            min_chars=min_chars, max_chars=max_chars, overlap=overlap)
        all_chunks.extend(chunks)
        print(f"  [{source_name}] -> {len(chunks)} chunks")
    return all_chunks