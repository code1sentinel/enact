# Outputs

After a run, Enact writes the same three user-facing files in the browser and on the CLI (the CLI also writes a Markdown summary).

## assessment-results.json

The official results file. It is NIST **OSCAL 1.1.2** `assessment-results`.

Use it when another GRC tool, an assessor, or a pipeline needs a standard document. Observations carry the check id, the control id, pass/fail/need-evidence/draft, and — for evidence envelopes — provenance props (evidence id, payload type, collected-at). They do not embed the raw payload body.

The in-app **Preview assessment-results.json** is this file: a readable summary first, then raw JSON. See [Run and results](run-and-results.md).

Validate on the CLI:

```bash
enact validate --assessment-results out/assessment-results.json
```

## poam.json

Plan of Action and Milestones — the list of **automated failures** that still need a fix.

- Failed automated (and failed hybrid) checks become POA&M items.
- **Need evidence** does not open a POA&M item.
- **Draft** never opens a POA&M item.

On the passing example, `poam.json` has no items. On the failing sample, you get one item per automated/hybrid failure (three in the bundled failing run).

```bash
enact validate --poam out/poam.json
```

## HTML report

A single offline file (`summary.html` on the CLI; **Download HTML report** in the browser).

It uses the same count cards and status labels as the app: Passed, Failed, Need evidence, Draft. You can filter and expand findings. It does not call the network. Appearance follows Light / Dark / System the same way the app does.

Open it from disk or serve a CLI output folder locally:

```bash
enact serve out
```

That binds `127.0.0.1` only.

## Markdown summary

`enact run` also writes `summary.md` with the same counts and pending heading (**Need evidence**). The hosted app does not download Markdown; use the CLI if you want that file.

## What the CLI writes together

```bash
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/checks.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass
```

Default `--format` is `oscal,poam,markdown,html`. A later FedRAMP Security Decision Record writer is reserved (`fedramp-sdr`) and is not shipped.
