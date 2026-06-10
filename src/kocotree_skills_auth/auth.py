"""飞书 OAuth 认证逻辑：token 换取、刷新、验证。"""

import secrets
import urllib.parse

import requests

from .config import settings

FEISHU_AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
FEISHU_USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"


def build_authorize_url(state=None):
    """构造飞书 OAuth 授权链接。"""
    if not state:
        state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.feishu_app_id,
        "redirect_uri": settings.feishu_redirect_uri,
        "response_type": "code",
        "state": state,
    }
    return f"{FEISHU_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}", state


def exchange_code_for_token(code):
    """用授权码换取 access_token + refresh_token。"""
    resp = requests.post(FEISHU_TOKEN_URL, json={
        "grant_type": "authorization_code",
        "client_id": settings.feishu_app_id,
        "client_secret": settings.feishu_app_secret,
        "code": code,
        "redirect_uri": settings.feishu_redirect_uri,
    }, timeout=10)
    data = resp.json()
    if resp.status_code != 200 or "access_token" not in data:
        return None, data.get("error_description", "Failed to exchange code")
    return data, None


def refresh_access_token(refresh_token):
    """用 refresh_token 刷新 access_token。"""
    resp = requests.post(FEISHU_TOKEN_URL, json={
        "grant_type": "refresh_token",
        "client_id": settings.feishu_app_id,
        "client_secret": settings.feishu_app_secret,
        "refresh_token": refresh_token,
    }, timeout=10)
    data = resp.json()
    if resp.status_code != 200 or "access_token" not in data:
        return None, data.get("error_description", "Failed to refresh token")
    return data, None


def verify_access_token(access_token):
    """调飞书用户信息 API 验证 token 有效性，返回用户信息或 None。"""
    resp = requests.get(FEISHU_USER_INFO_URL, headers={
        "Authorization": f"Bearer {access_token}",
    }, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("code") != 0:
        return None
    return data.get("data")
