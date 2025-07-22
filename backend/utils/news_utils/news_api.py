import asyncio
import sys
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

import httpx
import tenacity
from dotenv import load_dotenv
import structlog

from schemas.news_api_schemas import NewsArticle, NewsResponse
from utils.news_utils.config import NewsAPIConfig
from utils.news_utils.dataclasses import NewsMetrics
from utils.news_utils.exceptions import (
    APIQuotaExceededError, 
    InvalidQueryError, 
    NewsAPIError,
    APIError,
    ConfigurationError)

load_dotenv()

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class NewsAPI:
    """Production-ready News API client"""

    def __init__(self, config: Optional[NewsAPIConfig] = None):
        self.config = config or NewsAPIConfig()
        self.metrics = NewsMetrics()
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_queries)
        
        logger.info("NewsAPI initialized", 
                   base_url=self.config.base_url,
                   max_articles=self.config.max_articles_per_query)

    async def __aenter__(self):
        """Create shared HTTP client when entering context"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                headers={"User-Agent": "NewsAPI-Client/1.0"}
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Properly close HTTP client when exiting context"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests"""
        return {
            'X-API-KEY': self.config.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'NewsAPI-Client/1.0'
        }

    def _validate_query(self, query: str) -> str:
        """Validate and sanitize query"""
        if not query or not query.strip():
            raise InvalidQueryError("Query cannot be empty")
        
        query = query.strip()
        
        if len(query) < 2:
            raise InvalidQueryError("Query must be at least 2 characters")
        
        forbidden_chars = ['<', '>', '"', '&', '\n', '\r', '\t']
        for char in forbidden_chars:
            if char in query:
                query = query.replace(char, ' ')
        
        query = ' '.join(query.split())
        
        return query

    def _validate_location(self, location: str) -> str:
        """Validate and normalize location"""
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")
        
        location = location.lower().strip()
        
        try:
            if len(location) != 2:
                raise ValueError("Location must be a 2-letter country code")
            
            if not location.isalpha():
                raise ValueError("Location must contain only letters")
            
            return location
        except ValueError:
            logger.warning("Using non-standard country code", location=location)
            return location

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        reraise=True
    )
    async def _make_request(
        self, 
        url: str, 
        query: str, 
        location: str,
        request_id: str = None
    ) -> httpx.Response:
        """Make HTTP request with comprehensive error handling"""
        start_time = time.time()
        self.metrics.total_requests += 1
        
        if not self._client:
            raise NewsAPIError("HTTP client not initialized. Use async context manager.")
        
        try:
            payload = {"q": query, "gl": location}
            
            logger.info("Making news API request", 
                       query=query,
                       location=location,
                       request_id=request_id)
            
            response = await self._client.post(
                url,
                headers=self.get_headers(),
                json=payload,
                timeout=self.config.timeout
            )
            
            response_time = time.time() - start_time
            self.metrics.total_response_time += response_time
            
            # Handle different HTTP status codes
            if response.status_code == 200:
                self.metrics.successful_requests += 1
                logger.info("News API request successful", 
                          status_code=response.status_code,
                          response_time=response_time,
                          query=query,
                          request_id=request_id)
                return response
            elif response.status_code == 400:
                self.metrics.failed_requests += 1
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass
                logger.error("Bad request to news API", 
                           query=query,
                           error_data=error_data,
                           request_id=request_id)
                raise InvalidQueryError(f"Invalid query or parameters: {query}")
            elif response.status_code == 401:
                self.metrics.failed_requests += 1
                logger.error("News API authentication failed", request_id=request_id)
                raise ConfigurationError("Invalid API key")
            elif response.status_code == 429:
                self.metrics.failed_requests += 1
                logger.warning("News API quota exceeded", request_id=request_id)
                raise APIQuotaExceededError("API quota exceeded")
            elif response.status_code >= 500:
                self.metrics.failed_requests += 1
                logger.error("News API server error", 
                           status_code=response.status_code,
                           request_id=request_id)
                raise APIError(f"Server error: {response.status_code}", response.status_code)
            else:
                self.metrics.failed_requests += 1
                logger.error("News API error",
                           status_code=response.status_code,
                           response_text=response.text[:200],
                           request_id=request_id)
                raise APIError(f"API error: {response.status_code}", response.status_code)
                
        except httpx.TimeoutException as e:
            self.metrics.failed_requests += 1
            logger.error("News API timeout", error=str(e), query=query, request_id=request_id)
            raise APIError(f"Request timeout: {e}")
        except httpx.RequestError as e:
            self.metrics.failed_requests += 1
            logger.error("News API request error", error=str(e), query=query, request_id=request_id)
            raise APIError(f"Request error: {e}")

    def _parse_news_articles(self, data: Dict[str, Any], query: str) -> List[NewsArticle]:
        """Parse and validate news articles from API response"""
        articles = []
        
        news_data = data.get("news", [])
        if not isinstance(news_data, list):
            logger.warning("Invalid news data format", query=query)
            return articles
        
        for item in news_data[:self.config.max_articles_per_query]:
            if not isinstance(item, dict):
                continue
            
            try:
                title = item.get('title', '').strip()
                if not title:
                    continue
                
                snippet = item.get('snippet', '').strip()
                if not snippet:
                    snippet = None
                
                article = NewsArticle(
                    title=title,
                    snippet=snippet
                )
                
                articles.append(article)
                
            except Exception as e:
                logger.warning("Failed to parse news article", 
                             error=str(e), 
                             item=item, 
                             query=query)
                continue
        
        return articles

    async def get_news(
        self, 
        query: str, 
        location: str,
        request_id: str = None
    ) -> NewsResponse:
        """Get news articles for a specific query with comprehensive error handling"""
        async with self._semaphore:  # Limit concurrent requests
            try:
                validated_query = self._validate_query(query)
                validated_location = self._validate_location(location)
                
                response = await self._make_request(
                    self.config.base_url, 
                    validated_query, 
                    validated_location,
                    request_id
                )
                
                data = response.json()
                
                articles = self._parse_news_articles(data, validated_query)
                
                self.metrics.queries_processed += 1
                self.metrics.articles_retrieved += len(articles)
                
                result = NewsResponse(
                    query=validated_query,
                    articles=articles,
                    request_id=request_id
                )
                
                if not articles:
                    logger.warning("No news articles found", query=validated_query)
                else:
                    logger.info("News articles retrieved successfully",
                              query=validated_query,
                              count=len(articles),
                              request_id=request_id)
                
                return result
                
            except (InvalidQueryError, APIQuotaExceededError, ConfigurationError):
                # Re-raise specific errors
                raise
            except Exception as e:
                logger.error("Unexpected error getting news",
                           query=query,
                           location=location,
                           error=str(e),
                           request_id=request_id)
                return NewsResponse(
                    query=query,
                    articles=[],
                    request_id=request_id
                )

    async def get_news_for_query_list(
        self,
        query_list: List[str],
        location: str,
        request_id: str = None
    ) -> List[NewsResponse]:
        """Get news for multiple queries with error handling and concurrency control"""
        if not query_list:
            logger.warning("Empty query list provided")
            return []
        
        if len(query_list) > 50:  # Reasonable limit
            logger.warning("Query list too large, truncating", 
                          original_size=len(query_list), 
                          max_size=50)
            query_list = query_list[:50]
        
        try:
            validated_location = self._validate_location(location)
            
            async def safe_get_news(query: str, index: int) -> NewsResponse:
                """Safely get news for one query"""
                sub_request_id = f"{request_id}-{index}" if request_id else f"batch-{index}"
                try:
                    return await self.get_news(query, validated_location, sub_request_id)
                except Exception as e:
                    logger.error("Failed to get news for query in batch",
                               query=query,
                               error=str(e),
                               request_id=sub_request_id)

                    return NewsResponse(
                        query=query,
                        articles=[],
                        request_id=sub_request_id
                    )
            
            tasks = [
                safe_get_news(query, index) 
                for index, query in enumerate(query_list)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=False)
            
            successful_queries = sum(1 for result in results if result.articles)
            
            logger.info("Batch news retrieval completed",
                       total_queries=len(query_list),
                       successful_queries=successful_queries,
                       request_id=request_id)
            
            return results
            
        except Exception as e:
            logger.error("Error in batch news retrieval",
                        query_count=len(query_list),
                        location=location,
                        error=str(e),
                        request_id=request_id)

            return [
                NewsResponse(query=query, articles=[]) 
                for query in query_list
            ]

    def get_metrics(self) -> Dict[str, Any]:
        """Get API usage metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "average_response_time": self.metrics.average_response_time,
            "uptime_seconds": time.time() - self.metrics.start_time,
            "queries_processed": self.metrics.queries_processed,
            "articles_retrieved": self.metrics.articles_retrieved,
            "average_articles_per_query": self.metrics.average_articles_per_query
        }

    async def health_check(self, test_query: str = "technology") -> Dict[str, Any]:
        """Perform health check"""
        try:
            result = await self.get_news(test_query, 'us')
            return {
                "status": "healthy",
                "api_responsive": True,
                "test_query": test_query,
                "articles_found": len(result.articles),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "error": str(e),
                "test_query": test_query,
                "timestamp": time.time()
            }

    async def get_news_dict(self, query: str, location: str) -> Dict[str, List[Dict[str, str]]]:
        """Get news in the original dictionary format for backward compatibility"""
        try:
            response = await self.get_news(query, location)
            return {
                response.query: [
                    {
                        'title': article.title,
                        'snippet': article.snippet or ''
                    }
                    for article in response.articles
                ]
            }
        except Exception as e:
            logger.error("Error in backward compatibility method", 
                        query=query, error=str(e))
            return {query: []}

    async def get_news_for_query_list_dict(
        self,
        query_list: List[str],
        location: str
    ) -> List[Dict[str, List[Dict[str, str]]]]:
        """Get news for query list in original format for backward compatibility"""
        try:
            responses = await self.get_news_for_query_list(query_list, location)
            return [
                {
                    response.query: [
                        {
                            'title': article.title,
                            'snippet': article.snippet or ''
                        }
                        for article in response.articles
                    ]
                }
                for response in responses
            ]
        except Exception as e:
            logger.error("Error in backward compatibility batch method", error=str(e))
            return [{query: []} for query in query_list]


@asynccontextmanager
async def create_news_api(config: NewsAPIConfig = None):
    """Context manager for NewsAPI with proper resource management"""
    api = NewsAPI(config=config)
    try:
        async with api:
            yield api
    except Exception as e:
        logger.error("Error in NewsAPI context manager", error=str(e))
        raise