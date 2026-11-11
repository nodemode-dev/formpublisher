/* Generated from checks.json, publish.json and prepared.json (real runs of the engine). Loaded as a script so the demo opens from disk. */
window.FP_DEMO = {
 "checks": {
  "problems": [
   {
    "code": "link.broken",
    "file": "about/index.html",
    "fix": "Remove the link or add the page in FormWeb.",
    "id": "static:link.broken:about/index.html:2",
    "line": 2,
    "message": "The link to /missing has no page.",
    "route": "/about/index.html",
    "selector": "a[href=\"/missing\"]",
    "severity": "error",
    "tier": "static",
    "url": "/missing"
   },
   {
    "code": "heading.h1",
    "file": "index.html",
    "fix": "Use exactly one h1 heading per page.",
    "id": "static:heading.h1:index.html:2",
    "line": 2,
    "message": "The page has 2 h1 headings.",
    "route": "/index.html",
    "severity": "warning",
    "tier": "static"
   },
   {
    "code": "heading.h1",
    "file": "product/index.html",
    "fix": "Use exactly one h1 heading per page.",
    "id": "static:heading.h1:product/index.html:2",
    "line": 2,
    "message": "The page has 2 h1 headings.",
    "route": "/product/index.html",
    "severity": "warning",
    "tier": "static"
   }
  ],
  "running": null,
  "summary": {
   "errors": 1,
   "infos": 0,
   "ran": [
    "static"
   ],
   "tiers": {
    "deep": 0,
    "live": 0,
    "static": 3
   },
   "warnings": 2
  },
  "thumbs": {}
 },
 "prepared": {
  "build": "c0fbe406652f",
  "results": {
   "cloudflare-pages": {
    "commands": [
     {
      "cwd": ".",
      "label": "Deploy",
      "run": "npx wrangler pages deploy site --project-name northwind-notes-17959d"
     },
     {
      "cwd": ".",
      "label": "Run it locally",
      "run": "npx wrangler pages dev site"
     }
    ],
    "files": [
     {
      "path": "site/404.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/404/index.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/README.txt",
      "sha256": "4ea7da360422ec800878db74ef173187615609300188ce6680ae044170e4831b",
      "size": 312
     },
     {
      "path": "site/_headers",
      "sha256": "19087ba89267f11f58d3252cf12c28792e89137ac1fc8c49090e4992d2ec0497",
      "size": 137
     },
     {
      "path": "site/_redirects",
      "sha256": "671d4d8cca169fe1f406391075f26f490cbcdafe4ca5875de06e7aa596661643",
      "size": 40
     },
     {
      "path": "site/about/index.html",
      "sha256": "e6918790bbff19d949921281f04db0d1904e2f415d8611fef0e59a8e2b445b47",
      "size": 11061
     },
     {
      "path": "site/assets/0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp",
      "sha256": "0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913",
      "size": 32348
     },
     {
      "path": "site/assets/289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp",
      "sha256": "289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057",
      "size": 26728
     },
     {
      "path": "site/assets/2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2",
      "sha256": "2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa",
      "size": 72920
     },
     {
      "path": "site/assets/49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp",
      "sha256": "49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332",
      "size": 28108
     },
     {
      "path": "site/assets/804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp",
      "sha256": "804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3",
      "size": 19762
     },
     {
      "path": "site/assets/9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp",
      "sha256": "9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0",
      "size": 15842
     },
     {
      "path": "site/assets/d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp",
      "sha256": "d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42",
      "size": 27330
     },
     {
      "path": "site/assets/dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp",
      "sha256": "dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f",
      "size": 31012
     },
     {
      "path": "site/assets/f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp",
      "sha256": "f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7",
      "size": 31242
     },
     {
      "path": "site/assets/f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp",
      "sha256": "f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361",
      "size": 16012
     },
     {
      "path": "site/assets/pages/0.css",
      "sha256": "1f9839d828a40ae0d307decad284a24f8b2a140c3cece5ea11e173b2c370cff5",
      "size": 29415
     },
     {
      "path": "site/assets/pages/1.css",
      "sha256": "1aca71fb6172fde3a0071563ccaf7867051660ea7c36d42dfb412112c1f1cf66",
      "size": 19177
     },
     {
      "path": "site/assets/pages/2.css",
      "sha256": "d62854b0720a49e743b5e4879c4bd96a91f1e72f427c35b403a20bb8e28a7d2b",
      "size": 5938
     },
     {
      "path": "site/assets/pages/3.css",
      "sha256": "e675ed0b077fd0748f03579367a368beabb27f3a3e4a2e1fdbeb1be8ce329568",
      "size": 5769
     },
     {
      "path": "site/assets/runtime.js",
      "sha256": "7097e74ccc1659034b81fd938157480a799d7d08ef85f7f3adfd4b5d4da67a1a",
      "size": 119081
     },
     {
      "path": "site/assets/site.css",
      "sha256": "4f8e8b9cd6e63372fa97da932e3561a13da6e1f0fc8efcd040e464bf363dd3d2",
      "size": 717
     },
     {
      "path": "site/index.html",
      "sha256": "a85cebc303435a9e3f60722ccb3a69292b3e1706b6dedbefc933b271b063143f",
      "size": 66600
     },
     {
      "path": "site/product/index.html",
      "sha256": "a7ceb6468a3d1ded8f360468a730319a2d4a776968b64d46e33a765a816af8bd",
      "size": 50134
     },
     {
      "path": "site/redirects.json",
      "sha256": "a751b1df0ea98a4e6d24b71a034647112e398c75dcee3e9442ec818e4fa338fa",
      "size": 61
     },
     {
      "path": "site/robots.txt",
      "sha256": "316d29a60270c66b7555f0e80fcb9a039458be20c576cfe3c6cd73b5d68a67a2",
      "size": 64
     },
     {
      "path": "site/routes.json",
      "sha256": "fd53ef88c2eea55e6cebed9316526d1278ed67c3fda978f294c3da33fe1a222d",
      "size": 409
     },
     {
      "path": "site/sitemap.xml",
      "sha256": "d7c9451cd194ac28600d27b3169ab41f1d1f70e967c572e356a53c4c2a928623",
      "size": 523
     }
    ],
    "folder": "/tmp/fplab-8405/home/prepared/northwind-notes-17959d/c0fbe406652f/cloudflare-pages",
    "includeModel": false,
    "leftOut": [
     "asset-access.json",
     "site.formweb.json"
    ],
    "name": "Cloudflare Pages",
    "notes": [
     "Cloudflare allows 2000 static and 100 dynamic redirect rules in _redirects.",
     "No 404 rule is written: Pages serves 404.html on its own when the file exists.",
     "Left out FormWeb's model files (asset-access.json, site.formweb.json). Prepare again with includeModel to keep them in site/."
    ],
    "preparedAt": "2026-11-10T09:23:25Z",
    "warnings": []
   },
   "github-pages": {
    "commands": [
     {
      "cwd": "site",
      "label": "Start a repository for the site",
      "run": "git init -b gh-pages"
     },
     {
      "cwd": "site",
      "label": "Stage the files",
      "run": "git add -A"
     },
     {
      "cwd": "site",
      "label": "Commit",
      "run": "git commit -m \"Publish site\""
     },
     {
      "cwd": "site",
      "label": "Add your repository",
      "run": "git remote add origin git@github.com:OWNER/REPO.git"
     },
     {
      "cwd": "site",
      "label": "Push the gh-pages branch",
      "run": "git push -u origin gh-pages --force"
     },
     {
      "cwd": ".",
      "label": "Look at it locally",
      "run": "python3 -m http.server -d site 8080"
     }
    ],
    "files": [
     {
      "path": ".github/workflows/pages.yml",
      "sha256": "350d12b5c4935582aa5dbb975771009511ccafbef0e3f02cf5493e3bbe3ca908",
      "size": 577
     },
     {
      "path": "redirects/README.txt",
      "sha256": "5353f11f8d9bd98057c276b30a70ad1cf5d3233b3435af35f9c6b443775314d7",
      "size": 397
     },
     {
      "path": "site/.nojekyll",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size": 0
     },
     {
      "path": "site/404.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/404/index.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/README.txt",
      "sha256": "4ea7da360422ec800878db74ef173187615609300188ce6680ae044170e4831b",
      "size": 312
     },
     {
      "path": "site/about/index.html",
      "sha256": "e6918790bbff19d949921281f04db0d1904e2f415d8611fef0e59a8e2b445b47",
      "size": 11061
     },
     {
      "path": "site/assets/0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp",
      "sha256": "0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913",
      "size": 32348
     },
     {
      "path": "site/assets/289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp",
      "sha256": "289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057",
      "size": 26728
     },
     {
      "path": "site/assets/2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2",
      "sha256": "2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa",
      "size": 72920
     },
     {
      "path": "site/assets/49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp",
      "sha256": "49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332",
      "size": 28108
     },
     {
      "path": "site/assets/804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp",
      "sha256": "804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3",
      "size": 19762
     },
     {
      "path": "site/assets/9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp",
      "sha256": "9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0",
      "size": 15842
     },
     {
      "path": "site/assets/d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp",
      "sha256": "d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42",
      "size": 27330
     },
     {
      "path": "site/assets/dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp",
      "sha256": "dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f",
      "size": 31012
     },
     {
      "path": "site/assets/f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp",
      "sha256": "f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7",
      "size": 31242
     },
     {
      "path": "site/assets/f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp",
      "sha256": "f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361",
      "size": 16012
     },
     {
      "path": "site/assets/pages/0.css",
      "sha256": "1f9839d828a40ae0d307decad284a24f8b2a140c3cece5ea11e173b2c370cff5",
      "size": 29415
     },
     {
      "path": "site/assets/pages/1.css",
      "sha256": "1aca71fb6172fde3a0071563ccaf7867051660ea7c36d42dfb412112c1f1cf66",
      "size": 19177
     },
     {
      "path": "site/assets/pages/2.css",
      "sha256": "d62854b0720a49e743b5e4879c4bd96a91f1e72f427c35b403a20bb8e28a7d2b",
      "size": 5938
     },
     {
      "path": "site/assets/pages/3.css",
      "sha256": "e675ed0b077fd0748f03579367a368beabb27f3a3e4a2e1fdbeb1be8ce329568",
      "size": 5769
     },
     {
      "path": "site/assets/runtime.js",
      "sha256": "7097e74ccc1659034b81fd938157480a799d7d08ef85f7f3adfd4b5d4da67a1a",
      "size": 119081
     },
     {
      "path": "site/assets/site.css",
      "sha256": "4f8e8b9cd6e63372fa97da932e3561a13da6e1f0fc8efcd040e464bf363dd3d2",
      "size": 717
     },
     {
      "path": "site/index.html",
      "sha256": "a85cebc303435a9e3f60722ccb3a69292b3e1706b6dedbefc933b271b063143f",
      "size": 66600
     },
     {
      "path": "site/notes/index.html",
      "sha256": "f2478cdf90b16464ca1cf888933bf4025d78016752c64397f214658bb9557705",
      "size": 312
     },
     {
      "path": "site/pricing/index.html",
      "sha256": "3bb616382e1a52bb9364fb677754810af17026282c86e954192e9a9837d94577",
      "size": 304
     },
     {
      "path": "site/product/index.html",
      "sha256": "a7ceb6468a3d1ded8f360468a730319a2d4a776968b64d46e33a765a816af8bd",
      "size": 50134
     },
     {
      "path": "site/redirects.json",
      "sha256": "a751b1df0ea98a4e6d24b71a034647112e398c75dcee3e9442ec818e4fa338fa",
      "size": 61
     },
     {
      "path": "site/robots.txt",
      "sha256": "316d29a60270c66b7555f0e80fcb9a039458be20c576cfe3c6cd73b5d68a67a2",
      "size": 64
     },
     {
      "path": "site/routes.json",
      "sha256": "fd53ef88c2eea55e6cebed9316526d1278ed67c3fda978f294c3da33fe1a222d",
      "size": 409
     },
     {
      "path": "site/sitemap.xml",
      "sha256": "d7c9451cd194ac28600d27b3169ab41f1d1f70e967c572e356a53c4c2a928623",
      "size": 523
     }
    ],
    "folder": "/tmp/fplab-8405/home/prepared/northwind-notes-17959d/c0fbe406652f/github-pages",
    "includeModel": false,
    "leftOut": [
     "asset-access.json",
     "site.formweb.json"
    ],
    "name": "GitHub Pages",
    "notes": [
     "The site's own 404.html is used for unknown paths.",
     "2 redirect(s) became meta-refresh pages; see redirects/README.txt.",
     "Then set Settings > Pages > Source to the gh-pages branch.",
     "Or copy .github/workflows/pages.yml into your repository (with the site/ folder) and set Pages > Source to GitHub Actions.",
     ".nojekyll stops GitHub from running Jekyll over the files.",
     "Left out FormWeb's model files (asset-access.json, site.formweb.json). Prepare again with includeModel to keep them in site/."
    ],
    "preparedAt": "2026-11-10T09:23:25Z",
    "warnings": [
     "GitHub Pages ignores custom headers, so Referrer-Policy, X-Content-Type-Options for /* will not be sent.",
     "GitHub Pages ignores custom headers, so Cache-Control for /assets/* will not be sent."
    ]
   },
   "netlify": {
    "commands": [
     {
      "cwd": ".",
      "label": "Draft deploy (preview URL)",
      "run": "npx netlify-cli deploy --dir site"
     },
     {
      "cwd": ".",
      "label": "Production deploy",
      "run": "npx netlify-cli deploy --dir site --prod"
     },
     {
      "cwd": ".",
      "label": "Run it locally",
      "run": "npx netlify-cli dev --dir site"
     }
    ],
    "files": [
     {
      "path": "site/404.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/404/index.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/README.txt",
      "sha256": "4ea7da360422ec800878db74ef173187615609300188ce6680ae044170e4831b",
      "size": 312
     },
     {
      "path": "site/_headers",
      "sha256": "19087ba89267f11f58d3252cf12c28792e89137ac1fc8c49090e4992d2ec0497",
      "size": 137
     },
     {
      "path": "site/_redirects",
      "sha256": "ca5c461d7d75f1c69e817da8810a0f84e8fca79d9f498329b98d7885e25f01fe",
      "size": 57
     },
     {
      "path": "site/about/index.html",
      "sha256": "e6918790bbff19d949921281f04db0d1904e2f415d8611fef0e59a8e2b445b47",
      "size": 11061
     },
     {
      "path": "site/assets/0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp",
      "sha256": "0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913",
      "size": 32348
     },
     {
      "path": "site/assets/289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp",
      "sha256": "289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057",
      "size": 26728
     },
     {
      "path": "site/assets/2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2",
      "sha256": "2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa",
      "size": 72920
     },
     {
      "path": "site/assets/49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp",
      "sha256": "49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332",
      "size": 28108
     },
     {
      "path": "site/assets/804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp",
      "sha256": "804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3",
      "size": 19762
     },
     {
      "path": "site/assets/9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp",
      "sha256": "9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0",
      "size": 15842
     },
     {
      "path": "site/assets/d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp",
      "sha256": "d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42",
      "size": 27330
     },
     {
      "path": "site/assets/dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp",
      "sha256": "dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f",
      "size": 31012
     },
     {
      "path": "site/assets/f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp",
      "sha256": "f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7",
      "size": 31242
     },
     {
      "path": "site/assets/f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp",
      "sha256": "f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361",
      "size": 16012
     },
     {
      "path": "site/assets/pages/0.css",
      "sha256": "1f9839d828a40ae0d307decad284a24f8b2a140c3cece5ea11e173b2c370cff5",
      "size": 29415
     },
     {
      "path": "site/assets/pages/1.css",
      "sha256": "1aca71fb6172fde3a0071563ccaf7867051660ea7c36d42dfb412112c1f1cf66",
      "size": 19177
     },
     {
      "path": "site/assets/pages/2.css",
      "sha256": "d62854b0720a49e743b5e4879c4bd96a91f1e72f427c35b403a20bb8e28a7d2b",
      "size": 5938
     },
     {
      "path": "site/assets/pages/3.css",
      "sha256": "e675ed0b077fd0748f03579367a368beabb27f3a3e4a2e1fdbeb1be8ce329568",
      "size": 5769
     },
     {
      "path": "site/assets/runtime.js",
      "sha256": "7097e74ccc1659034b81fd938157480a799d7d08ef85f7f3adfd4b5d4da67a1a",
      "size": 119081
     },
     {
      "path": "site/assets/site.css",
      "sha256": "4f8e8b9cd6e63372fa97da932e3561a13da6e1f0fc8efcd040e464bf363dd3d2",
      "size": 717
     },
     {
      "path": "site/index.html",
      "sha256": "a85cebc303435a9e3f60722ccb3a69292b3e1706b6dedbefc933b271b063143f",
      "size": 66600
     },
     {
      "path": "site/product/index.html",
      "sha256": "a7ceb6468a3d1ded8f360468a730319a2d4a776968b64d46e33a765a816af8bd",
      "size": 50134
     },
     {
      "path": "site/redirects.json",
      "sha256": "a751b1df0ea98a4e6d24b71a034647112e398c75dcee3e9442ec818e4fa338fa",
      "size": 61
     },
     {
      "path": "site/robots.txt",
      "sha256": "316d29a60270c66b7555f0e80fcb9a039458be20c576cfe3c6cd73b5d68a67a2",
      "size": 64
     },
     {
      "path": "site/routes.json",
      "sha256": "fd53ef88c2eea55e6cebed9316526d1278ed67c3fda978f294c3da33fe1a222d",
      "size": 409
     },
     {
      "path": "site/sitemap.xml",
      "sha256": "d7c9451cd194ac28600d27b3169ab41f1d1f70e967c572e356a53c4c2a928623",
      "size": 523
     }
    ],
    "folder": "/tmp/fplab-8405/home/prepared/northwind-notes-17959d/c0fbe406652f/netlify",
    "includeModel": false,
    "leftOut": [
     "asset-access.json",
     "site.formweb.json"
    ],
    "name": "Netlify",
    "notes": [
     "You can also drag the site folder onto app.netlify.com/drop.",
     "_redirects lists exact rules first, then splat rules; Netlify uses the first match.",
     "A final rule serves 404.html with status 404 for unknown paths.",
     "Left out FormWeb's model files (asset-access.json, site.formweb.json). Prepare again with includeModel to keep them in site/."
    ],
    "preparedAt": "2026-11-10T09:23:25Z",
    "warnings": []
   },
   "nginx": {
    "commands": [
     {
      "cwd": ".",
      "label": "Prepare a scratch folder for the check",
      "run": "mkdir -p /tmp/formpublisher-nginx"
     },
     {
      "cwd": ".",
      "label": "Check the config",
      "run": "nginx -t -p /tmp/formpublisher-nginx/ -c \"$PWD/nginx-test.conf\""
     },
     {
      "cwd": ".",
      "label": "Run it in Docker",
      "run": "docker run --rm -p 8080:80 -v \"$PWD/site:/usr/share/nginx/html:ro\" -v \"$PWD/formpublisher.conf:/etc/nginx/conf.d/default.conf:ro\" nginx:stable"
     }
    ],
    "files": [
     {
      "path": "formpublisher.conf",
      "sha256": "f936bb5eb2d586e35b40620c26295b7f030ab998e04c6f8392f0735485480254",
      "size": 1200
     },
     {
      "path": "nginx-test.conf",
      "sha256": "b577acf8c39173afedd31ec6a9d6ac50379b098af6f475f388de1418c9b1fdc5",
      "size": 763
     },
     {
      "path": "site/404.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/404/index.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/README.txt",
      "sha256": "4ea7da360422ec800878db74ef173187615609300188ce6680ae044170e4831b",
      "size": 312
     },
     {
      "path": "site/about/index.html",
      "sha256": "e6918790bbff19d949921281f04db0d1904e2f415d8611fef0e59a8e2b445b47",
      "size": 11061
     },
     {
      "path": "site/assets/0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp",
      "sha256": "0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913",
      "size": 32348
     },
     {
      "path": "site/assets/289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp",
      "sha256": "289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057",
      "size": 26728
     },
     {
      "path": "site/assets/2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2",
      "sha256": "2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa",
      "size": 72920
     },
     {
      "path": "site/assets/49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp",
      "sha256": "49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332",
      "size": 28108
     },
     {
      "path": "site/assets/804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp",
      "sha256": "804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3",
      "size": 19762
     },
     {
      "path": "site/assets/9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp",
      "sha256": "9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0",
      "size": 15842
     },
     {
      "path": "site/assets/d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp",
      "sha256": "d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42",
      "size": 27330
     },
     {
      "path": "site/assets/dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp",
      "sha256": "dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f",
      "size": 31012
     },
     {
      "path": "site/assets/f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp",
      "sha256": "f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7",
      "size": 31242
     },
     {
      "path": "site/assets/f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp",
      "sha256": "f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361",
      "size": 16012
     },
     {
      "path": "site/assets/pages/0.css",
      "sha256": "1f9839d828a40ae0d307decad284a24f8b2a140c3cece5ea11e173b2c370cff5",
      "size": 29415
     },
     {
      "path": "site/assets/pages/1.css",
      "sha256": "1aca71fb6172fde3a0071563ccaf7867051660ea7c36d42dfb412112c1f1cf66",
      "size": 19177
     },
     {
      "path": "site/assets/pages/2.css",
      "sha256": "d62854b0720a49e743b5e4879c4bd96a91f1e72f427c35b403a20bb8e28a7d2b",
      "size": 5938
     },
     {
      "path": "site/assets/pages/3.css",
      "sha256": "e675ed0b077fd0748f03579367a368beabb27f3a3e4a2e1fdbeb1be8ce329568",
      "size": 5769
     },
     {
      "path": "site/assets/runtime.js",
      "sha256": "7097e74ccc1659034b81fd938157480a799d7d08ef85f7f3adfd4b5d4da67a1a",
      "size": 119081
     },
     {
      "path": "site/assets/site.css",
      "sha256": "4f8e8b9cd6e63372fa97da932e3561a13da6e1f0fc8efcd040e464bf363dd3d2",
      "size": 717
     },
     {
      "path": "site/index.html",
      "sha256": "a85cebc303435a9e3f60722ccb3a69292b3e1706b6dedbefc933b271b063143f",
      "size": 66600
     },
     {
      "path": "site/product/index.html",
      "sha256": "a7ceb6468a3d1ded8f360468a730319a2d4a776968b64d46e33a765a816af8bd",
      "size": 50134
     },
     {
      "path": "site/redirects.json",
      "sha256": "a751b1df0ea98a4e6d24b71a034647112e398c75dcee3e9442ec818e4fa338fa",
      "size": 61
     },
     {
      "path": "site/robots.txt",
      "sha256": "316d29a60270c66b7555f0e80fcb9a039458be20c576cfe3c6cd73b5d68a67a2",
      "size": 64
     },
     {
      "path": "site/routes.json",
      "sha256": "fd53ef88c2eea55e6cebed9316526d1278ed67c3fda978f294c3da33fe1a222d",
      "size": 409
     },
     {
      "path": "site/sitemap.xml",
      "sha256": "d7c9451cd194ac28600d27b3169ab41f1d1f70e967c572e356a53c4c2a928623",
      "size": 523
     }
    ],
    "folder": "/tmp/fplab-8405/home/prepared/northwind-notes-17959d/c0fbe406652f/nginx",
    "includeModel": false,
    "leftOut": [
     "asset-access.json",
     "site.formweb.json"
    ],
    "name": "nginx",
    "notes": [
     "formpublisher.conf is one server block for conf.d; nginx-test.conf wraps it so nginx -t can parse it alone.",
     "Unknown paths return 404 through try_files and show the site's 404.html.",
     "absolute_redirect is off so redirects keep working behind a port mapping or a proxy.",
     "Left out FormWeb's model files (asset-access.json, site.formweb.json). Prepare again with includeModel to keep them in site/."
    ],
    "preparedAt": "2026-11-10T09:23:25Z",
    "warnings": []
   },
   "static-zip": {
    "commands": [
     {
      "cwd": ".",
      "label": "Unpack the package",
      "run": "unzip site.zip -d site"
     },
     {
      "cwd": ".",
      "label": "Serve it locally",
      "run": "python3 -m http.server -d site 8080"
     }
    ],
    "files": [
     {
      "path": "README.txt",
      "sha256": "a6e0ed39d4e44c8a4c19e67d806247ea04b80e18a311f8d95e1ba1f0d67c734d",
      "size": 609
     },
     {
      "path": "SHA256SUMS",
      "sha256": "22313803a5a69c881bf3a44251ef6c9ea6e1b5247d51eb776997d2eeddf3ec47",
      "size": 154
     },
     {
      "path": "publish.json",
      "sha256": "80d5b133d16ecd027ca0dff2b86f1b7adbb128a9e9b7c4e9fb7c33d55c518ca2",
      "size": 6281
     },
     {
      "path": "site.zip",
      "sha256": "92873a409fadbfcf8b18056df4c223929d0a1e6411955a77b90fa5fae0f970d3",
      "size": 377852
     }
    ],
    "folder": "/tmp/fplab-8405/home/prepared/northwind-notes-17959d/c0fbe406652f/static-zip",
    "includeModel": false,
    "leftOut": [],
    "name": "Static zip",
    "notes": [
     "site.zip is the build's own bytes, so its hash matches publish.json and any signature.",
     "This host has no server rules: redirects and headers in publish.json are not applied by a plain file server.",
     "site.zip is unchanged, so it still holds FormWeb's model files. The includeModel option only affects the site/ folders of the other hosts."
    ],
    "preparedAt": "2026-11-10T09:23:25Z",
    "warnings": []
   },
   "vercel": {
    "commands": [
     {
      "cwd": ".",
      "label": "Preview deploy",
      "run": "npx vercel deploy site"
     },
     {
      "cwd": ".",
      "label": "Production deploy",
      "run": "npx vercel deploy site --prod"
     },
     {
      "cwd": ".",
      "label": "Run it locally",
      "run": "npx vercel dev site"
     }
    ],
    "files": [
     {
      "path": "site/404.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/404/index.html",
      "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
      "size": 10052
     },
     {
      "path": "site/README.txt",
      "sha256": "4ea7da360422ec800878db74ef173187615609300188ce6680ae044170e4831b",
      "size": 312
     },
     {
      "path": "site/about/index.html",
      "sha256": "e6918790bbff19d949921281f04db0d1904e2f415d8611fef0e59a8e2b445b47",
      "size": 11061
     },
     {
      "path": "site/assets/0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp",
      "sha256": "0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913",
      "size": 32348
     },
     {
      "path": "site/assets/289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp",
      "sha256": "289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057",
      "size": 26728
     },
     {
      "path": "site/assets/2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2",
      "sha256": "2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa",
      "size": 72920
     },
     {
      "path": "site/assets/49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp",
      "sha256": "49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332",
      "size": 28108
     },
     {
      "path": "site/assets/804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp",
      "sha256": "804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3",
      "size": 19762
     },
     {
      "path": "site/assets/9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp",
      "sha256": "9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0",
      "size": 15842
     },
     {
      "path": "site/assets/d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp",
      "sha256": "d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42",
      "size": 27330
     },
     {
      "path": "site/assets/dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp",
      "sha256": "dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f",
      "size": 31012
     },
     {
      "path": "site/assets/f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp",
      "sha256": "f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7",
      "size": 31242
     },
     {
      "path": "site/assets/f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp",
      "sha256": "f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361",
      "size": 16012
     },
     {
      "path": "site/assets/pages/0.css",
      "sha256": "1f9839d828a40ae0d307decad284a24f8b2a140c3cece5ea11e173b2c370cff5",
      "size": 29415
     },
     {
      "path": "site/assets/pages/1.css",
      "sha256": "1aca71fb6172fde3a0071563ccaf7867051660ea7c36d42dfb412112c1f1cf66",
      "size": 19177
     },
     {
      "path": "site/assets/pages/2.css",
      "sha256": "d62854b0720a49e743b5e4879c4bd96a91f1e72f427c35b403a20bb8e28a7d2b",
      "size": 5938
     },
     {
      "path": "site/assets/pages/3.css",
      "sha256": "e675ed0b077fd0748f03579367a368beabb27f3a3e4a2e1fdbeb1be8ce329568",
      "size": 5769
     },
     {
      "path": "site/assets/runtime.js",
      "sha256": "7097e74ccc1659034b81fd938157480a799d7d08ef85f7f3adfd4b5d4da67a1a",
      "size": 119081
     },
     {
      "path": "site/assets/site.css",
      "sha256": "4f8e8b9cd6e63372fa97da932e3561a13da6e1f0fc8efcd040e464bf363dd3d2",
      "size": 717
     },
     {
      "path": "site/index.html",
      "sha256": "a85cebc303435a9e3f60722ccb3a69292b3e1706b6dedbefc933b271b063143f",
      "size": 66600
     },
     {
      "path": "site/product/index.html",
      "sha256": "a7ceb6468a3d1ded8f360468a730319a2d4a776968b64d46e33a765a816af8bd",
      "size": 50134
     },
     {
      "path": "site/redirects.json",
      "sha256": "a751b1df0ea98a4e6d24b71a034647112e398c75dcee3e9442ec818e4fa338fa",
      "size": 61
     },
     {
      "path": "site/robots.txt",
      "sha256": "316d29a60270c66b7555f0e80fcb9a039458be20c576cfe3c6cd73b5d68a67a2",
      "size": 64
     },
     {
      "path": "site/routes.json",
      "sha256": "fd53ef88c2eea55e6cebed9316526d1278ed67c3fda978f294c3da33fe1a222d",
      "size": 409
     },
     {
      "path": "site/sitemap.xml",
      "sha256": "d7c9451cd194ac28600d27b3169ab41f1d1f70e967c572e356a53c4c2a928623",
      "size": 523
     },
     {
      "path": "site/vercel.json",
      "sha256": "898e808485ea8be6ee35a1680013ef1c34af666f8338a79ef6820966b4ab9401",
      "size": 716
     }
    ],
    "folder": "/tmp/fplab-8405/home/prepared/northwind-notes-17959d/c0fbe406652f/vercel",
    "includeModel": false,
    "leftOut": [
     "asset-access.json",
     "site.formweb.json"
    ],
    "name": "Vercel",
    "notes": [
     "vercel.json sits inside site/ so the deploy picks it up; Vercel serves 404.html itself when the file exists.",
     "Left out FormWeb's model files (asset-access.json, site.formweb.json). Prepare again with includeModel to keep them in site/."
    ],
    "preparedAt": "2026-11-10T09:23:25Z",
    "warnings": []
   }
  }
 },
 "publish": {
  "created": true,
  "files": 27,
  "id": "c0fbe406652f",
  "publish": {
   "builtWith": "FormPublisher 0.1.2",
   "checks": {
    "errors": 1,
    "infos": 0,
    "tiers": [
     "static"
    ],
    "warnings": 2
   },
   "files": [
    {
     "path": "404/index.html",
     "sha256": "7afe07b96db69cb4ca2e298399f149d342d38929e3960ec9598aeb4a4393d931",
     "size": 10052
    },
    {
     "path": "README.txt",
     "sha256": "4ea7da360422ec800878db74ef173187615609300188ce6680ae044170e4831b",
     "size": 312
    },
    {
     "path": "about/index.html",
     "sha256": "e6918790bbff19d949921281f04db0d1904e2f415d8611fef0e59a8e2b445b47",
     "size": 11061
    },
    {
     "path": "asset-access.json",
     "sha256": "1f4d5bcfaf3d3decc017356c6c9c4691e501f2e26b42d3e2254a739c67ebfd0c",
     "size": 1127
    },
    {
     "path": "assets/0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp",
     "sha256": "0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913",
     "size": 32348
    },
    {
     "path": "assets/289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp",
     "sha256": "289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057",
     "size": 26728
    },
    {
     "path": "assets/2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2",
     "sha256": "2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa",
     "size": 72920
    },
    {
     "path": "assets/49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp",
     "sha256": "49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332",
     "size": 28108
    },
    {
     "path": "assets/804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp",
     "sha256": "804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3",
     "size": 19762
    },
    {
     "path": "assets/9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp",
     "sha256": "9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0",
     "size": 15842
    },
    {
     "path": "assets/d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp",
     "sha256": "d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42",
     "size": 27330
    },
    {
     "path": "assets/dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp",
     "sha256": "dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f",
     "size": 31012
    },
    {
     "path": "assets/f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp",
     "sha256": "f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7",
     "size": 31242
    },
    {
     "path": "assets/f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp",
     "sha256": "f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361",
     "size": 16012
    },
    {
     "path": "assets/pages/0.css",
     "sha256": "1f9839d828a40ae0d307decad284a24f8b2a140c3cece5ea11e173b2c370cff5",
     "size": 29415
    },
    {
     "path": "assets/pages/1.css",
     "sha256": "1aca71fb6172fde3a0071563ccaf7867051660ea7c36d42dfb412112c1f1cf66",
     "size": 19177
    },
    {
     "path": "assets/pages/2.css",
     "sha256": "d62854b0720a49e743b5e4879c4bd96a91f1e72f427c35b403a20bb8e28a7d2b",
     "size": 5938
    },
    {
     "path": "assets/pages/3.css",
     "sha256": "e675ed0b077fd0748f03579367a368beabb27f3a3e4a2e1fdbeb1be8ce329568",
     "size": 5769
    },
    {
     "path": "assets/runtime.js",
     "sha256": "7097e74ccc1659034b81fd938157480a799d7d08ef85f7f3adfd4b5d4da67a1a",
     "size": 119081
    },
    {
     "path": "assets/site.css",
     "sha256": "4f8e8b9cd6e63372fa97da932e3561a13da6e1f0fc8efcd040e464bf363dd3d2",
     "size": 717
    },
    {
     "path": "index.html",
     "sha256": "a85cebc303435a9e3f60722ccb3a69292b3e1706b6dedbefc933b271b063143f",
     "size": 66600
    },
    {
     "path": "product/index.html",
     "sha256": "a7ceb6468a3d1ded8f360468a730319a2d4a776968b64d46e33a765a816af8bd",
     "size": 50134
    },
    {
     "path": "redirects.json",
     "sha256": "a751b1df0ea98a4e6d24b71a034647112e398c75dcee3e9442ec818e4fa338fa",
     "size": 61
    },
    {
     "path": "robots.txt",
     "sha256": "316d29a60270c66b7555f0e80fcb9a039458be20c576cfe3c6cd73b5d68a67a2",
     "size": 64
    },
    {
     "path": "routes.json",
     "sha256": "fd53ef88c2eea55e6cebed9316526d1278ed67c3fda978f294c3da33fe1a222d",
     "size": 409
    },
    {
     "path": "site.formweb.json",
     "sha256": "6380763c9bb55fc38091febbddfba2bbf8d9df2ed5169f34ae9d45b41b1ff370",
     "size": 180291
    },
    {
     "path": "sitemap.xml",
     "sha256": "d7c9451cd194ac28600d27b3169ab41f1d1f70e967c572e356a53c4c2a928623",
     "size": 523
    }
   ],
   "format": "formpublisher-site",
   "headers": [
    {
     "for": "/*",
     "values": {
      "Referrer-Policy": "strict-origin-when-cross-origin",
      "X-Content-Type-Options": "nosniff"
     }
    },
    {
     "for": "/assets/*",
     "values": {
      "Cache-Control": "public, max-age=3600"
     }
    }
   ],
   "package": {
    "file": "site.zip",
    "sha256": "92873a409fadbfcf8b18056df4c223929d0a1e6411955a77b90fa5fae0f970d3",
    "size": 377852
   },
   "redirects": [
    {
     "from": "/notes",
     "status": 301,
     "to": "/product"
    },
    {
     "from": "/pricing",
     "status": 302,
     "to": "/about"
    }
   ],
   "routes": [
    {
     "item": null,
     "locale": "en",
     "page": "home",
     "path": "index.html",
     "stylesheet": "assets/pages/0.css"
    },
    {
     "item": null,
     "locale": "en",
     "page": "page-1",
     "path": "product/index.html",
     "stylesheet": "assets/pages/1.css"
    },
    {
     "item": null,
     "locale": "en",
     "page": "page-2",
     "path": "about/index.html",
     "stylesheet": "assets/pages/2.css"
    },
    {
     "item": null,
     "locale": "en",
     "page": "page-3",
     "path": "404/index.html",
     "stylesheet": "assets/pages/3.css"
    }
   ],
   "site": {
    "id": "northwind-notes-17959d",
    "name": "northwind-notes",
    "revision": "20261110T092325Z",
    "source": {
     "kind": "formweb-export"
    }
   },
   "version": 1
  },
  "revision": "20261110T092325Z",
  "signature": false,
  "signed": false,
  "site": "northwind-notes-17959d",
  "size": 377852
 }
};
