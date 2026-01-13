from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import arxiv
from typing import List, Dict
from datetime import datetime
import html

app = FastAPI()

MAX_PAPERS = 50


def get_arxiv_full_metadata(query_term: str, max_results: int) -> List[Dict]:
    search = arxiv.Search(
        query=query_term,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending
    )

    client = arxiv.Client()
    papers_list = []

    for result in client.results(search):
        authors = [author.name for author in result.authors]
        if len(authors) > 1:
            authors[-2] = authors[-2] + " & " + authors[-1]
            authors.pop()

        papers_list.append({
            'Title': result.title.strip(),
            'Authors': ', '.join(authors),
            'Abstract': result.summary.strip(),
            'URL': result.entry_id.replace('http:', 'https:').replace('abs', 'pdf'),
            'Published': result.published.strftime("%B %d, %Y"),
        })

    return papers_list


def generate_styled_html(papers: List[Dict], search_query: str) -> str:
    safe_query = html.escape(search_query)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>ArXiv Search</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Playfair Display', serif; margin: 10px; }}
            .search-box {
                display: flex;
                justify-content: center;
                margin: 30px 0;
            }
            
            /* Style the input */
            .search-box input[type="text"] {
                width: 60%;
                padding: 12px 20px;
                font-size: 16px;
                border: 2px solid #ccc;
                border-radius: 30px 0 0 30px; /* rounded left side */
                outline: none;
                transition: 0.3s;
                font-family: 'Playfair Display', serif;
            }
            
            /* Focus effect */
            .search-box input[type="text"]:focus {
                border-color: #4A90E2;
                box-shadow: 0 0 10px rgba(74, 144, 226, 0.4);
            }
            
            /* Style the button */
            .search-box button {
                padding: 12px 25px;
                font-size: 16px;
                border: 2px solid #4A90E2;
                border-left: none; /* remove double border with input */
                background-color: #4A90E2;
                color: white;
                border-radius: 0 30px 30px 0; /* rounded right side */
                cursor: pointer;
                transition: 0.3s;
            }
            
            /* Hover effect */
            .search-box button:hover {
                background-color: #357ABD;
                border-color: #357ABD;
            }
            
            /* Make responsive for small screens */
            @media (max-width: 600px) {
                .search-box input[type="text"] {
                    width: 70%;
                    padding: 10px;
                    font-size: 14px;
                }
                .search-box button {
                    padding: 10px 15px;
                    font-size: 14px;
                }
            }
            .paper-section {{ margin-bottom: 25px; padding: 15px; border: 1px solid #e0e0e0; }}
            .authors {{ font-size: 11px; text-align: center; }}
            .title {{ font-size: 14px; font-weight: bold; text-align: center; }}
            .abstract {{ font-size: 11px; text-align: justify; }}
            .footer {{ font-size: 9px; color: #888; text-align: right; margin-top: 20px; }}
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
        for paper in papers:
            html_content += f"""
            <div class="paper-section">
                <div class="authors"><a href="{paper['URL']}" target="_blank">{paper['Authors']}</a></div>
                <div class="title"><a href="{paper['URL']}" target="_blank">{paper['Title']}</a></div>
                <p class="abstract"><b>Abstract.</b> {paper['Abstract']}</p>
            </div>
            """
    else:
        html_content += "<p style='text-align:center;'>Enter a search term to begin.</p>"

    html_content += f"""
    <div class="footer">Data fetched: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</div>
    </body></html>
    """

    return html_content


@app.get("/", response_class=HTMLResponse)
def papers(query: str = Query(default="")):
    if query.strip():
        papers = get_arxiv_full_metadata(query, MAX_PAPERS)
    else:
        papers = []

    return generate_styled_html(papers, query)


