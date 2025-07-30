import asyncio
import json
import logging
from sys import platform
from typing import List, Dict, Optional, Any
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, Response
from aiolimiter import AsyncLimiter

from schemas.trends_schemas import Topic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

trends_limiter = AsyncLimiter(max_rate=1, time_period=10)

class GoogleTrendsScraperError(Exception):
    """Custom exception for Google Trends scraper errors"""
    pass

class GoogleTrendsScraper:
    """
    Production-ready async Google Trends scraper using Playwright
    """
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ):
        self.headless = headless
        self.timeout = timeout
        self.user_agent = user_agent
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.trending_data: Optional[str] = None
        self._response_event: Optional[asyncio.Event] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self) -> None:
        """Initialize the browser and page"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            self.page = await self.browser.new_page(
                user_agent=self.user_agent
            )
            
            self.page.set_default_timeout(self.timeout)
            
            await self.page.route(
                "**/*.{png,jpg,jpeg,svg,woff,woff2,css,js}",
                lambda route: route.abort()
            )
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise GoogleTrendsScraperError(f"Browser initialization failed: {e}")
    
    async def close(self) -> None:
        """Clean up resources"""
        try:
            if self.page:
                await self.page.close()
                logger.debug("Page closed")
            
            if self.browser:
                await self.browser.close()
                logger.debug("Browser closed")
                
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
                logger.debug("Playwright stopped")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _handle_response(self, response: Response) -> None:
        """Handle network responses to capture trends data"""
        try:
            url = response.url
            if (
                '/_/TrendsUi/data/batchexecute' in url and
                'source-path=%2Ftrending' in url and
                'rpcids=i0OFE' in url
            ):
                logger.info(f"Captured trends API response: {url}")
                self.trending_data = await response.text()
                logger.debug("Trends data captured successfully")
                
                if self._response_event:
                    self._response_event.set()
                
        except Exception as e:
            logger.error(f"Error handling response: {e}")
    
    def _format_timestamp(self, timestamp: Optional[int]) -> Optional[str]:
        """Convert timestamp to readable format"""
        try:
            if timestamp:
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            return None
        except Exception as e:
            logger.warning(f"Error formatting timestamp {timestamp}: {e}")
            return None
    
    def _parse_trends_data(self, raw_data: str) -> List[Topic]:
        """
        Parse Google Trends batchexecute response to extract trending topics
        """
        try:
            if not raw_data:
                logger.warning("No raw data provided for parsing")
                return []
            
            lines = raw_data.strip().split('\n')
            
            json_line = None
            for line in lines:
                if line.startswith('[["wrb.fr","i0OFE"'):
                    json_line = line
                    break
            
            if not json_line:
                logger.warning("No valid JSON line found in response")
                return []
            
            parsed = json.loads(json_line)
            
            if len(parsed) < 1 or len(parsed[0]) < 3:
                logger.warning("Unexpected JSON structure")
                return []
            
            trends_str = parsed[0][2]
            trends_data = json.loads(trends_str)
            
            trending_topics = []
            
            if len(trends_data) >= 2 and trends_data[1]:
                for trend in trends_data[1]:
                    try:
                        if isinstance(trend, list) and len(trend) >= 10:
                            timestamp = trend[3][0] if trend[3] else None
                            topic = {
                                'query': trend[0],
                                'country': trend[2],
                                'timestamp': timestamp,
                                'formatted_timestamp': self._format_timestamp(timestamp),
                                'search_volume': trend[6] if len(trend) > 6 else None,
                                'related_queries': trend[9] if len(trend) > 9 else [],
                                'category': trend[10][0] if len(trend) > 10 and trend[10] else None
                            }

                            parsed_topic = Topic(**topic)
                            trending_topics.append(parsed_topic)
                    except (IndexError, TypeError) as e:
                        logger.warning(f"Error parsing individual trend: {e}")
                        continue
            
            logger.info(f"Successfully parsed {len(trending_topics)} trending topics")
            return trending_topics
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing trends data: {e}")
            return []
    
    async def _wait_for_trends_response(self, timeout_seconds: int = 30) -> bool:
        """
        Wait for the trends API response with timeout
        
        Args:
            timeout_seconds: Maximum time to wait for response
            
        Returns:
            True if response received, False if timeout
        """
        try:
            self._response_event = asyncio.Event()
            
            await asyncio.wait_for(
                self._response_event.wait(),
                timeout=timeout_seconds
            )
            
            logger.debug("Trends response received within timeout")
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for trends response ({timeout_seconds}s)")
            return False
        except Exception as e:
            logger.error(f"Error waiting for trends response: {e}")
            return False
        finally:
            self._response_event = None
    
    async def scrape_trending_topics(
        self,
        geo: str = "NG",
        response_timeout: int = 30,
        max_retries: int = 3,
        hours: int = 24
    ) -> List[Topic]:
        """
        Scrape trending topics from Google Trends
        
        Args:
            geo: Country code (default: NG for Nigeria)
            response_timeout: Timeout in seconds to wait for API response
            max_retries: Maximum number of retry attempts
            hours: Number of Hours started trending
            
        Returns:
            List of trending topic dictionaries
        """
        if not self.page:
            raise GoogleTrendsScraperError("Browser not initialized. Use 'async with' or call start() first.")
        
        for attempt in range(max_retries):
            try:
                self.trending_data = None
                self._response_event = asyncio.Event()
                
                self.page.on("response", self._handle_response)

                url = f"https://trends.google.com/trending?geo={geo}&hours={hours}"
                
                navigation_task = asyncio.create_task(
                    self.page.goto(url, wait_until="networkidle")
                )
                response_task = asyncio.create_task(
                    self._wait_for_trends_response(response_timeout)
                )

                navigation_response, response_received = await asyncio.gather(
                    navigation_task, 
                    response_task
                )

                
                if response_received and self.trending_data:
                    parsed = self._parse_trends_data(self.trending_data)
                    topics = self.get_top_topics(parsed, 5)
                    if topics:
                        logger.info(f"Successfully scraped {len(topics)} trending topics")
                        return topics
                    else:
                        logger.warning("No topics found in response data")
                else:
                    logger.warning("No trending data captured within timeout")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in 2 seconds... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping {geo} on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise GoogleTrendsScraperError(
                        f"Failed to scrape {geo} after {max_retries} attempts: {e}"
                    )
            finally:
                try:
                    self.page.remove_listener("response", self._handle_response)
                except:
                    pass
        
        return []
    
    async def scrape_multiple_geos(
        self,
        geos: List[str],
        response_timeout: int = 30,
        hours: int = 24
    ) -> Dict[str, List[Topic]]:
        """
        Scrape trending topics for multiple countries
        
        Args:
            geos: List of country codes
            response_timeout: Timeout for each API response
            hours: Number of Hours started trending
            
        Returns:
            Dictionary mapping country codes to trending topics
        """
        results = {}
        
        async def safe_scrape_geo(geo: str) -> tuple[str, List[Topic]]:
            """Safely scrape a single geo with rate limiting"""
            try:
                async with trends_limiter:
                    topics = await self.scrape_trending_topics(geo, response_timeout, hours=hours)
                    return geo, topics
            except Exception as e:
                logger.error(f"Failed to scrape {geo}: {e}")
                return geo, [] 
        
        tasks = [
            asyncio.create_task(safe_scrape_geo(geo), name=f"scrape_{geo}")
            for geo in geos
        ]
        
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(completed_tasks):
            if isinstance(result, Exception):
                logger.error(f"Task for {geos[i]} failed: {result}")
                results[geos[i]] = []
            else:
                geo, topics = result
                results[geo] = topics
        
        logger.info(f"Completed scraping for {len(results)} geos")
        return results
    
    def filter_topics_by_category(
        self,
        topics: List[Topic],
        category: Optional[int] = None
    ) -> List[Topic]:
        """
        Filter topics by category
        
        Args:
            topics: List of topic dictionaries
            category: Category number to filter by
            
        Returns:
            Filtered list of topics
        """
        if category is None:
            return topics
        
        return [topic for topic in topics if topic.category == category]
    
    def get_top_topics(
        self,
        topics: List[Topic],
        limit: int = 10,
        sort_by: str = 'search_volume'
    ) -> List[Topic]:
        """
        Get top trending topics
        
        Args:
            topics: List of topic dictionaries
            limit: Maximum number of topics to return
            sort_by: Field to sort by ('search_volume', 'timestamp', 'query')
            
        Returns:
            Top trending topics
        """
        try:
            if sort_by == 'search_volume':
                sorted_topics = sorted(
                    topics,
                    key=lambda x: x.search_volume or 0,
                    reverse=True
                )
            elif sort_by == 'timestamp':
                sorted_topics = sorted(
                    topics,
                    key=lambda x: x.timestamp or 0,
                    reverse=True
                )
            elif sort_by == 'query':
                sorted_topics = sorted(
                    topics,
                    key=lambda x: x.query.lower()
                )
            else:
                logger.warning(f"Unknown sort_by field: {sort_by}")
                sorted_topics = topics
            
            return sorted_topics[:limit]
            
        except Exception as e:
            logger.error(f"Error sorting topics: {e}")
            return topics[:limit]

async def main():
    """Example usage of the GoogleTrendsScraper"""
    try:
        async with GoogleTrendsScraper(headless=True) as scraper:
            topics = await scraper.scrape_trending_topics(
                geo='NG', 
                response_timeout=30, 
                hours=168
            )

            for topic in topics[:10]:
                print(f"- {topic['query']} ({topic['country']})")
                print(f"  Related: {topic['related_queries'][:3]}")
                print(f"  Search Volume: {topic['search_volume']}")
                print()
            
    except GoogleTrendsScraperError as e:
        logger.error(f"Scraper error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())