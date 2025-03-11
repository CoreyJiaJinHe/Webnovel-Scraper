import datetime

class NovelTemplate():
    bookID:int
    bookName:str
    bookDescription:str
    websiteHost:str
    firstChapter:int
    lastChapter:int
    lastScraped:datetime.date
    totalChapters:int
    
    def __init__(self, *args):
        
        pass
        
        '''
        self.bookID=kwargs.get("bookID","Template")
        self.bookName=kwargs.get("bookName","Template")
        self.bookDescription=kwargs.get("bookDescription","Template")
        self.websiteHost=kwargs.get("websiteHost","Template")
        self.firstChapter=kwargs.get("firstChapter",-1)
        self.lastChapter=kwargs.get("lastChapter",-1)
        self.lastScraped=kwargs.get("lastScraped",-1)'''