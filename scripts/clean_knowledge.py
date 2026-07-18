"""
清洗 knowledge/ 下所有 .md 文件：
1. 去掉 > 来源: ... 行
2. 去掉重复的 H1 标题
3. 去掉网站导航菜单（首页 学院概况 机构设置 ...）
4. 去掉 PDF 提取痕迹（## 第 X 页、> 提取方式: pdfplumber）
5. 去掉 HTML 标签
6. 去掉底部版权/访问次数/联系方式等垃圾
7. 合并多余空行，保留纯净文本
"""

import os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")

# ── 导航菜单关键词（匹配连续出现多个这种词的行块） ──
NAV_KEYWORDS = [
    "首页", "机构设置", "部门简介", "部门领导", "通知公告", "规章制度",
    "招生工作", "培养工作", "学位工作", "基地工作", "国际交流", "教育管理",
    "学院概况", "师资队伍", "人才培养", "学术科研", "党群工作", "学生工作",
    "校友动态", "合作发展", "下载专区", "网站首页", "科学研究", "本科教育",
    "研究生教育", "教学动态", "科研简介", "科研动态", "党群学工", "校友工作",
    "学院简介", "现任领导", "组织机构", "委员会", "人才招聘", "合作交流",
    "国内交流", "基金会概况", "基金会章程", "新闻动态", "捐赠项目",
    "捐赠指南", "信息公开", "English", "设为主页", "加入收藏", "院长信箱",
]

# ── 导航菜单正则（连续 5+ 个导航词的行） ──
NAV_PATTERN = re.compile(
    r"(?:"
    r"(?:网站首页|首页)\s+(?:学院概况|机构设置|通知公告|部门简介|部门领导|"
    r"人才培养|师资队伍|规章制度|招生工作|学位工作|基地工作|国际交流|"
    r"教育管理|学术科研|党群工作|学生工作|校友动态|合作发展|下载专区|"
    r"科学研究|本科教育|研究生教育|教学动态|科研动态|党群学工|校友工作|"
    r"学院简介|现任领导|组织机构|委员会|人才招聘|合作交流|国内交流|"
    r"基金会概况|基金会章程|新闻动态|捐赠项目|捐赠指南|信息公开|"
    r"English|设为主页|加入收藏|院长信箱"
    r"[^\S\n]*)+"
    r")",
    re.UNICODE,
)

# ── 函数定义 ──

def remove_nav_menus(text: str) -> str:
    """去掉导航菜单块"""
    lines = text.split("\n")
    cleaned = []
    in_nav_block = False
    nav_count = 0
    for line in lines:
        stripped = line.strip()
        # 如果一行里出现 4+ 个导航词 → 标记为导航行
        kw_count = sum(1 for kw in NAV_KEYWORDS if kw in stripped)
        is_nav = kw_count >= 4
        if is_nav:
            nav_count += 1
            if not in_nav_block:
                in_nav_block = True
            continue
        else:
            if in_nav_block:
                # 导航块结束：如果后面跟着空行/短行，继续跳过
                if not stripped or len(stripped) < 20:
                    continue
                in_nav_block = False
        if not in_nav_block:
            cleaned.append(line)
    # 如果整个文件都是导航则保留
    if nav_count > 0 and len(cleaned) == 0:
        return text
    return "\n".join(cleaned)


def remove_source_line(text: str) -> str:
    """去掉 > 来源: https://... 行"""
    return re.sub(r"^>\s*来源:?\s*https?://[^\n]*\n?", "", text, flags=re.MULTILINE)


def remove_extraction_info(text: str) -> str:
    """去掉 > 提取方式: pdfplumber 行"""
    return re.sub(r"^>\s*提取方式:?\s*[^\n]*\n?", "", text, flags=re.MULTILINE)


def remove_pdf_page_markers(text: str) -> str:
    """去掉 ## 第 X 页 标记"""
    return re.sub(r"^##?\s*第\s*\d+\s*页\s*\n?", "", text, flags=re.MULTILINE)


def remove_html_tags(text: str) -> str:
    """去掉 HTML 标签"""
    # 去掉 <tag ...> 和 </tag>
    text = re.sub(r"<[^>]+>", "", text)
    # 去掉 &nbsp; 等实体
    text = re.sub(r"&\w+;", " ", text)
    return text


def remove_duplicate_h1(text: str) -> str:
    """去掉重复的 H1 标题（同一行连续出现两次）"""
    lines = text.split("\n")
    result = []
    seen_h1 = set()
    for line in lines:
        if line.startswith("# ") and line.strip():
            h1_text = line.strip()
            if h1_text in seen_h1:
                continue  # skip duplicate H1
            seen_h1.add(h1_text)
        result.append(line)
    return "\n".join(result)


def remove_footer_garbage(text: str) -> str:
    """去掉底部版权/访问次数/技术支持/联系方式等"""
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        # 跳过只有这些内容的行
        if re.search(
            r"(版权所有|技术支持|访问次数?\s*[:：]\s*\d+|浏览次数?\s*[:：]\s*\d+|"
            r"邮编\s*[:：]\s*\d+|电话\s*[:：]\s*[\d-]+|"
            r"地址\s*[:：]\s*[\u4e00-\u9fff]+\s*(?:路|街|大道|号)|"
            r"苏[^\s]{2,10}号)",
            stripped,
        ):
            if len(stripped) < 80:  # 短行才跳过
                continue
        result.append(line)
    return "\n".join(result)


def remove_time_meta(text: str) -> str:
    """去掉 发布时间/文章来源 行"""
    text = re.sub(
        r"^(?:发布时间|文章来源|发布人|责任编辑|编辑)\s*[:：][^\n]*\n?",
        "",
        text,
        flags=re.MULTILINE,
    )
    return text


def clean_pdf_spacing(text: str) -> str:
    """PDF 提取的字符间空格修复"""
    # 中文之间或中文与英文之间的多余空格
    text = re.sub(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])", r"\1\2", text)
    text = re.sub(r"([\u4e00-\u9fff])\s+([a-zA-Z])", r"\1 \2", text)
    text = re.sub(r"([a-zA-Z])\s+([\u4e00-\u9fff])", r"\1 \2", text)
    return text


def normalize_whitespace(text: str) -> str:
    """合并多余空行，每段之间最多一个空行"""
    lines = text.split("\n")
    result = []
    prev_blank = False
    for line in lines:
        if not line.strip():
            if prev_blank:
                continue
            prev_blank = True
            result.append("")
        else:
            prev_blank = False
            result.append(line.rstrip())
    # 去掉开头空行
    while result and not result[0].strip():
        result.pop(0)
    # 去掉结尾空行
    while result and not result[-1].strip():
        result.pop()
    return "\n".join(result)


def clean_markdown_file(filepath: str) -> bool:
    """清洗单个文件，返回是否修改"""
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    text = original

    # 按顺序应用清洗规则
    text = remove_source_line(text)
    text = remove_extraction_info(text)
    text = remove_pdf_page_markers(text)
    text = remove_html_tags(text)
    text = remove_nav_menus(text)
    text = remove_duplicate_h1(text)
    text = remove_time_meta(text)
    text = remove_footer_garbage(text)
    text = clean_pdf_spacing(text)
    text = normalize_whitespace(text)

    if text == original:
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def main():
    if not os.path.exists(KNOWLEDGE_DIR):
        print(f"ERROR: {KNOWLEDGE_DIR} not found")
        sys.exit(1)

    total = 0
    cleaned = 0
    errors = 0

    for root, dirs, files in os.walk(KNOWLEDGE_DIR):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fp = os.path.join(root, fname)
            try:
                modified = clean_markdown_file(fp)
                total += 1
                if modified:
                    cleaned += 1
            except Exception as e:
                errors += 1
                print(f"  ERROR: {os.path.relpath(fp, KNOWLEDGE_DIR)} - {e}")

    print(f"\nDone: {total} files, {cleaned} modified, {errors} errors")


if __name__ == "__main__":
    main()
