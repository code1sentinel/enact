# Catalog

A catalog is the list of controls you want to assess. Enact reads NIST OSCAL 1.1.2 catalog JSON.

![Catalog step on the Enact landing page](assets/landing.png)

## What to do

On [the app](https://code1sentinel.github.io/enact/):

- Click **Use the access-control example** to load the bundled catalog, or
- Click **Open catalog JSON** and pick an OSCAL catalog from this computer.

Nothing is sent anywhere. There is no upload.

The bundled example is titled *Acme access-control statements*. It has four controls:

| Control | What it asks |
| --- | --- |
| `c-ac-2` | Review user accounts at least every 90 days |
| `c-ac-7` | Lock an account after 5 failed attempts |
| `c-ac-8` | Obtain signed access agreements |
| `c-ac-2p` | Review privileged accounts every 30 days |

Thresholds live in OSCAL parameters on the catalog (for example `c-ac-7_prm_1` = 5). Checks read those values. You change the limit in the catalog, not in the check code.

## After the example loads

A summary card lists how many controls and checks were filled in, which sample evidence was used, and offers **Run the assessment**.

![Example loaded summary on the Catalog step](assets/example-summary.png)

The progress rail at the top shows what is already in the tab (catalog, selected checks, evidence). Appearance defaults to your operating system; Light / Dark / System stays in the browser only.

## Your own catalog

If you already have an OSCAL 1.1.2 catalog — including one [Codify](codify.md) exported — open that JSON on this step. Enact also accepts a profile or a Component Definition as extra mapping; on the hosted app, Component Definitions are opened on [Checks](checks.md).

You do not need to write catalog JSON by hand. Codify can turn policy text into a catalog. See [Using Enact with Codify](codify.md).
