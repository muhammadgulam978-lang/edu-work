import fitz  # PyMuPDF
import re
from .models import Chapter, Topic, SubTopic

MAX_LENGTH = 255

def safe_title(text):
    return (text or "").strip()[:MAX_LENGTH] if text else "-"

def extract_features(doc):
    """
    Extract features from PDF for ML/NLP detection.
    Features per line:
    - font size
    - bold/italic
    - indentation (x0 coordinate)
    - numbering pattern
    - line length
    """
    lines = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if not text:
                        continue
                    # Features
                    font_size = span.get("size", 12)
                    bold = 1 if "Bold" in span.get("font", "") else 0
                    italic = 1 if "Italic" in span.get("font", "") else 0
                    x0 = span.get("bbox", [0,0,0,0])[0]  # indentation
                    numbering = 1 if re.match(r'^\d+(\.\d+)*', text) else 0
                    lines.append({
                        "text": safe_title(text),
                        "font_size": font_size,
                        "bold": bold,
                        "italic": italic,
                        "indent": x0,
                        "numbering": numbering,
                        "length": len(text.split())
                    })
    return lines

def heuristic_classify(line):
    """
    Fallback heuristic if ML model not available:
    - Big font + bold → Chapter
    - Smaller font, same indent → Topic
    - Smaller + indented more → SubTopic
    """
    if line["numbering"]:
        level = len(line["text"].split()[0].split("."))
        return min(level, 3)
    
    # Heuristic based on font size and indent
    if line["font_size"] >= 16 or line["bold"]:
        return 1  # Chapter
    elif line["font_size"] >= 12:
        return 2  # Topic
    else:
        return 3  # SubTopic

def parse_book_toc_ml(book):
    """
    Hybrid ML + heuristic TOC parser
    """
    try:
        doc = fitz.open(book.pdf_file.path)
    except Exception as e:
        print(f"PDF open error: {e}")
        return

    lines = extract_features(doc)

    current_chapter = None
    current_topic = None

    for line in lines:
        # Level classification (1=Chapter, 2=Topic, 3=SubTopic)
        level = heuristic_classify(line)
        title = line["text"]

        if level == 1:
            current_chapter = Chapter.objects.create(book=book, title=title)
            current_topic = None
        elif level == 2 and current_chapter:
            current_topic = Topic.objects.create(book=book, chapter=current_chapter, title=title, name=title)
        elif level == 3 and current_topic:
            SubTopic.objects.create(topic=current_topic, title=title)

    doc.close()
    book.parsed = True
    book.save()
    return True
