"""LINE 署名検証 — gaku-co5.0 app/line/signature.py 相当(中立化)。

Webhook 本文の HMAC-SHA256 を channel secret で検証する。LINE 仕様であり
ベンダー(LLM)中立性とは独立。FastAPI には依存させず、raw body + signature +
secret だけ受け取る純関数にしておく(テスト可能・他フレームワークでも使える)。
"""
from __future__ import annotations

import base64
import hashlib
import hmac


def verify(body: bytes, signature: str, channel_secret: str) -> bool:
    """X-Line-Signature ヘッダと本文 HMAC を比較する。一致なら True。"""
    if not channel_secret or signature is None:
        return False
    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)
