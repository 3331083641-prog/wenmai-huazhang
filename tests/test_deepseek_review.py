"""Offline security and protocol tests for the Bailian review client."""
from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import requests

from backend.services.deepseek_review import ConfigurationError, ReviewClient, ReviewError


BASE = "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
KEY = "sk-offline-test-placeholder"


def verdict():
    return {
        "overallScore": 81,
        "dimensions": {name: 80 for name in ("fidelity", "layering", "occlusion", "motion", "interaction")},
        "passed": True,
        "issues": [{"severity": "minor", "code": "edge", "description": "边缘需要改善"}],
        "suggestedParameters": {"subjectRelief": 0.1},
        "summary": "保持原图风格，遮挡连续。",
    }


class Response:
    def __init__(self, content=None, status=200):
        self.status_code = status
        self.headers = {"x-request-id": "request-123"}
        self.payload = content if content is not None else {
            "choices": [{"message": {"content": json.dumps(verdict()), "reasoning_content": "DO NOT RETURN"}}],
            "usage": {"prompt_tokens": 240, "completion_tokens": 120, "total_tokens": 360},
            "model": "deepseek-v4.1-flash-1017",
            "id": "chatcmpl-123",
        }

    def json(self):
        return self.payload


class Session:
    def __init__(self, response=None, error=None):
        self.response = response or Response()
        self.error = error
        self.calls = []
        self.trust_env = True

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


class ReviewClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / "tests")
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / "frame.png"
        Image.new("RGBA", (2048, 1200), (120, 80, 200, 170)).save(self.image)
        self.images = [{"label": "原图与真实画境", "path": self.image}]

    def client(self, session=None, **kwargs):
        return ReviewClient(KEY, BASE, session=session or Session(), **kwargs)

    def test_official_default_root_and_v1_routes_use_official_thinking_parameter(self):
        for suffix in ("", "/", "/v1", "/v1/"):
            session = Session()
            response = session.response.payload
            response["model"] = "deepseek-flash"
            client = ReviewClient(KEY, "https://api.deepseek.com" + suffix, session=session)
            result = client.review({}, self.images)
            self.assertEqual(client.provider, "official")
            self.assertEqual(client.model, "deepseek-flash")
            expected_path = "/v1" if "v1" in suffix else ""
            self.assertEqual(session.calls[0][0], "https://api.deepseek.com" + expected_path + "/chat/completions")
            body = session.calls[0][1]["json"]
            self.assertEqual(body["thinking"], {"type": "disabled"})
            self.assertNotIn("enable_thinking", body)
            self.assertEqual(result["_model"], "deepseek-flash")
        client = ReviewClient(KEY)
        self.addCleanup(client.session.close)
        self.assertEqual(client.base_url, "https://api.deepseek.com")
        self.assertEqual(client.provider, "official")

    def test_explicit_provider_mismatch_rejected_before_transport(self):
        for base, provider in ((BASE, "official"), ("https://api.deepseek.com", "bailian"),
                               (BASE, "anything")):
            with self.subTest(base=base, provider=provider), self.assertRaises(ConfigurationError):
                ReviewClient(KEY, base, provider=provider)
        client = ReviewClient(KEY, BASE, provider="bailian")
        self.addCleanup(client.session.close)
        self.assertEqual(client.provider, "bailian")
        self.assertEqual(client.model, "deepseek-v4.1-flash-1017")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": KEY, "DEEPSEEK_BASE_URL": BASE,
                                     "DEEPSEEK_PROVIDER": "official"}, clear=True):
            with self.assertRaises(ConfigurationError):
                ReviewClient.from_env()

    def test_official_config_rejects_urls_in_key_and_unsupported_paths_or_models(self):
        for key in ("https://api.deepseek.com", "http://api.deepseek.com", "Bearer " + KEY):
            with self.subTest(key=key):
                with self.assertRaises(ConfigurationError) as caught:
                    ReviewClient(key)
                self.assertNotIn(key, str(caught.exception))
        for url in ("https://api.deepseek.com.evil.test", "http://api.deepseek.com",
                    "https://api.deepseek.com:444", "https://user@api.deepseek.com",
                    "https://api.deepseek.com/compatible-mode/v1", "https://api.deepseek.com/v1//",
                    "https://api.deepseek.com?key=" + KEY):
            with self.subTest(url=url), self.assertRaises(ConfigurationError):
                ReviewClient(KEY, url)
        for model in ("qwen3-vl", "deepseek-chat", "deepseek-v4-pro", "deepseek-not-a-model"):
            with self.subTest(model=model), self.assertRaises(ConfigurationError):
                ReviewClient(KEY, model=model)

    def test_env_official_configuration_and_defaults(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": KEY, "DEEPSEEK_PROVIDER": "official"}, clear=True):
            client = ReviewClient.from_env()
        self.addCleanup(client.session.close)
        self.assertEqual(client.base_url, "https://api.deepseek.com")
        self.assertEqual(client.model, "deepseek-flash")
        self.assertEqual(client.provider, "official")

    def test_env_configuration_and_budget(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": KEY, "DEEPSEEK_BASE_URL": BASE,
                                     "DEEPSEEK_MODEL": "deepseek-v4.1-flash-1017",
                                     "DEEPSEEK_MAX_REVIEW_CALLS": "2"}, clear=True):
            client = ReviewClient.from_env()
        self.assertEqual(client.max_calls, 2)
        self.assertEqual(client.max_tokens, 4096)
        self.assertEqual(client.timeout, 180)
        self.assertFalse(client.session.trust_env)

    def test_invalid_configuration_never_echoes_value(self):
        for url in ("http://dashscope.aliyuncs.com/compatible-mode/v1",
                    "https://dashscope.aliyuncs.com.evil.test/compatible-mode/v1",
                    "https://evilmaas.aliyuncs.com/compatible-mode/v1",
                    "https://user:password@dashscope.aliyuncs.com/compatible-mode/v1",
                    BASE + "?api_key=" + KEY, BASE + "#fragment", BASE + "/chat/completions",
                    BASE.replace(".com/", ".com:444/"), "https://localhost/compatible-mode/v1"):
            with self.subTest(url=url), self.assertRaises(ConfigurationError) as caught:
                ReviewClient(KEY, url)
            self.assertNotIn(KEY, str(caught.exception))
            self.assertNotIn(url, str(caught.exception))
        for params in ({"max_calls": 4}, {"max_calls": True}, {"max_tokens": 999999},
                       {"timeout": float("nan")}, {"model": "not-deepseek"}):
            with self.subTest(params=params), self.assertRaises(ConfigurationError):
                self.client(**params)
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ConfigurationError):
            ReviewClient.from_env()

    def test_exact_public_and_workspace_endpoints_allowed(self):
        for host in ("dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com", "dashscope-us.aliyuncs.com",
                     "workspace.ap-southeast-1.maas.aliyuncs.com"):
            with self.subTest(host=host):
                ReviewClient(KEY, "https://" + host + "/compatible-mode/v1/")

    def test_protocol_uses_real_compressed_images_and_json_no_tools(self):
        session = Session()
        client = self.client(session)
        result = client.review({"instructions": "按原五件精选检查保真与遮挡。"}, self.images)
        url, args = session.calls[0]
        self.assertEqual(url, BASE + "/chat/completions")
        self.assertFalse(args["allow_redirects"])
        self.assertEqual(args["timeout"], 180)
        self.assertEqual(args["headers"]["Authorization"], "Bearer " + KEY)
        body = args["json"]
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertFalse(body["enable_thinking"])
        self.assertEqual(body["max_tokens"], 4096)
        self.assertNotIn("tools", body)
        self.assertEqual(body["messages"][0]["role"], "system")
        content = body["messages"][1]["content"]
        self.assertIn("原五件精选", content[0]["text"])
        self.assertTrue(any("原图与真实画境" in part.get("text", "") for part in content))
        data = next(part["image_url"]["url"] for part in content if part["type"] == "image_url")
        prefix, encoded = data.split(",", 1)
        self.assertEqual(prefix, "data:image/jpeg;base64")
        with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (1024, 600))
        self.assertEqual(result["summary"], verdict()["summary"])
        self.assertEqual(result["_usage"]["total_tokens"], 360)
        self.assertEqual(result["_model"], "deepseek-v4.1-flash-1017")
        self.assertEqual(result["_requestId"], "request-123")
        self.assertNotIn("reasoning", json.dumps(result))

    def test_redirect_and_network_errors_are_sanitized_and_not_retried(self):
        for status in (301, 302, 307, 401, 429, 500):
            session = Session(Response({"error": {"message": KEY, "code": "evil-" + KEY}}, status))
            with self.subTest(status=status), self.assertRaises(ReviewError) as caught:
                self.client(session).review({}, self.images)
            self.assertIn(str(status), str(caught.exception))
            self.assertNotIn(KEY, str(caught.exception))
            self.assertEqual(len(session.calls), 1)
        session = Session(error=requests.Timeout(KEY + " Authorization secret " + BASE))
        with self.assertRaises(ReviewError) as caught:
            self.client(session).review({}, self.images)
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn(BASE, str(caught.exception))
        self.assertEqual(len(session.calls), 1)

    def test_failed_request_counts_toward_hard_budget(self):
        session = Session(Response(status=429))
        client = self.client(session, max_calls=2)
        for _ in range(3):
            with self.assertRaises(ReviewError):
                client.review({}, self.images)
        self.assertEqual(client.call_count, 2)
        self.assertEqual(len(session.calls), 2)

    def test_response_schema_rejects_bad_types_nonfinite_and_unbounded_values(self):
        changes = [
            {"overallScore": True}, {"overallScore": float("nan")}, {"overallScore": 101},
            {"dimensions": {**verdict()["dimensions"], "motion": "90"}},
            {"passed": 1}, {"summary": "x" * 4001},
            {"issues": [{"severity": "critical", "code": "x", "description": "x"}]},
            {"suggestedParameters": {"relief": float("inf")}}, {"suggestedParameters": []},
        ]
        for change in changes:
            candidate = {**verdict(), **change}
            response = Response()
            response.payload["choices"][0]["message"]["content"] = json.dumps(candidate)
            with self.subTest(fields=list(change)), self.assertRaises(ReviewError):
                self.client(Session(response)).review({}, self.images)

    def test_invalid_json_or_envelope_never_exposes_raw_content(self):
        for payload in ({}, {"choices": []}, {"choices": [{"message": {"content": "bad " + KEY}}]},
                        {"choices": [{"message": {"content": json.dumps({"summary": KEY})}}]}):
            with self.subTest(), self.assertRaises(ReviewError) as caught:
                self.client(Session(Response(payload))).review({}, self.images)
            self.assertNotIn(KEY, str(caught.exception))

    def test_model_parameter_keys_are_not_policy_filtered_here(self):
        response = Response()
        candidate = verdict()
        candidate["suggestedParameters"] = {"unknownPolicyKey": 123}
        response.payload["choices"][0]["message"]["content"] = json.dumps(candidate)
        self.assertEqual(self.client(Session(response)).review({}, self.images)["suggestedParameters"],
                         {"unknownPolicyKey": 123})

    def test_usage_whitelisted_and_accumulates_without_provider_text(self):
        response = Response()
        response.payload["usage"]["secret"] = KEY
        response.payload["usage"]["completion_tokens_details"] = {"reasoning_tokens": 20, "secret": KEY}
        client = self.client(Session(response))
        first = client.review({}, self.images)
        client.review({}, self.images)
        self.assertNotIn(KEY, json.dumps(first))
        self.assertEqual(client.usage["total_tokens"], 720)

    def test_invalid_input_does_not_spend_budget(self):
        session = Session()
        client = self.client(session)
        for context, images in (({"bad": float("nan")}, self.images), ({"key": KEY}, self.images),
                                ({}, []), ({}, [{"label": "x", "path": self.image.with_name("missing.png")}])):
            with self.subTest(), self.assertRaises(ReviewError) as caught:
                client.review(context, images)
            self.assertNotIn(KEY, str(caught.exception))
        self.assertEqual(client.call_count, 0)
        self.assertEqual(session.calls, [])

    def test_response_metadata_and_decoded_json_cannot_echo_authentication(self):
        response = Response()
        response.payload["model"] = "deepseek-" + KEY
        result = self.client(Session(response)).review({}, self.images)
        self.assertNotIn(KEY, json.dumps(result))
        response = Response()
        candidate = verdict()
        candidate["summary"] = KEY
        response.payload["choices"][0]["message"]["content"] = json.dumps(candidate).replace("sk-offline", "\\u0073k-offline")
        with self.assertRaises(ReviewError) as caught:
            self.client(Session(response)).review({}, self.images)
        self.assertNotIn(KEY, str(caught.exception))

    def test_default_transport_does_not_install_retry_policy(self):
        client = ReviewClient(KEY, BASE)
        self.addCleanup(client.session.close)
        self.assertEqual(client.session.get_adapter(BASE).max_retries.total, 0)


if __name__ == "__main__":
    unittest.main()
