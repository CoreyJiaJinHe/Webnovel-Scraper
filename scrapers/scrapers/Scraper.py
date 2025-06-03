import bs4
import aiohttp
from common import write_to_logs, basicHeaders

class Scraper:
    async def fetch_novel_data(self,url):
        raise NotImplementedError
    async def fetch_chapter_list(self,url):
        raise NotImplementedError
    async def fetch_chapter_content(self,soup):
        raise NotImplementedError
    async def fetch_chapter_title(self,soup):
        raise NotImplementedError
    async def get_soup(self,url):
        
        try:
            async with aiohttp.ClientSession(headers = basicHeaders) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = bs4.BeautifulSoup(html, 'html.parser')
                        return soup
                    else:
                        errorText=f"Failed to get soup. Function get_soup Error: {response.status}"
                        write_to_logs(errorText)
        except Exception as e:
            errorText=f"Failed to get soup. Function get_soup Error: {e}, {url}"


