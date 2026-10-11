# Using Enact with Codify

[Codify](https://code1sentinel.github.io/policy-golden-path/) writes the catalog. Enact runs the checks.

Codify’s hosted app: [https://code1sentinel.github.io/policy-golden-path/](https://code1sentinel.github.io/policy-golden-path/)

## Who does what

| | Codify | Enact |
| --- | --- | --- |
| Who | Policy authors | GRC reviewers (browser) and engineers (CI) |
| In | Legacy policy text | OSCAL catalog / profile / component-definition |
| Out | OSCAL 1.1.2 catalog | OSCAL 1.1.2 assessment results, POA&M, Markdown, HTML |
| Parameters | `[90]` in a statement becomes `params` with `values` | The check reads those same `values` |

A catalog that Codify exported works as-is once you add `checks.json`, a Component Definition, or Enact props (`rule-id`, `check-type`, `engine`, `policy-path`) on the controls.

## Typical path

1. Author or import policy in Codify. Export OSCAL 1.1.2 catalog JSON.
2. Open [Enact](https://code1sentinel.github.io/enact/). On Catalog, open that JSON (or start from the access-control example to learn the steps).
3. On Checks, keep the library mappings or open your `checks.json` / Component Definition.
4. On Evidence, open a local settings file (or an adapter output).
5. Run and download assessment results.

For custom Rego or drafts, use the [CLI](cli.md) with the same catalog file.

## Catalog contract Enact reads

- OSCAL 1.1.2 JSON
- One control per statement, `parts[name=statement]`
- Placeholders as `params` (`c-ac-7_prm_1`) and `{{ insert: param, <id> }}` in prose
- Namespaced props under `https://grcengineering.club/ns/codify`

Enact adds its own props under `https://grcengineering.club/ns/enact`.

The bundled access-control example is in this Codify shape — four statements, thresholds in params, `rule-id` already on the controls.
