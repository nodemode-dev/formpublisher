# Templates

Templates starts a new site from a whole FormWeb site. FormPublisher has no editor: you start here, edit in FormWeb, and send the site back to check, package and publish it.

## The sheet

Open it from Home, or from File, Start from a Template. Nothing is fetched until you press Get the templates. The list is then kept in `templates/index.json` in the data folder with the time it was read, and Check again reads it anew.

Each card shows the preview, the site type, the name, the description, the size, the licence and the credit. The list holds eight starters today. Parts for FormWeb's own library are not whole sites, so they are counted in the status line and not offered.

## Where the list comes from

The list is `index.json` in the public formai-templates repository on GitHub, read at one fixed release. `TEMPLATES_REF` in `backend/app/services/templates.py` names it (`v0.2.0` in this version), so a version of FormPublisher always reads the same list. `FORMPUBLISHER_TEMPLATES_URL` points the engine at another copy.

The engine keeps only the FormWeb items of an index with format `formai-templates`, format version 1. Every path in it must be a relative path under `apps/formweb/`, with no `..`. The index may be 4 MB at most, a template 128 MB and a preview 2 MB. Redirects are not followed.

## Hash checks

- **Files.** The index gives each template's size and SHA-256. A download is kept only when both match, in `templates/files/` under its hash. A copy already there is hashed again before it is used.
- **Previews.** A preview is shown only when the index gives its SHA-256 and the bytes match. It is a `.webp`, `.png` or `.jpg`, kept in `templates/previews/` under its hash.

When something does not match, nothing is kept and the sheet says so.

## Site types and the filter

A template can carry one of five site types: business, portfolio, blog, event and shop. The card shows it as a badge (Business and services, Portfolio, Blog, Event, Shop window). A row of chips above the list filters by type. It starts at All and has a chip only for the types the list really holds.

## Start a site

1. Press Start a site from this on a card and choose a folder. The folder must exist.
2. The engine downloads that one file, checks its size and SHA-256, and opens it with the vendored FormWeb core to prove it is a real project.
3. It writes the project into your folder as `NAME.fweb`, named from the template. It never replaces a file: when that name is taken, choose another folder.

The sheet then shows the path and two buttons:

- **Edit in FormWeb** opens the FormWeb address from Preferences (`http://127.0.0.1:8240` unless you changed it). In FormWeb, choose File, Import .fweb or .fpub file, and pick the project.
- **Publish it** imports the project into FormPublisher as it is.

## Send it back

When the site is edited, bring it back one of the ways in [Importing Sites](Importing-Sites): FormWeb's Send to FormPublisher, the site open in a running FormWeb, a `site-export.zip`, or the `.fweb` file itself. Then go on with [Checks](Checks), [Packages and Signatures](Packages-and-Signatures) and [Publishing](Publishing).

## The same steps for agents

`./formpublisher run templates` prints the kept list and `templates --fetch` reads it now. `start TEMPLATE --to FOLDER [--name N]` makes the project. The MCP tools are `list_templates`, which fetches nothing, and `start_from_template`, which writes to the folder the person named. See [Agents](Agents).
