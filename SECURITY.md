# Security policy

## Reporting a vulnerability

Please report security problems privately, not in a public issue:

1. Go to the repository's **Security** tab.
2. Select **Report a vulnerability**.
3. Describe the problem and how to reproduce it.

You'll get a reply within 7 days. Fixes are released as a new version on
the default branch, and the release notes say what was fixed.

## Scope

Holdnote is a Claude skill: Markdown instructions plus Python scripts that
run in your own Claude session. Relevant reports include a script that
reads or writes outside the user's chosen `me/` folder, a request that
sends user data to a third party, or instructions that could make Claude
act without the user's request.
