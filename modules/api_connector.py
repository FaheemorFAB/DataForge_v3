"""
API Connector
═════════════
Fetches data from REST APIs and converts the response to a pandas DataFrame.
Handles pagination, authentication headers, and rate limiting.

Usage::

    from modules.data_sources.api_connector import APIConnector

    # Generic REST API
    conn = APIConnector(
        base_url = "https://api.example.com",
        headers  = {"Authorization": "Bearer TOKEN"},
    )
    df = conn.fetch("/v1/orders", data_path="orders")

    # Paginated API
    df = conn.fetch_paginated(
        endpoint     = "/v1/transactions",
        page_param   = "page",
        page_size    = 100,
        data_path    = "data",
        max_pages    = 20,
    )

Pre-built shortcuts:

    conn.fetch_stripe_charges(api_key="sk_live_...")
    conn.fetch_shopify_orders(shop="mystore.myshopify.com", token="...")
"""

import logging
import time
from typing import Any, Callable, Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)


def _dig(data: Any, path: str | None) -> Any:
    """Traverse nested dict using dot-notation path, e.g. 'result.data.items'."""
    if not path:
        return data
    for key in path.split("."):
        if isinstance(data, dict):
            data = data.get(key, [])
        elif isinstance(data, list) and key.isdigit():
            data = data[int(key)]
        else:
            break
    return data


class APIConnector:

    def __init__(
        self,
        base_url: str = "",
        headers: dict | None = None,
        timeout: int = 30,
        rate_limit_delay: float = 0.2,   # seconds between requests
    ):
        self.base_url         = base_url.rstrip("/")
        self.headers          = headers or {}
        self.timeout          = timeout
        self.rate_limit_delay = rate_limit_delay
        self._session         = requests.Session()
        self._session.headers.update(self.headers)

    # ── Core fetch ────────────────────────────────────────────────────────────
    def fetch(
        self,
        endpoint:  str,
        params:    dict | None = None,
        data_path: str | None = None,
        method:    str = "GET",
    ) -> pd.DataFrame:
        """
        Fetch a single API endpoint and return a DataFrame.
        data_path: dot-notation path to the list in the JSON response.
        """
        url      = self.base_url + endpoint if not endpoint.startswith("http") else endpoint
        response = self._session.request(method, url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data   = response.json()
        subset = _dig(data, data_path)

        if isinstance(subset, list):
            df = pd.json_normalize(subset)
        elif isinstance(subset, dict):
            df = pd.DataFrame([subset])
        else:
            raise ValueError(f"Unexpected data type at path '{data_path}': {type(subset)}")

        log.info("APIConnector.fetch: %s → %d rows", url, len(df))
        return df

    # ── Paginated fetch ───────────────────────────────────────────────────────
    def fetch_paginated(
        self,
        endpoint:      str,
        data_path:     str | None = None,
        page_param:    str = "page",
        page_size:     int = 100,
        size_param:    str = "limit",
        start_page:    int = 1,
        max_pages:     int = 50,
        stop_if_empty: bool = True,
        extra_params:  dict | None = None,
    ) -> pd.DataFrame:
        """
        Automatically paginate through an API endpoint.
        Stops when an empty result is returned or max_pages is reached.
        """
        all_frames: list[pd.DataFrame] = []
        params = {page_param: start_page, size_param: page_size, **(extra_params or {})}

        for page_num in range(start_page, start_page + max_pages):
            params[page_param] = page_num
            try:
                df = self.fetch(endpoint, params=params, data_path=data_path)
            except Exception as exc:
                log.warning("APIConnector: page %d failed — %s. Stopping.", page_num, exc)
                break

            if df.empty and stop_if_empty:
                break

            all_frames.append(df)
            log.info("APIConnector: page %d — %d rows", page_num, len(df))

            if len(df) < page_size and stop_if_empty:
                break                     # last page

            time.sleep(self.rate_limit_delay)

        if not all_frames:
            return pd.DataFrame()

        return pd.concat(all_frames, ignore_index=True)

    # ── Pre-built shortcuts ───────────────────────────────────────────────────
    @classmethod
    def stripe(cls, api_key: str) -> "APIConnector":
        return cls(
            base_url = "https://api.stripe.com",
            headers  = {"Authorization": f"Bearer {api_key}"},
        )

    def fetch_stripe_charges(self, limit: int = 100) -> pd.DataFrame:
        """Fetch the latest Stripe charges as a DataFrame."""
        return self.fetch("/v1/charges", params={"limit": limit}, data_path="data")

    def fetch_stripe_subscriptions(self, limit: int = 100) -> pd.DataFrame:
        return self.fetch("/v1/subscriptions", params={"limit": limit}, data_path="data")

    @classmethod
    def shopify(cls, shop: str, access_token: str) -> "APIConnector":
        return cls(
            base_url = f"https://{shop}/admin/api/2024-01",
            headers  = {"X-Shopify-Access-Token": access_token},
        )

    def fetch_shopify_orders(self, limit: int = 250) -> pd.DataFrame:
        return self.fetch("/orders.json", params={"limit": limit, "status": "any"}, data_path="orders")

    def fetch_shopify_products(self, limit: int = 250) -> pd.DataFrame:
        return self.fetch("/products.json", params={"limit": limit}, data_path="products")

    # ── Webhook receiver setup ────────────────────────────────────────────────
    @staticmethod
    def build_webhook_handler(callback: Callable[[dict], None]):
        """
        Returns a Flask view function that accepts POST webhook events
        and calls callback(payload).

        Usage in app.py:
          from modules.data_sources.api_connector import APIConnector
          from modules.your_handler import handle_event

          app.add_url_rule(
              "/webhook/<source>",
              "webhook_receiver",
              APIConnector.build_webhook_handler(handle_event),
              methods=["POST"],
          )
        """
        from flask import request as flask_request, jsonify

        def webhook_view(source: str):
            payload = flask_request.get_json(force=True, silent=True) or {}
            payload["_source"] = source
            try:
                callback(payload)
            except Exception as exc:
                log.warning("Webhook handler error (%s): %s", source, exc)
            return jsonify({"received": True}), 200

        return webhook_view

    def close(self):
        self._session.close()
