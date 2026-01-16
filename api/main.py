from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import arxiv
from typing import List, Dict
import html

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

MAX_PAPERS = 15  # safer for Vercel serverless

# ------------------ Categories ------------------
ARXIV_CATEGORIES = {
    "Computer Science": {
        "cs.AI": "Artificial Intelligence",
        "cs.LG": "Machine Learning",
        "cs.CV": "Computer Vision",
        "cs.CL": "NLP",
        "cs.RO": "Robotics",
        "cs.DB": "Databases",
        "cs.DS": "Algorithms",
        "cs.CR": "Security",
        "cs.OS": "Operating Systems",
        "cs.SE": "Software Engineering",
    },
    "Mathematics": {
        "math.CO": "Combinatorics",
        "math.NT": "Number Theory",
        "math.AG": "Algebraic Geometry",
        "math.PR": "Probability",
        "math.OC": "Optimization & Control",
        "math.ST": "Statistics Theory",
    },
    "Statistics": {
        "stat.ML": "Statistical ML",
        "stat.TH": "Theory",
        "stat.ME": "Methodology",
        "stat.AP": "Applications",
    },
    "Physics": {
        "quant-ph": "Quantum Physics",
        "hep-th": "High Energy Theory",
        "cond-mat.stat-mech": "Statistical Mechanics",
        "astro-ph.CO": "Cosmology",
        "gr-qc": "General Relativity",
    },
    "Quantitative Biology": {
        "q-bio.QM": "Quantitative Methods",
        "q-bio.NC": "Neurons & Cognition",
        "q-bio.GN": "Genomics",
    },
    "Quantitative Finance": {
        "q-fin.MF": "Mathematical Finance",
        "q-fin.ST": "Statistical Finance",
        "q-fin.PR": "Pricing",
        "q-fin.RM": "Risk Management",
    },
    "Economics": {
        "econ.EM": "Econometrics",
        "econ.TH": "Theory",
        "econ.GN": "General Economics",
    },
    "Electrical Engineering & Systems": {
        "eess.SP": "Signal Processing",
        "eess.IV": "Image & Video",
        "eess.SY": "Systems & Control",
        "eess.AS": "Audio & Speech",
    },
}

# ------------------ Query Builder ------------------
def build_arxiv_query(text_query: str, categories: List[str]) -> str:
    if not categories:
        return text_query
    cats = " OR ".join(f"cat:{c}" for c in categories)
    return f"({cats}) AND all:{text_query}"

# ------------------ ArXiv Metadata ------------------
def get_arxiv_full_metadata(query_term: str, categories: List[str], max_results: int) -> List[Dict]:
    final_query = build_arxiv_query(query_term, categories)

    search = arxiv.Search(
        query=final_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending,
    )

    papers = []
    for result in search.results():  # <-- serverless-safe
        authors = [a.name for a in result.authors]
        if len(authors) > 1:
            authors[-2] += " & " + authors[-1]
            authors.pop()

        papers.append({
            "Title": result.title.strip(),
            "Authors": ", ".join(authors),
            "Abstract": result.summary.strip(),
            "URL": result.entry_id.replace("http:", "https:").replace("abs", "pdf"),
            "DOI": result.doi or result.entry_id.split("abs/")[-1],
            "Categories": ", ".join(result.categories),
            "Published": result.published,
        })

    papers.sort(key=lambda x: x["Published"], reverse=True)
    for p in papers:
        try:
            p["Published"] = p["Published"].strftime("%B %d, %Y")
        except Exception:
            p["Published"] = "Unknown"

    return papers

# ------------------ HTML Generator ------------------
def generate_styled_html(papers: List[Dict], search_query: str, selected_cats: List[str]) -> str:
    safe_query = html.escape(search_query)
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Scriptorium: ArXiv Advance Search</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="/static/favicon-96x96.png" sizes="96x96" />
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
<link rel="shortcut icon" href="/static/favicon.ico" />
<link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png" />
<meta name="apple-mobile-web-app-title" content="Scriptorium" />
<link rel="manifest" href="/static/site.webmanifest" />
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display&display=swap" rel="stylesheet">
<style>
/* --- CSS omitted for brevity; keep your full CSS here --- */
</style>
</head>
<body>

<div class="search-box">
<form method="get">
<div class="search-row">
<span class="search-icon">🔍</span>
<input type="text" name="query" value="{safe_query}" placeholder="Search papers, authors, topics…" />
<button type="submit">Search</button>
</div>

<details class="advanced">
<summary><b>Advanced search</b></summary>
<div class="advanced-panel">
"""

    for domain, subs in ARXIV_CATEGORIES.items():
        html_content += f"<details class='domain'><summary>{domain}</summary><div class='subcats'>"
        for code, label in subs.items():
            checked = "checked" if code in selected_cats else ""
            html_content += f"""<label><input type="checkbox" name="cat" value="{code}" {checked}>{label}</label>"""
        html_content += "</div></details>"

    html_content += """
</div></details>
</form>
</div>
"""

    if search_query:
        html_content += f"<h2 style='text-align:center;'>Results for “{safe_query}”</h2>"
        for p in papers:
            html_content += f"""
<div class="paper">
    <a href="{p['URL']}" target="_blank" style="color:#000;text-decoration:none;">
        <div class="authors">{p['Authors']}</div>
        <div class="title">{p['Title']}</div>
        <p class="authors">Categories: {p['Categories']}, arXiv: <a href="{p['URL']}" target="_blank" style="color:#1155cc;">{p['DOI']}</a>, {p['Published']}</p>
        <p class="abstract"><b>Abstract. </b>{p['Abstract']}</p>
    </a>
</div>
"""

    return html_content

# ------------------ Routes ------------------
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
def papers(query: str = Query(default=""), cat: List[str] = Query(default=[])):
    results = []
    if query.strip():
        results = get_arxiv_full_metadata(query, cat, MAX_PAPERS)
    return generate_styled_html(results, query, cat)
