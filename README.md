# Profile Signal

A static site in `dist/` plus a local, read-only Reddit evidence pipeline. The site does not need Reddit credentials. It shows no numeric chart until reviewed evidence is built.

## Reddit access

Use an approved Reddit Data API app for this exact, personal noncommercial use case. Set these environment variables in your shell (never in the site or a committed file):

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT` (for example `windows:profile-signal:v0.1 (by /u/yourname)`)

You can instead put those three `KEY=value` lines in a local `.env` file at the repo root. It is ignored by Git. Do not send your secret in chat.

PowerShell example:

```powershell
$env:REDDIT_CLIENT_ID = 'your-client-id'
$env:REDDIT_CLIENT_SECRET = 'your-client-secret'
$env:REDDIT_USER_AGENT = 'windows:profile-signal:v0.1 (by /u/yourname)'
python scripts/reddit_evidence.py collect
```

The script samples recent search results for `profile review` and `profile feedback` in r/Bumble, r/hingeapp, and r/Tinder, then fetches top-level comments. It writes `data/review.csv`, which is ignored by Git. It stores no account names or post bodies. Reddit results and availability change; this is a convenience sample, not a representative one.

Open `data/review.csv` and enter one or more theme codes in the `themes` column of comments that actually give that advice. Separate codes with semicolons. Leave irrelevant comments blank. The accepted codes are listed by `python scripts/reddit_evidence.py themes`. Review the linked post and comment before coding. A thread counts once per theme, even if several comments mention it. After review:

```powershell
python scripts/reddit_evidence.py build
```

This writes `dist/evidence.json` with counts and links to supporting comments. The site loads that file on refresh. Review this public artifact before publishing. Keep the local CSV private: it contains short excerpts from other people's comments.

Do not use this workflow beyond your approved use case. Follow Reddit's [Data API terms](https://redditinc.com/policies/data-api-terms), [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy), and [API guidance](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki).
