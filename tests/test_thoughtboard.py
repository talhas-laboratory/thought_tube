import json
import shutil
import socket
import tempfile
import threading
import unittest
import urllib.request as urllib_request
from http.server import ThreadingHTTPServer
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.product_thoughtboard import (
    save_thoughtboard_card,
    load_thoughtboard_cards,
    delete_thoughtboard_card,
    ingest_pasted_conversation,
    build_thoughtboard_feed,
)
from conversation_os.thoughtboard_miniapp import make_thoughtboard_handler

REPO_ROOT = Path(__file__).resolve().parents[1]


class ThoughtboardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        
        # Copy required metadata and repository files
        for filename in [
            "TENETS.md",
            "AGENTS.md",
            "SESSION_PROTOCOL.md",
            "CONTEXT_ROUTING.md",
            "PRODUCT_THESIS.md",
            "pyproject.toml",
        ]:
            shutil.copy(REPO_ROOT / filename, self.root / filename)
            
        # Copy the product/thoughtboard_v1 folder so configuration files are present
        shutil.copytree(
            REPO_ROOT / "product" / "thoughtboard_v1",
            self.root / "product" / "thoughtboard_v1",
            dirs_exist_ok=True,
        )
        
        # Initialize conversation OS structure
        init_repo(self.root)
        
        # Start local miniapp server
        self.server, self.server_thread, self.base_url = self._start_server()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        self.tempdir.cleanup()

    def _start_server(self):
        handler = make_thoughtboard_handler(self.root)
        # Find a free port
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()
        
        server = ThreadingHTTPServer((host, port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, f"http://{host}:{port}"

    def _request(self, path: str, *, method: str = "GET", payload: dict | None = None, headers: dict | None = None):
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
            
        request = urllib_request.Request(
            url,
            data=data,
            method=method,
            headers=req_headers,
        )
        try:
            with urllib_request.urlopen(request) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return response.status, json.loads(body.decode("utf-8")), response.headers
                return response.status, body.decode("utf-8"), response.headers
        except urllib_request.HTTPError as e:
            body = e.read()
            content_type = e.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return e.code, json.loads(body.decode("utf-8")), e.headers
            return e.code, body.decode("utf-8"), e.headers

    def test_card_crud_operations(self) -> None:
        # 1. Create a card
        card_data = {
            "title": "A beautiful new insight",
            "summary": "This is a detailed summary of the insight.",
            "media_refs": ["https://example.com/image.png"],
            "tags": ["insight", "test"],
        }
        card = save_thoughtboard_card(self.root, card_data)
        self.assertIsNotNone(card.get("card_id"))
        self.assertEqual(card["title"], "A beautiful new insight")
        self.assertEqual(card["summary"], "This is a detailed summary of the insight.")
        self.assertEqual(card["media_refs"], ["https://example.com/image.png"])
        self.assertEqual(card["tags"], ["insight", "test"])
        
        card_id = card["card_id"]
        
        # 2. Load all cards and check it exists
        cards = load_thoughtboard_cards(self.root)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["card_id"], card_id)
        
        # 3. Delete the card
        success = delete_thoughtboard_card(self.root, card_id)
        self.assertTrue(success)
        
        # 4. Check loaded cards doesn't contain deleted card
        cards_after_delete = load_thoughtboard_cards(self.root)
        self.assertEqual(len(cards_after_delete), 0)

    def test_transcript_ingestion(self) -> None:
        transcript = (
            "user: What are the main tenets of a resilient UI?\n"
            "assistant: A resilient UI leverages native browser behaviors and graceful degradation."
        )
        result = ingest_pasted_conversation(self.root, "Resilient UI Tenets", transcript)
        self.assertIn("session_id", result)
        self.assertIn("card_id", result)
        
        # Check generated card contents
        card = result["card"]
        self.assertEqual(card["title"], "Resilient UI Tenets")
        self.assertIn("Discussing: What are the main tenets of a resilient UI?", card["summary"])
        self.assertIn("Synthesis: A resilient UI leverages native browser behaviors and graceful degradation.", card["summary"])
        self.assertEqual(card["tags"], ["chatbot-discussion"])
        self.assertTrue(card["source_ref"].startswith("session:import-thoughtboard"))

    def test_feed_building(self) -> None:
        # Create two related cards
        card_1 = save_thoughtboard_card(self.root, {
            "title": "First Insight",
            "summary": "Summary 1",
        })
        card_2 = save_thoughtboard_card(self.root, {
            "title": "Second Insight",
            "summary": "Summary 2",
            "relations": [card_1["card_id"]],
        })
        
        feed = build_thoughtboard_feed(self.root)
        self.assertIn("generated_at", feed)
        self.assertEqual(len(feed["cards"]), 2)
        
        # Check graph nodes and edges
        nodes = feed["graph"]["nodes"]
        edges = feed["graph"]["edges"]
        
        self.assertEqual(len(nodes), 2)
        node_ids = {n["id"] for n in nodes}
        self.assertIn(card_1["card_id"], node_ids)
        self.assertIn(card_2["card_id"], node_ids)
        
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["from"], card_2["card_id"])
        self.assertEqual(edges[0]["to"], card_1["card_id"])
        self.assertEqual(edges[0]["type"], "related")

    def test_api_feed_endpoint(self) -> None:
        # Create a card
        save_thoughtboard_card(self.root, {
            "title": "Feed Endpoint Card",
            "summary": "Testing endpoint",
        })
        
        # Test API
        status, data, headers = self._request("/api/thoughtboard/feed")
        self.assertEqual(status, 200)
        self.assertIn("cards", data)
        self.assertEqual(len(data["cards"]), 1)
        self.assertEqual(data["cards"][0]["title"], "Feed Endpoint Card")

    def test_api_embed_script_endpoint(self) -> None:
        status, content, headers = self._request("/thoughtboard/embed.js")
        self.assertEqual(status, 200)
        self.assertIn("application/javascript", headers.get("Content-Type", ""))
        self.assertIn("class ThoughtBoardElement extends HTMLElement", content)

    def test_api_card_crud_endpoints(self) -> None:
        # 1. Create a card via POST
        status, card, _ = self._request(
            "/api/thoughtboard/card",
            method="POST",
            payload={
                "title": "API Created Card",
                "summary": "API summary details",
            }
        )
        self.assertEqual(status, 200)
        card_id = card["card_id"]
        self.assertEqual(card["title"], "API Created Card")
        
        # 2. Verify it's in the feed
        status, feed, _ = self._request("/api/thoughtboard/feed")
        self.assertEqual(status, 200)
        self.assertEqual(feed["cards"][0]["card_id"], card_id)
        
        # 3. Delete it via DELETE
        status, delete_res, _ = self._request(
            f"/api/thoughtboard/card/{card_id}",
            method="DELETE",
        )
        self.assertEqual(status, 200)
        self.assertTrue(delete_res["success"])
        
        # 4. Verify it's removed from feed
        status, feed_after, _ = self._request("/api/thoughtboard/feed")
        self.assertEqual(status, 200)
        self.assertEqual(len(feed_after["cards"]), 0)

    def test_api_import_endpoint(self) -> None:
        status, import_res, _ = self._request(
            "/api/thoughtboard/import",
            method="POST",
            payload={
                "title": "API Import Conversation",
                "transcript": "user: Hello\nassistant: Hi there",
            }
        )
        self.assertEqual(status, 200)
        self.assertIn("session_id", import_res)
        self.assertIn("card_id", import_res)
        
        card = import_res["card"]
        self.assertEqual(card["title"], "API Import Conversation")
        self.assertIn("Discussing: Hello...", card["summary"])

    def test_api_not_found(self) -> None:
        status, data, _ = self._request("/api/thoughtboard/nonexistent")
        self.assertEqual(status, 404)
        self.assertEqual(data["error"], "not_found")

    def test_api_cors_preflight(self) -> None:
        status, content, headers = self._request(
            "/api/thoughtboard/feed",
            method="OPTIONS",
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("GET", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("POST", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("DELETE", headers.get("Access-Control-Allow-Methods", ""))


if __name__ == "__main__":
    unittest.main()
