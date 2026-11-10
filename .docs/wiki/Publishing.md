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

## Verify and remove

Verify re-reads the folder and checks each file against the hashes in `publish.json`, and the host's own files against a fresh prepare. Remove moves the folder to `trash/`. Preparing again replaces the folder. Folders live at `prepared/[site]/[build]/[host]/` in the data folder.

## Receive from FormWeb

FormWeb's Send to FormPublisher posts a `site-export.zip` to `POST /api/receive/formweb` on this computer (headers `X-FormWeb-Version`, and optionally `X-FormWeb-Site-Name` and `X-FormWeb-Project`). Other addresses are refused. When FormPublisher is closed, FormWeb writes the file into `inbox/` in the data folder; every `*.zip` or `*.fweb` there is imported when the engine starts and every 5 seconds after, and moved to `inbox/imported/` or, with a reason, to `inbox/failed/`. The window shows a toast with Open and adds the site to Recent. `./formpublisher run receive-status` reports the endpoint, the inbox and the last receipts.

## The same steps for agents

`./formpublisher run targets`, `prepare BUILD --target T` and `prepared BUILD`, or the MCP tools `list_targets`, `prepare_publish` and `get_prepared`. See [Agents](Agents).
