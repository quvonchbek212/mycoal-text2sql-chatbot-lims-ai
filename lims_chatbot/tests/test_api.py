"""API testlari: HTTP Basic avtorizatsiya, Swagger, suhbat xotirasi (soxta graf va baza bilan)."""
import pytest
from fastapi.testclient import TestClient

import main
from lims_chatbot.app.config import Settings
from lims_chatbot.app.memory import ChatMemory

AUTH = ("tester", "maxfiy-parol")


class FakeGraph:
    def __init__(self):
        self.histories = []
        self.langs = []

    async def run(self, question, history=None, lang="uz"):
        self.histories.append(list(history or []))
        self.langs.append(lang)
        if question == "salom":
            return {"route": "chitchat", "answer": "ok"}
        return {"route": "database", "answer": "ok", "sql": f"SELECT '{question}'", "columns": [], "rows": []}


class FakeDb:
    async def ping(self):
        return True


class FakeLlm:
    ok = True

    async def ping(self):
        return self.ok


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        c.app.state.graph = FakeGraph()
        c.app.state.db = FakeDb()
        c.app.state.llm = FakeLlm()
        c.app.state.memory = ChatMemory()
        c.app.state.settings = Settings(db_password="x", api_username=AUTH[0], api_password=AUTH[1])
        yield c


# ---------------- avtorizatsiya ----------------
@pytest.mark.parametrize("method,path", [("post", "/api/chat"), ("post", "/api/chat/stream"),
                                         ("get", "/api/schema"), ("get", "/healthz")])
def test_endpoints_require_login(client, method, path):
    kwargs = {"json": {"question": "x"}} if method == "post" else {}
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Basic"


def test_wrong_password_rejected(client):
    r = client.post("/api/chat", json={"question": "x"}, auth=(AUTH[0], "yomon"))
    assert r.status_code == 401
    r = client.post("/api/chat", json={"question": "x"}, auth=("boshqa", AUTH[1]))
    assert r.status_code == 401


def test_correct_login_passes(client):
    r = client.post("/api/chat", json={"question": "salom"}, auth=AUTH)
    assert r.status_code == 200 and r.json()["answer"] == "ok"


def test_missing_config_fails_closed(client):
    """Login/parol sozlanmagan bo'lsa API ochiq qolmaydi."""
    client.app.state.settings = Settings(db_password="x", api_username="", api_password="")
    assert client.post("/api/chat", json={"question": "x"}, auth=AUTH).status_code == 500
    assert client.post("/api/chat", json={"question": "x"}).status_code == 401


# ---------------- Swagger ----------------
def test_swagger_open_and_has_basic_scheme(client):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    schemes = spec["components"]["securitySchemes"]
    assert any(s.get("scheme") == "basic" for s in schemes.values())
    assert spec["paths"]["/api/chat"]["post"].get("security")


def test_root_redirects_to_docs(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


def test_chat_ui_removed(client):
    assert client.get("/static/index.html", auth=AUTH).status_code == 404


# ---------------- suhbat va holat ----------------
def test_session_memory(client):
    client.post("/api/chat", json={"question": "birinchi", "session_id": "abc"}, auth=AUTH)
    client.post("/api/chat", json={"question": "ikkinchi", "session_id": "abc"}, auth=AUTH)
    client.post("/api/chat", json={"question": "boshqa", "session_id": "xyz"}, auth=AUTH)
    hist = client.app.state.graph.histories
    assert hist[0] == []
    assert hist[1][0]["question"] == "birinchi"
    assert hist[2] == []


def test_session_id_generated_when_missing(client):
    first = client.post("/api/chat", json={"question": "birinchi"}, auth=AUTH).json()
    second = client.post("/api/chat", json={"question": "ikkinchi"}, auth=AUTH).json()
    assert first["session_id"] and first["session_id"] != second["session_id"]
    # Qaytgan session_id bilan suhbat davom etadi.
    client.post("/api/chat", json={"question": "davomi", "session_id": first["session_id"]}, auth=AUTH)
    assert client.app.state.graph.histories[-1][0]["question"] == "birinchi"


def test_given_session_id_echoed(client):
    r = client.post("/api/chat", json={"question": "x", "session_id": "abc"}, auth=AUTH)
    assert r.json()["session_id"] == "abc"


def test_only_sql_turns_become_context(client):
    client.post("/api/chat", json={"question": "salom", "session_id": "s1"}, auth=AUTH)
    client.post("/api/chat", json={"question": "sorov", "session_id": "s1"}, auth=AUTH)
    client.post("/api/chat", json={"question": "davomi", "session_id": "s1"}, auth=AUTH)
    assert [t["question"] for t in client.app.state.graph.histories[-1]] == ["sorov"]


def test_bad_session_id_rejected(client):
    r = client.post("/api/chat", json={"question": "x", "session_id": "../etc"}, auth=AUTH)
    assert r.status_code == 422


def test_healthz_hides_connection_details(client):
    response = client.get("/healthz", auth=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert data["db_connected"] is True
    assert data["memory_backend"] == "process" and data["memory_ok"] is True
    assert "db_user" not in data and "db_error" not in data and "db" not in data


def test_health_reports_real_llm_failure(client):
    client.app.state.llm.ok = False
    response = client.get("/healthz", auth=AUTH)
    assert response.status_code == 503
    assert response.json()["status"] == "degraded" and response.json()["llm_connected"] is False


def test_accounts_cannot_share_session_context(client):
    client.app.state.settings.api_accounts = {"alice": "alice-password", "bob": "bob-password", "empty": ""}
    for name in ("alice", "bob", "alice"):
        response = client.post("/api/chat", json={"question": name, "session_id": "same"},
                               auth=(name, name + "-password"))
        assert response.status_code == 200
    histories = client.app.state.graph.histories
    assert histories[0] == [] and histories[1] == []
    assert histories[2][0]["question"] == "alice"
    assert client.post("/api/chat", json={"question": "x"}, auth=("empty", "invalid-account")).status_code == 401


def test_page_endpoint_revalidates_and_is_user_bound(client):
    from lims_chatbot.app.pagination import QueryPages
    from lims_chatbot.app.schema_catalog import SchemaCatalog, Table, Column

    class Provider:
        async def catalog(self):
            return SchemaCatalog(tables={"lab": Table("lab", None, [Column("id", "integer")])})

    class RowsDb:
        async def run_select(self, sql):
            assert "OFFSET 20" in sql
            return {"columns": ["id"], "rows": [{"id": i} for i in range(20, 41)]}

    client.app.state.pages = pages = QueryPages()
    client.app.state.schema_provider = Provider()
    client.app.state.db = RowsDb()
    client.app.state.settings.api_accounts = {"bob": "bob-password"}
    cursor = pages.add("SELECT id FROM lab ORDER BY id", ["id"], 20, AUTH[0])
    bad = client.post("/api/chat/page", json={"cursor": cursor}, auth=("bob", "bob-password"))
    assert bad.status_code == 404
    response = client.post("/api/chat/page", json={"cursor": cursor}, auth=AUTH)
    assert response.status_code == 200
    assert response.json()["row_count"] == 20 and response.json()["next_cursor"]


def test_api_error_hides_internal_details(client):
    async def failed(*args):
        return {"route": "database", "answer": "service error", "error": "password=canary; private host"}
    client.app.state.graph.run = failed
    response = client.post("/api/chat", json={"question": "x"}, auth=AUTH)
    assert response.status_code == 200
    assert response.json()["error"] == "request_failed" and "canary" not in response.text


# ---------------- javob tili ----------------
def test_lang_defaults_to_uz_and_is_passed(client):
    client.post("/api/chat", json={"question": "x"}, auth=AUTH)
    client.post("/api/chat", json={"question": "x", "lang": "ru"}, auth=AUTH)
    client.post("/api/chat/stream", json={"question": "x", "lang": "en"}, auth=AUTH)
    assert client.app.state.graph.langs == ["uz", "ru", "en"]


def test_unknown_lang_rejected(client):
    r = client.post("/api/chat", json={"question": "x", "lang": "de"}, auth=AUTH)
    assert r.status_code == 422
