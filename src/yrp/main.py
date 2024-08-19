from ui import MyApp
import sys
from yrp.backend import main
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = MyApp(application_id="com.github.yrp")
    app.run(sys.argv)
