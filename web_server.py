"""Run the GeopolMonitor web interface."""
import uvicorn
from config.settings import WEB_HOST, WEB_PORT

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file


if __name__ == "__main__":
    uvicorn.run("src.web.main:app", host=WEB_HOST, port=WEB_PORT, reload=True,env_file=".env")