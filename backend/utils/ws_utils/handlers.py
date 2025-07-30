from typing import Union
from utils.gpt_utils.gpts import create_gpt_client
from utils.news_utils.news_api import create_news_api
from utils.taste_api_utils.taste_api import create_taste_api
from utils.trends_scraper import GoogleTrendsScraper
from utils.weather_utils.weather_api import create_weather_api


async def get_insights(location: str):
    """Get taste insights for a location."""
    async with create_taste_api(location) as taste:
        taste_data = await taste.get_all_insights()
        return taste_data
        
async def get_trends(country_code: str):
    """Get trending topics and related news for a country."""
    async with GoogleTrendsScraper(headless=True) as scraper:
        trends = await scraper.scrape_trending_topics(country_code.upper(), hours=168)
        if not trends:
            return []
        
    trends_list = []
    for topic in trends:
        query = topic.query
        trends_list.append(query)

    async with create_news_api() as news_api:
        news_list = await news_api.get_news_for_query_list(
            trends_list, 
            country_code.lower()
        )
        return [news.model_dump() for news in news_list]
    
async def get_forecast_info(country_name: str, use_weather: bool, days: Union[str, None] = None):
    """Get weather forecast information if weather is enabled."""
    if not use_weather or not days:
        return None
        
    async with create_weather_api() as weather_api:
        forecast_data = await weather_api.get_forecast(country_name, days)
        return [forecast.model_dump() for forecast in forecast_data]

async def get_slangs(country_name: str):
    """Get local slangs for a country."""
    async with create_gpt_client() as gpt:
        slangs = await gpt.get_slangs(country_name)
        return slangs.model_dump()