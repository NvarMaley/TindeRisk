"""Download official FOMC statements and score them in a separate offline run."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline

from .data_loader import next_market_session
from .paths import PROCESSED_DATA, RAW_DATA
from .provenance import sha256_file

FED = "https://www.federalreserve.gov"
START, END = "2010-01-01", "2020-03-31"
LABELS = {0: "dovish", 1: "hawkish", 2: "neutral"}
MODEL_ID = "gtfintechlab/FOMC-RoBERTa"
MODEL_REVISION = "1c0e40cc6f364fe60f92482ffa496f65647f4a34"
ROBERTA_FILES = ("config.json", "pytorch_model.bin", "tokenizer.json", "tokenizer_config.json")
DATA_REVISION = "98646987452b326507479cf641571b33814bb73f"
TRAIN_FILE, TEST_FILE = "1996-2019-train.xlsx", "2020-2022-test.xlsx"
STATEMENTS = "statements.json"
PATH_DATE = re.compile(r"/(?:monetary)?(\d{8})[a-z]\.htm$")
ABBREVIATIONS = re.compile(r"\b(?:[A-Za-z]\.){2,}|\b(?:Mr|Mrs|Ms|Dr|Gov|Sen|Rep)\.|\b[A-Z]\.")


def statement_links(html, archive_url):
    article = BeautifulSoup(html, "html.parser").select_one("#article")
    if article is None:
        raise ValueError(f"FOMC archive has no article: {archive_url}")
    urls = set()
    for anchor in article.select("a[href]"):
        url = urljoin(archive_url, anchor["href"])
        parsed = urlsplit(url)
        if (anchor.get_text(" ", strip=True) == "Statement"
                and parsed.netloc == "www.federalreserve.gov" and PATH_DATE.search(parsed.path)):
            urls.add(url)
    if not urls:
        raise ValueError(f"No FOMC statement links found on {archive_url}")
    return sorted(urls)


def parse_statement(html, source_url):
    article = BeautifulSoup(html, "html.parser").select_one("#article")
    if article is None:
        raise ValueError(f"FOMC release has no article: {source_url}")
    date = article.select_one(".article__time")
    title = article.select_one("h3")
    body = article.select_one("div.col-md-8:not(.heading)")
    if date is None or title is None or body is None:
        raise ValueError(f"FOMC release lacks date, title or body: {source_url}")
    published = datetime.strptime(date.get_text(" ", strip=True), "%B %d, %Y").date().isoformat()
    url_date = PATH_DATE.search(urlsplit(source_url).path)
    if url_date is None or published.replace("-", "") != url_date.group(1):
        raise ValueError(f"FOMC publication date differs from archive URL: {source_url}")
    paragraphs = []
    for p in body.select("p"):
        text = p.get_text(" ", strip=True)
        if text.startswith(("For media inquiries", "Last Update")):
            break
        link_text = " ".join(a.get_text(" ", strip=True) for a in p.select("a"))
        if text and text != link_text:
            paragraphs.append(text)
    if not paragraphs:
        raise ValueError(f"No FOMC statement paragraphs found: {source_url}")
    return {"publication_date": published, "title": title.get_text(" ", strip=True),
            "source_url": source_url, "paragraphs": paragraphs}


def _download(url):
    return subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location",
         "--retry", "2", "--max-time", "20", url],
        check=True, capture_output=True,
    ).stdout


def fetch_inputs(directory):
    """Fetch the Federal Reserve archive and the authors' pinned chronological splits."""
    directory.mkdir(parents=True, exist_ok=True)
    archives = [f"{FED}/monetarypolicy/fomchistorical{year}.htm" for year in range(2010, 2021)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        urls = {
            url for archive_url, html in zip(archives, pool.map(_download, archives), strict=True)
            for url in statement_links(html, archive_url)
        }
        urls = sorted(url for url in urls if START.replace("-", "") <= PATH_DATE.search(
            urlsplit(url).path).group(1) <= END.replace("-", ""))
        documents = []
        for url, html in zip(urls, pool.map(_download, urls), strict=True):
            document = parse_statement(html, url)
            document["source_sha256"] = hashlib.sha256(html).hexdigest()
            documents.append(document)
    documents.sort(key=lambda row: (row["publication_date"], row["source_url"]))
    (directory / STATEMENTS).write_text(json.dumps({
        "period": [START, END], "archive_urls": archives,
        "retrieved_at_utc": datetime.now(UTC).isoformat(), "statements": documents,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    base = f"https://raw.githubusercontent.com/gtfintechlab/fomc-hawkish-dovish/{DATA_REVISION}/look_ahead_bias"
    for name in (TRAIN_FILE, TEST_FILE):
        (directory / name).write_bytes(_download(f"{base}/{name}"))
    return len(documents)


def split_sentences(paragraphs):
    sentences = []
    for paragraph in paragraphs:
        protected = ABBREVIATIONS.sub(lambda match: match[0].replace(".", "\x00"), paragraph)
        sentences.extend(
            part.replace("\x00", ".") for part in re.split(r"(?<=[.!?])\s+", protected.strip()) if part
        )
    return sentences


def baseline_predictor(directory):
    """Train TF-IDF/logistic regression on the authors' 1996–2019 sample."""
    train = pd.read_excel(directory / TRAIN_FILE, usecols=["sentence", "year", "label"])
    test = pd.read_excel(directory / TEST_FILE, usecols=["sentence", "year", "label"])
    if not train["year"].between(1996, 2019).all() or not test["year"].between(2020, 2022).all():
        raise ValueError("Unexpected FOMC annotated split chronology")
    seen = train["sentence"].str.casefold().str.split().str.join(" ")
    repeated = test["sentence"].str.casefold().str.split().str.join(" ").isin(seen)
    test = test.loc[~repeated]
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(max_iter=500),
    ).fit(train["sentence"], train["label"])
    labels = model.predict(test["sentence"])
    return model.predict, {
        "classifier": "tfidf_logistic_baseline", "annotated_data_revision": DATA_REVISION,
        "train_rows": len(train), "test_rows": len(test), "test_train_duplicates": int(repeated.sum()),
        "test_accuracy": accuracy_score(test["label"], labels),
        "test_macro_f1": f1_score(test["label"], labels, average="macro"),
        "majority_accuracy": test["label"].eq(train["label"].mode().item()).mean(),
        "annotated_sha256": {name: sha256_file(directory / name) for name in (TRAIN_FILE, TEST_FILE)},
    }


def roberta_cached() -> bool:
    """Check the pinned checkpoint without contacting the Hub."""
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    return all(
        isinstance(try_to_load_from_cache(MODEL_ID, filename, revision=MODEL_REVISION), str)
        for filename in ROBERTA_FILES
    )


def roberta_predictor():
    """Use the official pinned checkpoint from the local Hugging Face cache."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    options = {"revision": MODEL_REVISION, "local_files_only": True}
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, **options)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, **options).eval()
    if model.config.num_labels != 3:
        raise ValueError("Unexpected number of FOMC-RoBERTa labels")

    def predict(sentences):
        with torch.inference_mode():
            inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True)
            return model(**inputs).logits.argmax(dim=1).tolist()

    return predict, {"classifier": MODEL_ID, "checkpoint_revision": MODEL_REVISION}


def score_statements(documents, predict):
    rows = []
    for document in documents:
        sentences = split_sentences(document["paragraphs"])
        labels = list(predict(sentences)) if sentences else []
        if not labels or len(labels) != len(sentences) or not all(code in LABELS for code in labels):
            raise ValueError(f"Invalid sentence predictions: {document['source_url']}")
        counts = {label: labels.count(code) for code, label in LABELS.items()}
        rows.append({
            "publication_date": document["publication_date"], "source_url": document["source_url"],
            **counts, "sentences": len(labels),
            "tone": (counts["hawkish"] - counts["dovish"]) / len(labels),
        })
    result = pd.DataFrame(rows).sort_values(["publication_date", "source_url"], ignore_index=True)
    result["publication_date"] = pd.to_datetime(result["publication_date"])
    result["available_date"] = next_market_session(result["publication_date"])
    return result


def build_tone(directory, output, classifier):
    predict, report = baseline_predictor(directory) if classifier == "baseline" else roberta_predictor()
    statement_path = directory / STATEMENTS
    source = json.loads(statement_path.read_text(encoding="utf-8"))
    tone = score_statements(source["statements"], predict)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"fomc_tone_{classifier}.parquet"
    tone.to_parquet(path, index=False)
    report.update(documents=len(tone), sentences=int(tone["sentences"].sum()),
                  statements_sha256=sha256_file(statement_path), tone_sha256=sha256_file(path))
    path.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    return tone, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fetch", "baseline", "roberta"))
    args = parser.parse_args()
    directory = RAW_DATA / "fomc"
    if args.action == "fetch":
        print(f"Downloaded {fetch_inputs(directory)} dated statements and two annotated splits.")
    else:
        if args.action == "roberta" and not roberta_cached():
            parser.error(f"Official checkpoint missing locally. Request access at https://huggingface.co/{MODEL_ID}, "
                         f"then cache revision {MODEL_REVISION} before running offline.")
        _, report = build_tone(directory, PROCESSED_DATA, args.action)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
