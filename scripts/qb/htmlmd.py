"""Convert LeetCode HTML fragments to Markdown without dropping code or tables."""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _Conv(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []
        self.ignore = 0
        self.href: str | None = None
        self.lists: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attr = {k.lower(): (v or "") for k, v in attrs}
        if tag in ("script", "style"):
            self.ignore += 1
            return
        if self.ignore:
            return
        if tag == "p":
            self.out.append("\n\n")
        elif tag == "br":
            self.out.append("\n")
        elif tag in ("strong", "b"):
            self.out.append("**")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag == "code":
            if "pre" not in self.stack:
                self.out.append("`")
        elif tag == "pre":
            self.out.append("\n\n```\n")
        elif tag in ("ul", "ol"):
            self.lists.append(tag)
            self.out.append("\n")
        elif tag == "li":
            bullet = "- " if (self.lists and self.lists[-1] == "ul") else "1. "
            self.out.append("\n" + bullet)
        elif tag == "img":
            alt = attr.get("alt", "")
            src = attr.get("src", "")
            self.out.append(f"\n![{alt}]({src})\n")
        elif tag == "a":
            self.href = attr.get("href", "")
            self.out.append("[")
        elif tag == "sup":
            self.out.append("<sup>")
        elif tag == "sub":
            self.out.append("<sub>")
        elif tag in ("h1", "h2", "h3", "h4"):
            level = int(tag[1])
            self.out.append("\n\n" + ("#" * level) + " ")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style"):
            self.ignore = max(0, self.ignore - 1)
            return
        if self.ignore:
            return
        if tag in ("strong", "b"):
            self.out.append("**")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag == "code":
            if "pre" in self.stack:
                pass
            else:
                self.out.append("`")
        elif tag == "pre":
            self.out.append("\n```\n")
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self.out.append("\n")
        elif tag == "a":
            href = self.href or ""
            self.out.append(f"]({href})")
            self.href = None
        elif tag == "sup":
            self.out.append("</sup>")
        elif tag == "sub":
            self.out.append("</sub>")
        elif tag in ("h1", "h2", "h3", "h4", "p"):
            self.out.append("\n")
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()

    def handle_data(self, data):
        if self.ignore:
            return
        self.out.append(data)


def html_to_markdown(html: str | None) -> str:
    if not html:
        return ""
    parser = _Conv()
    parser.feed(html)
    parser.close()
    text = "".join(parser.out)
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_IMG_MD = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_IMG_HTML = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)


def extract_images(text: str | None) -> list[dict]:
    if not text:
        return []
    found: list[dict] = []
    seen: set[str] = set()
    for alt, src in _IMG_MD.findall(text):
        if src and src not in seen:
            seen.add(src)
            found.append({"url": src, "alt": alt})
    for src in _IMG_HTML.findall(text):
        if src and src not in seen:
            seen.add(src)
            found.append({"url": src, "alt": ""})
    return found
