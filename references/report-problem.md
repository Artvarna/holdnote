# Report a problem

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

Runs on "report a problem", "this is broken", "file a bug", "tell the
developer", "Holdnote didn't read my export", or "I have an idea for
Holdnote". The goal: the user presses one link and submits a useful report
in under a minute. Nothing is sent for them.

## 1. Pick the form

| The problem | `--kind` |
|---|---|
| A report looks wrong, a run stopped, a feature didn't work | `bug` |
| Their broker's export or screenshot wasn't read | `broker` |
| Something Holdnote should do | `idea` |

## 2. Fill it from the conversation

Write each field in plain words from what happened in this conversation, so
the user doesn't have to retype it: what they asked (`--asked`), what went
wrong (`--what`), what they expected (`--expected`), and any error message
word for word (`--error`). Ask at most one question, and only when what went
wrong isn't clear from the conversation.

`--install`: `plugin` when this skill's folder sits in a Claude Code plugin
cache (its name is a commit hash), `zip` for the Claude app, otherwise
`other`. Leave it out when unsure.

For `broker`: `--broker` is the broker or app, `--filetype` what they gave
(`csv`, `xlsx`, `screenshot`, `pdf`, `other`), and `--headers` the **first
line of the file only**, its column headers.

**Never put in a field** a money amount, a quantity of shares, an account or
card number, a name, an email, or any row of the user's holdings. Tickers,
ISINs, fund names and percentages are fine. The script also removes amounts,
long numbers and emails, but write the fields without them in the first
place.

## 3. Make the link

```
python3 <skill>/scripts/report_problem.py --kind bug --title "<5-8 words>" \
  --what "..." --expected "..." --asked "..." --error "..." --install plugin
```

It prints the link, then every field as it went in. Give the user:

1. the link, as a link;
2. one line: `It opens a GitHub issue with everything filled in. Check it, then press Submit. You'll need a free GitHub account.`

Show the fields only if they ask what's in it. Without a shell, write the
same fields as a short message they can paste at
https://github.com/Artvarna/holdnote/issues/new/choose, with the
never-put-in rule above.
