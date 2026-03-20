#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
以 Harry Potter 的单词表为主，在第三列添加词根词缀文件中的排名（基于原型匹配）
使用 ecdict.csv 找到单词的原型（lemma），用原型去匹配词根词缀排名
"""

import csv
import re


def load_lemma_dict(ecdict_path):
    """
    从 ecdict.csv 加载词形还原映射（word → lemma）
    exchange 字段格式：0:go/1:i/s:goings  其中 0:xxx 表示原型

    另外包含一个常见不规则动词的 fallback 字典，用于补充 ecdict 中缺失的条目
    """
    lemma_dict = {}

    # fallback 字典：ecdict 中缺失的常见不规则动词变形
    fallback_dict = {
        'was': 'be',
        'am': 'be',
        'is': 'be',
        'are': 'be',
    }
    lemma_dict.update(fallback_dict)

    with open(ecdict_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row['word'].lower()
            exchange = row.get('exchange', '').strip()
            if not exchange:
                continue
            # 解析 exchange 字段，查找 0:xxx 模式（原型）
            # 格式可能是：0:go/1:i 或 0:child/1:s/s:children 或 1:p/0:be
            match = re.search(r'(^|/)0:([^/]+)', exchange)
            if match:
                lemma = match.group(2)
                if lemma and lemma != word:  # 只有当原型与原词不同时才记录
                    lemma_dict[word] = lemma
    return lemma_dict


def load_root_word_rank(csv_path):
    """
    加载词根词缀文件中的单词排名（全部）
    如果单词重复出现，只保留第一次出现的排名（即排名数字最小的）
    """
    rank_dict = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row['Word'].lower()
            rank = row['COCA_Rank']
            # 只在单词首次出现时存入，保证保留最小排名
            if word not in rank_dict:
                rank_dict[word] = rank
    return rank_dict

def merge_data(harry_potter_csv, root_word_rank, lemma_dict, output_csv):
    """
    合并 Harry Potter 数据和词根词缀排名（基于原型匹配）

    匹配逻辑：
    1. 先用原词直接匹配词根词缀排名
    2. 如果直接匹配不到，再用原型去匹配
    """

    rows_written = 0
    matched_direct = 0  # 直接匹配成功的数量
    matched_with_lemma = 0  # 通过原型匹配成功的数量

    with open(harry_potter_csv, 'r', encoding='utf-8-sig') as infile:
        reader = csv.DictReader(infile)

        # 创建输出字段：word, frequency, 词根词缀排名，原词
        fieldnames = ['word', 'frequency', '词根词缀排名', '原词']

        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                word = row['word'].lower()
                frequency = row['frequency']

                # 先查 ecdict 找原型
                lemma = lemma_dict.get(word, None)

                # Step 1: 先用原词直接匹配
                rank = root_word_rank.get(word, '')

                # Step 2: 如果直接匹配不到，再用原型匹配
                used_lemma = False
                if not rank and lemma:
                    rank = root_word_rank.get(lemma, '')
                    used_lemma = True

                # 记录匹配方式
                if rank:
                    if used_lemma:
                        matched_with_lemma += 1
                    else:
                        matched_direct += 1

                # 构建输出行
                output_row = {
                    'word': word,
                    'frequency': frequency,
                    '词根词缀排名': rank,
                    '原词': lemma if lemma else ''
                }

                writer.writerow(output_row)
                rows_written += 1

    return rows_written, matched_with_lemma, matched_direct

def main():
    # 文件路径
    ecdict_csv = 'ecdict.csv'
    root_word_csv = '词根词缀记单词.csv'
    harry_potter_csv = "1.Harry Potter and the Philosopher's Stone_unique_words.csv"
    output_csv = "HarryPotter_词根词缀排名_原型匹配.csv"

    print("正在从 ecdict.csv 加载词形还原映射...")
    lemma_dict = load_lemma_dict(ecdict_csv)
    print(f"已加载 {len(lemma_dict)} 个单词的原型映射")

    print("\n正在加载词根词缀排名...")
    root_rank = load_root_word_rank(root_word_csv)
    print(f"已加载 {len(root_rank)} 个单词的排名")

    print("\n正在合并数据...")
    rows, matched_with_lemma, matched_direct = merge_data(harry_potter_csv, root_rank, lemma_dict, output_csv)

    print(f"\n完成！共处理 {rows} 行")
    print(f"输出文件：{output_csv}")

    # 统计信息
    with open(output_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        matched = 0
        not_matched = 0
        has_lemma = 0
        for row in reader:
            if row['词根词缀排名']:
                matched += 1
            else:
                not_matched += 1
            if row['原词']:
                has_lemma += 1

    print(f"\n统计信息:")
    print(f"  - 在词根词缀中的单词：{matched} 个")
    print(f"    - 直接匹配：{matched_direct} 个")
    print(f"    - 通过原型匹配：{matched_with_lemma} 个")
    print(f"  - 不在词根词缀中的单词：{not_matched} 个")
    print(f"  - 有原型变形的单词：{has_lemma} 个")


if __name__ == '__main__':
    main()
