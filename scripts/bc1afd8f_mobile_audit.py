"""Session arena-bc1afd8f — static phone-first audit of the *built* pages.

The brief asks for a site a reader can use on a phone: an executive summary that
links to the updated picks, both teams' probabilities on every row, an obvious
pick, a separate unresolved section, and no horizontal scrolling at 320 px.

Runtime checks (real Chromium at 320/390/768/1440 px, axe-core, no-JS) already
live in ``checks.yml`` and ``tests/browser/``. This module is the **static**
half: it reads the rendered HTML and CSS and asserts the contract those runtime
checks depend on, so a regression is caught even when a browser is unavailable
and even on a snapshot another session collected. It never edits a page, never
recalculates a probability and never invents a value: every check reports what it
actually found.

Usage
-----
    python -m scripts.bc1afd8f_mobile_audit                     # audit site/ against data/
    python -m scripts.bc1afd8f_mobile_audit --site site --data data --out data/research/bc1afd8f
    python -m scripts.bc1afd8f_mobile_audit --root .            # audit the published branch root

Exit status is 1 when a *current view* check fails, 0 otherwise. Findings about
explicitly archived views (``archive/``, ``docs/``) never fail the audit; they are
reported, because those pages are preserved snapshots of earlier sessions.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from bs4 import BeautifulSoup

UTC = timezone.utc
SCHEMA_VERSION = 1
SESSION = "arena-bc1afd8f"

#: Directories in a build that are explicitly archived session views, not current pages.
ARCHIVED_DIRS = ("archive", "docs")

#: The pages a phone reader is expected to reach from the executive summary.
REQUIRED_EXEC_TARGETS = (
    ("complete picks list", ("origination/#picks",)),
    ("featured picks feed", ("picks/", "picks/index.html")),
    ("unresolved & limitations", ("unresolved/", "#unresolved-register", "origination/#unresolved", "#unresolved")),
)

VIEWPORT = "width=device-width, initial-scale=1"
MIN_TAP_PX = 44
PHONE_WIDTH_PX = 320


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


# --------------------------------------------------------------------------- CSS


def parse_css(text: str) -> list[dict]:
    """A minimal, honest CSS reader: selector, declarations and media context.

    Only what the audit needs — no cascade resolution is attempted, and the report
    says so wherever the effective value could depend on the cascade.
    """
    rules: list[dict] = []
    media_stack: list[str] = []
    depth = 0
    buffer = ""
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "{":
            prelude = buffer.strip()
            buffer = ""
            if prelude.startswith("@media"):
                media_stack.append(re.sub(r"\s+", " ", prelude))
                depth += 1
                index += 1
                continue
            if prelude.startswith("@"):
                # @keyframes / @supports and friends: skip the whole block.
                depth += 1
                index += 1
                continue
            body_start = index + 1
            body_end = text.find("}", body_start)
            if body_end == -1:
                break
            declarations = text[body_start:body_end]
            rules.append(
                {
                    "selector": re.sub(r"\s+", " ", prelude),
                    "declarations": re.sub(r"\s+", " ", declarations).strip(),
                    "media": list(media_stack),
                }
            )
            index = body_end + 1
            continue
        if char == "}":
            buffer = ""
            if media_stack and depth > 0:
                media_stack.pop()
                depth -= 1
            index += 1
            continue
        buffer += char
        index += 1
    return rules


def declarations_for(rules: Sequence[dict], selector_fragment: str) -> list[dict]:
    return [rule for rule in rules if selector_fragment in rule["selector"]]


def min_height_px(rules: Sequence[dict], selector_fragment: str) -> tuple[float | None, list[str]]:
    """The largest declared ``min-height`` for a selector, and where it came from."""
    best: float | None = None
    sources: list[str] = []
    for rule in declarations_for(rules, selector_fragment):
        for match in re.finditer(r"min-height\s*:\s*([0-9.]+)px", rule["declarations"]):
            value = float(match.group(1))
            sources.append(f"{rule['selector']} {{min-height:{value:g}px}} " + (f"in {rule['media'][-1]}" if rule["media"] else ""))
            if best is None or value > best:
                best = value
    return best, sources


def overflow_auto_selectors(rules: Sequence[dict]) -> set[str]:
    """Every selector that declares ``overflow-x:auto`` — the phone scroll wrappers."""
    out: set[str] = set()
    for rule in rules:
        if re.search(r"overflow-x\s*:\s*auto", rule["declarations"]):
            for selector in rule["selector"].split(","):
                name = selector.strip()
                if name.startswith("."):
                    out.add(name[1:].split(":")[0].split("[")[0].strip())
    return out


def wide_fixed_widths(rules: Sequence[dict], *, include_tables: bool = False) -> list[dict]:
    """``width``/``min-width`` declarations in px that cannot fit a 320 px phone.

    A ``table`` selector is excluded from the failing set by default: this
    stylesheet deliberately gives tables a ``min-width`` *inside* a wrapper that
    declares ``overflow-x:auto``, so the table scrolls in its own box instead of
    stretching the page. Those are reported separately as informational, and the
    wrapper itself is asserted by ``table-scroll-wrappers``.
    """
    found = []
    for rule in rules:
        if "table" in rule["selector"] and not include_tables:
            continue
        for match in re.finditer(r"(?<![-\w])(width|min-width)\s*:\s*([0-9.]+)px", rule["declarations"]):
            value = float(match.group(2))
            if value > PHONE_WIDTH_PX:
                found.append(
                    {
                        "selector": rule["selector"],
                        "property": match.group(1),
                        "px": value,
                        "media": rule["media"],
                    }
                )
    return found


def font_sizes(rules: Sequence[dict], selector_fragment: str) -> list[str]:
    out = []
    for rule in declarations_for(rules, selector_fragment):
        for match in re.finditer(r"font-size\s*:\s*([0-9.]+)px", rule["declarations"]):
            out.append(f"{rule['selector']} {{font-size:{match.group(1)}px}}" + (f" in {rule['media'][-1]}" if rule["media"] else ""))
    return out


# -------------------------------------------------------------------------- HTML


def current_pages(site: Path) -> list[Path]:
    pages = []
    index = site / "index.html"
    if index.is_file():
        pages.append(index)
    for child in sorted(site.iterdir()):
        if not child.is_dir() or child.name in ARCHIVED_DIRS or child.name.startswith(("_", ".")):
            continue
        if child.name in {"assets", "data"}:
            continue
        page = child / "index.html"
        if page.is_file():
            pages.append(page)
    return pages


def archived_pages(site: Path) -> list[Path]:
    out = []
    for name in ARCHIVED_DIRS:
        directory = site / name
        if directory.is_dir():
            out.extend(sorted(p for p in directory.rglob("*.html") if p.is_file()))
    return out


def active_fixture_ids(data_dir: Path) -> list[str]:
    try:
        payload = json.loads((data_dir / "latest.json").read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return [
        str(match.get("id"))
        for match in payload.get("matches") or []
        if match.get("availability") in {"open", "locked", "unknown_lock"}
    ]


# ------------------------------------------------------------------------ checks


def check(name: str, description: str, passed: bool, detail: str, *, scope: str = "current") -> dict:
    return {"id": name, "description": description, "passed": bool(passed), "detail": detail, "scope": scope}


def audit_site(site: Path, data_dir: Path) -> list[dict]:
    checks: list[dict] = []
    pages = current_pages(site)
    if not pages:
        return [check("site-present", "The build output contains a landing page", False, f"no index.html under {site}")]
    soups = {path: BeautifulSoup(path.read_text(), "html.parser") for path in pages}
    index = site / "index.html"
    index_soup = soups[index]

    # 1. viewport on every current page
    missing = [str(path.relative_to(site)) for path, soup in soups.items()
               if not any(meta.get("name") == "viewport" and VIEWPORT.replace(" ", "") in (meta.get("content") or "").replace(" ", "")
                          for meta in soup.find_all("meta"))]
    checks.append(check(
        "viewport-meta",
        f"Every current page declares `{VIEWPORT}`",
        not missing,
        "all " + str(len(pages)) + " current pages declare it" if not missing else "missing on: " + ", ".join(missing),
    ))

    # 2. executive summary exists and says so
    h1 = index_soup.find("h1")
    h1_text = (h1.get_text(" ") if h1 else "").strip()
    checks.append(check(
        "executive-summary",
        "The landing page opens with an executive summary",
        bool(h1) and "executive summary" in h1_text.lower(),
        f"h1 = {h1_text!r}",
    ))

    # 3. the summary links, inside this site, to where the picks are
    banner = index_soup.select_one(".exec-banner")
    checks.append(check(
        "exec-banner",
        "The landing page carries the `Start here on your phone` executive-summary banner",
        banner is not None,
        "found section.exec-banner" if banner is not None
        else "no section.exec-banner: this build predates the phone-first executive summary",
    ))
    # Only the banner's own links are audited: a link that lives somewhere else on
    # the page does not make the executive summary a route to the picks.
    internal = {a.get("href") or "" for a in banner.find_all("a", href=True)} if banner is not None else set()
    for label, targets in REQUIRED_EXEC_TARGETS:
        hits = sorted({href for href in internal if any(href.endswith(target) or target in href for target in targets)})
        checks.append(check(
            f"exec-link-{label.split()[0]}",
            f"The executive summary links inside this site to the {label}",
            bool(hits),
            "links: " + ", ".join(hits) if hits else f"no link to any of {', '.join(targets)}",
        ))
    external = sorted(href for href in internal if href.startswith("http"))
    checks.append(check(
        "exec-links-internal",
        "The banner's own links stay inside this site (no reader is sent off-site to find a pick)",
        banner is not None and not external,
        ("no banner to audit" if banner is None else "external links in the banner: " + (", ".join(external) or "none")),
    ))

    # 4/5. the glance index covers every active fixture and shows both probabilities
    rows = index_soup.select(".glance-row")
    row_ids = [row.get("data-glance-id") for row in rows]
    wanted = active_fixture_ids(data_dir)
    absent = [identifier for identifier in wanted if identifier not in row_ids]
    checks.append(check(
        "glance-coverage",
        "Every active fixture in the snapshot appears in the phone pick index",
        bool(wanted) and not absent,
        f"{len(rows)} rows for {len(wanted)} active fixtures" + ("" if not absent else "; missing: " + ", ".join(absent)),
    ))
    incomplete: list[str] = []
    unresolved_rows: list[str] = []
    for row in rows:
        identifier = row.get("data-glance-id")
        probability = row.select_one(".glance-prob")
        other = row.select_one(".glance-other")
        label = row.select_one(".glance-pick-label")
        label_text = (label.get_text(" ") if label else "").strip().lower()
        if probability and other and re.search(r"\d", probability.get_text()) and re.search(r"\d", other.get_text()):
            continue
        if "unresolved" in label_text or "no side" in (probability.get_text() if probability else "").lower():
            # An explicit blank is allowed only when the row explains itself.
            if row.select_one('a[href*="unresolved"]'):
                unresolved_rows.append(identifier)
                continue
        incomplete.append(identifier)
    checks.append(check(
        "glance-both-probabilities",
        "Every pick row shows both teams' win probability, or is an explicit blank that links to its limitation",
        not incomplete,
        f"{len(rows) - len(incomplete) - len(unresolved_rows)} rows show both percentages; "
        f"{len(unresolved_rows)} explicit blanks link to their limitation"
        + ("" if not incomplete else "; incomplete: " + ", ".join(incomplete)),
    ))

    # 6. phone navigation reaches the picks in one tap
    nav = index_soup.select_one(".mobile-nav")
    nav_links = nav.select("a") if nav else []
    labels = [(a.get_text(" ") or "").strip() for a in nav_links]
    checks.append(check(
        "mobile-nav",
        "A fixed phone navigation bar with at least five labelled, internal destinations",
        len(nav_links) >= 5 and all(labels) and all(not (a.get("href") or "").startswith("http") for a in nav_links),
        f"{len(nav_links)} slots: " + ", ".join(label for label in labels if label),
    ))
    picks_link = next((a.get("href") for a in nav_links if "picks" in (a.get_text(" ") or "").lower()), None)
    checks.append(check(
        "mobile-nav-picks",
        "One phone-nav slot goes straight to the picks",
        bool(picks_link),
        f"href = {picks_link}" if picks_link else "no nav slot labelled for picks",
    ))

    # 7. the unresolved register is its own section on the landing page
    register = index_soup.find(id="unresolved-register") or index_soup.find(id="unresolved")
    checks.append(check(
        "unresolved-section",
        "The landing page carries a separate unresolved-picks section with its limitations",
        register is not None,
        f"found #{register.get('id')}" if register is not None else "no #unresolved-register or #unresolved section",
    ))

    # 8. CSS tap targets
    css_paths = sorted((site / "assets").glob("*.css")) if (site / "assets").is_dir() else []
    rules: list[dict] = []
    for path in css_paths:
        rules.extend(parse_css(path.read_text()))
    for fragment, label in ((".mobile-nav>a", "phone navigation slots"), (".exec-banner-actions a", "executive-summary action buttons")):
        height, sources = min_height_px(rules, fragment)
        checks.append(check(
            f"tap-target-{re.sub(r'[^a-z0-9]+', '-', fragment.strip('.').lower()).strip('-')}",
            f"{label} declare a ≥{MIN_TAP_PX}px tap target",
            height is not None and height >= MIN_TAP_PX,
            (f"largest declared min-height {height:g}px — " + "; ".join(sources[-2:])) if height else "no min-height declared",
        ))

    # 9. every table sits in a wrapper that can scroll instead of stretching the page
    wrappers = overflow_auto_selectors(rules)
    unwrapped: list[str] = []
    for path, soup in soups.items():
        for table in soup.find_all("table"):
            node = table.parent
            safe = False
            while node is not None and getattr(node, "name", None):
                classes = node.get("class") or []
                if any(cls in wrappers for cls in classes):
                    safe = True
                    break
                node = node.parent
            if not safe:
                classes = ",".join(table.get("class") or []) or "table"
                unwrapped.append(f"{path.relative_to(site)}:{classes}")
    checks.append(check(
        "table-scroll-wrappers",
        "Every table in a current view sits inside a wrapper that scrolls horizontally (no page-wide overflow at 320 px)",
        not unwrapped,
        f"scroll wrappers in CSS: {', '.join('.' + name for name in sorted(wrappers)) or 'none'}; unwrapped tables: "
        + (", ".join(unwrapped) if unwrapped else "none"),
    ))

    # 10. no fixed width that cannot fit a 320 px phone
    wide = wide_fixed_widths(rules)
    checks.append(check(
        "no-wide-fixed-widths",
        f"No non-table layout rule declares a fixed width wider than {PHONE_WIDTH_PX}px",
        not wide,
        "; ".join(f"{item['selector']} {item['property']}:{item['px']:g}px" for item in wide) or "none found",
    ))
    table_widths = wide_fixed_widths(rules, include_tables=True)
    checks.append(check(
        "table-min-widths",
        "Tables wider than a phone scroll inside their own wrapper rather than stretching the page (informational)",
        not unwrapped,
        ("table min-widths: " + "; ".join(f"{item['selector']} {item['property']}:{item['px']:g}px" for item in table_widths)
         if table_widths else "no table declares a fixed min-width")
        + (" — every one of them is inside a wrapper that declares overflow-x:auto" if table_widths and not unwrapped else "")
        + ("" if not unwrapped else "; UNWRAPPED: " + ", ".join(unwrapped)),
    ))

    # 11. phone media queries exist (the layout actually adapts)
    phone_queries = sorted({rule["media"][-1] for rule in rules if rule["media"] and re.search(r"max-width\s*:\s*(\d+)px", rule["media"][-1] or "")})
    checks.append(check(
        "phone-breakpoints",
        "The stylesheet carries max-width phone breakpoints",
        bool(phone_queries),
        f"{len(phone_queries)} distinct phone media queries: " + ", ".join(phone_queries[:6]),
    ))

    # 12. informational: declared sizes of the probability text on a phone
    probabilities = font_sizes(rules, ".glance-prob") + font_sizes(rules, ".glance-other")
    checks.append(check(
        "probability-type-size",
        "The probability text declares a readable phone size (informational — the cascade decides the effective size)",
        bool(probabilities),
        "; ".join(probabilities[-4:]) or "no explicit font-size for .glance-prob/.glance-other",
    ))

    # 13. archived views are reported, never silently assumed current
    archived = archived_pages(site)
    archived_missing_viewport = [
        str(path.relative_to(site))
        for path in archived
        if not any(meta.get("name") == "viewport" for meta in BeautifulSoup(path.read_text(), "html.parser").find_all("meta"))
    ]
    checks.append(check(
        "archived-views",
        "Archived session views are reported separately from the current pages",
        True,
        f"{len(archived)} archived page(s); without a viewport meta: "
        + (", ".join(archived_missing_viewport) if archived_missing_viewport else "none"),
        scope="archived",
    ))
    return checks


def render_markdown(report: dict) -> str:
    lines = [
        f"# {SESSION} — phone-first static audit",
        "",
        f"Observed **{report['observed_at']}** against `{report['site']}` (data `{report['data']}`).",
        "Static HTML/CSS contract only; the runtime 320/390/768/1440 px browser checks live in",
        "`checks.yml` and `tests/browser/`. No page was edited and no value recalculated.",
        "",
        f"Result: **{report['counts']['passed']}/{report['counts']['total']} checks passed**"
        + (f" — {report['counts']['failed']} failed" if report["counts"]["failed"] else ""),
        "",
        "| Check | Result | What was found |",
        "| --- | --- | --- |",
    ]
    for item in report["checks"]:
        state = "PASS" if item["passed"] else ("FAIL" if item["scope"] == "current" else "NOTE")
        lines.append(f"| `{item['id']}` — {item['description']} | {state} | {item['detail']} |")
    return "\n".join(lines) + "\n"


def build_report(site: Path, data_dir: Path, *, observed_at: datetime | None = None) -> dict:
    checks = audit_site(site, data_dir)
    current = [item for item in checks if item["scope"] == "current"]
    return {
        "schema_version": SCHEMA_VERSION,
        "session": SESSION,
        "observed_at": iso(observed_at or utc_now()),
        "site": str(site),
        "data": str(data_dir),
        "counts": {
            "total": len(checks),
            "passed": sum(1 for item in checks if item["passed"]),
            "failed": sum(1 for item in current if not item["passed"]),
            "current": len(current),
        },
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--root", type=Path, default=None, help="audit a published root instead of site/")
    parser.add_argument("--out", type=Path, default=Path("data/research/bc1afd8f"))
    parser.add_argument("--label", default="site", help="output file suffix, e.g. 'root' for the published branch root")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args(argv)

    site = (args.root or args.site).resolve()
    data_dir = (args.root / "data").resolve() if args.root else args.data.resolve()
    report = build_report(site, data_dir)

    report["label"] = args.label
    args.out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", args.label.lower()).strip("-") or "site"
    (args.out / f"mobile-audit-{slug}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    markdown = render_markdown(report)
    (args.out / f"mobile-audit-{slug}.md").write_text(markdown)
    if not args.json_only:
        print(markdown)
    counts = report["counts"]
    print(f"{SESSION}: {counts['passed']}/{counts['total']} phone-first checks passed, {counts['failed']} failed")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
