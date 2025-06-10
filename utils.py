import os
import datetime
import logging
from dotenv import load_dotenv, find_dotenv



def write_to_logs(log):
    logLocation=os.getenv("LOGS",
        #os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    )
    #Debugging purposes.
    # logging.warning(f"Log location: {logLocation}")
    
    # print("CWD:", os.getcwd())
    # print("LOGS env:", os.getenv("LOGS"))
    # print("logLocation:", logLocation)
    
    
    
    todayDate=datetime.datetime.today().strftime('%Y-%m-%d')
    log = datetime.datetime.now().strftime('%c') +" "+log+"\n"
    fileLocation=f"{logLocation}/{todayDate}.txt"
    logging.warning(f"Writing to log file: {fileLocation}")
    if os.path.exists(fileLocation):
        f=open(fileLocation,"a")
    else:
        f=open(fileLocation,'w')
    f.write(log)
    f.close()
