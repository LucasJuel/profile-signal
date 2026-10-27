"""Collect a small Reddit review queue and publish manually coded counts.

Uses only the Python standard library. No Reddit content is sent to a third party.
"""

import argparse
import base64
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "data" / "review.csv"
OUTPUT = ROOT / "dist" / "evidence.json"
COMMUNITIES = ("Bumble", "hingeapp", "Tinder")
THEMES = {
    "first_photo": "Weak first photo",
    "generic_prompts": "Generic prompts",
    "photo_variety": "No photo variety",
    "intention": "Unclear intention",
    "negative_framing": "Negative framing",
    "reply_hook": "No reply hook",
    "story_mismatch": "Mismatch in story",
}
FIELDS = ("subreddit", "post_id", "post_url", "comment_url", "comment_excerpt", "themes")


def load_local_env():
    """Read only the expected keys from an ignored local .env file."""
    path = ROOT / ".env"
    if not path.exists():
        return
    allowed = {"REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in allowed:
            os.environ.setdefault(key, value.strip().strip("'\""))


def request(url, *, token=None, data=None, basic=None, agent=None):
    headers = {"User-Agent": agent or "ProfileSignal/0.1"}
    if token:
        headers["Authorization"] = "bearer " + token
    if basic:
        headers["Authorization"] = "Basic " + base64.b64encode(basic.encode()).decode()
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.load(response)
            remaining = response.headers.get("X-Ratelimit-Remaining")
            reset = response.headers.get("X-Ratelimit-Reset")
            if remaining and reset and float(remaining) < 2:
                time.sleep(min(float(reset) + 1, 120))
            return payload
    except urllib.error.HTTPError as error:
        detail = error.read(300).decode("utf-8", "replace")
        raise RuntimeError(f"Reddit API returned HTTP {error.code}: {detail}") from error


def oauth_token(agent):
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET first.")
    auth = f"{client_id}:{client_secret}"
    result = request(
        "https://www.reddit.com/api/v1/access_token",
        data=b"grant_type=client_credentials",
        basic=auth,
        agent=agent,
    )
    if "access_token" not in result:
        raise RuntimeError(f"Reddit did not issue an access token: {result.get('error', 'unknown error')}")
    return result["access_token"]


def api(path, params, token, agent):
    query = urllib.parse.urlencode({**params, "raw_json": 1})
    return request(f"https://oauth.reddit.com{path}?{query}", token=token, agent=agent)


def collect(per_community):
    if REVIEW.exists():
        raise RuntimeError(f"{REVIEW} already exists; move it aside before collecting again so your coding is preserved.")
    load_local_env()
    agent = os.getenv("REDDIT_USER_AGENT")
    if not agent or "yourname" in agent:
        raise RuntimeError("Set REDDIT_USER_AGENT to a unique value with your Reddit username.")
    token = oauth_token(agent)
    rows = []
    seen = set()
    for community in COMMUNITIES:
        for phrase in ('"profile review"', '"profile feedback"'):
            listing = api(
                f"/r/{community}/search",
                {"q": phrase, "restrict_sr": "on", "sort": "new", "t": "year", "limit": per_community},
                token, agent,
            )
            for item in listing.get("data", {}).get("children", []):
                post = item.get("data", {})
                post_id = post.get("id")
                if not post_id or post_id in seen or post.get("over_18"):
                    continue
                seen.add(post_id)
                comments = api(
                    f"/comments/{post_id}",
                    {"limit": 30, "depth": 1, "sort": "top"}, token, agent,
                )
                if not isinstance(comments, list) or len(comments) < 2:
                    continue
                post_url = "https://www.reddit.com" + post.get("permalink", "")
                for item in comments[1].get("data", {}).get("children", []):
                    if item.get("kind") != "t1":
                        continue
                    comment = item.get("data", {})
                    body = " ".join(comment.get("body", "").split())
                    if len(body) < 40 or body in ("[deleted]", "[removed]"):
                        continue
                    rows.append({
                        "subreddit": community,
                        "post_id": post_id,
                        "post_url": post_url,
                        "comment_url": f"https://www.reddit.com/r/{community}/comments/{post_id}/_/{comment['id']}/",
                        "comment_excerpt": body[:240],
                        "themes": "",
                    })
                time.sleep(0.7)
    REVIEW.parent.mkdir(exist_ok=True)
    with REVIEW.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Collected {len(rows)} comments from {len(seen)} candidate threads into {REVIEW}")


def build():
    if not REVIEW.exists():
        raise RuntimeError("Run collect first, then code the themes column in data/review.csv.")
    with REVIEW.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    counts = defaultdict(set)
    links = defaultdict(list)
    coded_threads = set()
    coded_comments = 0
    for row in rows:
        codes = {part.strip() for part in row["themes"].split(";") if part.strip()}
        unknown = codes - THEMES.keys()
        if unknown:
            raise ValueError(f"Unknown theme code(s): {', '.join(sorted(unknown))}")
        if codes:
            coded_comments += 1
            coded_threads.add(row["post_id"])
        for code in codes:
            key = (row["subreddit"], code)
            counts[key].add(row["post_id"])
            if row["comment_url"] not in links[key] and len(links[key]) < 5:
                links[key].append(row["comment_url"])
    if not coded_comments:
        raise RuntimeError("No themes were coded. Review the CSV before building evidence.")
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "Recent Reddit search results for profile review/profile feedback; manually coded top-level comments. Counts are distinct threads with at least one coded comment, not prevalence estimates.",
        "candidate_threads": len({row["post_id"] for row in rows}),
        "candidate_comments": len(rows),
        "coded_comments": coded_comments,
        "coded_threads": len(coded_threads),
        "themes": [
            {
                "id": code,
                "name": label,
                "counts": {community.lower(): len(counts[(community, code)]) for community in COMMUNITIES},
                "sources": {community.lower(): links[(community, code)] for community in COMMUNITIES},
            }
            for code, label in THEMES.items()
        ],
    }
    OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {OUTPUT} from {coded_comments} coded comments in {len(coded_threads)} threads")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "build", "themes"))
    parser.add_argument("--per-community", type=int, default=25, help="results per query per community (1-100)")
    args = parser.parse_args()
    try:
        if args.command == "themes":
            for code, label in THEMES.items():
                print(f"{code}: {label}")
        elif args.command == "collect":
            if not 1 <= args.per_community <= 100:
                parser.error("--per-community must be between 1 and 100")
            collect(args.per_community)
        else:
            build()
    except (RuntimeError, ValueError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
