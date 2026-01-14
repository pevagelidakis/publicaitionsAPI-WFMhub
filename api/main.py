from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import arxiv
from typing import List, Dict
from datetime import datetime, timezone
import html

app = FastAPI()

MAX_PAPERS = 50


def get_arxiv_full_metadata(query_term: str, max_results: int) -> List[Dict]:
    search = arxiv.Search(
        query=query_term,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending,
    )

    # ✅ REQUIRED: user_agent
    client = arxiv.Client(
        page_size=100,
        delay_seconds=3,
        num_retries=3,
        user_agent="FastAPI-arXiv-search/1.0"
    )

    papers = []

    for result in client.results(search):
        authors = [a.name for a in result.authors]
        if len(authors) > 1:
            authors[-2] = authors[-2] + " & " + authors[-1]
            authors.pop()

        papers.append({
            "Title": result.title.strip(),
            "Authors": ", ".join(authors),
            "Abstract": result.summary.strip(),
            # ✅ Correct PDF URL
            "URL": result.pdf_url,
            "DOI": result.doi or result.get_short_id(),
            "Published": result.published,
        })

    papers.sort(key=lambda x: x["Published"], reverse=True)

    for p in papers:
        try:
            p["Published"] = p["Published"].strftime("%B %d, %Y")
        except Exception:
            p["Published"] = "Unknown"

    return papers


def generate_styled_html(papers: List[Dict], search_query: str) -> str:
    esc = html.escape
    safe_query = esc(search_query)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>arXiv Search</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display&display=swap" rel="stylesheet">
<style>
body {{ font-family: 'Playfair Display', serif; margin: 10px; }}
.search-box {{ display: flex; justify-content: center; margin: 30px 0; }}
.search-box form {{ display: flex; width: 80%; max-width: 800px; }}
.search-box input {{ flex: 1; padding: 12px; font-size: 16px; }}
.paper-section {{ margin-bottom: 25px; padding: 15px; border: 1px solid #e0e0e0; }}
.authors {{ font-size: 12px; text-align: center; }}
.title {{ font-size: 18px; font-weight: bold; text-align: center; }}
.abstract {{ font-size: 14px; text-align: justify; }}
.footer {{ font-size: 11px; color: #888; text-align: right; margin-top: 20px; }}
</style>
</head>
<body>

<div class="search-box">
<form method="get">
<input type="text" name="query" value="{safe_query}" placeholder="🔍 Search publications or topics..." />
<button type="submit">Search</button>
</form>
</div>
"""

    if search_query:
        html_content += f'<h2 style="text-align:center;">Latest Papers for "{safe_query}"</h2>'

        for p in papers:
            html_content += f"""
<div class="paper-section">
<div class="authors"><a href="{esc(p['URL'])}" target="_blank">{esc(p['Authors'])}</a></div>
<div class="title"><a href="{esc(p['URL'])}" target="_blank">{esc(p['Title'])}</a></div>
<p class="authors">arXiv: {esc(p['DOI'])} — {esc(p['Published'])}</p>
<p class="abstract"><b>Abstract.</b> {esc(p['Abstract'])}</p>
</div>
"""
    else:
        html_content += "<p style='text-align:center;'>Enter a search term to begin.</p>"

    html_content += f"""
<div class="footer">
Data fetched: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
</div>
</body></html>
"""

    return html_content


@app.get("/", response_class=HTMLResponse)
def papers(query: str = Query(default="", max_length=300)):
    try:
        results = get_arxiv_full_metadata(query.strip(), MAX_PAPERS) if query.strip() else []
        return generate_styled_html(results, query)
    except Exception as e:
        # ✅ Prevent serverless crash
        return HTMLResponse(
            content=f"<h3>Internal error</h3><pre>{html.escape(str(e))}</pre>",
            status_code=500
        )