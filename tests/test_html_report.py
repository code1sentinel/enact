from __future__ import annotations

from enact.writers import HtmlWriter, OscalPoamWriter


def test_passing_report_has_count_cards_and_filters(
    example_dir, catalog_path, manifest_path, passing_input, fixed_clock
) -> None:
    from enact.runner import run_assessment

    run, bundle = run_assessment(
        [catalog_path],
        manifest_path=manifest_path,
        input_path=passing_input,
        workdir=example_dir,
        title="Access-control example",
        clock=fixed_clock,
    )
    html = HtmlWriter().render(run, bundle)
    assert "<h1>Access-control example</h1>" in html
    assert ">2</p>" in html  # passed count
    assert "Manual / Not checked" in html
    assert 'aria-valuenow="100"' in html
    assert 'id="q"' in html
    assert 'data-filter="fail"' in html
    assert "getElementById" in html
    assert "https://" not in html
    assert "http://" not in html
    assert "fonts.googleapis" not in html
    assert html.count('class="expand"') == 0
    assert "POA&amp;M" in html


def test_failing_rows_expand_with_poam_reference(
    example_dir, catalog_path, manifest_path, failing_input, fixed_clock
) -> None:
    from enact.runner import run_assessment

    run, bundle = run_assessment(
        [catalog_path],
        manifest_path=manifest_path,
        input_path=failing_input,
        workdir=example_dir,
        title="Access-control example",
        clock=fixed_clock,
    )
    html = HtmlWriter().render(run, bundle)
    poam = OscalPoamWriter().render(run, bundle)
    item = poam["plan-of-action-and-milestones"]["poam-items"][0]
    assert item["uuid"] in html
    assert "Remediate" in html
    assert "Parameters" in html
    assert "Finding" in html
    assert html.count('class="expand"') == 3
    assert 'data-status="fail"' in html
    assert "c-ac-2" in html
    assert "automated" in html
    assert "hybrid" in html
    assert "manual" in html


def test_landing_page_keeps_relative_demo_links_and_codify() -> None:
    from pathlib import Path

    html = Path(__file__).resolve().parents[1].joinpath("site", "index.html").read_text(encoding="utf-8")
    for href in (
        "examples/pass/summary.html",
        "examples/pass/assessment-results.json",
        "examples/pass/poam.json",
        "examples/fail/summary.html",
        "examples/fail/assessment-results.json",
        "examples/fail/poam.json",
        "styles.css",
        "https://code1sentinel.github.io/policy-golden-path/",
    ):
        assert f'href="{href}"' in html
    assert 'href="/enact/' not in html
    assert "enact run" in html
