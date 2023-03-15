from datetime import datetime
from coleo import Option, tooled

from paperoni.sources.acquire import readpage
from paperoni.model import (
    Author,
    DatePrecision,
    Institution,
    InstitutionCategory,
    Link,
    Meta,
    Paper,
    PaperAuthor,
    Release,
    Venue,
    VenueType,
)

from .base import BaseScraper

def parse_paper(entry):
    if evt := getattr(entry, "event", None):
        # Define the release if the paper is related to an event
        if "start" in evt:
            # Use the start date of the event if it is mentioned
            date_parts = evt["start"]["date-parts"][0]
        else:
            # Otherwise, use the information of print publication, global publication,
            # online publication or creation of the entry (in this order priority)
            for field in (
                "published-print",
                "published",
                "published-online",
                "created",
            ):
                if dateholder := getattr(entry, field, None):
                    date_parts = dateholder["date-parts"][0]
                    break
        
        precision = [
            DatePrecision.year,
            DatePrecision.month,
            DatePrecision.day,
        ][len(date_parts) -1]

        date_parts += [1] * (3 - len(date_parts))
        release = Release(
            venue=Venue(
                aliases=[],
                name=evt["name"],
                type=VenueType.conference,
                series=evt["name"],
                links=[],
                open=False,
                peer_reviewed=False,
                publisher=None,
                date_precision=precision,
                date=datetime(*date_parts),
                quality=(1,),
            ),
            status="published",
            pages=None,
        )
        
        releases = [release]
    else:
        releases = []

    # Create the Paper
    p = Paper(
        title=entry["title"][0],
            authors=[
                PaperAuthor(
                    author=Author(
                        name=f"{author['given']} {author['family']}" if "given" in author and "family" in author else "",
                        roles=[],
                        aliases=[],
                        links=[],
                    ),
                    affiliations=[
                        Institution(
                            name=aff["name"],
                            category=InstitutionCategory.unknown,
                            aliases=[],
                        )
                        for aff in author["affiliation"]
                    ],
                )
                for author in entry["author"]
            ] if "author" in entry else [],
            abstract=entry["abstract"] if "abstract" in entry else "",
            links=[Link(type="doi", link=entry["URL"])],
            topics=[],
            releases=releases,
            quality=(0,),
    )
    return p

class CrossrefScraper(BaseScraper):
    @tooled
    def query(
        self,
        # Title of the article to query
        # [alias -t]
        title: Option = None,
    ):
        data = readpage(
            f"http://api.crossref.org/works?query.title=%22{title}%22",
            format="json",
        )

        # Parse and yield the resulting papers
        results = data["message"]["items"]
        for entry in results:
            yield parse_paper(entry)

    @tooled
    def acquire(self):
        # Title of the article to query
        # [alias -t]
        title: Option = (None,)

        yield Meta(
            scraper="crossref",
            date=datetime.now(),
        )
        yield from self.query(title)

    @tooled
    def prepare(self):
        pass


__scrapers__ = {
    "crossref": CrossrefScraper,
}