import pytest

from conftest import DEMO

ALL = ["static-zip", "netlify", "cloudflare-pages", "vercel", "github-pages", "nginx"]
EXPECTED = {
    "static-zip": {"README.txt", "SHA256SUMS", "publish.json", "site.zip"},
    "netlify": {"site/index.html", "site/404.html", "site/_redirects", "site/_headers"},
    "cloudflare-pages": {"site/index.html", "site/404.html", "site/_redirects", "site/_headers"},
    "vercel": {"site/index.html", "site/404.html", "site/vercel.json"},
    "github-pages": {"site/index.html", "site/404.html", "site/.nojekyll", ".github/workflows/pages.yml"},
    "nginx": {"site/index.html", "site/404.html", "formpublisher.conf", "nginx-test.conf", "nginx-check.sh"},
}


@pytest.fixture
def prepared(client):
    site = client.import_path(str(DEMO / "sites" / "lowlight.zip"))
    build = client.build(site["id"])
    return client.prepare(build["id"], ALL)["results"]


def test_targets_are_the_six(client):
    assert [t["id"] for t in client.targets()["targets"]] == ALL


@pytest.mark.parametrize("target", ALL)
def test_each_target_writes_its_files_and_commands(prepared, target):
    result = prepared[target]
    names = {f["path"] for f in result["files"]}
    assert EXPECTED[target] <= names
    assert result["commands"]
    assert result["folder"].endswith(target)


def test_model_files_are_left_out_of_host_folders(prepared):
    for target in ALL[1:]:
        names = {f["path"] for f in prepared[target]["files"]}
        assert "site/site.formweb.json" not in names
        assert "site/asset-access.json" not in names


def test_nothing_is_uploaded_the_commands_are_for_the_person(prepared):
    assert prepared["netlify"]["commands"][0]["run"] == "npx netlify-cli@27 deploy --dir site"
    assert prepared["github-pages"]["commands"][-2]["run"].startswith("git push")
    assert prepared["nginx"]["commands"][0]["run"] == "sh nginx-check.sh"


def test_prepared_can_be_read_back(client, prepared):
    build = client.builds()["builds"][0]["id"]
    assert set(client.prepared(build)["results"]) == set(ALL)
