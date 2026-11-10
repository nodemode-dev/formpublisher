# Media in the sample site

The sample site in `sample-site/` and `sample-site.zip` is "Northwind Notes", a made-up product. It was built in FormWeb (library sections re-cast with new text, plus a few native sections) and exported with `GET /api/export`. Nothing in it comes from a third party except the font listed last. No remote picture is used: every image is a local file under `sample-site/assets/`.

Every picture below was drawn for this sample with a short Python script using Pillow 12 (rounded rectangles and text, no photographs, no scraped screenshots, no stock images). They carry no third-party content and are released under CC0 1.0 (public domain dedication) by the FormPublisher project. The text inside the pictures is set in DejaVu Sans (Bitstream Vera license, free to embed and redistribute).

| File in `sample-site/assets/` | What it shows | Source | License |
| --- | --- | --- | --- |
| `f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp` | Notes window, dark (call to action, Home and Product) | Generated here with Pillow | CC0 1.0 |
| `0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp` | Notes window, light | Generated here with Pillow | CC0 1.0 |
| `289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp` | Notes board, dark (Product, step Write) | Generated here with Pillow | CC0 1.0 |
| `dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp` | Notes board, light | Generated here with Pillow | CC0 1.0 |
| `d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp` | Editor with source and preview, dark (step Link) | Generated here with Pillow | CC0 1.0 |
| `49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp` | Editor with source and preview, light | Generated here with Pillow | CC0 1.0 |
| `804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp` | Export view with three progress bars (step Export, both themes) | Generated here with Pillow | CC0 1.0 |
| `9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp` | Bar chart of notes written each week, dark (Home figures) | Generated here with Pillow | CC0 1.0 |
| `f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp` | Same chart, light | Generated here with Pillow | CC0 1.0 |
| `2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2` | Inter 4 variable, latin subset (the site's text font, embedded by the formai-studio preset) | Bundled with FormWeb at `library/presets/fonts/inter-4-var-latin.woff2` | SIL OFL 1.1, Copyright (c) 2016 The Inter Project Authors |

`assets/formpublisher*.webp` (four files) are the FormPublisher app mark, copied unchanged from `frontend/src/assets/brand/`. Source: the owner's own art, GPL-3.0-only with this repository (see NOTICE.md).

The offline demo (`index.html`, `demo.css`, `demo.js`) draws its own window with CSS and inline SVG and loads no image, font or script from outside this folder.
