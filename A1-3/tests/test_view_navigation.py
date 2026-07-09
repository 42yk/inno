import json
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ShellParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = []
        self.mains = []
        self.forms = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "section":
            self.sections.append(attributes)
        if tag == "main":
            self.mains.append(attributes)
        if tag == "form":
            self.forms.append(attributes)
        if tag == "a":
            self.links.append(attributes)


def read_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def section_by_id(sections, section_id):
    for section in sections:
        if section.get("id") == section_id:
            return section
    raise AssertionError(f"section #{section_id} not found")


def test_index_is_shell_for_fetched_views():
    parser = ShellParser()
    parser.feed(read_text("frontend/index.html"))

    assert any(main.get("id") == "app-view" for main in parser.mains)
    assert not [section for section in parser.sections if section.get("data-view")]
    assert not parser.forms

    route_links = [link.get("href") for link in parser.links if link.get("href", "").startswith("#")]
    assert "#home" in route_links
    assert "#recommend" in route_links
    assert "#ranking" in route_links


def test_view_fragments_define_three_screens():
    for view_name in ("home", "recommend", "ranking"):
        parser = ShellParser()
        parser.feed(read_text(f"frontend/views/{view_name}.html"))

        section = section_by_id(parser.sections, view_name)
        assert section["data-view"] == view_name
        assert "view" in section.get("class", "").split()

    recommend_parser = ShellParser()
    recommend_parser.feed(read_text("frontend/views/recommend.html"))
    assert any(form.get("id") == "recommend-form" for form in recommend_parser.forms)


def test_app_js_fetches_views_and_initializes_screen_events():
    app_js = read_text("frontend/js/app.js")

    assert "const VIEW_PATHS =" in app_js
    assert "async function loadView(" in app_js
    assert "await fetch(VIEW_PATHS[viewName])" in app_js
    assert "function handleRoute(" in app_js
    assert 'window.addEventListener("hashchange", handleRoute)' in app_js
    assert "function initRecommendView()" in app_js
    assert "function initRankingView()" in app_js
    assert "aria-current" in app_js
    assert "body.dataset.view" not in app_js


def test_vercel_serves_view_fragments():
    config = json.loads(read_text("vercel.json"))
    rewrites = {(rule["source"], rule["destination"]) for rule in config["rewrites"]}

    assert ("/views/(.*)", "/frontend/views/$1") in rewrites


if __name__ == "__main__":
    test_index_is_shell_for_fetched_views()
    test_view_fragments_define_three_screens()
    test_app_js_fetches_views_and_initializes_screen_events()
    test_vercel_serves_view_fragments()
