"""Replicate client for image generation / editing / try-on / background ops.

`replicate` is imported lazily so the app runs (and the UI loads) without the
package installed or a token configured — calls only fail when actually invoked.
"""
from __future__ import annotations


class ReplicateError(RuntimeError):
    pass


class ReplicateClient:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self._client = None

    def _get(self):
        if not self.api_token:
            raise ReplicateError(
                "Replicate API token is not set (config.json -> replicate_api_token)."
            )
        if self._client is None:
            try:
                import replicate
            except ImportError as e:  # pragma: no cover
                raise ReplicateError(
                    "The 'replicate' package is not installed (pip install replicate)."
                ) from e
            self._client = replicate.Client(api_token=self.api_token)
        return self._client

    def run(self, model: str, inputs: dict):
        """Run a model, returning its raw output (often a list of URLs / FileOutput).

        `model` may be "owner/name" (latest version) or "owner/name:version".
        Per-model input keys differ; the service layer fills them and they may need
        tuning once tested against the real model schemas.
        """
        return self._get().run(model, input=inputs)
