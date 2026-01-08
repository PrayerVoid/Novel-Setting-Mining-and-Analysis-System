import re
import chardet

def split_novel_by_chapters(file_path):
    """
    读取小说文件，自动检测编码，并按章节切分。
    返回一个列表，每项为 {"number": int, "title": str, "content": str}
    """
    # 1. 检测编码
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000) # 读取前10KB进行检测
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        print(f"检测到文件编码: {encoding}")

    # 2. 读取全文
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            full_text = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}")
        return []

    # 3. 正则匹配章节
    # 常见格式: "第xxx章 标题" 或 "第xxx节"
    # 这是一个比较通用的正则，匹配 "第" + 中文数字/阿拉伯数字 + "章/节/回"
    # 修改：增加 (?:^|\n)\s* 前缀，确保只匹配行首（或换行后）的章节标题，避免匹配正文中的类似文本
    pattern = r"(?:^|\n)\s*(第[0-9零一二三四五六七八九十百千]+[章节回][^\n]*)"
    
    chapters = []
    # split 会保留分隔符在列表中，如果使用捕获组 ()
    parts = re.split(pattern, full_text)
    
    # parts[0] 通常是序章前的废话，或者空字符串
    # 之后的结构是: [标题1, 内容1, 标题2, 内容2, ...]
    
    current_chapter_num = 1
    
    # 从索引 1 开始遍历 (因为 split 的第一个元素通常是第一章之前的内容)
    # 如果 parts[0] 有内容，可以作为“序章”处理，这里简单起见跳过
    
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        # 保留段首缩进：只移除开头的换行符（避免吞掉首段缩进），并移除末尾多余空白
        content = parts[i+1].lstrip('\r\n').rstrip() if i+1 < len(parts) else ""
        
        # 尝试从标题中提取数字 (可选，用于校对)
        # 这里简单地使用自增 ID
        
        chapters.append({
            "number": current_chapter_num,
            "title": title,
            "content": content
        })
        current_chapter_num += 1
        
    print(f"成功切分出 {len(chapters)} 个章节。")
    return chapters

if __name__ == "__main__":
    import os
    # 测试切分
    # 动态获取上一级目录下的测试文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    path = os.path.join(project_root, "《从零开始》.txt")
    
    if os.path.exists(path):
        chapters = split_novel_by_chapters(path)
        if chapters:
            print(f"第一章: {chapters[0]['title']}")
            print(f"内容预览: {chapters[0]['content'][:50]}...")
    else:
        print(f"测试文件不存在: {path}")
