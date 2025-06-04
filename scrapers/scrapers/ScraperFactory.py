from common import write_to_logs
import RoyalRoadScraper,FoxaholicScraper,NovelBinScraper,SpaceBattlesScraper


class ScraperFactory:
    @staticmethod
    def get_scraper(url):
        if "royalroad.com" in url:
            return RoyalRoadScraper()
        elif "foxaholic.com" in url:
            return FoxaholicScraper()
        elif "novelbin.me" in url or "novelbin.com" in url:
            return NovelBinScraper()
        elif "spacebattles.com" in url:
            return SpaceBattlesScraper()
        else:
            errorText="Failed to get scraper. Function get_scraper Error: Unsupported website"
            write_to_logs(errorText)
            raise ValueError("Unsupported website")
        