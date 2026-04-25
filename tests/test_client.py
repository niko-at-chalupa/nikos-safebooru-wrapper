from marshal import load
import json
import os
import pytest
from dotenv import load_dotenv
from rule34.client import Client
from rule34.posts import Post

class DummyResponse:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

def pytest_addoption(parser):
    parser.addoption("--post-id", action="store", type=int, default=16290528)

@pytest.fixture
def client():
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    user_id = os.environ.get("USER_ID")
    if not api_key or not user_id:
        pytest.skip("API_KEY and USER_ID must be set")
    return Client(api_key=api_key, user_id=user_id)

@pytest.fixture
def dummy_client():
    return Client(api_key="x", user_id="y")

def test_post_from_json():
    post_dict = {
        "height": 100,
        "score": 10,
        "file_url": "",
        "parent_id": 0,
        "sample_url": "",
        "sample_width": 50,
        "sample_height": 50,
        "preview_url": "",
        "rating": "s",
        "tags": "tag1 tag2",
        "id": 123,
        "width": 100,
        "change": 0,
        "hash": "abc",
        "owner": "user",
        "status": "active",
        "source": "",
        "has_notes": False,
        "comment_count": 0,
        "tag_info": [],
    }
    p = Post.from_json(json.dumps(post_dict))
    assert p.post_id == 123
    assert p.tags == {"tag1", "tag2"}
    assert p.rating.name == "SAFE"

def test_get_with_retry_retries_on_429(monkeypatch, dummy_client):
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, stream=False):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResponse(status_code=429, headers={"Retry-After": "0"})
        return DummyResponse(status_code=200, content=b"[]")

    monkeypatch.setattr("rule34.client.requests.get", fake_get)
    resp = dummy_client._get_with_retry("https://api.rule34.xxx/index.php", params={})
    assert resp.status_code == 200
    assert calls["count"] == 2

def test_list_posts_empty(monkeypatch, dummy_client):
    def fake_get(url, params=None, headers=None, stream=False):
        return DummyResponse(status_code=200, content=b"")

    monkeypatch.setattr("rule34.client.requests.get", fake_get)
    assert dummy_client.list_posts(tags="test", limit=1) == []

def test_get_real_post(client):
    post = client.get_post(16290528)
    assert isinstance(post, Post)
    assert post.post_id == 16290528
    assert isinstance(post.tags, set)
    assert len(post.tags) > 0
    assert post.rating is not None
    assert post.file_url