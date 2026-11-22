# Hosting

FormPublisher gets a site ready for a host and never uploads it. The hosting guide, `docs/HOSTING.md` in the repository, takes you from the folder Publish wrote to a site on your own domain. In the window, each prepared host opens the guide at its own part.

You pay your host and your domain, nothing else. No host is recommended over another.

## The parts of the guide

- **Before you start.** Check, build and Prepare, where the folder is, what `site/` holds, and how connecting a domain works on every host.
- **Each host.** One part each for Static zip, Netlify, Cloudflare Pages, Vercel, GitHub Pages and nginx on your own server: the commands to run, your domain's DNS records and HTTPS.
- **Updating the site later.** Edit in FormWeb, send the site again, check, build, Prepare the same host and run the same deploy commands. The domain and HTTPS stay as they are.
- **Forms.** A static host serves files, so something has to receive a form. On Netlify that can be Netlify itself. On every other host it is a form service you choose. The checks flag a form that would send nothing.
- **Analytics and search engines.** FormPublisher adds no analytics and no tracking. The part shows where to add a visitor count yourself, and how to tell Google Search Console and Bing Webmaster Tools about the site.
- **What FormPublisher does not do.** It uploads nothing, buys no domain, changes no DNS record and hosts nothing.

## The live-site check

After you deployed a folder yourself, the live-site check reads your public site and says what to fix. It is in the Live site part at the bottom of the Publish sheet: an Address field, a Host picker and the button Check the live site. It runs only when you press the button and confirm. Opening the sheet reads nothing.

**The address.** A domain name, or an https address with no path (`example.com`, `https://www.example.com/`). An IP address or a local name is refused. The check reads two names: the bare domain and `www.` in front of it.

**What it reads.** DNS for both names, the certificate and its end date, the https home page, and http on port 80. Then, on the name that serves the home page: the build's exact redirects (50 at most), one made-up address for the 404, and up to three files of the build that are not pages, compared with their SHA-256 in `publish.json`. It follows no redirect, and it stops the redirect and file reads after two minutes.

**The findings.** One row each, with a severity, a message and a fix:

| Code | Says |
| --- | --- |
| `live.dns` | whether each name resolves |
| `live.tls`, `live.cert-expiry` | whether the certificate is valid, and a warning when it ends within 7 days |
| `live.www` | whether the bare name and `www` lead to the same site |
| `live.http` | whether http goes to https |
| `live.redirect` | whether the build's redirects answer as built |
| `live.404` | whether a missing page answers 404 |
| `live.build` | whether the files online are this build's |

Every warning and error has Read the guide, which opens `docs/HOSTING.md` at the part to read for that host. The last result of each site is kept in `live/SITE.json` in the data folder.

**What it does not do.** It uploads nothing, sends no form and no cookie, signs in nowhere and changes no DNS record.

## The same steps for agents

`./formpublisher run live-check SITE-ID --address DOMAIN [--build B] [--target T]` prints one line per finding and exits 1 on a warning or error. The MCP tool is `check_live_site`. Both read only the address the person gave. See [Agents](Agents) and [Publishing](Publishing).
