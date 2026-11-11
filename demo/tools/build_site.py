"""Build the Northwind Notes sample site in a running FormWeb backend and export it.

Usage: python3 build_site.py --formweb http://127.0.0.1:PORT --images IMG_DIR --out SITE_ZIP

--formweb  the FormWeb backend to build in (a private one, for example /home/claude/scripts/fw_backend.sh PORT start).
           The open document is REPLACED by a new blank site, so never point this at a backend whose site you want to keep.
--images   the folder gen_images.py wrote (the nine notes-*.webp files).
--out      where to write the export zip (GET /api/export). Nothing else on disk is written.
"""

import argparse
import copy
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--formweb", required=True, help="FormWeb backend URL, for example http://127.0.0.1:8398")
ap.add_argument("--images", required=True, help="folder with the pictures made by gen_images.py")
ap.add_argument("--out", required=True, help="path of the export zip to write")
ARGS = ap.parse_args()
B = ARGS.formweb.rstrip("/")
IMG = Path(ARGS.images)
OUT = Path(ARGS.out)


def call(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method, headers={"content-type": "application/json"} if data else {})
    try:
        r = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except urllib.error.URLError as e:
        raise SystemExit(f"FormWeb is not reachable at {B}: {e.reason}")
    b = r.read()
    return r.status, (b if raw else json.loads(b))


def state():
    return call('GET', '/api/state')[1]


def batch(cmds):
    rev = state()['revision']
    s, r = call('POST', '/api/batch', {"commands": cmds, "expectedRevision": rev})
    if s != 200:
        raise SystemExit(f'batch failed {s} {str(r)[:600]}')
    return r


def upload(name):
    data = (IMG / name).read_bytes()
    req = urllib.request.Request(B + '/api/assets', data=data, method='POST', headers={'content-type': 'image/webp', 'x-filename': name})
    r = json.loads(urllib.request.urlopen(req).read())
    return r['url']


def tree(id, tag, name, text='', attrs=None, styles=None, kids=None):
    return dict(id=id, tag=tag, name=name, text=text, attrs=attrs or {}, styles=styles or {}, kids=kids or [])


def flat(parent, t):
    node = {k: t[k] for k in ('id', 'tag', 'name', 'text', 'attrs', 'styles')}
    node['children'] = []
    node['breakpoints'] = {}
    out = [{"command": "node.add", "params": {"parent": parent, "node": node}}]
    for k in t['kids']:
        out += flat(t['id'], k)
    return out


def add_native(parent, t):
    batch(flat(parent, t))


def sect(id, name, inner, extra=None, tag='section'):
    base = {"--hue": "#3bb3c4", "box-sizing": "border-box", "width": "100%", "padding-top": "var(--sp-8)", "padding-bottom": "var(--sp-8)", "color": "var(--ink)"}
    base.update(extra or {})
    return tree(id, tag, name, styles=base, kids=[inner])


def frame(id, kids, extra=None):
    st = {"box-sizing": "border-box", "width": "100%", "max-width": "var(--page-max)", "margin-left": "auto", "margin-right": "auto", "padding-left": "var(--gutter)", "padding-right": "var(--gutter)"}
    st.update(extra or {})
    return tree(id, 'div', 'Frame', styles=st, kids=kids)


def link(id, text, href, primary=False):
    st = {"display": "inline-flex", "align-items": "center", "min-height": "var(--control-h)", "padding": "0 var(--sp-4)", "border-radius": "var(--radius-m)", "text-decoration": "none", "font-size": "var(--fs-s)", "font-weight": "var(--weight-strong)"}
    if primary:
        st.update({"background": "var(--hue)", "color": "#06161a"})
    else:
        st.update({"border": "1px solid var(--edge-strong)", "color": "var(--ink)"})
    return tree(id, 'a', text, text, {"href": href}, st)


def head(id, text, size='var(--fs-2xl)', tag='h2'):
    return tree(id, tag, text, text, styles={"margin": "0 0 var(--sp-4)", "font-size": size, "line-height": "1.08", "font-weight": "var(--weight-display)", "letter-spacing": "var(--track-tight)", "max-width": "18em"})


def para(id, text, soft=True):
    return tree(id, 'p', 'Text', text, styles={"margin": "0 0 var(--sp-5)", "max-width": "var(--prose-max)", "font-size": "var(--fs-m)", "color": "var(--ink-soft)" if soft else "var(--ink)"})


def header(pfx, current):
    items = [('Home', '/'), ('Product', '/product'), ('About', '/about')]
    navs = []
    for i, (t, h) in enumerate(items):
        navs.append(tree(f'{pfx}-nav{i}', 'a', t, t, {"href": h, **({"aria-current": "page"} if t == current else {})}, {"color": "var(--ink)" if t == current else "var(--ink-soft)", "text-decoration": "none", "font-size": "var(--fs-s)", "padding": "var(--sp-2) var(--sp-3)"}))
    brand = tree(f'{pfx}-brand', 'a', 'Brand', 'Northwind Notes', {"href": "/"}, {"color": "var(--ink)", "text-decoration": "none", "font-weight": "var(--weight-strong)", "font-size": "var(--fs-m)"})
    nav = tree(f'{pfx}-nav', 'nav', 'Navigation', attrs={"aria-label": "Main"}, styles={"display": "flex", "gap": "var(--sp-2)"}, kids=navs)
    inner = tree(f'{pfx}-in', 'div', 'Bar', styles={"box-sizing": "border-box", "width": "100%", "min-height": "var(--bar-h)", "display": "flex", "align-items": "center", "justify-content": "space-between", "padding-left": "var(--gutter)", "padding-right": "var(--gutter)"}, kids=[brand, nav])
    return tree(pfx, 'header', 'Header', styles={"position": "sticky", "top": "0", "z-index": "var(--z-sticky)", "background": "var(--bar-veil)", "backdrop-filter": "blur(12px)", "border-bottom": "1px solid var(--edge)", "color": "var(--ink)"}, kids=[inner])


def footer(pfx):
    cols = [tree(f'{pfx}-c0', 'p', 'Line', 'Northwind Notes is a made-up product for the FormPublisher sample site. Nothing here is for sale.', styles={"margin": "0", "max-width": "32em"}),
            tree(f'{pfx}-c1', 'nav', 'Footer links', attrs={"aria-label": "Footer"}, styles={"display": "flex", "gap": "var(--sp-4)"}, kids=[
                tree(f'{pfx}-l0', 'a', 'Home', 'Home', {"href": "/"}, {"color": "var(--ink-soft)"}),
                tree(f'{pfx}-l1', 'a', 'Product', 'Product', {"href": "/product"}, {"color": "var(--ink-soft)"}),
                tree(f'{pfx}-l2', 'a', 'About', 'About', {"href": "/about"}, {"color": "var(--ink-soft)"}),
            ])]
    row = frame(f'{pfx}-row', cols, {"display": "flex", "justify-content": "space-between", "gap": "var(--sp-6)", "flex-wrap": "wrap"})
    return tree(pfx, 'footer', 'Footer', styles={"border-top": "1px solid var(--edge)", "padding-top": "var(--sp-7)", "padding-bottom": "var(--sp-7)", "color": "var(--ink-faint)", "font-size": "var(--fs-s)"}, kids=[row])


def suffix(root):
    return root.rsplit('-', 1)[1]


def rewrite(root, mapping, hrefs=None, alts=None):
    sfx = suffix(root)
    site = state()['site']
    cmds = []
    for key, text in mapping.items():
        nid = f'{key}-{sfx}'
        if nid not in site['nodes']:
            raise SystemExit('missing node ' + nid)
        cmds.append({"command": "node.update", "params": {"id": nid, "patch": {"text": text}}})
    for key, href in (hrefs or {}).items():
        cmds.append({"command": "node.update", "params": {"id": f'{key}-{sfx}', "patch": {"attrs": {"href": href}}}})
    for key, alt in (alts or {}).items():
        cmds.append({"command": "node.update", "params": {"id": f'{key}-{sfx}', "patch": {"attrs": {"alt": alt}}}})
    batch(cmds)


def swap_images(root, table):
    """table: node key -> (file name, alt or None). Removes srcset and sizes, sets a local src."""
    sfx = suffix(root)
    cmds = []
    for key, (name, alt) in table.items():
        attrs = {"src": URLS[name], "srcset": None, "sizes": None}
        if alt:
            attrs["alt"] = alt
        cmds.append({"command": "node.update", "params": {"id": f'{key}-{sfx}', "patch": {"attrs": attrs}}})
    batch(cmds)


def insert(sid, page, values):
    s, r = call('POST', f'/api/library/sections/{sid}/insert', {"page": page, "values": values})
    if s != 200:
        raise SystemExit(f'insert {sid} failed {s} {str(r)[:600]}')
    return r['root']


if not IMG.is_dir():
    sys.exit(f"the images folder does not exist: {IMG} (run gen_images.py first)")
print(call('POST', '/api/new', {"name": "Northwind Notes", "blank": True})[0])
batch([{"command": "page.add", "params": {"name": "Product", "slug": "/product"}},
       {"command": "page.add", "params": {"name": "About", "slug": "/about"}},
       {"command": "page.add", "params": {"name": "Not found", "slug": "/404"}}])
print('preset', call('POST', '/api/library/presets/formai-studio/apply', {"mode": "all", "page": "home"})[0])
site = state()['site']
PAGES = {p['slug']: p for p in site['pages']}
URLS = {n.name: upload(n.name) for n in sorted(IMG.iterdir())}
print(URLS)

# Home
root = PAGES['/']['root']
add_native(root, header('hd-home', 'Home'))
hero = sect('hero-home', 'Hero', frame('hero-home-f', [
    tree('hero-kicker', 'p', 'Kicker', 'Local first notes', styles={"margin": "0 0 var(--sp-3)", "color": "var(--hue)", "font-size": "var(--fs-s)", "font-weight": "var(--weight-strong)"}),
    head('hero-h', 'Notes that stay on your computer.', 'var(--fs-hero)', 'h1'),
    para('hero-p', 'Northwind Notes keeps every note as a plain file in a folder you choose. Link notes together, search them in a blink and export the lot whenever you like.'),
    tree('hero-actions', 'div', 'Actions', styles={"display": "flex", "gap": "var(--sp-3)", "flex-wrap": "wrap"}, kids=[link('hero-a1', 'See how it works', '/product', True), link('hero-a2', 'About the project', '/about')]),
]), {"padding-top": "var(--sp-10)"})
add_native(root, hero)
r_fig = insert('formbench-figures', 'home', {"tint": "#3bb3c4"})
r_faq = insert('formmcp-faq', 'home', {"tint": "#3bb3c4", "cta_label": "How it works", "cta_link": "/product"})
r_cta = insert('formcompiler-cta', 'home', {"tint": "#3bb3c4", "headline": "Start a notebook in one minute.", "lead": "Install it, pick a folder and write.", "name": "Notes", "intro": "keeps your notes as plain files, so any other tool can open them too.", "button": "See how it works", "link": "/product", "fine": "Free to try, no account needed."})
add_native(root, footer('ft-home'))

rewrite(r_fig, {"label-form": "Northwind", "label-suffix": " Notes", "label-meta": "Measured, not claimed", "heading": "How quick is a note, really?", "summary": "Timed on an eight year old laptop, from key press to saved file.",
                "unit-1": "Milliseconds to open a note", "unit-2": "Median over 10,000 notes", "note": "Measured with the timing script that ships with the app, on a laptop with a spinning disk. Your numbers will differ.",
                "count-1-l": "notes in the test library", "count-2-l": "linked notes in the largest graph", "cap": "Weekly notes written during the beta, from 40 people who agreed to share a count."},
        alts={"shot-dark": "A bar chart of notes written each week, rising over four months", "shot-light": "A bar chart of notes written each week, rising over four months"})
r_figs = {"count-1-n": 10000, "count-2-n": 412, "num": 40}
rewrite(r_faq, {"label-form": "Northwind", "label-suffix": " Notes", "label-meta": "Four questions / Free", "title": "Questions about Northwind Notes.",
                "q1-t": "Where are my notes kept?", "a1-p": "In a folder you choose, one plain text file for each note. There is no database and no account.",
                "q2-t": "Can I use another editor?", "a2-p": "Yes. Any editor that opens text files can open your notes, and Northwind Notes picks up the changes at once.",
                "q3-t": "Does it work offline?", "a3-p": "It never needs a network. The sample site you are reading is a static export and needs none either.",
                "q4-t": "How do I leave?", "a4-p": "Copy the folder. Export also writes a single archive with every note and its links.",
                "prompt-h": "More questions?", "prompt-s": "The product page walks through the three steps."})
rewrite(r_cta, {"p-form": "Northwind", "p-suffix": " Notes"}, alts={"shot-dark": "The Northwind Notes window with a notebook, a note list and an open note", "shot-light": "The Northwind Notes window with a notebook, a note list and an open note"})
swap_images(r_fig, {"shot-dark": ("notes-activity-dark.webp", None), "shot-light": ("notes-activity-light.webp", None)})
swap_images(r_cta, {"shot-dark": ("notes-hero-dark.webp", None), "shot-light": ("notes-hero-light.webp", None)})

# Product
root = PAGES['/product']['root']
add_native(root, header('hd-prod', 'Product'))
intro = sect('intro-prod', 'Intro', frame('intro-prod-f', [
    tree('intro-kicker', 'p', 'Kicker', 'The product', styles={"margin": "0 0 var(--sp-3)", "color": "var(--hue)", "font-size": "var(--fs-s)", "font-weight": "var(--weight-strong)"}),
    head('intro-h', 'Write, link, take it with you.', 'var(--fs-hero)', 'h1'),
    para('intro-p', 'Three ideas, and no more: notes are files, links are written in the note, and leaving is a copy.'),
]), {"padding-top": "var(--sp-10)", "padding-bottom": "var(--sp-5)"})
add_native(root, intro)
r_how = insert('formencoder-how-it-works', 'page-1', {"tint": "#3bb3c4", "name": "Notes", "label": "How it works", "desc1": "Press N and start typing. Each note is saved as you go, as a plain text file in your notebook folder.", "desc2": "Type two square brackets to link to another note. Links show up on both notes, so you can walk the trail either way.", "desc3": "Press Export to write every note and its links to a folder or one archive. It takes seconds, even for a big notebook.", "button": "About the project", "link": "/about"})
r_cta2 = insert('formcompiler-cta', 'page-1', {"tint": "#3bb3c4", "headline": "Your notes, your folder.", "lead": "Nothing to sign up for.", "name": "Notes", "intro": "is free while it is a sample, and it is not real, so there is nothing to download.", "button": "Back to the start", "link": "/", "fine": "A sample product for the FormPublisher demo."})
add_native(root, footer('ft-prod'))
rewrite(r_how, {"h-form": "Northwind", "h-suffix": " Notes", "t1": "Write", "t2": "Link", "t3": "Export",
                "l1a-t": "One plain file for each note", "l1b-t": "Saved as you type, with undo", "l1c-t": "Folders watched for outside edits",
                "l2a-t": "Links written in double brackets", "l2b-t": "Backlinks listed on every note", "l2c-t": "Rename a note and its links follow",
                "l3a-t": "A folder of files or one archive", "l3b-t": "Links and tags kept intact", "l3c-t": "Plain files, readable anywhere"},
        alts={"fig1-d": "The notes board with nine notes in three columns", "fig1-l": "The notes board with nine notes in three columns",
              "fig2-d": "A note in the editor with its source beside the preview", "fig2-l": "A note in the editor with its source beside the preview",
              "fig3-i": "The export view with three notebooks and a progress bar for each"})
swap_images(r_how, {"fig1-d": ("notes-board-dark.webp", None), "fig1-l": ("notes-board-light.webp", None), "fig2-d": ("notes-editor-dark.webp", None), "fig2-l": ("notes-editor-light.webp", None), "fig3-i": ("notes-export.webp", None)})
rewrite(r_cta2, {"p-form": "Northwind", "p-suffix": " Notes"}, alts={"shot-dark": "The Northwind Notes window with a notebook, a note list and an open note", "shot-light": "The Northwind Notes window with a notebook, a note list and an open note"})
swap_images(r_cta2, {"shot-dark": ("notes-hero-dark.webp", None), "shot-light": ("notes-hero-light.webp", None)})

# About
root = PAGES['/about']['root']
add_native(root, header('hd-about', 'About'))
about = sect('about-main', 'About', frame('about-f', [
    tree('about-kicker', 'p', 'Kicker', 'About', styles={"margin": "0 0 var(--sp-3)", "color": "var(--hue)", "font-size": "var(--fs-s)", "font-weight": "var(--weight-strong)"}),
    head('about-h', 'A small sample for a publishing tool.', 'var(--fs-hero)', 'h1'),
    para('about-p1', 'Northwind Notes does not exist. This three page site was built in FormWeb to give FormPublisher something real to open, check, package and prepare for six hosts.'),
    para('about-p2', 'It has a redirect from an old address, a page for addresses that do not exist and pictures that were drawn for it, so every check has something to look at.'),
    tree('about-actions', 'div', 'Actions', styles={"display": "flex", "gap": "var(--sp-3)", "flex-wrap": "wrap"}, kids=[link('about-a1', 'See the product', '/product', True), link('about-a2', 'An address that does not exist', '/missing')]),
]), {"padding-top": "var(--sp-10)"})
add_native(root, about)
add_native(root, footer('ft-about'))

# Not found
root = PAGES['/404']['root']
add_native(root, header('hd-404', ''))
nf = sect('nf-main', 'Not found', frame('nf-f', [
    tree('nf-kicker', 'p', 'Kicker', 'Error 404', styles={"margin": "0 0 var(--sp-3)", "color": "var(--hue)", "font-size": "var(--fs-s)", "font-weight": "var(--weight-strong)"}),
    head('nf-h', 'That page is not here.', 'var(--fs-hero)', 'h1'),
    para('nf-p', 'The address may have moved or may never have existed. The start page lists everything on this site.'),
    tree('nf-actions', 'div', 'Actions', styles={"display": "flex", "gap": "var(--sp-3)"}, kids=[link('nf-a1', 'Go to the start page', '/', True), link('nf-a2', 'See the product', '/product')]),
]), {"padding-top": "var(--sp-10)", "min-height": "60vh"})
add_native(root, nf)
add_native(root, footer('ft-404'))

# counters, redirects, SEO
site = state()['site']
motion = copy.deepcopy(site['extensions']['motion'])
for k, v in r_figs.items():
    nid = f'{k}-{suffix(r_fig)}'
    motion['counters'][nid]['to'] = v
batch([{"command": "extension.set", "params": {"group": "motion", "value": motion}}])
seo = {"redirects": {"/notes": "/product", "/pricing": {"to": "/about", "status": 302}}}
s, r = call('POST', '/api/batch', {"commands": [{"command": "extension.set", "params": {"group": "seo", "value": seo}}], "expectedRevision": state()['revision']})
print('seo', s, str(r)[:300] if s != 200 else 'ok')
descs = {'/': 'Northwind Notes keeps every note as a plain file in a folder you choose.', '/product': 'Write, link and export: how Northwind Notes works.', '/about': 'Northwind Notes is a made-up product that gives FormPublisher a sample site.', '/404': 'This page is not here.'}
cmds = []
for p in state()['site']['pages']:
    cmds.append({"command": "page.update", "params": {"id": p['id'], "patch": {"seo": {"title": ("Northwind Notes" if p['slug'] == '/' else p['name'] + ' - Northwind Notes'), "description": descs[p['slug']], "noindex": p['slug'] == '/404'}}}})
s, r = call('POST', '/api/batch', {"commands": cmds, "expectedRevision": state()['revision']})
print('pages seo', s, str(r)[:300] if s != 200 else 'ok')
s, z = call('GET', '/api/export', raw=True)
if s != 200:
    raise SystemExit(f'export failed {s}')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(z)
print('export', s, len(z), '->', OUT)
