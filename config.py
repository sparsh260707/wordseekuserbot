import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv('API_ID'))
    API_HASH = os.getenv('API_HASH')
    
    START_WORD = os.getenv('START_WORD', 'apple')
    WORDLIST_FILE = os.getenv('WORDLIST_FILE', 'words/commonWords.json')
    GUESS_DELAY = float(os.getenv('GUESS_DELAY', '0.5'))
    AUTO_LOOP = os.getenv('AUTO_LOOP', 'true').lower() == 'true'
