"""Camoufox browser manager with humanize (bezier curve) and Chinese locale support.

Uses Camoufox's native Python API (Camoufox context manager / NewBrowser)
instead of low-level launch_options + raw Playwright, so that locale, fonts,
fingerprint, and humanize are all handled correctly at C++ level.

CLI usage:
    python scripts/browser.py open https://www.xiaohongshu.com
    python scripts/browser.py open https://www.xiaohongshu.com --screenshot /tmp/shot.png
    python scripts/browser.py open https://www.xiaohongshu.com --wait 10 --screenshot /tmp/shot.png
    python scripts/browser.py open https://www.xiaohongshu.com --interactive

Auth priority: persistent profile session > .env XHS_COOKIE > QR code login.
"""

from __future__ import annotations

import platform
import sys
import time
from pathlib import Path
from typing import Any, Optional, Union

from playwright.sync_api import Browser, BrowserContext, Page, PlaywrightContextManager

from camoufox.sync_api import Camoufox, NewBrowser


DEFAULT_PROFILES_DIR = Path.home() / ".xhs-skill" / "profiles"


def load_env(env_path: Optional[Path] = None) -> dict:
    """Load .env file, searching upward from cwd if no path given."""
    if env_path and env_path.exists():
        return _parse_env(env_path)
    current = Path.cwd()
    while current.parent != current:
        candidate = current / ".env"
        if candidate.exists():
            return _parse_env(candidate)
        if any((current / m).exists() for m in [".git", "SKILL.md"]):
            return _parse_env(candidate)
        current = current.parent
    return {}


def _parse_env(path: Path) -> dict:
    """Parse a .env file into a dict, handling quoted values."""
    env_vars = {}
    if not path.exists():
        return env_vars
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            env_vars[key.strip()] = value
    return env_vars


class BrowserManager:
    """Manages Camoufox browser lifecycle with persistent profiles.

    Key design choices:
    - Uses Camoufox's high-level API which properly configures locale through
      the C++ engine (navigator.language, Accept-Language, Intl API).
    - Persistent context stores cookies/localStorage per hotel+platform combo.
    - humanize=True enables bezier-curve mouse movement at C++ level.
    """

    KNOWN_DOMAINS = ("xiaohongshu.com", "rednote.com")

    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        headless: bool = False,
        humanize: bool = True,
        locale: str = "zh-CN",
        os_target: Optional[Union[str, list[str]]] = None,
        window: Optional[tuple[int, int]] = None,
        xhs_domain: str = "xiaohongshu.com",
    ):
        self.profile_dir = profile_dir
        self.headless = headless
        self.humanize = humanize
        self.locale = locale
        self.os_target = os_target or self._detect_os()
        self.window = window
        self.xhs_domain = xhs_domain
        self.xhs_home = f"https://www.{xhs_domain}"
        self._camoufox_cm: Optional[PlaywrightContextManager] = None
        self._browser_or_ctx: Optional[Union[Browser, BrowserContext]] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @staticmethod
    def _detect_os() -> str:
        """Match Camoufox fingerprint OS to the actual host so fonts resolve correctly."""
        system = platform.system()
        if system == "Darwin":
            return "macos"
        if system == "Windows":
            return "windows"
        return "linux"

    def _build_launch_kwargs(self) -> dict[str, Any]:
        """Build kwargs for Camoufox / NewBrowser."""
        kwargs: dict[str, Any] = {
            "headless": self.headless,
            "humanize": self.humanize,
            "locale": self.locale,
            "os": self.os_target,
        }
        if self.window:
            kwargs["window"] = self.window
        if self.profile_dir:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            kwargs["persistent_context"] = True
            kwargs["user_data_dir"] = str(self.profile_dir)
        return kwargs

    def launch(self) -> Page:
        """Launch browser and return the active page."""
        if self._page is not None:
            return self._page

        kwargs = self._build_launch_kwargs()

        self._camoufox_cm = Camoufox(**kwargs)
        self._browser_or_ctx = self._camoufox_cm.__enter__()

        if self.profile_dir:
            self._context = self._browser_or_ctx  # type: ignore[assignment]
            pages = self._context.pages
            self._page = pages[0] if pages else self._context.new_page()
        else:
            browser: Browser = self._browser_or_ctx  # type: ignore[assignment]
            self._context = browser.new_context()
            self._page = self._context.new_page()

        return self._page

    def launch_with_auth(self, fallback_cookie: str = "") -> Page:
        """Launch browser and authenticate using profile-first strategy.

        Priority: profile session > fallback_cookie (.env) > raise error.
        Designed for AI agent code generation — single call handles all auth.

        Args:
            fallback_cookie: raw cookie string to try if profile session is invalid.
                Typically from .env XHS_COOKIE. Only imported when profile fails.

        Returns:
            Authenticated page ready for navigation.

        Raises:
            RuntimeError: if all auth methods fail (needs QR login).
        """
        self.launch()

        if self.check_login():
            print("✅ Profile session valid")
            return self._page

        if fallback_cookie:
            print("⚠️  Profile session invalid, trying fallback cookie...")
            self.import_cookies(fallback_cookie)
            if self.check_login():
                print("✅ Fallback cookie valid")
                return self._page

        raise RuntimeError(
            "Login required: run `python scripts/browser.py login` to scan QR code. "
            "Session will persist in profile for future use."
        )

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to URL and wait for load."""
        self.page.goto(url, wait_until=wait_until)

    def screenshot(self, path: str) -> str:
        """Take screenshot and return the file path."""
        self.page.screenshot(path=path)
        return path

    def import_cookies(self, cookie_str: str, domain: Optional[str] = None) -> int:
        """Import cookies from a raw "name=value; name2=value2" string.

        Uses dot-domain for broad subdomain coverage (e.g. ".xiaohongshu.com").
        Deduplicates by name to avoid double entries.

        Returns the number of cookies imported.
        """
        if self._context is None:
            raise RuntimeError("Browser not launched. Call launch() first.")

        count = 0
        effective_domain = domain or self.xhs_domain
        dot_domain = effective_domain if effective_domain.startswith(".") else f".{effective_domain}"

        for pair in cookie_str.split("; "):
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            name, value = name.strip(), value.strip()
            if not name:
                continue
            self._context.add_cookies([{
                "name": name,
                "value": value,
                "domain": dot_domain,
                "path": "/",
            }])
            count += 1

        return count

    def check_login(self, url: Optional[str] = None, navigate: bool = True) -> bool:
        """Check if the current session is logged in.

        Args:
            url: URL to navigate to for checking (defaults to self.xhs_home).
            navigate: If False, check on the current page without navigating.
        Returns True if logged in, False otherwise.
        """
        if navigate:
            self.navigate(url or self.xhs_home)
            time.sleep(3)

        try:
            login_btn = self.page.locator('text="登录"').first
            if login_btn.is_visible(timeout=2000):
                return False
        except Exception:
            pass

        try:
            login_btn_en = self.page.locator('text="Log in"').first
            if login_btn_en.is_visible(timeout=1000):
                return False
        except Exception:
            pass

        try:
            user_avatar = self.page.locator('[class*="avatar"], [class*="user-icon"], [class*="sidebar-avatar"], [class*="profile"]').first
            if user_avatar.is_visible(timeout=2000):
                return True
        except Exception:
            pass

        title = self.page.title().lower()
        if "登录" in title or "login" in title:
            return False

        return True

    def screenshot_qrcode(self, save_path: str = "/tmp/xhs-qrcode.png") -> Optional[str]:
        """Navigate to login page, trigger QR code display, and screenshot it.

        Returns the screenshot file path, or None if QR code not found.
        """
        self.navigate(self.xhs_home)
        time.sleep(2)

        for label in ['"登录"', '"Log in"', '"Sign in"']:
            try:
                login_btn = self.page.locator(f'text={label}').first
                if login_btn.is_visible(timeout=2000):
                    login_btn.click()
                    time.sleep(2)
                    break
            except Exception:
                continue

        try:
            qr_selectors = [
                '[class*="qrcode"]',
                '[class*="qr-code"]',
                '[class*="login-qr"]',
                'canvas',
                '[class*="code-container"]',
                '[class*="login"] img',
            ]

            for selector in qr_selectors:
                try:
                    qr_el = self.page.locator(selector).first
                    if qr_el.is_visible(timeout=2000):
                        qr_el.screenshot(path=save_path)
                        return save_path
                except Exception:
                    continue

            self.page.screenshot(path=save_path)
            return save_path

        except Exception as e:
            print(f"⚠️  QR code screenshot failed: {e}")
            self.page.screenshot(path=save_path)
            return save_path

    def wait_for_login(self, timeout: int = 120, poll_interval: int = 3) -> bool:
        """Wait for user to scan QR code, page redirect to homepage, and confirm logged-in state.

        Flow: QR scanned → page redirects to homepage → detect logged-in avatar → return True.
        Does NOT return early; waits for the full redirect + login confirmation.
        """
        elapsed = 0
        scan_detected = False

        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval

            current_url = self.page.url
            page_title = self.page.title()

            if not scan_detected:
                has_login_btn = False
                for label in ['"登录"', '"Log in"', '"Sign in"']:
                    try:
                        btn = self.page.locator(f'text={label}').first
                        if btn.is_visible(timeout=500):
                            has_login_btn = True
                            break
                    except Exception:
                        continue
                if not has_login_btn:
                    scan_detected = True
                    print("🔄 QR scan detected, waiting for page redirect to homepage...")

            if scan_detected:
                is_homepage = (self.xhs_domain in current_url) and ("/explore" in current_url or current_url.rstrip("/").endswith(self.xhs_domain))
                if is_homepage:
                    try:
                        avatar = self.page.locator('[class*="avatar"], [class*="user-icon"], [class*="sidebar-avatar"]').first
                        if avatar.is_visible(timeout=3000):
                            print("✅ Homepage loaded, user avatar visible — login confirmed!")
                            time.sleep(2)
                            return True
                    except Exception:
                        pass

                    has_login_btn = False
                    for label in ['"登录"', '"Log in"', '"Sign in"']:
                        try:
                            btn = self.page.locator(f'text={label}').first
                            if btn.is_visible(timeout=500):
                                has_login_btn = True
                                break
                        except Exception:
                            continue

                    if not has_login_btn:
                        print("✅ Homepage loaded, no login button — login confirmed!")
                        time.sleep(2)
                        return True

            if elapsed % 15 == 0:
                status = "waiting for homepage redirect..." if scan_detected else "waiting for QR scan..."
                print(f"⏳ {status} ({elapsed}s / {timeout}s)")

        return False

    def evaluate(self, expression: str) -> Any:
        """Execute JavaScript expression on the current page and return the result.

        Args:
            expression: JavaScript code to evaluate (can be a function or expression).

        Returns:
            The return value of the JS expression (serialized as Python object).
        """
        return self.page.evaluate(expression)

    def _dismiss_login_popup(self) -> None:
        """Dismiss login popup/modal if it appears (common after cookie injection)."""
        close_selectors = [
            '[class*="close-button"]',
            '[class*="login-modal"] [class*="close"]',
            '[class*="modal"] [class*="close"]',
            'div[class*="mask"]',
        ]
        for selector in close_selectors:
            try:
                el = self.page.locator(selector).first
                if el.is_visible(timeout=1000):
                    el.click()
                    time.sleep(1)
                    return
            except Exception:
                continue

        try:
            self.page.keyboard.press("Escape")
            time.sleep(1)
        except Exception:
            pass

    def scrape_note(self, url: str) -> dict:
        """Open a XiaoHongShu note URL and extract structured content.

        Returns a dict with: title, content, cover_url, images, tags, likes,
        collects, comments, author, author_id.
        """
        self.navigate(url, wait_until="networkidle")
        time.sleep(3)

        self._dismiss_login_popup()

        try:
            login_overlay = self.page.locator('[class*="login"], [class*="mask"]').first
            if login_overlay.is_visible(timeout=1000):
                self.page.reload(wait_until="networkidle")
                time.sleep(3)
                self._dismiss_login_popup()
        except Exception:
            pass

        result: dict[str, Any] = {
            "url": url,
            "title": "",
            "content": "",
            "cover_url": "",
            "images": [],
            "tags": [],
            "likes": "",
            "collects": "",
            "comments": "",
            "author": "",
            "author_id": "",
        }

        try:
            title_el = self.page.locator('#detail-title, [class*="title"][class*="note"]').first
            if title_el.is_visible(timeout=3000):
                result["title"] = title_el.inner_text().strip()
        except Exception:
            pass

        try:
            content_el = self.page.locator('#detail-desc, [class*="desc"], [class*="note-text"]').first
            if content_el.is_visible(timeout=3000):
                result["content"] = content_el.inner_text().strip()
        except Exception:
            pass

        try:
            images = self.page.evaluate("""
                () => {
                    const imgs = document.querySelectorAll(
                        '.swiper-slide:not(.swiper-slide-duplicate) .img-container img, ' +
                        '[class*="note-image"] img, ' +
                        '[class*="carousel"] img'
                    );
                    return Array.from(imgs).map(img => img.currentSrc || img.src).filter(Boolean);
                }
            """)
            result["images"] = images or []
            if images:
                result["cover_url"] = images[0]
        except Exception:
            pass

        if not result["images"]:
            try:
                active_img = self.page.evaluate("""
                    () => {
                        const el = document.querySelector(
                            '.swiper-slide-active:not(.swiper-slide-duplicate) .img-container img'
                        );
                        return el ? (el.currentSrc || el.src) : null;
                    }
                """)
                if active_img:
                    result["images"] = [active_img]
                    result["cover_url"] = active_img
            except Exception:
                pass

        try:
            tags = self.page.evaluate("""
                () => {
                    const els = document.querySelectorAll('[class*="tag"], a[href*="/search_result/"]');
                    return Array.from(els).map(el => el.textContent.trim()).filter(t => t.startsWith('#'));
                }
            """)
            result["tags"] = tags or []
        except Exception:
            pass

        try:
            like_el = self.page.locator('[class*="like"] [class*="count"], [class*="like-wrapper"] span').first
            if like_el.is_visible(timeout=2000):
                result["likes"] = like_el.inner_text().strip()
        except Exception:
            pass

        try:
            collect_el = self.page.locator('[class*="collect"] [class*="count"], [class*="collect-wrapper"] span').first
            if collect_el.is_visible(timeout=2000):
                result["collects"] = collect_el.inner_text().strip()
        except Exception:
            pass

        try:
            comment_el = self.page.locator('[class*="chat"] [class*="count"], [class*="comment-wrapper"] span').first
            if comment_el.is_visible(timeout=2000):
                result["comments"] = comment_el.inner_text().strip()
        except Exception:
            pass

        try:
            author_el = self.page.locator('[class*="author"] [class*="name"], [class*="user-name"]').first
            if author_el.is_visible(timeout=2000):
                result["author"] = author_el.inner_text().strip()
        except Exception:
            pass

        try:
            author_link = self.page.evaluate("""
                () => {
                    const el = document.querySelector('a[href*="/user/profile/"]');
                    if (!el) return '';
                    const match = el.href.match(/profile\\/([^?]+)/);
                    return match ? match[1] : '';
                }
            """)
            result["author_id"] = author_link or ""
        except Exception:
            pass

        return result

    def download_image(self, url: str, save_path: str) -> Optional[str]:
        """Download an image from URL using the browser context (inherits cookies/session).

        Returns the save path on success, None on failure.
        """
        try:
            response = self.page.evaluate("""
                async (url) => {
                    const resp = await fetch(url);
                    const blob = await resp.blob();
                    const reader = new FileReader();
                    return new Promise((resolve) => {
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }
            """, url)
            if response and "," in response:
                import base64
                data = response.split(",", 1)[1]
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(data))
                return save_path
        except Exception as e:
            print(f"⚠️  Image download failed: {e}")

        return None

    def export_cookies(self, domain: Optional[str] = None) -> str:
        """Export current browser cookies for a domain as a semicolon-separated string.

        Uses document.cookie from the page (the actual cookie string browsers send),
        supplemented by httpOnly cookies from the context API (document.cookie
        cannot access httpOnly cookies).

        Primary use: diagnostics and optional .env backup. Profile persistence
        is the preferred auth mechanism.
        """
        if self._context is None:
            raise RuntimeError("Browser not launched. Call launch() first.")

        effective_domain = domain or self.xhs_domain

        doc_cookie = ""
        try:
            doc_cookie = self.page.evaluate("document.cookie") or ""
        except Exception:
            pass

        seen_names: set[str] = set()
        parts: list[str] = []

        if doc_cookie:
            for pair in doc_cookie.split("; "):
                if "=" not in pair:
                    continue
                name = pair.split("=", 1)[0].strip()
                if name and name not in seen_names:
                    seen_names.add(name)
                    parts.append(pair.strip())

        context_cookies = self._context.cookies()
        for c in context_cookies:
            if effective_domain not in c.get("domain", ""):
                continue
            name = c.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                parts.append(f"{name}={c['value']}")

        return "; ".join(parts)

    def close(self) -> None:
        """Close browser and cleanup."""
        if self._camoufox_cm:
            try:
                self._camoufox_cm.__exit__(None, None, None)
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser_or_ctx = None
        self._camoufox_cm = None

    def __enter__(self) -> "BrowserManager":
        self.launch()
        return self

    def __exit__(self, *args) -> None:
        self.close()


def main():
    """CLI entry point for browser operations."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Camoufox anti-fingerprint browser for xhs-skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Auth priority: profile session > .env XHS_COOKIE > QR login.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Browser command")

    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument("--headless", action="store_true", help="Run headless")
    common_args.add_argument("--profile", type=str, default=None, help="Profile name (default: xhs-default)")
    common_args.add_argument("--env", type=str, default=None, help="Path to .env file")

    open_parser = subparsers.add_parser("open", parents=[common_args], help="Open URL in Camoufox")
    open_parser.add_argument("url", help="URL to navigate to")
    open_parser.add_argument("--screenshot", type=str, help="Save screenshot to path")
    open_parser.add_argument("--wait", type=int, default=3, help="Wait seconds after page load (default: 3)")
    open_parser.add_argument("--interactive", action="store_true", help="Keep browser open until Enter is pressed")

    login_parser = subparsers.add_parser("login", parents=[common_args], help="Login to XHS via QR code")
    login_parser.add_argument("--qr-path", type=str, default="/tmp/xhs-qrcode.png", help="Save QR code screenshot to path")
    login_parser.add_argument("--timeout", type=int, default=120, help="Login timeout in seconds (default: 120)")
    login_parser.add_argument("--save-cookie", action="store_true", help="Save cookies to .env after login")

    check_parser = subparsers.add_parser("check", parents=[common_args], help="Check XHS login status")

    scrape_parser = subparsers.add_parser("scrape", parents=[common_args], help="Scrape XHS note content")
    scrape_parser.add_argument("url", help="XHS note URL to scrape")
    scrape_parser.add_argument("--screenshot", type=str, help="Save page screenshot to path")
    scrape_parser.add_argument("--download-cover", type=str, help="Download cover image to path")

    eval_parser = subparsers.add_parser("evaluate", parents=[common_args], help="Execute JS on a page")
    eval_parser.add_argument("url", help="URL to navigate to before evaluating")
    eval_parser.add_argument("--js", type=str, required=True, help="JavaScript expression to evaluate")
    eval_parser.add_argument("--wait", type=int, default=3, help="Wait seconds after page load (default: 3)")

    publish_parser = subparsers.add_parser("publish", parents=[common_args], help="Publish image-text note to XHS")
    publish_parser.add_argument("--cover", type=str, required=True, help="Cover image path (local file)")
    publish_parser.add_argument("--title", type=str, required=True, help="Note title (<=20 chars recommended)")
    publish_parser.add_argument("--body", type=str, required=True, help="Note body text (use \\n for newlines)")
    publish_parser.add_argument("--dry-run", action="store_true", help="Fill content but stop before clicking publish")

    reset_parser = subparsers.add_parser("reset", help="Reset browser profile (clear cookies/session)")
    reset_parser.add_argument("--profile", type=str, default=None, help="Profile name to reset (default: xhs-default)")
    reset_parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "reset":
        import shutil
        profile_name = args.profile or "xhs-default"
        profile_dir = DEFAULT_PROFILES_DIR / profile_name

        if not profile_dir.exists():
            print(f"ℹ️  Profile '{profile_name}' does not exist at {profile_dir}")
            sys.exit(0)

        size_mb = sum(f.stat().st_size for f in profile_dir.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"🗂️  Profile: {profile_dir}")
        print(f"📦 Size: {size_mb:.1f} MB")

        if not args.confirm:
            answer = input("⚠️  Delete this profile? All cookies/session will be lost. [y/N] ")
            if answer.lower() != "y":
                print("❌ Cancelled")
                sys.exit(0)

        shutil.rmtree(profile_dir)
        print(f"✅ Profile '{profile_name}' deleted. Next launch will create a fresh profile.")
        sys.exit(0)

    env_vars = load_env(Path(args.env) if args.env else None)
    xhs_cookie = env_vars.get("XHS_COOKIE", "")
    xhs_domain = env_vars.get("XHS_DOMAIN", "").strip() or "xiaohongshu.com"
    if xhs_domain not in BrowserManager.KNOWN_DOMAINS:
        print(f"⚠️  XHS_DOMAIN='{xhs_domain}' not recognized, expected one of {BrowserManager.KNOWN_DOMAINS}")

    profile_name = args.profile or "xhs-default"
    profile_dir = DEFAULT_PROFILES_DIR / profile_name

    bm = BrowserManager(
        profile_dir=profile_dir,
        headless=args.headless,
        humanize=True,
        xhs_domain=xhs_domain,
    )

    try:
        bm.launch()
        print(f"✅ Camoufox launched (profile: {profile_name})")

        _needs_cookie_import = True

        if args.command in ("open", "check", "login", "scrape", "evaluate"):
            print("🔍 Checking profile session...")
            if bm.check_login():
                print("✅ Profile session valid, skipping .env cookie import")
                _needs_cookie_import = False
            else:
                print("⚠️  Profile session invalid, falling back to .env cookie")

        if _needs_cookie_import and xhs_cookie:
            count = bm.import_cookies(xhs_cookie)
            print(f"🍪 Imported {count} cookies from .env (domain: {xhs_domain})")
        elif _needs_cookie_import and not xhs_cookie:
            print("⚠️  No XHS_COOKIE in .env and profile session invalid")

        if args.command == "open":
            print(f"🌐 Navigating to {args.url}")
            bm.navigate(args.url)
            print(f"📄 Page title: {bm.page.title()}")

            if args.wait > 0:
                time.sleep(args.wait)

            if args.screenshot:
                bm.screenshot(args.screenshot)
                print(f"📸 Screenshot saved: {args.screenshot}")

            if args.interactive:
                print("🎮 Interactive mode. Press Enter to close browser...")
                input()
            else:
                print("✅ Done")

        elif args.command == "check":
            print("🔍 Checking login status...")
            logged_in = bm.check_login()
            if logged_in:
                print("✅ Login status: LOGGED IN")
            else:
                print("❌ Login status: NOT LOGGED IN")
                print("   Run: python scripts/browser.py login")
            sys.exit(0 if logged_in else 1)

        elif args.command == "login":
            print("🔍 Checking current login status...")
            logged_in = bm.check_login()

            if logged_in:
                print("✅ Already logged in, no action needed.")
            else:
                print("❌ Not logged in. Getting QR code...")
                qr_path = bm.screenshot_qrcode(args.qr_path)
                if qr_path:
                    print(f"📱 QR code screenshot saved: {qr_path}")
                    print("   Please scan the QR code with your XiaoHongShu app.")
                    print(f"⏳ Waiting for login (timeout: {args.timeout}s)...")

                    success = bm.wait_for_login(timeout=args.timeout)
                    if not success:
                        print(f"⏰ Login timed out after {args.timeout}s")
                        print("   Please try again: python scripts/browser.py login")
                        sys.exit(1)

                    print("✅ QR scan detected! Verifying login state...")
                    verified = bm.check_login(navigate=False)
                    if not verified:
                        print("⚠️  Login state not confirmed, skipping cookie export.")
                        print("   Tip: manually copy cookies from Chrome F12 → paste into .env")
                        sys.exit(1)

                    print("✅ Login verified!")
                    print(f"📂 Session persisted in profile: {profile_dir}")
                    cookie_str = bm.export_cookies()
                    cookie_names = [p.split("=", 1)[0].strip() for p in cookie_str.split("; ") if "=" in p]
                    print(f"🍪 Exported {len(cookie_names)} cookies: {cookie_names}")

                    if "web_session" not in cookie_names:
                        print("⚠️  Warning: missing 'web_session', cookies may not work cross-session")

                    if args.save_cookie:
                        _save_cookie_to_env(cookie_str)
                        print("💾 Cookies also saved to .env (XHS_COOKIE) as backup")
                    else:
                        print("   Profile session is auto-saved. Use --save-cookie to also backup to .env")

        elif args.command == "scrape":
            import json
            print(f"🔍 Scraping note: {args.url}")
            note_data = bm.scrape_note(args.url)

            if args.screenshot:
                bm.screenshot(args.screenshot)
                print(f"📸 Screenshot saved: {args.screenshot}")

            if args.download_cover and note_data.get("cover_url"):
                dl_path = bm.download_image(note_data["cover_url"], args.download_cover)
                if dl_path:
                    print(f"🖼️  Cover downloaded: {dl_path}")
                    note_data["cover_local_path"] = dl_path

            print(json.dumps(note_data, ensure_ascii=False, indent=2))

        elif args.command == "evaluate":
            import json
            print(f"🌐 Navigating to {args.url}")
            bm.navigate(args.url)

            if args.wait > 0:
                time.sleep(args.wait)

            print(f"⚡ Evaluating JS...")
            result = bm.evaluate(args.js)
            if isinstance(result, (dict, list)):
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(result)

        elif args.command == "publish":
            cover_path = Path(args.cover).expanduser().resolve()
            if not cover_path.exists():
                print(f"❌ Cover image not found: {cover_path}")
                sys.exit(1)

            title = args.title
            body_lines = args.body.replace("\\n", "\n").split("\n")

            print(f"📝 Publishing note: {title[:30]}...")
            print(f"🖼️  Cover: {cover_path}")

            page = bm.page
            bm.navigate(
                "https://creator.xiaohongshu.com/publish/publish?source=official",
                wait_until="networkidle",
            )
            time.sleep(5)

            page.evaluate("""() => {
                for (const t of document.querySelectorAll('span')) {
                    if (t.textContent.trim() === '上传图文') { t.click(); return; }
                }
            }""")
            time.sleep(3)
            print("✅ Switched to 上传图文 tab")

            page.locator('input[type="file"]').first.set_input_files(str(cover_path))
            time.sleep(10)
            print("✅ Cover uploaded")

            page.evaluate("""(t) => {
                const input = document.querySelector('input[placeholder*="标题"]');
                if (input) {
                    const setter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    setter.call(input, t);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", title)
            time.sleep(1)
            print(f"✅ Title filled: {title}")

            page.evaluate("""() => {
                const editor = document.querySelector('.ProseMirror[contenteditable="true"]');
                if (editor) { editor.focus(); editor.click(); }
            }""")
            time.sleep(0.5)
            for i, line in enumerate(body_lines):
                if i > 0:
                    page.keyboard.press("Enter")
                if line:
                    page.keyboard.type(line, delay=8)
            time.sleep(2)
            print("✅ Body filled")

            if args.dry_run:
                screenshot_path = "/tmp/xhs-publish-preview.png"
                bm.screenshot(screenshot_path)
                print(f"🛑 Dry run — stopped before publish. Preview: {screenshot_path}")
            else:
                clicked = page.evaluate("""() => {
                    for (const b of document.querySelectorAll('button')) {
                        const t = b.textContent.trim();
                        if (t === '发布笔记' || t === '发布') { b.click(); return t; }
                    }
                    return null;
                }""")
                if clicked:
                    print(f"🚀 Clicked: {clicked}")
                    time.sleep(10)
                    final_url = page.url
                    if "published=true" in final_url:
                        print(f"✅ Published! URL: {final_url}")
                    else:
                        print(f"⚠️  Publish status unclear. URL: {final_url}")
                else:
                    print("❌ Publish button not found")
                    sys.exit(1)

    finally:
        bm.close()


def _save_cookie_to_env(cookie_str: str) -> None:
    """Save XHS_COOKIE to the .env file."""
    env_path = None
    current = Path.cwd()
    while current.parent != current:
        candidate = current / ".env"
        if candidate.exists():
            env_path = candidate
            break
        if any((current / m).exists() for m in [".git", "SKILL.md"]):
            env_path = candidate
            break
        current = current.parent

    if not env_path:
        env_path = Path.cwd() / ".env"

    if env_path.exists():
        content = env_path.read_text()
        lines = content.splitlines()
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith("XHS_COOKIE="):
                new_lines.append(f'XHS_COOKIE="{cookie_str}"')
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f'XHS_COOKIE="{cookie_str}"')
        env_path.write_text("\n".join(new_lines) + "\n")
    else:
        env_path.write_text(f'XHS_COOKIE="{cookie_str}"\n')


if __name__ == "__main__":
    main()
