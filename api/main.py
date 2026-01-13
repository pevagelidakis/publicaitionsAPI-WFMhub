from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import arxiv
from typing import List, Dict
from datetime import datetime
import html

app = FastAPI()

MAX_PAPERS = 50


def get_arxiv_full_metadata(query_term: str, max_results: int) -> List[Dict]:
    """Retrieves metadata safely from arXiv."""
    papers_list = []
    try:
        search = arxiv.Search(
            query=query_term,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending
        )

        client = arxiv.Client()

        for result in client.results(search):
            try:
                authors = [author.name for author in result.authors] if result.authors else ["Unknown"]
                if len(authors) > 1:
                    authors[-2] = authors[-2] + " & " + authors[-1]
                    authors.pop()
                authors_str = ', '.join(authors)

                #published_str = result.published.strftime("%B %d, %Y") if result.published else "Unknown"
                doi_str = result.doi if result.doi else result.entry_id.split("arxiv.org/abs/")[-1]
                abstract_str = result.summary.strip() if result.summary else "No abstract available"
                title_str = result.title.strip() if result.title else "No title"

                papers_list.append({
                    'Title': title_str,
                    'Authors': authors_str,
                    'Abstract': abstract_str,
                    'URL': result.entry_id.replace('http:', 'https:').replace('abs', 'pdf'),
                    'DOI': doi_str,
                    #'Published': published_str,
                    'Published': result.published if result.published else None,
                })
            except Exception as e_paper:
                # Skip a paper if processing fails
                print(f"Skipping a paper due to error: {e_paper}")
                continue
        for res in papers_list:
            if isinstance(res['Published'], datetime):
                res['Published'] = res['Published'].strftime("%B %d, %Y")
            else:
                res['Published'] = "Unknown"

    except Exception as e_search:
        print(f"Error fetching arXiv results: {e_search}")

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
            /* Center the box */
            .search-box {{
                display: flex;
                justify-content: center;
                margin: 30px 0;
            }}
            
            /* Form container: align input and button horizontally */
            .search-box form {{
                display: flex;
                width: 80%;   /* make form wider */
                max-width: 800px;
            }}
            
            /* Style the input */
            .search-box input[type="text"] {{
                flex: 1; /* take all available space */
                padding: 12px 20px;
                font-size: 16px;
                border: 2px solid #ccc;
                border-radius: 30px 0 0 30px; /* rounded left side */
                outline: none;
                transition: 0.3s;
                font-family: 'Playfair Display', serif;
            }}
            
            /* Focus effect */
            .search-box input[type="text"]:focus {{
                border-color: #4A90E2;
                box-shadow: 0 0 10px rgba(74, 144, 226, 0.4);
            }}
            
            /* Style the button */
            .search-box button {{
                padding: 12px 25px;
                font-size: 16px;
                border: 2px solid #4A90E2;
                border-left: none; /* avoid double border with input */
                background-color: #4A90E2;
                color: white;
                border-radius: 0 30px 30px 0; /* rounded right side */
                cursor: pointer;
                transition: 0.3s;
            }}
            
            /* Hover effect */
            .search-box button:hover {{
                background-color: #357ABD;
                border-color: #357ABD;
            }}
            
            /* Responsive */
            @media (max-width: 600px) {{
                .search-box form {{
                    width: 95%;
                }}
                .search-box input[type="text"], .search-box button {{
                    font-size: 14px;
                    padding: 10px;
                }}
            }}
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
            html_content += f"""<h2 style= "text-align: center;\n font-size: 28px;\n font-family: 'Playfair Display', serif;\n ">Latest Papers for "{search_query}"</h2>"""
        for paper in papers:
            html_content += f"""
            <div class="paper-section">
                <div class="authors"><a href="{paper['URL']}" target="_blank" style = "color: #000000;\n      text-decoration: none;">{paper['Authors']}</a></div>
                <div class="title">
                    <a href="{paper['URL']}" target="_blank" style = "color: #000000;\n      text-decoration: none;">{paper['Title']}</a>
                </div>
                <p class="authors">
                arXiv: <a href="{paper['URL']}" target="_blank" style = "color: #1155cc;\n      text-decoration: none;">{paper['DOI']}</a>, {paper['Published']}
                </p>
                <p class="abstract">
                    <a href="{paper['URL']}" target="_blank" style = "color: #000000;\n      text-decoration: none;"><span class="bold-prefix">Abstract. </span>{paper['Abstract']}</a>
                </p>
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













