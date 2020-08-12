import re
import sys

from coleo import Argument as Arg, default, tooled

from ..config import get_config
from ..io import ResearchersFile
from ..papers import Papers
from ..query import QueryError, QueryManager


def _date(x, ending):
    if x is None:
        return None
    elif re.match(r"^[0-9]+$", x):
        return f"{x}-{ending}"
    else:
        return x


@tooled
def search():

    # Microsoft Cognitive API key
    key: Arg & str = default(get_config("key"))

    # [alias: -t]
    # [nargs: *]
    # Search words in the title
    title: Arg & str = default(None)
    title = title and " ".join(title)

    # [alias: -a]
    # [nargs: *]
    # Search for an author
    author: Arg & str = default(None)
    author = author and " ".join(author)
    if author and re.match(r"^[0-9]+$", author):
        author = int(author)

    # [alias: -w]
    # [nargs: *]
    # Search words in the title or abstract
    words: Arg & str = default(None)
    words = words and " ".join(words)

    # [alias: -k]
    # [nargs: *]
    # Search for keywords
    keywords: Arg & str = default(None)

    # [alias: -i]
    # [nargs: *]
    # Search papers from institution
    institution: Arg & str = default(None)
    institution = institution and " ".join(institution)

    # [alias: -r]
    # Researchers file (JSON)
    researchers: Arg = default(None)
    if researchers:
        researchers = ResearchersFile(researchers)

    # [nargs: *]
    # Researcher status(es) to filter for
    status: Arg = default([])

    # [alias: -y]
    # Year
    year: Arg & int = default(None)

    # Start date (yyyy-mm-dd or yyyy)
    start: Arg = default(str(year) if year is not None else None)
    start = _date(start, ending="01-01")

    # End date (yyyy-mm-dd or yyyy)
    end: Arg = default(str(year) if year is not None else None)
    end = _date(end, ending="12-31")

    # Sort by most recent
    recent: Arg & bool = default(False)

    # Sort by most cited
    cited: Arg & bool = default(False)

    # Number of papers to fetch (default: 100)
    limit: Arg & int = default(100)

    # Search offset
    offset: Arg & int = default(0)

    qm = QueryManager(key)

    if researchers:
        qs = []
        for researcher in researchers:
            for role in researcher.with_status(*status):
                for rid in researcher.ids:
                    qs.append(
                        {
                            "title": title,
                            "author": rid,
                            "words": words,
                            "keywords": keywords,
                            "institution": institution,
                            "daterange": (role.begin, role.end),
                        }
                    )

    else:
        qs = [
            {
                "title": title,
                "author": author,
                "words": words,
                "keywords": keywords,
                "institution": institution,
                "daterange": (start, end),
            }
        ]

    papers = []

    for q in qs:
        if recent:
            orderby = "D:desc"
        elif cited:
            orderby = "CC:desc"
        else:
            orderby = None

        papers.extend(
            qm.query(
                q,
                attrs=",".join(Papers.fields),
                orderby=orderby,
                count=limit,
                offset=offset,
            )
        )
    papers = Papers({p["Id"]: p for p in papers}, researchers)

    # We need to re-sort the papers if there was more than one query
    if len(qs) > 1:
        if recent:
            papers = papers.sorted("D", desc=True)
        elif cited:
            papers = papers.sorted("CC", desc=True)

    return papers
