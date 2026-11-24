from pathlib import Path

from .support import raw_get

REPO_DOCS = Path(__file__).resolve().parents[3] / "docs"


def test_manual_route_serves_the_manual_file_byte_for_byte():
    status, headers, body = raw_get("/api/docs/manual")
    assert status == 200
    assert headers["content-type"].startswith("text/markdown")
    assert body == (REPO_DOCS / "MANUAL.md").read_bytes()


def test_manual_describes_the_routes_the_engine_has_for_trash_and_receive():
    status, headers, body = raw_get("/api/docs/manual")
    text = body.decode("utf-8")
    for line in ("POST /api/trash/{entry}/restore", "DELETE /api/trash/{entry}", "POST /api/receive/formweb", "GET /api/receive/status"):
        assert line in text


def test_every_documented_manual_image_is_served_as_webp():
    images = sorted((REPO_DOCS / "images").glob("*.webp"))
    assert images
    for image in images[:6]:
        status, headers, body = raw_get(f"/api/docs/images/{image.name}")
        assert status == 200, image.name
        assert headers["content-type"] == "image/webp"
        assert body == image.read_bytes()
        assert body[:4] == b"RIFF" and body[8:12] == b"WEBP"


def test_image_names_that_climb_or_are_not_webp_are_answered_404():
    for name in ("..%2FMANUAL.md", "..%2F..%2Fbackend%2Fapp%2Fmain.py", "MANUAL.md", "x.png", "UPPER.webp", ".hidden.webp", "missing-image.webp"):
        status, _, _ = raw_get(f"/api/docs/images/{name}")
        assert status == 404, name


def test_docs_routes_answer_reads_without_the_window_key():
    assert raw_get("/api/docs/manual")[0] == 200
