# Privacy policy

Last updated: 22 November 2026

Holdnote is an open-source Claude skill. It runs inside your own Claude
session and has no server, account system or analytics of its own.

## What Holdnote collects

Nothing. Holdnote does not collect, store or share personal data, and it
has no way to send data to its author.

## What Holdnote reads

- **Files you give it**: a broker export, a screenshot of your holdings, or
  the files in your `me/` folder. These are read inside your Claude session
  to answer your question.
- **Public documents**: SEC filings, fund factsheets, KIDs, fund holdings
  files, exchange prices, ECB rates and news articles. The full list of
  sites is in the README under "What it connects to". A request to these
  sites names at most the fund, ticker or ISIN being researched, never your
  holdings, amounts or account details.

## Where your data is kept

Only where you choose at setup: a folder on your computer, your own private
GitHub repository, or nowhere (you attach your file each time). Holdnote
writes there only when you ask it to save something. Deleting that folder or
repository deletes everything Holdnote kept.

Your conversations with Claude are handled by Anthropic under its own
privacy policy: https://www.anthropic.com/legal/privacy

## Optional GitHub setup

If you choose the GitHub option, a GitHub Actions workflow in your own copy
of the repository downloads public fund holdings files and commits them to
that repository. It runs under your GitHub account and sends nothing
elsewhere.

## Contact

Questions about privacy: open an issue at
https://github.com/Artvarna/holdnote/issues
