import re
from dataclasses import dataclass, field
from typing import List, Optional

import fitz  # PyMuPDF
from PIL import Image

from admin_panel.models import Book, Chapter, Topic, SubTopic, ContentBlock as DBContentBlock





@dataclass
class ContentBlock:
    type: str
    text: Optional[str] = None
    lines: Optional[List[str]] = None


@dataclass
class HeadingNode:
    number: str
    title: str
    level: int
    blocks: List[ContentBlock] = field(default_factory=list)
    children: List["HeadingNode"] = field(default_factory=list)


@dataclass
class ChapterStructure:
    chapter_number: Optional[int]
    chapter_title: str
    sections: List[HeadingNode]


# ---------------------------
# PDF → TEXT
# ---------------------------

def extract_text_from_pdf(pdf_path: str, ocr_threshold: int = 40) -> str:
    doc = fitz.open(pdf_path)
    all_text = []

    for idx, page in enumerate(doc):
        text = page.get_text().strip()

        if len(text) < ocr_threshold:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        all_text.append(text)

    return "\n".join(all_text).replace("\r", "")


# ---------------------------
# CLEANING + FIXES
# ---------------------------

def normalize_number_dots(text: str) -> str:
    for _ in range(3):
        text = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", text)
    return text


def merge_broken_chapter_lines(text: str) -> str:
    lines = text.split("\n")
    out = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if re.match(r"^\d+$", line):
            if i + 1 < len(lines) and re.match(r"^[A-Za-z]", lines[i+1].strip()):
                out.append(f"{line} {lines[i+1].strip()}")
                i += 2
                continue
        out.append(lines[i])
        i += 1

    return "\n".join(out)


def remove_footer_noise(text: str) -> str:
    BAD = ["illegal", "photocopy", "hodder", "sample", "teacher", "exam"]
    cleaned = []
    for l in text.split("\n"):
        if any(b in l.lower() for b in BAD):
            continue
        cleaned.append(l)
    return "\n".join(cleaned)


def clean_text(text: str) -> str:
    text = normalize_number_dots(text)
    text = merge_broken_chapter_lines(text)
    text = remove_footer_noise(text)
    cleaned = []
    for l in text.split("\n"):
        cleaned.append(re.sub(r"[ \t]{2,}", " ", l).rstrip())
    return "\n".join(cleaned)


# ---------------------------
# HEADING EXTRACTION
# ---------------------------

HEADING_LINE_REGEX = re.compile(r"^\s*(\d+(?:\.\d+)+)\s*(.*)$")
BULLET_REGEX = re.compile(r"^[\-\*\u2022\u2023\u25E6>\•]\s+(.+)$")

def looks_like_table_line(line: str) -> bool:
    if "|" in line:
        return True
    if re.search(r"\S\s{2,}\S", line):
        return True
    return False


def extract_headings_linear(text: str):
    lines = text.split("\n")
    headings = []

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        m = HEADING_LINE_REGEX.match(stripped)

        if not m:
            i += 1
            continue

        number = m.group(1)
        rest = m.group(2).strip()
        title = rest

        if not rest:
            j = i + 1
            while j < len(lines):
                line2 = lines[j].strip()
                if not line2:
                    j += 1
                    continue
                if HEADING_LINE_REGEX.match(line2):
                    break
                title = line2
                break
        else:
            j = i

        content = []
        k = j + 1
        while k < len(lines):
            nxt = lines[k].strip()
            if HEADING_LINE_REGEX.match(nxt):
                break
            content.append(lines[k])
            k += 1

        headings.append({
            "number": number,
            "title": title,
            "level": len(number.split(".")),
            "content": "\n".join(content).strip()
        })

        i = k

    return headings


# ---------------------------
# ⭐ FIX 1 — MERGE DUPLICATE HEADINGS
# ---------------------------

def merge_duplicate_headings(flat):
    seen = {}
    final = []

    for h in flat:
        key = (h["number"], h["title"].strip())
        if key not in seen:
            seen[key] = h
            final.append(h)
        else:
            if h["content"]:
                seen[key]["content"] += "\n" + h["content"]

    return final


# ---------------------------
# CONTENT BLOCKS
# ---------------------------

def parse_content_blocks(text: str) -> List[ContentBlock]:
    lines = [l.rstrip() for l in text.split("\n")]

    blocks = []
    para = []
    table = []

    def flush_para():
        nonlocal para
        if para:
            blocks.append(ContentBlock("paragraph", text=" ".join(para).strip()))
            para = []

    def flush_table():
        nonlocal table
        if table:
            blocks.append(ContentBlock("table", lines=[x.strip() for x in table]))
            table = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_para()
            flush_table()
            continue

        m = BULLET_REGEX.match(line)
        if m:
            flush_para()
            flush_table()
            blocks.append(ContentBlock("bullet", text=m.group(1).strip()))
            continue

        if looks_like_table_line(line):
            flush_para()
            table.append(raw)
            continue

        if table:
            flush_table()

        para.append(raw)

    flush_para()
    flush_table()

    if not blocks and text.strip():
        blocks.append(ContentBlock("raw", text=text.strip()))

    return blocks


# ---------------------------
# ⭐ FIX 2 — IMPROVED TREE BUILDER
# ---------------------------

def build_tree(flat):
    nodes = []
    stack = []

    for h in flat:
        node = HeadingNode(
            number=h["number"],
            title=h["title"],
            level=h["level"],
            blocks=parse_content_blocks(h["content"])
        )

        while stack and stack[-1].level >= node.level:
            stack.pop()

        if stack:
            stack[-1].children.append(node)
        else:
            nodes.append(node)

        stack.append(node)

    return nodes


# ---------------------------
# FINAL STRUCTURE BUILDER
# ---------------------------

def parse_book_text_to_structure(text: str, book: Book):
    cleaned = clean_text(text)

    flat = extract_headings_linear(cleaned)

    # ⭐ Apply duplicate merge FIX
    flat = merge_duplicate_headings(flat)

    # ⭐ Ensure proper numeric sorting
    flat = sorted(flat, key=lambda h: [int(x) for x in h["number"].split(".")])

    # Build hierarchical tree
    tree = build_tree(flat)

    chapter_title = book.title if hasattr(book, "title") else "Chapter"

    return [ChapterStructure(None, chapter_title, tree)]


# ---------------------------
# SAVE TO DB
# ---------------------------
def _save_topics_and_subtopics(chapter, tree):
    """
    tree = List[HeadingNode]
    """

    for node in tree:
        # ✅ TOPIC
        topic = Topic.objects.create(
            chapter=chapter,
            title=node.title
        )

        # ============================
        # CASE 1: Proper SubTopics hain
        # ============================
        if node.children:
            for child in node.children:
                subtopic = SubTopic.objects.create(
                    topic=topic,
                    title=child.title
                )

                # content blocks save karo
                for block in child.blocks:
                    text = block.text or "\n".join(block.lines or [])
                    if text.strip():
                        DBContentBlock.objects.create(
                            subtopic=subtopic,
                            text=text.strip()
                        )

        # ======================================
        # CASE 2: SubTopics nahi → auto subtopic
        # ======================================
        else:
            auto_subtopic = SubTopic.objects.create(
                topic=topic,
                title=f"Explanation of {topic.title}"
            )

            for block in node.blocks:
                text = block.text or "\n".join(block.lines or [])
                if text.strip():
                    DBContentBlock.objects.create(
                        subtopic=auto_subtopic,
                        text=text.strip()
                    )


def save_book_structure_to_db(book: Book, structure):
    Chapter.objects.filter(book=book).delete()
    created = []

    for ch in structure:
        chapter_obj = Chapter.objects.create(
            book=book,
            title=ch.chapter_title
        )

        _save_topics_and_subtopics(chapter_obj, ch.sections)
        created.append(chapter_obj)

    return created


def parse_book_toc(book: Book):
    pdf_path = book.pdf_file.path
    raw = extract_text_from_pdf(pdf_path)
    structure = parse_book_text_to_structure(raw, book)
    chapters = save_book_structure_to_db(book, structure)
    return chapters


def save_blocks_to_db(blocks, topic=None, subtopic=None):
    """
    blocks = List[ContentBlock dataclass]
    """

    for b in blocks:
        if not b.text and not b.lines:
            continue

        text = b.text or "\n".join(b.lines)

        DBContentBlock.objects.create(
            topic=topic,
            subtopic=subtopic,
            text=text.strip()
        )

def parse_chapter_pdf(chapter):
    """
    Chapter PDF se Topics / SubTopics / ContentBlocks extract karta hai
    EXACTLY same logic jo pehle book parsing mein chal rahi thi
    """

    # safety check
    if not chapter.pdf_file:
        return

    pdf_path = chapter.pdf_file.path

    # 1️⃣ PDF → TEXT
    raw_text = extract_text_from_pdf(pdf_path)

    # 2️⃣ CLEAN TEXT (same old logic)
    cleaned_text = clean_text(raw_text)

    # 3️⃣ FLAT HEADINGS NIKALO
    flat = extract_headings_linear(cleaned_text)

    # 4️⃣ DUPLICATES MERGE
    flat = merge_duplicate_headings(flat)

    # 5️⃣ SORT PROPERLY (1.1, 1.2, 2.1 etc)
    flat = sorted(flat, key=lambda h: [int(x) for x in h["number"].split(".")])

    # 6️⃣ TREE BANAO (HeadingNode)
    tree = build_tree(flat)

    # 7️⃣ RE-UPLOAD CASE: PURANAY TOPICS DELETE
    chapter.topics.all().delete()

    # 8️⃣ SAVE TO DB (Topic / SubTopic / ContentBlock)
    _save_topics_and_subtopics(chapter, tree)
