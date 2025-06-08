import logging
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def get_player_rank(riot_id: str) -> str:
    if "#" not in riot_id:
        raise ValueError("wrong format, use 'name#tag'.")

    riot_name, riot_tag = riot_id.split("#")
    url = f"https://tracker.gg/valorant/profile/riot/{riot_name}%23{riot_tag}/overview"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        try:
            await page.set_extra_http_headers(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                }
            )

            await page.goto(url, timeout=60000)
            logger.info(f"Loaded page for {riot_id}: {await page.title()}")

            if "just a moment" in (await page.title()).lower():
                logger.info("Cloudflare protection detected, waiting for clearance...")
                await page.wait_for_timeout(5000)
                if "just a moment" in (await page.title()).lower():
                    raise Exception("blocked by Cloudflare protection")

            if "not found" in (await page.title()).lower():
                raise Exception(f"profile not found for {riot_id}")

            await page.wait_for_selector(
                ".rating-summary__content .rating-entry__rank-info .label",
                timeout=60000,
            )
            rank_element = await page.query_selector(
                ".rating-summary__content .rating-entry__rank-info .label"
            )

            if not rank_element:
                logger.info(
                    f"Debug: Rank element not found. Page content: {await page.content()[:500]}"
                )
                raise Exception(f"rank not found {riot_id}.")

            rank = await rank_element.inner_text()
            logger.info(f"Rank found for {riot_id}: {rank.strip()}")
            return rank.strip()

        except Exception as e:
            logger.error(f"Error for {riot_id}: {str(e)}")
            return None

        finally:
            await browser.close()
