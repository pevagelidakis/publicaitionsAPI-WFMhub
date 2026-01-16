from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import arxiv
from typing import List, Dict
from datetime import datetime
import html

app = FastAPI()
MAX_PAPERS = 50


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
def build_arxiv_query(text_query: str, categories: List[str]) -> str:
    """
    Constructs a boolean query string for searching ArXiv with optional category filtering.

    Parameters:
        text_query (str): The main search query text (e.g., keywords, author names, or phrases).
        categories (List[str]): A list of ArXiv category codes to filter the search.
            If empty, no category filtering is applied.

    Returns:
        str: A combined ArXiv search query string.
            - If categories are provided, the query is of the form:
              "(cat:category1 OR cat:category2 ...) AND all:text_query"
            - If no categories are provided, it returns just the text_query.

    Example:
        >>> build_arxiv_query("deep learning", ["cs.LG", "cs.CV"])
        "(cat:cs.LG OR cat:cs.CV) AND all:deep learning"
    """
    if not categories:
        return text_query
    cats = " OR ".join(f"cat:{c}" for c in categories)
    return f"({cats}) AND all:{text_query}"



def get_arxiv_full_metadata(query_term: str, categories: List[str], max_results: int) -> List[Dict]:
    """
    Searches ArXiv using the provided query and categories, and returns structured metadata for each paper.

    Parameters:
        query_term (str): The main search query string.
        categories (List[str]): A list of ArXiv category codes to filter the search.
        max_results (int): Maximum number of papers to fetch from ArXiv.

    Returns:
        List[Dict]: A list of dictionaries, each representing a paper with the following keys:
            - "Title" (str): Paper title
            - "Authors" (str): Comma-separated author names, combining the last two with '&'
            - "Abstract" (str): Paper abstract
            - "URL" (str): Direct PDF URL to the paper
            - "DOI" (str): Paper DOI or ArXiv identifier if DOI is unavailable
            - "Categories" (str): Comma-separated ArXiv categories
            - "Published" (str): Publication date formatted as "Month Day, Year"; "Unknown" if unavailable

    Behavior:
        - Builds a query using `build_arxiv_query`.
        - Sorts results by relevance in descending order.
        - Combines the last two authors with '&' if multiple authors exist.
        - Formats the publication date to a readable string.
        - Returns papers sorted by newest first.

    Example:
        >>> papers = get_arxiv_full_metadata("transformers", ["cs.CL"], 5)
        >>> papers[0]["Title"]
        "Attention Is All You Need"
    """
    final_query = build_arxiv_query(query_term, categories)

    search = arxiv.Search(
        query=final_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending,
    )

    client = arxiv.Client()
    papers = []

    for result in client.results(search):
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


def generate_styled_html(papers: List[Dict], search_query: str, selected_cats: List[str]) -> str:
    """
    Generates a fully styled HTML page displaying the search results and an advanced search panel.

    Parameters:
        papers (List[Dict]): List of paper metadata dictionaries (as returned by `get_arxiv_full_metadata`).
        search_query (str): The original search query string to display in the search box and results header.
        selected_cats (List[str]): List of category codes that were selected for filtering (used to pre-check checkboxes).

    Returns:
        str: A string containing a complete HTML page including:
            - A modern, pill-shaped search input
            - An "Advanced search" expandable section with category checkboxes
            - A list of papers, each displayed as a card with:
                - Title, authors, categories, DOI, publication date
                - Abstract preview
                - Hover effects for visual interaction

    Features:
        - Uses Playfair Display font
        - Responsive layout
        - Hover animations for paper cards
        - Expanding/collapsing advanced search section
        - Color-coded, modern UI styling

    Example:
        >>> html_content = generate_styled_html(papers, "quantum computing", ["quant-ph"])
        >>> with open("results.html", "w") as f:
        >>>     f.write(html_content)
    """
    safe_query = html.escape(search_query)

    html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>ArXiv Search</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Playfair Display', serif; margin: 10px; }}
            /* Center the box */
            .search-box {{
                display: flex;
                justify-content: center;
                margin: 30px 0;
            }}
            
            /* Form container: align input and button horizontally */
            .search-box form {{
                display: flex;
                flex-direction: column;
                gap: 14px;
                width: 80%;
                max-width: 800px;
            }}

            .search-row {{
                display: flex;
                align-items: center;
                background: white;
                border-radius: 999px;
                padding: 6px;
                box-shadow: 0 12px 30px rgba(0,0,0,0.08);
                transition: box-shadow 0.3s ease, transform 0.2s ease;
            }}

            .search-row:focus-within {{
                box-shadow: 0 14px 40px rgba(74,144,226,0.25);
                transform: translateY(-1px);
            }}

            .search-icon {{
                margin-left: 14px;
                font-size: 16px;
                opacity: 0.6;
            }}

            
            /* Style the input */
            .search-box input[type="text"] {{
                flex: 1;
                padding: 14px 16px;
                font-size: 16px;
                border: none;
                outline: none;
                background: transparent;
                font-family: 'Playfair Display', serif;
            }}

            /*.search-box input[type="text"] {{
                flex: 1; 
                padding: 12px 20px;
                font-size: 16px;
                border: 2px solid #ccc;
                border-radius: 30px 0 0 30px; /* rounded left side */
                outline: none;
                transition: 0.3s;
                font-family: 'Playfair Display', serif;
            }}*/
            
            /* Focus effect */
            .search-box input[type="text"]:focus {{
                border-color: #4A90E2;
                box-shadow: 0 0 10px rgba(74, 144, 226, 0.4);
            }}
            

            .search-box button {{
                padding: 12px 25px;
                font-size: 18px;
                font-weight: 600;
                border: 2px solid #4A90E2;
                border-left: none; 
                background: linear-gradient(135deg, #4A90E2, #357ABD);
                color: white;
                border-radius: 999px;
                cursor: pointer;
                transition: transform 0.15s ease, box-shadow 0.2s ease;
                font-family: 'Playfair Display', serif;

            }}

            .search-box button:hover {{
                transform: translateY(-1px);
                box-shadow: 0 6px 18px rgba(53,122,189,0.35);
            }}


            /* Style the button 
            .search-box button {{
                padding: 12px 25px;
                font-size: 16px;
                border: 2px solid #4A90E2;
                border-left: none; 
                background-color: #4A90E2;
                color: white;
                border-radius: 0 30px 30px 0; 
                cursor: pointer;
                transition: 0.3s;
            }}
            
            .search-box button:hover {{
                background-color: #357ABD;
                border-color: #357ABD;
            }}*/

/* ---------- Advanced Search ---------- */

details.advanced {{
    margin-top: 14px;
    justify:center;
}}

details.advanced summary {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-radius: 999px;
    background: #eef3fb;
    color: #2f5fb3;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    list-style: none;
}}

details.advanced summary::marker {{
    display: none;
}}

details.advanced summary::after {{
    content: "▾";
    font-size: 12px;
    transition: transform 0.2s ease;
}}

details.advanced[open] summary::after {{
    transform: rotate(180deg);
}}

.advanced-panel {{
    margin-top: 14px;
    padding: 18px;
    border-radius: 14px;
    background: white;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
    animation: fadeIn 0.2s ease;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(0px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

details.domain {{
    margin: 12px 0;
}}

details.domain summary {{
    font-weight: 600;
    cursor: pointer;
    align: center;
}}

.subcats {{
    margin: 10px 0 0 20px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 6px;
}}

label {{
    font-size: 14px;
}}


.authors {{ font-size: 12px; text-align: center; }}
.title {{ font-size: 18px; font-weight: bold; text-align: center; }}
.abstract {{ font-size: 14px; text-align: justify; }}


.paper {{
    background: white;
    border-radius: 16px;
    padding: 20px;
    margin: 22px 0;
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    transition: transform 0.25s ease, box-shadow 0.25s ease, border 0.25s ease;
    border: 1px solid transparent;
    cursor: pointer;
}}

.paper:hover {{
    transform: translateY(-4px) scale(1.02);
    box-shadow: 0 16px 40px rgba(0,0,0,0.12);
    border: 1px solid #4A90E2; /* subtle highlight on hover */
}}

.paper::before {{
    content: "";
    display: block;
    height: 4px;
    border-radius: 2px 2px 0 0;
    background: linear-gradient(90deg, #4A90E2, #357ABD);
    margin: -20px -20px 16px -20px; 
    opacity: 0;
    transition: opacity 0.25s ease;
}}
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
            html_content += f"""
<label>
<input type="checkbox" name="cat" value="{code}" {checked}>
{label}
</label>
"""
        html_content += "</div></details>"

    html_content += """
</div>
</details>

</form>
</div>
"""

    if search_query:
        html_content += f"<h2>Results for “{safe_query}”</h2>"
        for p in papers:
            html_content += f"""
<div class="paper">
    <a href="{p['URL']}" target="_blank" style = "color: #000000;\n      text-decoration: none;">
    <div class="authors"><a href="{p['URL']}" target="_blank" style = "color: #000000;\n      text-decoration: none;">{p['Authors']}</a></div>
    <div class="title">
        <a href="{p['URL']}" target="_blank" style = "color: #000000;\n      text-decoration: none;">{p['Title']}</a>
    </div>
    <p class="authors">
    Categories: {p['Categories']},  arXiv: <a href="{p['URL']}" target="_blank" style = "color: #1155cc;\n      text-decoration: none;">{p['DOI']}</a>, {p['Published']}
    </p>
    <p class="abstract">
        <a href="{p['URL']}" target="_blank" style = "color: #000000;\n      text-decoration: none;"><b>Abstract. </b>{p['Abstract']}</a>
    </p>
    </a>
</div>
"""

    return html_content


@app.get("/", response_class=HTMLResponse)
def papers(
    query: str = Query(default=""),
    cat: List[str] = Query(default=[]),
):
"""
FastAPI endpoint: GET /

Description:
This endpoint serves the main search page for arXiv papers. It handles user queries and category filters,
fetches relevant papers from the arXiv API, and returns a fully rendered HTML page.

Parameters:
- query (str, optional): The search term entered by the user. Default is an empty string.
- cat (List[str], optional): A list of selected arXiv category codes (e.g., ['cs.LG', 'cs.AI']). Default is an empty list.

Returns:
- HTMLResponse: A complete HTML page containing:
    * A search bar for entering queries
    * An advanced search panel with category checkboxes
    * A list of paper cards with authors, title, abstract, categories, DOI, and publication date
    * Interactive styles: hover effects, collapsible panels, and responsive layout

Behavior:
- If the 'query' parameter is non-empty, the endpoint calls 'get_arxiv_full_metadata' to fetch papers from arXiv.
- Selected categories in 'cat' are applied as filters.
- The search results are sorted by relevance and displayed in a styled HTML page.
- If 'query' is empty, the endpoint returns a search page with no results.

Example Usage:
GET http://localhost:8000/?query=machine+learning&cat=cs.LG&cat=cs.AI
"""

    results = []
    if query.strip():
        results = get_arxiv_full_metadata(query, cat, MAX_PAPERS)

    return generate_styled_html(results, query, cat)
