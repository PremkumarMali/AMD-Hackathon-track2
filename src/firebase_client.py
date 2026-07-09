"""Optional Firestore history layer for caption runs.

After a clip is captioned, ``save_caption_run()`` stores the run's metadata and
the four generated captions in a Firestore collection (``caption_runs``) so the
project keeps a history of what it produced. This is a *best-effort* layer:

  * it is off unless ``FIREBASE_ENABLED=1`` **and** a service-account JSON exists
    at ``FIREBASE_CREDENTIALS_PATH``;
  * every function degrades quietly (returns ``False``) and NEVER raises, so the
    app keeps working exactly the same with Firebase disabled, misconfigured, or
    unreachable;
  * the Firebase SDK is imported lazily, so nothing here breaks if
    ``firebase-admin`` is not installed.

Security: the service-account file is git-ignored and never committed. This
module never prints or logs the credential contents, the private key, or the
saved record — only short, safe status lines.
"""

from __future__ import annotations

import os
import ssl
import sys
import tempfile
import threading

# Firestore collection that stores one document per caption run.
_COLLECTION = "caption_runs"

# The Firestore client is initialised once per process and cached. A failed
# init is remembered so we do not retry (and re-log) on every single save.
_init_lock = threading.Lock()
_client = None
_init_failed = False


def is_firebase_enabled() -> bool:
    """True only when Firebase is switched on *and* usable.

    Requires ``FIREBASE_ENABLED=1`` and an existing credentials file at
    ``FIREBASE_CREDENTIALS_PATH``. Reads config from the environment (loaded
    from ``.env`` by the caller). Does not import the Firebase SDK, so it is
    always safe and cheap to call.
    """
    if os.environ.get("FIREBASE_ENABLED", "0").strip() != "1":
        return False
    path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "").strip()
    return bool(path) and os.path.isfile(path)


def save_caption_run(record: dict) -> bool:
    """Save one caption run to the ``caption_runs`` collection.

    Returns ``True`` on a successful write, ``False`` otherwise — when Firebase
    is disabled, the credentials/SDK are missing, or any Firebase error occurs.
    Never raises: caption generation must keep working even if this fails.
    """
    if not is_firebase_enabled():
        return False
    client = _get_client()
    if client is None:
        return False
    try:
        doc = dict(record)  # shallow copy so we never mutate the caller's dict
        doc.setdefault("created_at", _server_timestamp())
        client.collection(_COLLECTION).add(doc)
        _log("saved caption run to Firestore")
        return True
    except Exception as exc:  # noqa: BLE001 - never crash the app for Firebase
        _log(f"save failed ({type(exc).__name__})")
        return False


def _get_client():
    """Initialise the Firebase Admin SDK once and cache the Firestore client.

    Returns the cached client, or ``None`` if initialisation is not possible
    (SDK missing, credentials missing, or any init error). Thread-safe and
    idempotent; a failure is remembered so we do not retry every call.
    """
    global _client, _init_failed
    if _client is not None:
        return _client
    if _init_failed:
        return None
    with _init_lock:
        if _client is not None:
            return _client
        if _init_failed:
            return None
        try:
            # In TLS-interception environments (corporate proxy / VPN / AV),
            # gRPC's own root store lacks the intercepting CA, so Firestore
            # handshakes fail even when `requests` works. Trust the OS roots.
            _ensure_grpc_ca_roots()

            import firebase_admin
            from firebase_admin import credentials, firestore

            path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "").strip()
            if not path or not os.path.isfile(path):
                _init_failed = True
                return None
            # Reuse an app if one already exists in this process; otherwise
            # create it from the service-account certificate.
            try:
                app = firebase_admin.get_app()
            except ValueError:
                cred = credentials.Certificate(path)
                app = firebase_admin.initialize_app(cred)
            _client = firestore.client(app)
            _log("Firestore client initialised")
            return _client
        except Exception as exc:  # noqa: BLE001 - degrade quietly, never crash
            _init_failed = True
            _log(f"init failed ({type(exc).__name__})")
            return None


def _ensure_grpc_ca_roots() -> None:
    """Best-effort: make gRPC trust the OS/VPN root CAs (Windows only).

    With TLS interception, gRPC's bundled roots don't include the intercepting
    CA, so Firestore fails with ``CERTIFICATE_VERIFY_FAILED`` — even though
    ``requests`` works (via pip-system-certs). We build a CA bundle of certifi's
    roots plus the Windows trust store and point ``GRPC_DEFAULT_SSL_ROOTS_FILE_PATH``
    at it. This only ADDS trusted roots; it never disables verification. No-op if
    the var is already set, if not on Windows, or on any error (the save then
    just degrades quietly). Must run before the first gRPC channel is created.
    """
    if os.environ.get("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"):
        return  # respect an explicit user/CI override
    if sys.platform != "win32" or not hasattr(ssl, "enum_certificates"):
        return  # only needed for the Windows trust store
    try:
        import certifi

        with open(certifi.where(), "r", encoding="utf-8") as fh:
            pem = fh.read()
        for store in ("ROOT", "CA"):
            try:
                for der, _enc, _trust in ssl.enum_certificates(store):
                    try:
                        pem += "\n" + ssl.DER_cert_to_PEM_cert(der)
                    except Exception:  # noqa: BLE001 - skip any unconvertible cert
                        pass
            except Exception:  # noqa: BLE001 - store may be unavailable
                pass
        bundle = os.path.join(tempfile.gettempdir(), "grpc_ca_bundle.pem")
        with open(bundle, "w", encoding="utf-8") as fh:
            fh.write(pem)
        os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = bundle
        _log("configured gRPC CA roots from system trust store")
    except Exception as exc:  # noqa: BLE001 - never block on this best-effort step
        _log(f"gRPC CA roots setup skipped ({type(exc).__name__})")


def _server_timestamp():
    """Firestore server-timestamp sentinel, or a UTC ISO string as a fallback."""
    try:
        from firebase_admin import firestore

        return firestore.SERVER_TIMESTAMP
    except Exception:  # noqa: BLE001
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def _log(message: str) -> None:
    """Emit a safe, prefixed debug line to stderr.

    Never includes the credential file contents, the private key, or the saved
    record — only short status text.
    """
    print(f"[firebase] {message}", file=sys.stderr, flush=True)
