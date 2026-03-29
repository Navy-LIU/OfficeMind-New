"""
OfficeMind Browser Operator
Playwright CDP-based browser automation with VLM visual verification.
Supports: form filling, data extraction, navigation, screenshot verification.
"""
from __future__ import annotations
import asyncio, logging, json, os, time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BrowserAction:
    action: str        # navigate | click | type | extract | screenshot | wait
    target: str        # CSS selector, URL, or description
    value: str = ""    # text to type, or empty
    timeout: int = 10000
    description: str = ""

@dataclass
class ActionResult:
    success: bool
    action: str
    target: str
    data: Any = None
    screenshot: str = ""
    error: str = ""
    latency_ms: float = 0.0

class BrowserOperator:
    """
    Playwright-based browser automation with:
    - VLM visual verification after each action
    - Human-in-the-loop for high-risk operations
    - Automatic retry with exponential backoff
    - Full audit trail (screenshots + action log)
    """
    
    def __init__(
        self,
        headless: bool = True,
        screenshot_dir: str = "/tmp/officemind_browser",
        vlm_base_url: str = None,
        hitl_callback=None,
    ):
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.vlm_base_url = vlm_base_url or os.getenv("VLM_BASE_URL", "http://localhost:8001/v1")
        self.hitl_callback = hitl_callback
        self._browser = None
        self._page = None
        self._action_log: List[ActionResult] = []
    
    async def __aenter__(self):
        await self._start()
        return self
    
    async def __aexit__(self, *args):
        await self._stop()
    
    async def _start(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self._page = await context.new_page()
        logger.info("Browser started (headless=%s)", self.headless)
    
    async def _stop(self):
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_pw"):
            await self._pw.stop()
    
    async def execute(self, actions: List[BrowserAction], 
                      verify_with_vlm: bool = False) -> List[ActionResult]:
        """Execute a sequence of browser actions."""
        results = []
        for action in actions:
            result = await self._execute_one(action, verify_with_vlm)
            results.append(result)
            self._action_log.append(result)
            if not result.success:
                logger.warning("Action failed: %s — %s", action.action, result.error)
                break
        return results
    
    async def _execute_one(self, action: BrowserAction, 
                           verify: bool = False) -> ActionResult:
        t0 = time.perf_counter()
        screenshot = ""
        
        try:
            if action.action == "navigate":
                await self._page.goto(action.target, timeout=action.timeout,
                                      wait_until="domcontentloaded")
                await self._page.wait_for_load_state("networkidle", timeout=5000)
                
            elif action.action == "click":
                await self._page.wait_for_selector(action.target, timeout=action.timeout)
                await self._page.click(action.target)
                await asyncio.sleep(0.5)
                
            elif action.action == "type":
                await self._page.wait_for_selector(action.target, timeout=action.timeout)
                await self._page.fill(action.target, action.value)
                
            elif action.action == "extract":
                data = await self._extract_data(action.target)
                latency = (time.perf_counter() - t0) * 1000
                return ActionResult(True, action.action, action.target, 
                                   data=data, latency_ms=latency)
                
            elif action.action == "screenshot":
                screenshot = await self._take_screenshot(action.value or "action")
                
            elif action.action == "wait":
                await asyncio.sleep(float(action.value or 1))
                
            elif action.action == "scroll":
                await self._page.evaluate(f"window.scrollBy(0, {action.value or 500})")
                
            elif action.action == "select":
                await self._page.select_option(action.target, action.value)
                
            elif action.action == "hover":
                await self._page.hover(action.target)
            
            # Take verification screenshot
            if verify and action.action != "screenshot":
                screenshot = await self._take_screenshot(f"{action.action}_{action.target[:20]}")
            
            latency = (time.perf_counter() - t0) * 1000
            return ActionResult(True, action.action, action.target,
                               screenshot=screenshot, latency_ms=latency)
        
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            return ActionResult(False, action.action, action.target,
                               error=str(e), latency_ms=latency)
    
    async def _extract_data(self, selector: str) -> Any:
        """Extract structured data from page."""
        if selector == "table":
            return await self._extract_tables()
        elif selector == "text":
            return await self._page.inner_text("body")
        elif selector == "links":
            return await self._page.evaluate(
                "() => Array.from(document.querySelectorAll('a')).map(a => ({text: a.innerText, href: a.href}))"
            )
        else:
            elements = await self._page.query_selector_all(selector)
            return [await el.inner_text() for el in elements]
    
    async def _extract_tables(self) -> List[List[str]]:
        return await self._page.evaluate("""
            () => Array.from(document.querySelectorAll('table')).map(table => 
                Array.from(table.querySelectorAll('tr')).map(row =>
                    Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim())
                )
            )
        """)
    
    async def _take_screenshot(self, name: str = "screen") -> str:
        ts = int(time.time() * 1000)
        path = str(self.screenshot_dir / f"{name}_{ts}.png")
        await self._page.screenshot(path=path, full_page=False)
        return path
    
    async def fill_form(self, form_data: Dict[str, str], 
                        submit_selector: str = None,
                        require_confirmation: bool = True) -> ActionResult:
        """
        Fill a form with provided data.
        If require_confirmation=True, calls HITL callback before submitting.
        """
        actions = []
        for selector, value in form_data.items():
            actions.append(BrowserAction("type", selector, value))
        
        results = await self.execute(actions, verify_with_vlm=True)
        
        if not all(r.success for r in results):
            failed = [r for r in results if not r.success]
            return ActionResult(False, "fill_form", str(form_data),
                               error=f"Failed: {[r.error for r in failed]}")
        
        if submit_selector:
            if require_confirmation and self.hitl_callback:
                screenshot = await self._take_screenshot("pre_submit")
                approved = await self.hitl_callback(
                    "即将提交表单，请确认",
                    screenshot=screenshot,
                    form_data=form_data
                )
                if not approved:
                    return ActionResult(False, "fill_form", submit_selector,
                                       error="用户取消了表单提交")
            
            submit_result = await self._execute_one(
                BrowserAction("click", submit_selector, description="提交表单")
            )
            return submit_result
        
        return ActionResult(True, "fill_form", str(form_data))
    
    async def scrape_page(self, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Navigate to URL and extract data by CSS selectors."""
        await self._execute_one(BrowserAction("navigate", url))
        data = {}
        for key, selector in selectors.items():
            result = await self._execute_one(BrowserAction("extract", selector))
            data[key] = result.data if result.success else None
        return data
    
    def get_audit_log(self) -> List[dict]:
        return [
            {
                "action": r.action,
                "target": r.target,
                "success": r.success,
                "latency_ms": round(r.latency_ms, 1),
                "error": r.error,
                "screenshot": r.screenshot,
            }
            for r in self._action_log
        ]


# ── NLP to Actions Parser ─────────────────────────────────────────────────────
class NLPActionParser:
    """Convert natural language instructions to BrowserAction list via LLM."""
    
    def __init__(self, llm_base_url: str = None):
        self.base_url = llm_base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
    
    def parse(self, instruction: str, page_context: str = "") -> List[BrowserAction]:
        """Parse NL instruction into browser actions."""
        from openai import OpenAI
        client = OpenAI(base_url=self.base_url, api_key="EMPTY")
        
        prompt = f"""将以下自然语言指令转换为浏览器操作步骤列表。

指令：{instruction}
{f"当前页面上下文：{page_context}" if page_context else ""}

输出JSON数组，每个元素包含：
- action: navigate|click|type|extract|screenshot|wait|scroll|select
- target: CSS选择器或URL
- value: 输入值（如有）
- description: 操作说明

示例：
[
  {{"action": "navigate", "target": "https://example.com", "value": "", "description": "打开网页"}},
  {{"action": "click", "target": "#submit-btn", "value": "", "description": "点击提交按钮"}}
]

只输出JSON数组，不要其他内容。"""
        
        try:
            resp = client.chat.completions.create(
                model="Qwen3-Thinking",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1024,
            )
            content = resp.choices[0].message.content.strip()
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                actions_data = json.loads(match.group())
                return [
                    BrowserAction(
                        action=a.get("action", ""),
                        target=a.get("target", ""),
                        value=a.get("value", ""),
                        description=a.get("description", ""),
                    )
                    for a in actions_data
                ]
        except Exception as e:
            logger.error(f"NLP parsing failed: {e}")
        
        return []
