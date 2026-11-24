import io
import json
import zipfile

import pytest

from app.cli import OpError
from .compile_lane import core_path, write_fweb

NO_CORE = pytest.mark.skipif(core_path() is not None, reason="formweb-core is built here; this checks the refusal given when it is absent")
MISSING = "Opening .fweb projects needs formweb-core. Run ./setup/install_compiler."


@NO_CORE
@pytest.mark.parametrize("version", [1, 2])
def test_opening_a_fweb_project_without_the_compiler_is_refused_with_the_install_hint(version, client, tmp_path):
    path = write_fweb(tmp_path / "site.fweb", {"name": "x", "pages": []}, version)
    with pytest.raises(OpError) as caught:
        client.import_path(str(path))
    assert MISSING in caught.value.message
    assert client.sites()["sites"] == []


@NO_CORE
def test_compile_without_the_compiler_answers_422_core_missing(tmp_path):
    from app.services import compile as compiler

    path = write_fweb(tmp_path / "site.fweb", {"name": "x"}, 1)
    with pytest.raises(compiler.CompileError) as caught:
        compiler.compile_fweb(path, tmp_path / "out")
    assert (caught.value.message, caught.value.status, caught.value.code) == (MISSING, 422, "core-missing")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("value", ["../x.html", "/abs.html", "a//b.html", "a/./b.html", "c:/x.html", "a\\b.html", "", None, "a/../b"])
def test_an_export_path_that_could_leave_the_site_folder_is_refused(value):
    from app.services import compile as compiler

    with pytest.raises(compiler.CompileError):
        compiler.safe_path(value)


def test_a_plain_nested_export_path_is_kept_as_given():
    from app.services import compile as compiler

    assert compiler.safe_path("blog/post/index.html").parts == ("blog", "post", "index.html")


def test_a_version_1_envelope_reads_back_the_site_that_was_written(tmp_path):
    from app.services import compile as compiler

    site = {"name": "Round trip", "pages": [{"id": "home"}]}
    assert compiler.read_envelope(write_fweb(tmp_path / "a.fweb", site, 1))["site"] == site


def test_a_version_2_archive_reads_back_the_site_that_was_written(tmp_path):
    from app.services import compile as compiler

    site = {"name": "Round trip", "pages": [{"id": "home"}]}
    with zipfile.ZipFile(write_fweb(tmp_path / "a.fweb", site, 2)) as archive:
        assert compiler.read_project_json(archive)["site"] == site


@pytest.mark.parametrize(
    "text,message",
    [
        ("{not json", "that .fweb file is not valid JSON"),
        (json.dumps({"format": "other", "site": {}}), "that file is not a FormWeb project (format com.nodemode.formweb)"),
        (json.dumps({"format": "com.nodemode.formweb"}), "the .fweb file has no site"),
    ],
    ids=["not JSON", "another format", "no site"],
)
def test_a_bad_version_1_envelope_is_refused_with_its_reason(text, message, tmp_path):
    from app.services import compile as compiler

    path = tmp_path / "bad.fweb"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(compiler.CompileError) as caught:
        compiler.read_envelope(path)
    assert caught.value.message == message


def archive_of(entries):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    out.seek(0)
    return zipfile.ZipFile(out)


GOOD = json.dumps({"format": "com.nodemode.formweb", "version": 2, "site": {}})


@pytest.mark.parametrize(
    "entries,message",
    [
        ([("assets/a.png", b"x"), ("project.json", GOOD)], "the .fweb archive must start with project.json"),
        ([("project.json", "{nope")], "the .fweb archive project.json is not valid JSON"),
        ([("project.json", GOOD.replace("2", "1"))], "the .fweb archive project.json is not a FormWeb version 2 project"),
        ([("project.json", json.dumps({"format": "com.nodemode.formweb", "version": 2}))], "the .fweb archive has no site"),
    ],
    ids=["project.json not first", "not JSON", "version 1 inside an archive", "no site"],
)
def test_a_bad_version_2_archive_is_refused_with_its_reason(entries, message):
    from app.services import compile as compiler

    with archive_of(entries) as archive, pytest.raises(compiler.CompileError) as caught:
        compiler.read_project_json(archive)
    assert caught.value.message == message


def test_a_site_zip_is_not_taken_for_a_fweb_project_and_a_fweb_is(tmp_path):
    from app.services import compile as compiler
    from .compile_lane import DEMO

    assert compiler.looks_like_fweb(DEMO / "sites" / "lowlight.zip") is False
    assert compiler.looks_like_fweb(write_fweb(tmp_path / "one", {}, 1)) is True
    assert compiler.looks_like_fweb(write_fweb(tmp_path / "two", {}, 2)) is True
