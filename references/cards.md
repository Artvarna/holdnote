# Cards and share images

Reference for Holdnote (`holdnote`). Follow `RULES.md`. Read on "make a card", "make my portfolio card", "something I can post", "share my portfolio".

## Portfolio card

Three images of what a portfolio looks through to, made to be posted. Two are
**share images** that lead with one sentence about the poster, in big type:

- `story.png` (1080 x 1920, Instagram and TikTok stories): "I bought 4
  things." and "I own 5,965 companies", then the company reached through most
  holdings and how. At factsheet top-10 depth, where no company count exists,
  the five biggest companies replace the count.
- `wide.png` (1200 x 675, the shape X shows in full in a timeline): the same
  sentence and figure side by side.
- `card.png` (1080 x 1350): the detailed card, set like a fund factsheet:
  composition, three key figures, the top 10 companies with each fund's part,
  countries and sectors.

1. **Get a checked Mode C draft** with the tables Allocation, Holdings,
   Look-through, Hidden bets, Countries and Sectors — the user's portfolio
   (`references/portfolio-view.md`, Mode C), or the demo with
   `--tables "Allocation,Holdings,Look-through,Hidden bets,Countries,Sectors"`
   (`references/demo.md`). A draft from earlier in the conversation is used
   when it has them; never rebuild one from the rendered report.
2. Run `python3 <skill>/scripts/card.py <draft> --out <scratch>/card`. It
   checks the draft against the contract first and writes each image as SVG,
   plus PNG when Pillow is installed.
3. **Give the user the PNGs as files** (the SVGs when no PNG was made),
   `story.png` and `wide.png` first, then `card.png`, the way this
   environment hands files to the user: its file-sending tool when it has
   one, else its outputs folder (`/mnt/user-data/outputs/` where that
   exists). Never a bare path or a description of the image instead. Add one
   line: which is for where, and that they carry percentages only.

**Percentages only.** The images draw cells of the draft's tables — shares of
the portfolio's market value — and never a quantity, close, value or amount,
so the user can post it without showing what they have. It says nothing the
tables do not: no rating, no verdict. A demo card is labelled `DEMO ·
SYNTHETIC PORTFOLIO`. Without GitHub the card is made from a look-through
at factsheet top-10 depth (`references/any-broker.md` → Look-through without
GitHub) and says `PARTIAL · TOP-10 DEPTH`. Exit 1 means the draft cannot
make a card (most often Look-through is `Not available`): say why in one
line and offer what would fix it — attach an export, or run the demo card.

