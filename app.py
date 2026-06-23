import re
import time
import requests
from bs4 import BeautifulSoup
from collections import Counter
from urllib.parse import urlparse, urljoin, urldefrag

import streamlit as st

SPIDER_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 400" width="60" height="60" style="display:block;margin:0 auto 8px auto;">
  <defs>
    <style>
      .s-body { fill: #2d2d5e; }
      .s-leg  { stroke: #2d2d5e; stroke-width: 3; stroke-linecap: round; fill: none; }
      .s-paper{ fill: #f5f5f0; stroke: #bbb; stroke-width: 1.5; }
      .s-line { stroke: #aaa; stroke-width: 1; }
      .s-pen  { fill: #c0392b; }
      .s-tip  { fill: #888; }
      .s-lens { fill: rgba(150,210,255,0.3); stroke: #1a1a2e; stroke-width: 2; }
      .s-frame{ stroke: #1a1a2e; stroke-width: 2; fill: none; }
      .s-eye  { fill: #fff; }
      .s-pupil{ fill: #1a1a2e; }
      .s-hi   { fill: rgba(255,255,255,0.15); }
    </style>
  </defs>
  <path class="s-leg" d="M300,185 Q265,165 235,145"/>
  <path class="s-leg" d="M298,195 Q260,190 225,180"/>
  <path class="s-leg" d="M298,210 Q262,215 228,225"/>
  <path class="s-leg" d="M300,222 Q268,240 242,265"/>
  <path class="s-leg" d="M380,185 Q415,165 445,145"/>
  <path class="s-leg" d="M382,195 Q420,190 455,180"/>
  <path class="s-leg" d="M382,210 Q418,215 452,225"/>
  <path class="s-leg" d="M380,222 Q412,240 438,265"/>
  <ellipse cx="340" cy="255" rx="38" ry="50" class="s-body"/>
  <ellipse cx="340" cy="248" rx="22" ry="18" class="s-hi"/>
  <circle cx="340" cy="190" r="50" class="s-body"/>
  <ellipse cx="340" cy="178" rx="30" ry="18" class="s-hi"/>
  <circle cx="323" cy="185" r="10" class="s-eye"/>
  <circle cx="357" cy="185" r="10" class="s-eye"/>
  <circle cx="325" cy="186" r="5" class="s-pupil"/>
  <circle cx="359" cy="186" r="5" class="s-pupil"/>
  <rect x="308" y="176" width="22" height="16" rx="5" class="s-lens"/>
  <rect x="350" y="176" width="22" height="16" rx="5" class="s-lens"/>
  <line x1="330" y1="184" x2="350" y2="184" class="s-frame"/>
  <line x1="308" y1="184" x2="297" y2="182" class="s-frame"/>
  <line x1="372" y1="184" x2="383" y2="182" class="s-frame"/>
  <rect x="215" y="195" width="55" height="68" rx="3" class="s-paper" transform="rotate(-12, 242, 229)"/>
  <line x1="222" y1="210" x2="262" y2="204" class="s-line" transform="rotate(-12, 242, 229)"/>
  <line x1="222" y1="220" x2="262" y2="214" class="s-line" transform="rotate(-12, 242, 229)"/>
  <line x1="222" y1="230" x2="262" y2="224" class="s-line" transform="rotate(-12, 242, 229)"/>
  <line x1="222" y1="240" x2="250" y2="235" class="s-line" transform="rotate(-12, 242, 229)"/>
  <g transform="rotate(30, 430, 210)">
    <rect x="420" y="195" width="8" height="40" rx="2" class="s-pen"/>
    <polygon points="420,235 428,235 424,248" class="s-tip"/>
    <rect x="420" y="193" width="8" height="6" rx="1" fill="#888"/>
  </g>
</svg>
"""

st.set_page_config(page_title="Word Crawler", page_icon="🔍", layout="centered")

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; }
    .stat-box {
        background: #f0f4ff;
        border: 1px solid #d1d9f0;
        border-radius: 12px;
        padding: 24px 16px;
        text-align: center;
    }
    .stat-value { font-size: 2.2rem; font-weight: 700; color: #1a56db; }
    .stat-label { font-size: 0.82rem; color: #6b7280; margin-top: 4px; letter-spacing: 0.03em; text-transform: uppercase; }
    .stProgress > div > div { background-color: #1a56db; }
    .word-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 12px;
        border-radius: 8px;
        margin-bottom: 4px;
        background: #f9fafb;
        font-size: 0.95rem;
    }
    .word-row:nth-child(odd) { background: #f0f4ff; }
    .word-name { font-weight: 600; color: #111827; }
    .word-count { color: #1a56db; font-weight: 700; }
    .page-item {
        padding: 6px 12px;
        background: #f9fafb;
        border-radius: 8px;
        margin-bottom: 4px;
        font-size: 0.88rem;
        color: #374151;
        word-break: break-all;
    }
    .page-item:nth-child(odd) { background: #f0f4ff; }
</style>
""", unsafe_allow_html=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

STOP_WORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "is","it","its","be","was","are","were","as","by","from","that","this",
    "have","has","had","not","he","she","they","we","you","i","do","did",
    "will","would","can","could","what","which","who","their","if","so","about"
}

def get_domain(url):
    p = urlparse(url)
    return p.scheme + "://" + p.netloc

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception:
        return None

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "meta", "noscript", "head", "footer", "nav", "aside"]):
        tag.decompose()
    return soup.get_text(separator=" ")

def extract_links(html, current_url, base_domain):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        full, _ = urldefrag(urljoin(current_url, a["href"]))
        if full.startswith(base_domain) and urlparse(full).scheme in ("http", "https"):
            links.add(full.rstrip("/"))
    return links

def count_words(text):
    return re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", text.lower())

def stat(value, label):
    return f'<div class="stat-box"><div class="stat-value">{value}</div><div class="stat-label">{label}</div></div>'

def render_top_words(freq, n=20):
    st.subheader("Most repeated words")
    rows = ""
    for word, count in freq.most_common(n):
        if word not in STOP_WORDS:
            rows += f'<div class="word-row"><span class="word-name">{word}</span><span class="word-count">{count:,}</span></div>'
    st.markdown(rows, unsafe_allow_html=True)

def render_pages(visited, base_domain):
    st.subheader(f"Crawled pages ({len(visited)})")
    rows = ""
    for page in sorted(visited):
        short = page.replace(base_domain, "") or "/"
        rows += f'<div class="page-item">🔗 {short}</div>'
    st.markdown(rows, unsafe_allow_html=True)

# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown(SPIDER_SVG, unsafe_allow_html=True)
st.title("Web Word Crawler")

mode = st.segmented_control("", ["Single page", "Full website"], default="Single page")
url_input = st.text_input("", placeholder="https://example.com", label_visibility="collapsed")

if mode == "Full website":
    max_pages = st.number_input("Max pages to crawl", min_value=1, max_value=500, value=30)

run = st.button("Analyse", type="primary", use_container_width=True)

if run:
    if not url_input.strip():
        st.warning("Please enter a URL.")
        st.stop()

    url = url_input.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # ── Single page ────────────────────────────────────────────────────────────
    if mode == "Single page":
        with st.spinner("Fetching page..."):
            html = fetch(url)

        if not html:
            st.error("Could not fetch the page. Check the URL or try another site.")
            st.stop()

        words = count_words(extract_text(html))
        freq  = Counter(words)

        st.divider()
        c1, c2 = st.columns(2)
        c1.markdown(stat(f"{len(words):,}", "Total words"), unsafe_allow_html=True)
        c2.markdown(stat(f"{len(freq):,}", "Unique words"), unsafe_allow_html=True)

        st.divider()
        render_top_words(freq)

    # ── Full crawl ─────────────────────────────────────────────────────────────
    else:
        base_domain = get_domain(url)
        visited, queue, all_words = set(), [url.rstrip("/")], []

        st.divider()
        progress_bar = st.progress(0, text="Starting crawl...")

        while queue and len(visited) < max_pages:
            current = queue.pop(0)
            if current in visited:
                continue

            visited.add(current)
            progress_bar.progress(
                len(visited) / max_pages,
                text=f"Crawling page {len(visited)} of {max_pages} — {current.replace(base_domain,'') or '/'}"
            )

            html = fetch(current)
            if html:
                words = count_words(extract_text(html))
                all_words.extend(words)
                new_links = extract_links(html, current, base_domain) - visited
                queue.extend(sorted(new_links))

            time.sleep(0.5)

        progress_bar.empty()

        if not all_words:
            st.error("No words collected. The site may be blocking requests.")
            st.stop()

        freq = Counter(all_words)

        c1, c2, c3 = st.columns(3)
        c1.markdown(stat(f"{len(visited):,}", "Pages crawled"), unsafe_allow_html=True)
        c2.markdown(stat(f"{len(all_words):,}", "Total words"),  unsafe_allow_html=True)
        c3.markdown(stat(f"{len(freq):,}",      "Unique words"), unsafe_allow_html=True)

        st.divider()
        col1, col2 = st.columns([1, 1])
        with col1:
            render_top_words(freq)
        with col2:
            render_pages(visited, base_domain)
