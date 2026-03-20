#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析词汇覆盖率 - 计算达到特定文本覆盖率需要认识的单词数
"""

import csv
import sys

def analyze_coverage(unique_words_csv, total_words=None):
    """分析达到不同覆盖率所需的单词数"""

    word_freqs = []
    total = 0

    with open(unique_words_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row['word']
            freq = int(row['frequency'])
            word_freqs.append((word, freq))
            total += freq

    if total_words is None:
        total_words = total

    # 计算累积覆盖率
    cumulative = 0

    print(f"文件：{unique_words_csv}")
    print(f"总单词数：{total_words:,}")
    print(f"唯一单词数：{len(word_freqs):,}")
    print()

    # 目标覆盖率
    targets = [50, 70, 80, 85, 90, 95, 96, 97, 98, 99, 99.5, 100]

    results = []
    for i, (word, freq) in enumerate(word_freqs, 1):
        cumulative += freq
        coverage = cumulative / total_words * 100

        while targets and coverage >= targets[0]:
            target = targets.pop(0)
            results.append((target, i, coverage))

    print("覆盖率分析:")
    print(f"{'目标覆盖率':<15} {'需要单词数':<15} {'实际覆盖率':<15}")
    print("-" * 45)
    for target, count, actual in results:
        print(f"{target:<15.1f} {count:<15,} {actual:<15.2f}%")

    # 找到 95% 对应的单词数
    for target, count, actual in results:
        if target == 95:
            print(f"\n结论：要达到 95% 的文本覆盖率，需要认识前 {count:,} 个最高频的单词")
            return count

    return None

if __name__ == '__main__':
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = "1.Harry Potter and the Philosopher's Stone_unique_words.csv"

    analyze_coverage(csv_file)
