#!/usr/bin/python3

import pymumble_py3
import subprocess as sp
import audioop, time
import json
import re

with open("config.json") as f:
	config = json.load(f)

server = config["host"]
nick = config["user"]
passwd = config["password"]
port = config["port"]
certfile = config["certfile"]
keyfile = config["keyfile"]

playing = False
skip = False
with open("helpmessage.html") as f:
	helpmessage = f.read()
	print(helpmessage)
	print(type(helpmessage))
queueMessage = "<p>Current Queue</p>\
	\n<p>No songs in queue</p>"
currentSongMessage = "<p>Currently Playing:</p>\
	\n<p>Nothing!</p>"
playbackSpeedMessage = "<p>Playback speed: 1x</p>"
queue = []
serverDied = False

def setPlaybackSpeedMesage(playbackSpeed):
    global playbackSpeedMessage
    playbackSpeedMessage = "<p>Playback speed: {0}x</p>".format(str(playbackSpeed))

def cleanhtml(raw_html):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext

def updateQueue():
	global queueMessage
	titles = []
	for song in queue:
		command = ["youtube-dl", "-e", song] # Get title
		with sp.Popen(command, stdout=sp.PIPE) as p:
			title = str(p.stdout.readline().decode('UTF-8').strip())
		titles.append(title)

	queueMessage = "<p>Current queue:</p>"
	if len(titles) > 0:
		for title in titles:
			queueMessage += "\n<p>" + title + "</p>"

def message_received(text):
	global url, skip, queueMessage, queue
	message = cleanhtml(text.message)
	#user = mumble.users[text.actor]

	if message.startswith("!"):
		if message.startswith("!play "):
			queue.append(message[6::])

			updateComment()
		elif message == "!skip":
			mumble.sound_output.clear_buffer()
			skip = True
			time.sleep(3)
			updateComment()
		elif message == "!yeet":
			mumble.stop()
			exit()
		elif message == "!clear":
			queue = []
			time.sleep(1)
			updateComment()
		elif message == "!stopall":
			queue = []
			mumble.sound_output.clear_buffer()
			skip = True
			time.sleep(1)
			updateComment()


def updateComment():
	updateQueue()

	comment = currentSongMessage
	comment += "<br />"
	comment += queueMessage
	comment += "<br />"
    comment += playbackSpeedMessage
    comment += "<br />"
	comment += helpmessage

	botUser.comment(comment)

def died():
	global serverDied
	serverDied = True

mumble = pymumble_py3.Mumble(server, nick, password=passwd, port=port, certfile=certfile, keyfile=keyfile)
mumble.callbacks.set_callback(pymumble_py3.callbacks.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received)
mumble.callbacks.set_callback(pymumble_py3.callbacks.PYMUMBLE_CLBK_DISCONNECTED, died)
mumble.start()
mumble.is_ready()   #wait for Mumble to get ready to avoid errors after startup
botUser = mumble.users.myself
updateComment()

while True:
	print("start Processing")
	print("Queue:", queue)
	if len(queue) > 0:
		url = queue.pop(0)
		command = ["youtube-dl", "-e", url]
		with sp.Popen(command, stdout=sp.PIPE) as p:
			currentSongMessage = "<p>Currently Playing:</p>"
			currentSongMessage += "<p>"
			currentSongMessage += str(p.stdout.readline().decode('UTF-8').strip())
			currentSongMessage += "</p>"

		command = ["youtube-dl","-f","bestaudio", url, "--buffer-size", "2M", "-o", "-"]
		wave_file = sp.Popen(command, stdout=sp.PIPE).stdout
		# Convert and play wave file
		command = ["ffmpeg", "-i", "-", "-acodec", "pcm_s16le", "-f", "s16le", "-ab", "192k", "-ac", "1", "-ar", "48000", "-fflags", "nobuffer",  "-"]
		sound = sp.Popen(command, stdout=sp.PIPE, stderr=sp.DEVNULL, stdin=wave_file, bufsize=1024)
		print("playing")
		playing = True
		updateComment()
		while True:
			if skip:
				skip = False
				break
			raw_music = sound.stdout.read(1024)
			if not raw_music:
				break
			#mumble.sound_output.add_sound(audioop.mul(raw_music, 2, vol))   #adjusting volume
			mumble.sound_output.add_sound(raw_music)

		print("Buffer filled")
		updateComment()

	while mumble.sound_output.get_buffer_size() > 0.5:  #
		time.sleep(0.01)
	playing = False
	currentSongMessage = "<p>Currently Playing:</p>\
		\n<p>Nothing!</p>"
	print("sleep")
	updateComment()
	time.sleep(2)
	if serverDied:
		exit()
