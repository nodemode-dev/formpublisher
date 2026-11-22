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

## Before you start

1. In FormPublisher, open the site, run the checks and build a package (sign it if you want a signature to check later).
2. In Publish, tick the host and press Prepare. FormPublisher writes one folder per host under your data folder: `~/FormPublisher/prepared/[site]/[build]/[host]`. Reveal opens it.
3. Every host folder except Static zip holds `site/`, the files to put online, with that host's own rules for redirects, headers and the 404 page already in it. FormWeb's model files (`site.formweb.json`, `asset-access.json`) are left out unless you asked to keep them.
4. The result card lists the exact commands for that folder. Run them in a terminal opened in that folder.

The commands that start with `npx` need Node.js on your computer; `npx` fetches the host's own command line tool the first time.

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

**What you need:** a Netlify account and Node.js.

**The folder:** `site/` with `_redirects` (exact rules first, then splat rules; Netlify uses the first match, and a last rule serves `404.html` with status 404) and `_headers`.

**Steps:**

1. In a terminal in the folder, sign in once: `npx netlify-cli login` (it opens your browser).
2. Draft deploy: `npx netlify-cli deploy --dir site`. The first time, the tool asks you to pick an existing site or create a new one and links this folder to it. It prints a draft URL to look at.
3. When the draft looks right: `npx netlify-cli deploy --dir site --prod`.

Without the command line, you can drag the `site` folder onto `app.netlify.com/drop`.

**Your domain:** add it to the site in Netlify (Domain management). Netlify adds both the bare domain and `www`. Then, at your DNS provider:

| Name | Type | Value |
| --- | --- | --- |
| `@` (the bare domain) | `ALIAS`, `ANAME` or flattened `CNAME` | `apex-loadbalancer.netlify.com` |
| `@`, only if your provider has none of those | `A` | `75.2.60.5` |
| `www` | `CNAME` | your site's `[name].netlify.app` |

Netlify shows the records it expects under Domain management, Production domains, Pending DNS verification.

**HTTPS:** Netlify issues and renews a Let's Encrypt certificate for the domain on its own once DNS points at it. Its state is under Domain management, HTTPS.

## Cloudflare Pages

**What you need:** a Cloudflare account and Node.js.

**The folder:** `site/` with `_redirects` and `_headers`. No 404 rule is written: Pages serves `404.html` itself.

**Steps:**

1. Sign in once: `npx wrangler login`.
2. The first time, create the project: `npx wrangler pages project create`, give it the name from the command FormPublisher wrote (the site id) and a production branch name. The site is then served at `[project].pages.dev`.
3. Deploy: `npx wrangler pages deploy site --project-name [project]`, the exact line is in the result card.

Without the command line: Workers & Pages, Create application, then the drag and drop upload, and drop the `site` folder. A project made by direct upload stays a direct upload project; it cannot be switched to a Git connection later.

**Your domain:** in the dashboard, Workers & Pages, your project, Custom domains, Set up a domain. Add the domain there first, before any DNS record: a `CNAME` made before the domain is added to the project fails to resolve.

| Domain | What Cloudflare needs |
| --- | --- |
| The bare domain (`example.com`) | The domain must be a Cloudflare zone: point your domain's nameservers at the ones Cloudflare gives you. Cloudflare then makes the record itself. |
| A subdomain (`www.example.com`) | A `CNAME` at your DNS provider from `www` to `[project].pages.dev`. In a Cloudflare zone it is made for you. |

**HTTPS:** Cloudflare issues the certificate for a custom domain of a Pages project. If your DNS has `CAA` records, they must allow Cloudflare's certificate authorities, or the certificate cannot be issued.

## Vercel

**What you need:** a Vercel account and Node.js.

**The folder:** `site/` with `vercel.json` (redirects and headers) inside it, so the deploy picks it up. Vercel serves `404.html` itself.

**Steps:**

1. Sign in once: `npx vercel login`.
2. Preview deploy: `npx vercel deploy site`. The first time, the tool asks to set up and link a project. The first deploy of a new project is a production deploy even without `--prod`.
3. Later production deploys: `npx vercel deploy site --prod`.

**Your domain:** in the project, Settings, Domains, Add Existing, and type the domain (Vercel offers to add `www` as well). Vercel then shows the records for your project:

| Domain | Type | Value |
| --- | --- | --- |
| The bare domain | `A` | the address Vercel shows for your project |
| A subdomain | `CNAME` | the project's own value Vercel shows (each project has a unique one) |

You can instead move the domain's nameservers to Vercel; copy your other records (mail, verification) to Vercel first.

**HTTPS:** Vercel requests a Let's Encrypt certificate for each domain added to a project and renews it on its own, once the DNS records are in place.

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

**Way 2, GitHub Actions:** put `site/` and `.github/workflows/pages.yml` from this folder at the top of the repository on its `main` branch and push. In Settings, Pages, set Source to GitHub Actions. Each push to `main` publishes `site/`.

**Your domain:** in Settings, Pages, Custom domain, type the domain and Save. Do this before the DNS records, so nobody else can claim the name. Then, at your DNS provider:

| Name | Type | Value |
| --- | --- | --- |
| `@` (the bare domain) | `A` | `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` (all four) |
| `@`, optional for IPv6 | `AAAA` | `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153` |
| `@`, instead of the `A` records | `ALIAS` or `ANAME` | `OWNER.github.io` |
| `www` | `CNAME` | `OWNER.github.io` (without the repository name) |

With Way 1, GitHub stores the domain in a file named `CNAME` at the top of the `gh-pages` branch. The force push in step 5 replaces the whole branch, so before each later push put a file named `CNAME` in `site/` holding your domain on one line, or the domain is dropped. With Way 2 no `CNAME` file is used.

**HTTPS:** when DNS is in place, tick Enforce HTTPS in Settings, Pages. It can take up to a day before the option is offered.

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

Keep the key file readable only by root (nginx's master process reads it). Renewing the certificate is up to you or the client you chose; reload nginx after it changes.

## Updating the site later

1. Edit the site in FormWeb and send it again (File, Send to FormPublisher) or import it again. The same project gains a new revision.
2. Run the checks, build, sign if you sign, and Prepare the same host again. Preparing again replaces that host's folder.
3. Run the same deploy commands as the first time:
   - Static zip: upload the new `site/` contents over the old.
   - Netlify: `npx netlify-cli deploy --dir site --prod` (the folder stays linked).
   - Cloudflare Pages: `npx wrangler pages deploy site --project-name [project]`.
   - Vercel: `npx vercel deploy site --prod`.
   - GitHub Pages, Way 1: the same five commands in the new `site/`, with your `CNAME` file in it; Way 2: replace `site/` in the repository and push.
   - nginx: copy the new `site/` over the old on the server; reload nginx only when `formpublisher.conf` changed.

The domain and HTTPS stay as they are; you set them up once.

## What FormPublisher does not do

- It uploads nothing and signs you in nowhere. The commands run on your computer, with your account at the host.
- It buys no domain and changes no DNS record.
- It hosts nothing. When FormPublisher is closed, your site stays wherever you put it.
- It has no editor of its own: sites are edited in FormWeb.
