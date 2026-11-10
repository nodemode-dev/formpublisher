# Publishing

Publish prepares a package for a host. It writes a folder and shows the exact commands to run. FormPublisher never uploads anything: running the commands is up to you.

## The sheet

Open it from the toolbar's Publish button, from the Package sheet's Publish button or from the command palette (`publish.open`). Pick a build (the latest is selected; Build now makes one when there is none), tick the hosts and press Prepare. Each prepared host gets a panel with its folder (Reveal, Copy path), its commands (each with a copy button), notes and warnings, Verify and Remove. The sheet remembers what is prepared for a build when you close and reopen it.

## The six hosts

Every folder is written from the build's own `site.zip`, never from the live site folder, and the same build always gives the same bytes.

| Host | Writes | Commands |
| --- | --- | --- |
| Static zip | `site.zip`, `publish.json`, `SHA256SUMS`, `README.txt` | `unzip`, `python3 -m http.server` |
| Netlify | `site/` with `_redirects` (and a `/* /404.html 404` rule when the site has a 404 page) and `_headers` | `npx netlify-cli deploy --dir site`, with `--prod`, and `dev` |
| Cloudflare Pages | `site/` with `_redirects` and `_headers`; no 404 rule, Pages serves `404.html` itself | `npx wrangler pages deploy site`, and `pages dev` |
| Vercel | `site/` with `vercel.json` | `npx vercel deploy site`, with `--prod`, and `dev` |
| GitHub Pages | `site/` with `.nojekyll`, `404.html`, meta-refresh pages for redirects, and a workflow in `.github/workflows/pages.yml` | `git` for a `gh-pages` branch, or the workflow |
| nginx | `site/` with `formpublisher.conf` and `nginx-test.conf` | `nginx -t -c ...`, and `docker run` with `nginx:stable` |

A FormWeb 404 page exported as `404/index.html` counts as the site's 404 and is also written as `404.html`. A host that cannot represent something says so under Warnings: GitHub Pages has no server redirects and ignores custom headers, so each one is named, never dropped silently.

FormWeb 0.19.7 exports splat redirects (`/blog/*` to `/docs/:splat`) and a root `404.html`. Netlify and Cloudflare Pages write the splat into `_redirects`, Vercel as `:path*` in `vercel.json`, and nginx as a regex `location`. GitHub Pages has no server redirects, so a small script at the top of `404.html` follows splats under the site's base path (the status is the 404 page's); exact ones become refresh pages. For older exports with only `404/index.html`, every target writes it as `404.html` with its URLs made root-absolute and says so in its notes. Static zip stays byte for byte.

Where `nginx` is installed, preparing and verifying the nginx target run `nginx -t` on the prepared config; verify answers `nginx` with `ran`, `ok`, `version` and `output`, and a failure is a problem row. Prepare the nginx folder again after updating from 0.1.7.

## FormWeb's model files

A FormWeb site carries `site.formweb.json` and `asset-access.json`. Hosts do not need them, so the `site/` folder of each host is written without them. Tick Keep FormWeb's model files in the sheet (`--include-model` on the command line, `includeModel: true` in the MCP tool) to keep them for that prepare. Prepared panels show "Left out: ...", results list `leftOut`, and Verify knows what was left out. `site.zip` is unchanged and still holds both files, so the option affects the five host folders that have a `site/` folder, not the Static zip.

## Verify and remove

Verify re-reads the folder and checks each file against the hashes in `publish.json`, and the host's own files against a fresh prepare. Remove moves the folder to `trash/`, where Home's Trash page can restore it. Preparing again replaces the folder. Folders live at `prepared/[site]/[build]/[host]/` in the data folder.

## Receive from FormWeb

FormWeb's Send to FormPublisher posts a `site-export.zip` to `POST /api/receive/formweb` on this computer (headers `X-FormWeb-Version`, and optionally `X-FormWeb-Site-Name` and `X-FormWeb-Project`). Other addresses are refused. When FormPublisher is closed, FormWeb writes the file into `inbox/` in the data folder; every `*.zip` or `*.fweb` there is imported when the engine starts and every 5 seconds after, and moved to `inbox/imported/` or, with a reason, to `inbox/failed/`. FormWeb also writes a `NAME.zip.json` beside the zip with `siteName`, `project` and `version`, so an inbox arrival has a name and a later arrival of the same project adds a revision (the file moves with the zip). The window shows a toast with Open and adds the site to Recent. Two switches in Preferences, both off by default, run the static checks and then a build on every site that arrives (`receive.autoCheck`, `receive.autoBuild`). A site that arrived again lists its revisions and what changed on Home's site card and in its panel (`./formpublisher run revisions`, `diff`). `./formpublisher run receive-status` reports the endpoint, the inbox and the last receipts.

## The same steps for agents

`./formpublisher run targets`, `prepare BUILD --target T` and `prepared BUILD`, or the MCP tools `list_targets`, `prepare_publish` and `get_prepared`. See [Agents](Agents).
