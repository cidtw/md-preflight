# Design Debt — MD Preflight (SGAEM Live Deployment Session)

| Slide | Finding | Severity | Why deferred | Fix |
|-------|---------|----------|---------------|-----|
| slide-02, slide-07 | Wordmark size is 11pt on TOC/closing vs 10pt on content pages 03-06; style token `wordmark_samsung_top_right` recommends 13-14pt | Minor | Cosmetic, does not affect legibility or hierarchy; consistent within each page family | Snap all wordmark instances to one shared size (e.g. 11pt) in a future pass |
| slide-01, slide-02 | Label text (`.eyebrow`, `.num`, `.title`, `.eng-sub`) sits in raw `<span>` rather than a wrapped `<p>`/semantic tag | Minor | Mechanical only, no visible side effect in current render | Wrap label text nodes in `<p>` and position the wrapper via flex/grid if touched again |
| slide-05 | `.kpi-item` uses a 1px `#D8DBE2` hairline divider between KPI columns; approved style's `kpi_huge_combo` archetype specifies bare text with no card/border | Minor | Divider uses an approved palette token, reads as a light structural aid rather than a card/box; does not violate color discipline | Remove the border-right divider and rely on whitespace only, if strict archetype match is desired |
| slide-06 | `.col-title` left-accent bar uses `#0028A8` (accent samsung blue) rather than the style's dedicated `#0D2062` "accent navy hairline commentary" token used for comparable tab labels elsewhere in the reference style | Minor | Both colors are approved palette tokens; no palette violation, just a token-role mismatch | Swap to `#0D2062` for exact archetype alignment in a future pass |
