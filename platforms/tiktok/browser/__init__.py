"""TikTok browser helpers."""

from platforms.tiktok.browser.captcha import is_visible, solve_if_visible
from platforms.tiktok.browser.comments import fetch_comments
from platforms.tiktok.browser.customtdk import fetch_customtdk

__all__ = ["fetch_comments", "fetch_customtdk", "is_visible", "solve_if_visible"]
