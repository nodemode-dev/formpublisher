# Host it yourself

FormPublisher gets a site ready for a host. It does not host it. This guide takes you from the folder FormPublisher wrote to a site on your own domain, for each of the six targets the Publish step prepares.

## What this costs

- **Your host.** You choose one and you pay it, if it charges. Some hosts have a free tier and some do not, and both change: see the host's pricing page.
- **Your domain.** You buy it from a registrar of your choice and renew it there. FormPublisher buys no domain.
- **FormPublisher.** Nothing. No subscription, no account, no account with the Form family. It runs on your computer.

FormPublisher uploads nothing and changes no DNS. Every step below is one you run, on your account with your host. No host here is recommended over another, and no link in this guide is an affiliate link.

## Contents

- [Before you start](#before-you-start)
- [Static zip](#static-zip)
- [Netlify](#netlify)
- [Cloudflare Pages](#cloudflare-pages)
- [Vercel](#vercel)
- [GitHub Pages](#github-pages)
- [nginx on your own server](#nginx-on-your-own-server)
- [Updating the site later](#updating-the-site-later)
- [Forms](#forms)
- [Analytics and search engines](#analytics-and-search-engines)

## Before you start

1. In FormPublisher, open the site, run the checks and build a package (sign it if you want a signature to check later).
2. In Publish, tick the host and press Prepare. FormPublisher writes one folder per host under your data folder: `~/FormPublisher/prepared/[site]/[build]/[host]`. Reveal opens it.
3. Every host folder except Static zip holds `site/`, the files to put online, with that host's own rules for redirects, headers and the 404 page already in it. FormWeb's model files (`site.formweb.json`, `asset-access.json`) are left out unless you asked to keep them.
4. The result card lists the exact commands for that folder. Run them in a terminal opened in that folder.

The commands that start with `npx` need Node.js 22.13 or later on your computer (any current LTS release: 22, 24 or 26); `npx` fetches the host's own command line tool the first time. Each command names the major version of the tool FormPublisher was checked with (for example `netlify-cli@27`), and `npx` fetches the newest release of that major version.

Connecting a domain works the same way everywhere: you add the domain to your site in the host's dashboard first, the host then shows the DNS records it wants, and you add those records where your domain's DNS is managed (usually your registrar). The values below are the ones each host's documentation gives today; when the host's dashboard shows other values for your site, use the dashboard's. DNS changes can take up to a day to reach everyone.

## Static zip

For any host that takes a folder or an archive: shared web hosting, an object store with a website setting, or a host not listed here.

**What you need:** a host that serves static files, and its way of uploading them (its file manager, SFTP or its own tool).

**The folder:** `site.zip` (the package, byte for byte what FormPublisher built), `publish.json` (every file with its SHA-256, the routes, redirects and headers), `SHA256SUMS` and `README.txt`.

**Steps:**

1. Check the files: `sha256sum -c SHA256SUMS`
2. Unpack: `unzip site.zip -d site`
3. Look at it on your computer: `python3 -m http.server -d site 8080`, then open `http://127.0.0.1:8080/`.
4. Upload the contents of `site/` to your host's web root, the way your host's documentation says.

A plain file server does not apply redirects or headers. `publish.json` lists them so that you can set them in your host's settings; the other targets write them in the host's own format for you.

**Your domain:** follow your host's documentation. Most ask for an `A` record (or a `CNAME` for a subdomain) pointing at the address they give you.

**HTTPS:** depends on the host; many issue a certificate once the domain points at them. If yours does not, see [nginx on your own server](#nginx-on-your-own-server) for doing it yourself.

## Netlify

**What you need:** Node.js, and a Netlify account to keep the site. You can try it without an account: drag the `site` folder onto `app.netlify.com/drop`, or run `npx netlify-cli@27 deploy --dir site --allow-anonymous`. An anonymous deploy gets a live URL, and you have one hour to claim it by logging in or creating an account. After that hour an unclaimed project is removed.

**The folder:** `site/` with `_redirects` (exact rules first, then splat rules; Netlify uses the first match, and a last rule serves `404.html` with status 404) and `_headers`.

**Steps:**

1. In a terminal in the folder, sign in once: `npx netlify-cli@27 login` (it opens your browser).
2. Draft deploy: `npx netlify-cli@27 deploy --dir site`. The first time, the tool asks you to pick an existing site or create a new one and links this folder to it. It prints a draft URL to look at.
3. When the draft looks right: `npx netlify-cli@27 deploy --dir site --prod`.

Without the command line, you can drag the `site` folder onto `app.netlify.com/drop`. If you are not logged in, Netlify publishes the folder as it is.

**Your domain:** add it to the site in Netlify (Domain management). Netlify adds both the bare domain and `www`. With DNS outside Netlify, Netlify recommends making `www` the primary domain; the bare domain then redirects to it. Then, at your DNS provider:

| Name | Type | Value |
| --- | --- | --- |
| `@` (the bare domain) | `ALIAS`, `ANAME` or flattened `CNAME` | `apex-loadbalancer.netlify.com` |
| `@`, only if your provider has none of those | `A` | `75.2.60.5` |
| `www` | `CNAME` | your site's `[name].netlify.app` |

Netlify shows the records it expects under Domain management, Production domains, Pending DNS verification. Netlify says the change may take a full day; if the site is still not reachable after 24 hours, check the records.

**HTTPS:** Netlify issues and renews a Let's Encrypt certificate for the domain on its own once DNS points at it. Its state is under Domain management, HTTPS.

## Cloudflare Pages

**What you need:** a Cloudflare account and Node.js.

Cloudflare now suggests Workers for new projects. Pages direct upload still works, and it is what this folder is for.

**The folder:** `site/` with `_redirects` and `_headers`. No 404 rule is written: Pages serves `404.html` itself. Cloudflare reads at most 2,000 static and 100 dynamic redirect rules and 100 header rules; Prepare warns when the site has more.

**Steps:**

1. Sign in once: `npx wrangler@4 login`.
2. The first time, create the project: `npx wrangler@4 pages project create [project] --production-branch main` (the exact line is in the result card). The site is then served at `[project].pages.dev`.
3. Deploy: `npx wrangler@4 pages deploy site --project-name [project]`, the exact line is in the result card.

Without the command line: Workers & Pages, Create application, then the drag and drop upload, and drop the `site` folder. A project made by direct upload stays a direct upload project; it cannot be switched to a Git connection later.

Drag and drop takes up to 1,000 files; `wrangler` takes up to 20,000 on the free plan. No file may be larger than 25 MiB.

**Your domain:** in the dashboard, Workers & Pages, your project, Custom domains, Set up a domain. Add the domain there first, before any DNS record: a `CNAME` made before the domain is added to the project fails to resolve.

| Domain | What Cloudflare needs |
| --- | --- |
| The bare domain (`example.com`) | The domain must be a Cloudflare zone: point your domain's nameservers at the ones Cloudflare gives you. Cloudflare then makes the record itself. |
| A subdomain (`www.example.com`) | A `CNAME` at your DNS provider from `www` to `[project].pages.dev`. In a Cloudflare zone it is made for you. |

**HTTPS:** Cloudflare issues the certificate for a custom domain of a Pages project. If your DNS has `CAA` records, they must allow Cloudflare's certificate authorities, or the certificate cannot be issued.

## Vercel

**What you need:** Node.js, and a Vercel account to keep the site. To try it without an account, run `npx vercel@66 deploy site --temporary`: it deploys to production and prints a claim URL and how long until the deployment expires. Open the claim URL to keep it, and do not share it. This does not work in a folder already linked to a Vercel project.

**The folder:** `site/` with `vercel.json` (redirects and headers) inside it, so the deploy picks it up. Vercel serves `404.html` itself.

**Steps:**

1. Sign in once: `npx vercel@66 login`.
2. Preview deploy: `npx vercel@66 deploy site`. The first time, the tool asks to set up and link a project. The first deploy of a new project is a production deploy even without `--prod`.
3. Later production deploys: `npx vercel@66 deploy site --prod`.

**Your domain:** in the project, Settings, Domains, Add Existing, and type the domain (Vercel offers to add `www` as well). Vercel then shows the records for your project:

| Domain | Type | Value |
| --- | --- | --- |
| The bare domain | `A` | the address Vercel shows for your project |
| A subdomain | `CNAME` | the project's own value Vercel shows (each project has a unique one) |

You can instead move the domain's nameservers to Vercel; copy your other records (mail, verification) to Vercel first.

**HTTPS:** Vercel requests a Let's Encrypt certificate for each domain added to a project and renews it on its own, once the DNS records are in place. Vercel says it tries to renew it 14 to 30 days before it expires.

## GitHub Pages

**What you need:** a GitHub account, a repository for the site, and git.

**The folder:** `site/` with `.nojekyll` (so GitHub does not run Jekyll over the files) and the site's own `404.html`, and `.github/workflows/pages.yml`. GitHub Pages ignores custom headers, so the result card warns which headers will not be sent.

There are two ways; pick one.

**Way 1, the gh-pages branch** (the commands in the result card), run in `site/`:

1. `git init -b gh-pages`
2. `git add -A`
3. `git commit -m "Publish site"`
4. `git remote add origin git@github.com:OWNER/REPO.git` (your repository)
5. `git push -u origin gh-pages --force`
6. In the repository, Settings, Pages: set Source to Deploy from a branch, branch `gh-pages`, folder `/ (root)`.

**Way 2, GitHub Actions:** put `site/` and `.github/workflows/pages.yml` from this folder at the top of the repository on its `main` branch and push. In Settings, Pages, set Source to GitHub Actions. Each push to `main` publishes `site/`, including files whose names start with a dot, such as `.nojekyll` and `.well-known/`.

**Your domain:** first verify the domain for your account, so no other GitHub user can take it over: your profile picture, Settings, Pages, Add a domain (for an organization: the organization's Settings, Pages). GitHub shows a `TXT` record named `_github-pages-challenge-[account].[your domain]`; add it at your DNS provider, wait, then press Verify. Keep that record. Then, in the repository's Settings, Pages, Custom domain, type the domain and Save. Do this before the DNS records, so nobody else can claim the name. Then, at your DNS provider:

| Name | Type | Value |
| --- | --- | --- |
| `@` (the bare domain) | `A` | `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` (all four) |
| `@`, optional for IPv6 | `AAAA` | `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153` |
| `@`, instead of the `A` records | `ALIAS` or `ANAME` | `OWNER.github.io` |
| `www` | `CNAME` | `OWNER.github.io` (without the repository name) |

With Way 1, GitHub stores the domain in a file named `CNAME` at the top of the `gh-pages` branch. The force push in step 5 replaces the whole branch, so before each later push put a file named `CNAME` in `site/` holding your domain on one line, or the domain is dropped. With Way 2 no `CNAME` file is used.

**HTTPS:** when DNS is in place, tick Enforce HTTPS in Settings, Pages. It can take up to 24 hours before the option is offered. GitHub gets the certificate from Let's Encrypt.

## nginx on your own server

**What you need:** a server you run (a computer at home with a fixed address, or a virtual server you rent) with nginx installed, and a way to copy files to it (scp, rsync or SFTP).

**The folder:** `site/`, `formpublisher.conf` (one `server` block for `conf.d`: the redirects, the headers, `try_files` so unknown paths get the site's `404.html` with status 404, gzip, and `absolute_redirect off`), `nginx-test.conf` and `nginx-check.sh`.

**Steps:**

1. Check the config on your computer: `sh nginx-check.sh` (it runs `nginx -t` on a scratch copy and changes nothing; it needs nginx installed). Or try the whole site in Docker with the `docker run` line in the result card, then open `http://127.0.0.1:8080/`.
2. Copy `site/` to the server, to `/usr/share/nginx/html` or to another folder (then change `root` in `formpublisher.conf` to it).
3. Copy `formpublisher.conf` into nginx's `conf.d` folder (often `/etc/nginx/conf.d/`), and set `server_name` to your domain, for example `server_name example.com www.example.com;`.
4. On the server: `sudo nginx -t`, then `sudo nginx -s reload`.

**Your domain:** at your DNS provider, an `A` record for `@` with your server's IPv4 address (and an `AAAA` record with its IPv6 address if it has one), and for `www` a `CNAME` to the bare domain or the same `A` record.

**HTTPS:** nginx serves HTTPS with a certificate you get from a certificate authority, for example Let's Encrypt with the client it recommends. Add a second server block, or extend this one:

```nginx
listen 443 ssl;
server_name example.com www.example.com;
ssl_certificate     /path/to/fullchain.pem;
ssl_certificate_key /path/to/privkey.pem;
```

Keep the key file readable only by root (nginx's master process reads it). Let's Encrypt certificates are getting shorter: 90 days today, 64 days for certificates issued from 10 February 2027, and 45 days from 16 February 2028. Use a client that renews on its own (one that supports ACME Renewal Information, or that renews at about two thirds of the lifetime), not a fixed 60-day timer, and reload nginx after each renewal.

## Updating the site later

1. Edit the site in FormWeb and send it again (File, Send to FormPublisher) or import it again. The same project gains a new revision.
2. Run the checks, build, sign if you sign, and Prepare the same host again. Preparing again replaces that host's folder.
3. Run the same deploy commands as the first time:
   - Static zip: upload the new `site/` contents over the old.
   - Netlify: `npx netlify-cli@27 deploy --dir site --prod` (the folder stays linked).
   - Cloudflare Pages: `npx wrangler@4 pages deploy site --project-name [project]`.
   - Vercel: `npx vercel@66 deploy site --prod`.
   - GitHub Pages, Way 1: the same five commands in the new `site/`, with your `CNAME` file in it; Way 2: replace `site/` in the repository and push.
   - nginx: copy the new `site/` over the old on the server; reload nginx only when `formpublisher.conf` changed.

The domain and HTTPS stay as they are; you set them up once.

## Forms

A static host serves files. To get a form's messages, something has to receive the form when a visitor presses Send. On Netlify that can be Netlify itself. On every other target it is a form service you choose, which emails you each message. FormWeb's own form service needs FormWeb's server, so it does not work on a static host.

The checks look at each form that posts. A form with no action, an action on the site itself (FormWeb's `/api/forms/` route included) or an address on this computer is an error, because it will send nothing once the site is on a static host. A form with Netlify's attribute and a name, or one that posts to a form service on the web, passes, except a Web3Forms form with no `access_key` value, which is an error. A field without a name gets a warning.

### Every target: a form service

Several services take a plain HTML form, with no JavaScript, and email you what visitors send. Examples, in alphabetical order: Basin (usebasin.com), Formspree (formspree.io) and Web3Forms (web3forms.com). This guide recommends none of them. Each has a free tier with a monthly limit, and the limits change, so see the service's own pricing page. Read its privacy terms too: your visitors' messages pass through it.

1. Make an account with the service (Web3Forms instead emails you an access key) and create a form.
2. In FormWeb, set the form's action to the address the service gives you, with method POST:
   - Basin: `https://usebasin.com/f/[your form id]`
   - Formspree: `https://formspree.io/f/[your form id]`
   - Web3Forms: `https://api.web3forms.com/submit`, plus a hidden field `access_key` holding your key, and a hidden field `redirect` holding the full address of your thank-you page.
3. Give every field a name. A field without a name is not sent.
4. Add the service's hidden spam trap field if you want one: `_gotcha` for Basin and Formspree, `botcheck` for Web3Forms.
5. Send FormWeb's site to FormPublisher again, run the checks, Prepare and deploy.
6. Send yourself a test message from the live site and check that the email arrives.

### Forms on Netlify

Netlify can receive the form itself, or you can use a form service as above. Netlify Forms needs a Netlify account.

1. In FormWeb, give the form a name (each form on the site needs its own) and method POST, and add the attribute `data-netlify="true"`.
2. If you want a thank-you page, set the form's action to its path, starting with `/` (for example `/thanks`).
3. If you want a spam trap, add `netlify-honeypot="bot-field"` to the form and a field named `bot-field` hidden from people.
4. In Netlify, open the project's Forms page and choose Enable form detection. It is off until you do. When the site has such a form, Prepare for Netlify reminds you.
5. Deploy again. Netlify finds forms by reading the HTML of each deploy, so a form only works after a deploy made with detection on.
6. Send a test message. It shows on the Forms page. To get an email for each message: Forms, Submission notifications.

Netlify filters messages for spam and lists the rest as verified. On Netlify's current plans form submissions use no credits. A form with `data-netlify="true"` does nothing on any other host: Prepare warns about it for every other target.

### Forms on Cloudflare Pages

Pages serves files and has no form receiver of its own. Running your own code needs Pages Functions, which this folder does not include. Use a form service (see above).

### Forms on Vercel

Vercel serves files and has no form receiver of its own. Running your own code needs Vercel Functions, which this folder does not include. Use a form service (see above).

### Forms on GitHub Pages

GitHub Pages is a static host: it publishes files and runs no code for your site. Use a form service (see above). GitHub asks that Pages sites not be used to send passwords or card numbers.

### Forms on nginx

`formpublisher.conf` serves files only and has no form receiver. Use a form service (see above), or run a receiver of your own on the server, which this guide does not cover.

### Forms with Static zip

It depends on your host. If your host offers a form receiver, follow its documentation. Otherwise use a form service (see above).

## Analytics and search engines

FormPublisher adds no analytics and no tracking to your site, and it sends nothing anywhere. If you want visitor counts, you choose a service and add its snippet in FormWeb.

### Visitor counts

Some hosts can count visits for you:

- Netlify counts visits from its own server logs, with nothing added to your pages: the project's Analytics & metrics, Analytics, Enable Analytics. See Netlify's pricing for its cost.
- Cloudflare Pages: Workers & Pages, your project, Metrics, Enable under Web Analytics. Cloudflare adds its own snippet to the next deployment.
- Vercel Web Analytics is turned on in the project's Analytics tab and also needs its script in your pages.

Other services give you one script tag to paste into every page. Examples, in alphabetical order: Cloudflare Web Analytics, Fathom, GoatCounter, Plausible, Simple Analytics and Umami. Cloudflare Web Analytics, GoatCounter, Plausible and Simple Analytics say they set no cookies, and Fathom says it sets no tracking cookies. Whether you still need a consent notice depends on the law where you and your visitors are, so read the service's own compliance page. Google Analytics sets cookies (`_ga`) in your visitors' browsers.

1. Make an account with the service and add your site there. It gives you a snippet with your site's id in it.
2. In FormWeb, add the snippet to the site's head so it is on every page.
3. Run the checks. No setting is needed: they recognise the snippets of the services named here, and warn when a snippet is on some pages but not on others (the 404 page and pages marked noindex are not counted). When they find Google's tag, they note that it sets cookies.
4. Prepare and deploy, then open the live site and check that the service shows your visit.

### Google Search Console

1. Open Google Search Console and add a property. A Domain property (`example.com`) covers `www` and every other subdomain, and is verified with a DNS record. A URL-prefix property (`https://www.example.com/`) covers that address only, and can also be verified with a meta tag or a file.
2. To verify by DNS: add the `TXT` record Search Console shows at your DNS provider, then press Verify.
3. To verify by meta tag: in FormWeb, add the `<meta name="google-site-verification" content="...">` tag Search Console shows to the home page's head, send the site to FormPublisher again, deploy, then press Verify.
4. Keep the record or the tag. If it goes, the site is no longer verified. Preparing again rebuilds `site/` from what FormWeb sent, so a tag or file you add by hand to `site/` is lost on the next Prepare.
5. Submit your sitemap: in Search Console, Sitemaps, type the sitemap's address (for example `https://www.example.com/sitemap.xml`) and press Submit. You need to be an owner of the property.

### Bing Webmaster Tools

1. Open Bing Webmaster Tools and add your site. One way is to import it from Google Search Console: the site is then verified and its sitemap comes with it.
2. Otherwise verify with what Bing shows: a meta tag named `msvalidate.01` in the home page's head (added in FormWeb), a file at the site root, or a DNS record.
3. Submit your sitemap under Sitemaps, if the import did not bring it.

Bing and some other search engines (not Google) also accept IndexNow, a way to tell them a page changed. It needs a key file at your site root and a tool that sends the notice. FormPublisher sends nothing, so this is up to you.

## What FormPublisher does not do

- It uploads nothing and signs you in nowhere. The commands run on your computer, with your account at the host.
- It buys no domain and changes no DNS record.
- It adds no analytics to your site and sends nothing about your visitors.
- It hosts nothing. When FormPublisher is closed, your site stays wherever you put it.
- It has no editor of its own: sites are edited in FormWeb.
