import os
import warnings
from dotenv import load_dotenv
import websocket
from pushbullet import Pushbullet
import threading
import urllib
import time
from common import wait_for

from server_management import ServerManager


def has_internet_connection():
    try:
        urllib.request.urlopen("http://www.pushbullet.com", timeout=2)
        return True
    except urllib.error.URLError as err:
        return False


class WebSocketMessageReceiver:
    def __init__(self):
        super().__init__()
        self.last_created_message = 0

    def on_ws_message(self, pb, ws_message, on_message):
        if ws_message.find("tickle") == -1:
            return

        pushes = pb.get_pushes(limit=1)
        match pushes:
            case [push]:
                content = push["body"]
                created = push["created"]
                if created > self.last_created_message:
                    self.last_created_message = created
                    try:
                        on_message(content)
                    except ServerManager.UnknownApplicationIDError as ex:
                        # TODO: signal faliure
                        pass
                    except KeyboardInterrupt:
                        raise KeyboardInterrupt
                    except Exception:
                        # TODO: signal faliure
                        pass
            case [push, *tail]:
                warnings.warn(f"Expected response of length 1. Got {len(pushes)}")
            case _:
                warnings.warn(f"Expected response as list")


if __name__ == "__main__":
    load_dotenv()
    pb_api_key = os.getenv("PUSHBULLET_API_KEY")
    assert pb_api_key is not None, "Could not get pushbullet API key"

    pb = Pushbullet(pb_api_key)

    wsmr = WebSocketMessageReceiver()

    ws = websocket.WebSocketApp(
        f"wss://stream.pushbullet.com/websocket/{pb_api_key}",
        on_message=lambda ws, msg: wsmr.on_ws_message(pb, msg, print),
    )
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

    # Hang main thread until internet connection drops as this would indicate that the websocket is no longer responsive
    wait_for(lambda: not has_internet_connection(), interval=60.0, timeout=None)

    # daemon thread exits at the end of the main thread
