import pymumble_py3 as pymumble
import json
from time import sleep

with open("config.json") as f:
    config = json.load(f)

class MumbleJukebox:
    def __init__(self):
        self.mumble = pymumble.Mumble(
            config["host"],
            config["user"],
            config["port"],
            config["password"],
            config["certfile"],
            config["keyfile"],
            config["reconnect"],
            stereo=True,
            debug=True)

        self.mumble.callbacks.set_callback(pymumble.callbacks.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, self.message_received)
        self.mumble.set_application_string("Kittens Rule The World!")
        self.mumble.set_codec_profile("audio")
        self.mumble.set_receive_sound(False)
        self.mumble.start()
        self.mumble.is_ready()
        self.mumble.channels.find_by_name("Music").move_in()
        self.mumble.set_bandwidth(96000)
        self.mumble.loop()

    def message_received(self, text):
        message = text.message
        print(message)

if __name__ == "__main__":
    bot = MumbleJukebox()
