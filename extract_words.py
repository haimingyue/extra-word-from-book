#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 epub 书籍中提取所有单词并输出为 CSV 文件
"""

from ebooklib import epub
import csv
import re
from collections import Counter
from html import unescape


def extract_text_from_epub(epub_path):
    """从 epub 文件中提取所有文本内容"""
    all_text = []

    book = epub.read_epub(epub_path)

    # 遍历所有内容文件
    for item in book.get_items():
        # 只处理 HTML 内容文件
        if item.media_type in ['application/xhtml+xml', 'text/html']:
            content = item.get_content().decode('utf-8', errors='ignore')
            # 移除 HTML 标签，提取纯文本
            text = remove_html_tags(content)
            if text:
                all_text.append(text)

    return '\n'.join(all_text)


def remove_html_tags(html_text):
    """移除 HTML 标签"""
    # 解码 HTML 实体
    text = unescape(html_text)
    # 移除所有 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', text)
    # 移除脚本和样式内容
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    return text


# 合法的单个字母单词（英语中真正的单词）
VALID_SINGLE_LETTERS = {'a', 'i', 'o'}  # a=一个，i=我，o=哦（感叹词）


def extract_words(text):
    """从文本中提取单词"""
    # 使用正则表达式匹配单词（只包含字母）
    words = re.findall(r'[a-zA-Z]+', text.lower())
    # 过滤掉无效的单个字母（保留 a, i, o 等合法单词）
    words = [w for w in words if len(w) > 1 or w in VALID_SINGLE_LETTERS]
    return words


def count_word_frequencies(words):
    """统计单词频率"""
    return Counter(words)


def save_to_csv(word_data, output_path, include_details=True):
    """
    将单词数据保存为 CSV 文件

    Args:
        word_data: 单词数据（列表或 Counter）
        output_path: 输出文件路径
        include_details: 是否包含详细信息（词频、位置等）
    """
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)

        if isinstance(word_data, Counter):
            # 写入表头
            writer.writerow(['word', 'frequency'])
            # 按频率排序写入数据
            for word, freq in word_data.most_common():
                writer.writerow([word, freq])
        else:
            # 写入表头
            writer.writerow(['word'])
            # 写入所有单词（包括重复）
            for word in word_data:
                writer.writerow([word])


def main():
    import sys

    # 输入文件路径（支持命令行参数）
    if len(sys.argv) > 1:
        epub_path = sys.argv[1]
    else:
        epub_path = 'How To Win Friends and Influence People.epub'

    # 输出文件路径（根据输入文件名生成）
    base_name = epub_path.rsplit('.', 1)[0]
    all_words_csv = f'{base_name}_all_words.csv'
    unique_words_csv = f'{base_name}_unique_words.csv'

    print(f"正在处理文件：{epub_path}")

    # 提取文本
    print("正在提取文本内容...")
    text = extract_text_from_epub(epub_path)
    print(f"提取到 {len(text)} 个字符")

    # 提取单词
    print("正在提取单词...")
    all_words = extract_words(text)
    print(f"提取到 {len(all_words)} 个单词")

    # 统计词频
    print("正在统计词频...")
    word_freq = count_word_frequencies(all_words)
    print(f"共有 {len(word_freq)} 个唯一单词")

    # 保存到 CSV
    print(f"保存所有单词到：{all_words_csv}")
    save_to_csv(all_words, all_words_csv, include_details=False)

    print(f"保存唯一单词（带频率）到：{unique_words_csv}")
    save_to_csv(word_freq, unique_words_csv, include_details=True)

    print("\n完成！")
    print(f"\n统计信息:")
    print(f"  - 总单词数：{len(all_words)}")
    print(f"  - 唯一单词数：{len(word_freq)}")

    # 显示最高频的 20 个单词
    print(f"\n最高频的 20 个单词:")
    for i, (word, freq) in enumerate(word_freq.most_common(20), 1):
        print(f"  {i}. {word}: {freq}")


if __name__ == '__main__':
    main()
