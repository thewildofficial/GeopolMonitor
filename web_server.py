"""Run the GeopolMonitor web interface."""
import uvicorn
from config.settings import WEB_HOST, WEB_PORT

if __name__ == "__main__":
    uvicorn.run("src.web.main:app", host=WEB_HOST, port=WEB_PORT, reload=True)