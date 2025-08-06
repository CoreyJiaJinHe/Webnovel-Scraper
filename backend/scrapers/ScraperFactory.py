from backend.common import write_to_logs
from backend.scrapers.FoxaholicScraper import FoxaholicScraper
from backend.scrapers.RoyalRoadScraper import RoyalRoadScraper
from backend.scrapers.NovelBinScraper import NovelBinScraper
from backend.scrapers.SpaceBattlesScraper import SpaceBattlesScraper


class ScraperFactory:
    @staticmethod
    def create_scraper(url):
        if "royalroad" in url:
            return RoyalRoadScraper()
        elif "foxaholic" in url:
            return FoxaholicScraper()
        elif "novelbin" in url:
            return NovelBinScraper()
        elif "spacebattles" in url:
            return SpaceBattlesScraper()
        else:
            errorText="Failed to get scraper. Function get_scraper Error: Unsupported website"
            write_to_logs(errorText)
            raise ValueError("Unsupported website")
        