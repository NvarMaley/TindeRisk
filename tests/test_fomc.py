import pandas as pd
import pytest

from src.fomc import parse_statement, score_statements, split_sentences, statement_links

URL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm"


def test_archive_links_deduplicate_and_skip_other_materials():
    archive = """
    <div id="article">
      <a href="/newsevents/pressreleases/monetary20200315a.htm">Statement</a>
      <a href="/newsevents/pressreleases/monetary20200315a.htm">Statement</a>
      <a href="/newsevents/pressreleases/monetary20200315b.htm">Implementation Note</a>
      <a href="https://other.example/monetary20200315a.htm">Statement</a>
    </div>
    """
    assert statement_links(archive, URL) == [URL]


def test_publication_date_and_statement_body():
    html = """
    <div id="article">
      <p class="article__time">March 15, 2020</p>
      <h3>Federal Reserve issues FOMC statement</h3>
      <div class="col-md-8"><p>One policy sentence.</p>
      <p><a href="/more">Related announcement</a></p>
      <p>For media inquiries, call the Board.</p>
      <p>Footer.</p></div>
    </div>
    """
    item = parse_statement(html, URL)
    assert item["publication_date"] == "2020-03-15"
    assert item["paragraphs"] == ["One policy sentence."]
    with pytest.raises(ValueError, match="differs"):
        parse_statement(html.replace("March 15", "March 16"), URL)


def test_sentence_boundaries_keep_abbreviations_initials_and_decimals():
    paragraphs = ["Mr. J. Powell cited U.S. inflation of 2.5 percent. Why did it rise?",
                  "Second paragraph with no final stop"]
    assert split_sentences(paragraphs) == [
        "Mr. J. Powell cited U.S. inflation of 2.5 percent.", "Why did it rise?",
        "Second paragraph with no final stop",
    ]


def test_tone_includes_neutral_sentences_and_uses_next_nyse_session():
    docs = [{"paragraphs": ["First. Second. Third."], "publication_date": "2020-03-15", "source_url": URL}]
    tone = score_statements(docs, lambda sentences: [0, 2, 2])
    assert tone.loc[0, "tone"] == pytest.approx(-1 / 3)
    assert tone.loc[0, "neutral"] == 2
    assert tone.loc[0, "available_date"] == pd.Timestamp("2020-03-16")
    with pytest.raises(ValueError, match="Invalid sentence predictions"):
        score_statements(docs, lambda sentences: [0, 2, 3])
