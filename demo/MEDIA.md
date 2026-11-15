# Media in the sample site

The sample site in `sample-site/` and `sample-site.zip` is "Northwind Notes", a made-up product. It was built in FormWeb (library sections re-cast with new text, plus a few native sections) and exported with `GET /api/export`. Nothing in it comes from a third party except the font listed last. No remote picture is used: every image is a local file under `sample-site/assets/`.

Every picture below was drawn for this sample with a short Python script using Pillow 12 (rounded rectangles and text, no photographs, no scraped screenshots, no stock images). They carry no third-party content and are the owner's own work, Apache-2.0. The text inside the pictures is set in DejaVu Sans (Bitstream Vera license, free to embed and redistribute).

| File in `sample-site/assets/` | What it shows | Source | License |
| --- | --- | --- | --- |
| `f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp` | Notes window, dark (call to action, Home and Product) | Generated here with Pillow | Own work, Apache-2.0 |
| `0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp` | Notes window, light | Generated here with Pillow | Own work, Apache-2.0 |
| `289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp` | Notes board, dark (Product, step Write) | Generated here with Pillow | Own work, Apache-2.0 |
| `dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp` | Notes board, light | Generated here with Pillow | Own work, Apache-2.0 |
| `d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp` | Editor with source and preview, dark (step Link) | Generated here with Pillow | Own work, Apache-2.0 |
| `49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp` | Editor with source and preview, light | Generated here with Pillow | Own work, Apache-2.0 |
| `804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp` | Export view with three progress bars (step Export, both themes) | Generated here with Pillow | Own work, Apache-2.0 |
| `9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp` | Bar chart of notes written each week, dark (Home figures) | Generated here with Pillow | Own work, Apache-2.0 |
| `f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp` | Same chart, light | Generated here with Pillow | Own work, Apache-2.0 |
| `2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa.woff2` | Inter 4 variable, latin subset (the site's text font, embedded by the formai-studio preset) | Bundled with FormWeb at `library/presets/fonts/inter-4-var-latin.woff2` | SIL OFL 1.1, Copyright (c) 2016 The Inter Project Authors |

`demo/assets/formpublisher.webp`, `formpublisher@2x.webp`, `formpublisher-light.webp` and `formpublisher-light@2x.webp` (four files, used by the offline demo) are the FormPublisher app mark, copied unchanged from `frontend/src/assets/brand/`. Source: the owner's own art. As pictures shipped in the demo they are own work, Apache-2.0; the same art is also licensed GPL-3.0-only with this repository (see NOTICE.md, "Shipped in the app"), and the FormPublisher name and mark stay the owner's trademark.

The offline demo (`index.html`, `demo.css`, `demo.js`) draws its own window with CSS and inline SVG and loads no image, font or script from outside this folder.

Home's card picture for the sample, `frontend/public/demos/northwind/cover.webp`, is the first picture of the table above (Notes window, dark) cropped to its middle 1600x900 and resized to 640x360. Own work, Apache-2.0.

# Media in the three FormWeb demo sites

`sites/lowlight.zip`, `sites/looking-back.zip` and `sites/harbour-ferries.zip` are the three demo sites FormWeb ships, as FormWeb's `GET /api/export` wrote them: "Lowlight" (a planetarium-show studio, fictional), "Looking Back" (a photo essay on pictures of Earth from far away) and "Harbour Ferries" (a ferry operator, fictional). Each zip holds the export at the archive root, written with sorted names and fixed dates so the same export gives the same bytes. Every asset's file name is the SHA-256 of its bytes. Nothing is AI generated and nothing was retouched.

The NASA pictures were not downloaded for this repository: each file is byte for byte the file FormDeck (`frontend/public/demos/nasa/`) or Form.md (`demos/views/assets/media/`) already ships, resized and converted to WebP there. Their source pages carry a credit line and no licence text; NASA's media guidelines (https://www.nasa.gov/nasa-brand-center/images-and-media/) say NASA content "generally are not subject to copyright in the United States" and that "NASA should be acknowledged as the source of the material". "NASA content" below means: not subject to copyright in the United States (NASA media guidelines). The credit lines are the ones on each picture's own NASA page, read again on 15 November 2026; the NASA Image and Video Library records (images.nasa.gov) have no credit line, only the NASA centre, so those rows say NASA with the centre in brackets. `NOTICE.md` lists the same pictures with their full file names, credit lines and the changes made; the two files are kept in step.

One picture is not NASA-only: the Hubble Ultra Deep Field is published by ESA/Hubble under Creative Commons Attribution 4.0 International (https://creativecommons.org/licenses/by/4.0/, stated at https://esahubble.org/copyright/), which requires the full credit line to be shown. It was recorded before as public domain on the strength of its Wikimedia Commons page, which is not the original publisher's term. The file is a copy made through Wikimedia Commons (https://commons.wikimedia.org/wiki/File:Hubble_ultra_deep_field.jpg, whose source is the March 2004 NASA/STScI release 2004/07 that ESA/Hubble published as heic0406a), resized to 1400x1400; its tone differs slightly from the ESA/Hubble JPEG. NASA publishes the same picture at https://science.nasa.gov/asset/hubble/hubble-ultra-deep-field-image-reveals-galaxies-galore/ (credit there: "NASA, ESA, S. Beckwith (STScI) and the HUDF Team").

"Own work, Apache-2.0" below means the file was made for these demos by the owner's team; a capture of a demo site is own work, and the outside pictures visible in it keep the credit and status of their own rows.

Home's card pictures, `frontend/public/demos/<id>/cover.webp`, are the top 1440x810 of a 1440x900 screenshot of each site's home page, resized to 640x360 WebP with Pillow. Own work, Apache-2.0. The Looking Back card shows the Apollo 17 picture listed below (NASA (JSC), NASA content); the other two show no photograph.

## Lowlight (24 pictures, 4 fonts)

| File in `assets/` (first 12 characters of the name) | What it shows | Source | License |
| --- | --- | --- | --- |
| `a9d3e2fbb94e` .webp | Earthrise, Apollo 8 (AS08-14-2383) | NASA/William Anders, https://www.nasa.gov/image-detail/moon-landing-l-7-months-10-apollo-8-earthrise-photo-as08-14-2383 | NASA content |
| `07bd8a6730b2` .webp | A Breathtaking Earthset from Orion (art002e021278) | NASA, https://images.nasa.gov/details/art002e021278 | NASA content |
| `e422ff4c83b9` .webp | Solar System Portrait, Earth as Pale Blue Dot (PIA00452), Voyager 1 | NASA/JPL-Caltech, https://science.nasa.gov/photojournal/solar-system-portrait-earth-as-pale-blue-dot/ | NASA content |
| `fde102acb7e7` .webp | The Day the Earth Smiled (PIA17172) | NASA/JPL-Caltech/SSI, https://science.nasa.gov/photojournal/the-day-the-earth-smiled/ | NASA content |
| `955dcecd6515` .webp | The Greatest Saturn Portrait ...Yet (PIA06193) | NASA/JPL/Space Science Institute, https://science.nasa.gov/photojournal/the-greatest-saturn-portrait-yet/ | NASA content |
| `68e6d0d35c06` .webp | The Edge of the Night (PIA17199) | NASA/JPL-Caltech/Space Science Institute, https://science.nasa.gov/photojournal/the-edge-of-the-night/ | NASA content |
| `b03262099309` .webp | Cassini Jupiter Portrait (PIA04866) | NASA/JPL/Space Science Institute, https://science.nasa.gov/photojournal/cassini-jupiter-portrait/ | NASA content |
| `3425fd92e0c6` .webp | Looking Up at Mars Rover Curiosity in 'Buckskin' Selfie (PIA19808) | NASA/JPL-Caltech/MSSS, https://science.nasa.gov/photojournal/looking-up-at-mars-rover-curiosity-in-buckskin-selfie/ | NASA content |
| `87bbfdcfacff` .webp | Curiosity Self-Portrait at 'Mojave' Site on Mount Sharp (PIA19142) | NASA/JPL-Caltech/MSSS, https://science.nasa.gov/photojournal/curiosity-self-portrait-at-mojave-site-on-mount-sharp/ | NASA content |
| `3b3a4b424570` .webp | Perseverance's Selfie with Ingenuity (PIA24542) | NASA/JPL-Caltech/MSSS, https://science.nasa.gov/photojournal/perseverances-selfie-with-ingenuity/ | NASA content |
| `44acd0e9283f` .webp | The same picture cropped to 1245x1177 (columns 345 to 1590) and re-encoded as WebP at quality 86 with Pillow, for the tile-cut component | Same as the row above | NASA content |
| `25038129e80f` .webp | Perseverance's Selfie With 'Cheyava Falls' (PIA26344) | NASA/JPL-Caltech/MSSS, https://science.nasa.gov/photojournal/perseverances-selfie-with-cheyava-falls/ | NASA content |
| `1978facdbeee` .webp | Hubble Ultra Deep Field (ESA/Hubble heic0406a) | NASA, ESA, and S. Beckwith (STScI) and the HUDF Team, https://esahubble.org/images/heic0406a/ | Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/ (stated at https://esahubble.org/copyright/); the full credit must be shown; NASA's own copy: https://science.nasa.gov/asset/hubble/hubble-ultra-deep-field-image-reveals-galaxies-galore/ |
| `adb1b774966e`, `86196b445b96` .webp | Poster of the starfield component, dark and light | A still of the site's own component | Own work, Apache-2.0 |
| `cb033eaf2d91`, `fc4a5fbd93d5` .webp | Poster of the specks component, dark and light | A still of the site's own component | Own work, Apache-2.0 |
| `f74dc7cc5be2`, `72e06ffd2ad5` .webp | Poster of the receipt-printer component, dark and light | A still of the site's own component | Own work, Apache-2.0 |
| `996675ea94a8`, `d7aceb85e4e7` .webp | Poster of the orbit-constellation component, dark and light; it shows crops of the pictures above, among them the Hubble Ultra Deep Field | A still of the site's own component | Own work, Apache-2.0 (the still); the pictures in it keep the credit and status of their own rows above, including CC BY 4.0 for the Hubble Ultra Deep Field |
| `3c8bd2d2f376`, `56cca781ae81` .webp | Poster of the tile-cut component, dark and light; it shows PIA24542 cut into tiles | A still of the site's own component | Own work, Apache-2.0 (the still); the picture in it is NASA/JPL-Caltech/MSSS, NASA content |
| `f9eed231b2a4` .png | Lowlight site icon, 256 px | Drawn with Pillow for the demo | Own work, Apache-2.0 |
| `2c295d99e26d` .woff2 | Inter 4 variable, latin subset | Bundled with FormWeb at `library/presets/fonts/inter-4-var-latin.woff2` | SIL OFL 1.1, Copyright (c) 2016 The Inter Project Authors |
| `65fd17fcbd2e`, `35f8aec56cfd` .woff2 | Space Grotesk 400 and 700, latin | The @fontsource package, as shipped by FormTxt | SIL OFL 1.1 |
| `08949f728dc5` .woff2 | IBM Plex Mono 400 | As shipped by FormVis (`frontend/public/fonts/ibm-plex-mono/`) | SIL OFL 1.1, Copyright 2017 IBM Corp. |

## Looking Back (10 pictures, 5 fonts)

| File in `assets/` (first 12 characters of the name) | What it shows | Source | License |
| --- | --- | --- | --- |
| `a9d3e2fbb94e`, `07bd8a6730b2`, `e422ff4c83b9`, `fde102acb7e7` .webp | Earthrise, Earthset from Orion, Pale Blue Dot and The Day the Earth Smiled: the same four files as in Lowlight | As in the Lowlight table | NASA content |
| `f8414ced3bf6` .webp | View of the Earth seen by the Apollo 17 crew (as17-148-22727), 1972-12-07 | NASA (JSC), https://images.nasa.gov/details/as17-148-22727 | NASA content |
| `7fdaa80d0e06` .webp | Apollo 10 view of the Earth (as10-34-5013), 1969-05-18 | NASA (JSC), https://images.nasa.gov/details/as10-34-5013 | NASA content |
| `aa973715ed51` .webp | Gulf Coast from Atchafalaya Bay to Apalachicola seen from Gemini 11 (s66-54563), 1966-09-14 | NASA (JSC), https://images.nasa.gov/details/s66-54563 | NASA content |
| `703fbb02c672` .webp | GEMINI-TITAN (GT)-9 - EARTH-SKY - AUGMENTED TARGET DOCKING ADAPTER (ATDA) (s66-37923), 1966-06-06 | NASA (JSC), https://images.nasa.gov/details/s66-37923 | NASA content |
| `7d6de2d25625` .webp | GEMINI-TITAN (GT)-10 - EARTH SKY - DOCKING - IN-SPACE (s66-46249), 1966-07-18 | NASA (JSC), https://images.nasa.gov/details/s66-46249 | NASA content |
| `9702623b49c6` .png | Looking Back site icon, 256 px | Drawn with Pillow for the demo | Own work, Apache-2.0 |
| `1fe9ad5d8b2e` .woff2 | Playfair Display 400 | As shipped by FormVis (`frontend/public/fonts/playfair-display/`) | SIL OFL 1.1, Copyright 2017 The Playfair Display Project Authors |
| `02194deb92d3`, `882b7c150c29`, `7691c51bc286` .woff2 | Source Serif 4 400, 400 italic and 700, latin | The @fontsource package, as shipped by FormTxt | SIL OFL 1.1 |
| `08949f728dc5` .woff2 | IBM Plex Mono 400 | As shipped by FormVis | SIL OFL 1.1, Copyright 2017 IBM Corp. |

## Harbour Ferries (1 picture, 5 fonts)

The site uses no photograph. Its harbour map and logo are inline SVG written for the demo.

| File in `assets/` (first 12 characters of the name) | What it shows | Source | License |
| --- | --- | --- | --- |
| `4f9d2b2f49e0` .png | Harbour Ferries site icon, 256 px | Drawn with Pillow for the demo | Own work, Apache-2.0 |
| `e902b779e439`, `aae665c75af8` .woff2 | Oswald 400 and 700 | As shipped by FormVis (`frontend/public/fonts/oswald/`) | SIL OFL 1.1, Copyright 2016 The Oswald Project Authors |
| `418b06936717`, `c1e512679670` .woff2 | Work Sans 400 and 700, latin | The @fontsource package, as shipped by FormTxt | SIL OFL 1.1 |
| `08949f728dc5` .woff2 | IBM Plex Mono 400 | As shipped by FormVis | SIL OFL 1.1, Copyright 2017 IBM Corp. |

## Pictures linked by code, not stored

In `lowlight.zip`, `assets/components/orbit-constellation.js` and `site.formweb.json` name twelve default picture addresses under `https://media.formai.studio/media/formvfx/` as a fallback. The demo does not use them: the page sets its own pictures (the stored NASA and ESA/Hubble files above), so nothing from those addresses loads or is stored. They are the owner's own captures, linked and not bundled (FormWeb `LICENSES.md`, "Bundled content: section library").
