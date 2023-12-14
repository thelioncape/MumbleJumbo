#!/usr/bin/python3

import pymumble_py3 as pymumble
from pymumble_py3 import callbacks as cbks
import subprocess as sp
import audioop
import time
import json
import re
import sys
import threading

"""
Main bot class
Contains actions required to load the bot and control actions
"""


class MumbleBot:
	def __init__(self):  # Defines configuration file
		with open("config.json") as f:
			config = json.load(f)

		self.messages = Messages()
		self.configurables = Configurables(config, self.messages)
		self.callbacks = Callbacks(self)
		self.processes = ProcessManager()

	def startBot(self):
		self.mumble = pymumble.Mumble(
			host     = self.configurables.SERVER,
			user     = self.configurables.NICK,
			port     = self.configurables.PORT,
			password = self.configurables.PASSWD,
			certfile = self.configurables.CERTFILE,
			keyfile	 = self.configurables.KEYFILE,
			stereo   = self.configurables.STEREO)

		# Set MESSAGE_RECEIVED callback
		self.mumble.callbacks.set_callback(
			cbks.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED,
			self.callbacks.message_received)

		# Set DISCONNECT callback
		self.mumble.callbacks.set_callback(
			cbks.PYMUMBLE_CLBK_DISCONNECTED,
			self.callbacks.died)

		# Start bot engine
		self.mumble.start()

		# Wait for connection to complete to prevent thread clashes
		self.mumble.is_ready()

		# Get bot's user as an object
		self.botUserObj = self.mumble.users.myself

		# Initial comment update
		self.updateComment()

	def updateComment(self): #TODO
		self.configurables.updateQueue()

		comment =  self.messages.currentSongMessage
		comment += "<br />"

		comment += self.messages.queueMessage
		comment += "<br />"

		comment += self.messages.playbackSpeedMessage
		comment += "<br />"

		comment += self.messages.helpmessage

		self.botUserObj.comment(comment)

	def mainLoop(self):
		while True:
			print("Start Tick Processing")
			print("Current queue:", self.configurables.queue)
			if len(self.configurables.queue) > 0: # If there are songs queued
				url = self.configurables.queue.pop(0) # Pop next item in queue
				# Get title of next item in queue
				command = ["youtube-dl", "-e", url]
				with sp.Popen(command, stdout=sp.PIPE) as p:
					self.messages.currentSongMessage = (
						"<p>Currently Playing:</p>")
					self.messages.currentSongMessage += "<p>"
					self.messages.currentSongMessage += str(
						p.stdout.readline().decode('UTF-8').strip())
					self.messages.currentSongMessage += "</p>"

				# Begin downloading video to stdout pipe to wave_file
				if "youtube.com" in url or "youtu.be" in url:
					print("Looks like a YouTube link.")
					command = 	["youtube-dl",
								"-f", "bestaudio",
								url,
								"--buffer-size", "2M",
								"-o", "-"]
				else:
					print("Doesn't look like a YouTube link.")
					command = ["youtube-dl",
								url,
								"--buffer-size", "2M",
								"-o", "-"]
				download_proc = sp.Popen(command, stdout=sp.PIPE)
				wave_file = download_proc.stdout
				self.processes.track(download_proc)
				# Convert and play wave_file
				command = 	["ffmpeg",
							"-i", "-",
							"-acodec", "pcm_s16le",
							"-f", "s16le",
							"-ab", "192k",
							"-ac", "1",
							"-ar", "48000",
							"-fflags", "nobuffer",
							"-filter:a",
							"atempo=" + str(self.configurables.playbackSpeed),
							"-"]
				sound = sp.Popen(command,
								stdout=sp.PIPE,
								stderr=sp.DEVNULL,
								stdin=wave_file, bufsize=1024)
				self.processes.track(sound)

				print("Playing")
				self.configurables.playing = True
				self.updateComment()
				# Send audio bytes to Mumble sound queue and play
				while True:
					raw_music = sound.stdout.read(1024)
					if not raw_music: # No more data -> buffer filled
						break
					# Add raw sound to mumble output buffer
					self.mumble.sound_output.add_sound(raw_music)
				print("Buffer filled")
				self.updateComment()

				# Wait for Mumble to output sound buffer to server
				while self.mumble.sound_output.get_buffer_size() > 0.5:
					time.sleep(1)

				# Song finished
				self.configurables.playing = False
				self.currentSongMessage = (
					"<p>Currently Playing:</p>\n<p>Nothing!</p>")
			print("Tick Processing Completed")
			self.updateComment()
			time.sleep(2)
			if self.configurables.serverDied:
				sys.exit(0)
			if self.configurables.skip:
				self.configurables.skip = False



class Callbacks:
	def __init__(self, mumblebot):
		self.mumblebot = mumblebot
		self.conf = self.mumblebot.configurables
		self.messages = self.mumblebot.messages

	# Removes any HTML tags from a string using regex
	# Used when cleaning incoming messages for processing
	def cleanhtml(self, raw_html):
		cleanr = re.compile("<.*?>")
		cleantext = re.sub(cleanr, '', raw_html)
		return cleantext

	# Processes incoming messages to see if they are commands for us
	def message_received(self, text):
		message = self.cleanhtml(text.message)
		actor = text.actor
		#user = mumble.users[text.actor]

		if message.startswith("!"):
			if message.startswith("!play "):
				self.conf.queue.append(message[6::])
				self.mumblebot.updateComment()

			elif message == "!skip":
				self.mumblebot.processes.killall()
				self.mumblebot.mumble.sound_output.clear_buffer()
				self.conf.skip = True
				time.sleep(3)
				self.mumblebot.updateComment()

			elif message == "!yeet":
				self.mumblebot.mumble.stop()
				sys.exit(0)

			elif message == "!clear":
				self.conf.queue = []
				time.sleep(1)
				self.mumblebot.updateComment()

			elif message == "!stopall":
				self.conf.queue = []
				self.mumblebot.processes.killall()
				self.mumblebot.mumble.sound_output.clear_buffer()
				self.conf.skip = True
				time.sleep(1)
				self.mumblebot.updateComment()

			elif message.startswith("!speed"):
				try:
					if self.conf.speedchange(message[7:]):
						self.mumblebot.mumble.users[actor].send_text_message(
								"Speed changed to " + str(message[7:]) + "x")
					else:
						self.mumblebot.mumble.users[actor].send_text_message(
							"Please provide a speed between 0.5 and 2")
				except Exception as e:
					print(e)
					self.mumblebot.mumble.users[actor].send_text_message(
							"Please provide a speed between 0.5 and 2")

	def died(self): self.conf.serverDied = True

"""
Class containing all configurables for the bot
As per PEP8, constants are declared in CAPITALS
"""
class Configurables:
	def __init__(self, config, messages):
		self.messages = messages

		self.SERVER = config["host"]
		self.NICK = config["user"]
		self.PASSWD = config["password"]
		self.PORT = config["port"]
		self.CERTFILE = config["certfile"]
		self.KEYFILE = config["keyfile"]
		#self.STEREO = config["stereo"]#ffmpeg command must be adjusted first.
		self.STEREO = False

		self.playbackSpeed = 1 # Sanitisation required
		self.playing = False
		self.skip = False

		self.queue = []
		self.serverDied = False

	# Updates the queue of songs to play and the corresponding message
	# in the Messages object
	def updateQueue(self):
		titles = []
		for song in self.queue:
			command = ["youtube-dl", "-e", song] # Get title only
			# Runs above command and directs stdout to a pipe
			with sp.Popen(command, stdout=sp.PIPE) as p:
				# Reads title from stdout and decodes into a usable string
				title = str(p.stdout.readline().decode('UTF-8').strip())
			titles.append(title)

		# Fill the queue comment with current songs
		self.messages.queueMessage = "<p>Current queue:</p>"
		if len(titles) > 0:
			for title in titles:
				self.messages.queueMessage += "\n<p>" + title + "</p>"
		else:
			self.messages.queueMessage += "\n<p>No songs in queue</p>"

	# Changes the currently playback speed by adding a filter
	# into FFMPEG
	def speedchange(self, target):
		try:
			target = float(target)
		except ValueError:
			print("[!] Invalid Speed Received.")
			return False

		if target <= 2 and target >= 0.5: # Limits of the ffmpeg filter.
			self.playbackSpeed = target
			self.messages.setPlaybackSpeedMessage(target)
			return True
		else:
			return False


"""
Class containing all messages that may be sent/set by the bot

This includes blocks of text in the Mumble status field for a user
"""
class Messages:
	def __init__(self):
		# Help message is stored in helpmessage.html to reduce clutter
		with open("helpmessage.html") as f:
			self.helpmessage = f.read()

		self.queueMessage = "<p>Current Queue</p>\
							<p>No songs in queue</p>"

		self.currentSongMessage =	"<p>Currently Playing:</p>\
									<p>Nothing!</p>"

		self.playbackSpeedMessage = "<p>Playback speed: 1x</p>"

	# Sets the playback speed message based on the
	# Configurables object passed to it
	def setPlaybackSpeedMessage(self, target):
		self.playbackSpeedMessage = "<p>Playback speed: {0}x</p>".format(
				str(target))


"""
Class responsible for tracking long-running processes (yt-dlp, ffmpeg, etc.) used by the bot, so we can kill them if needs be.
"""
class ProcessManager:
	def __init__(self):
		self.processes = []
	
	def _watcher(self, process):
		# If a process exits normally, remove it from the list.
		process.wait()
		self.processes.remove(process)
	
	def _kill(self, process):
		try:
			process.terminate()
			process.wait(timeout=5)
		except TimeoutExpired:
			print("Process refused to exit. It has been killed.")
			process.kill()

	def track(self, process):
		self.processes.append(process)
		thread = threading.Thread(target=self._watcher, args=(process,))
		thread.start()
		return True
	
	def killall(self):
		for p in self.processes:
			threading.Thread(target=self._kill, args=(p,)).start()


bot_instance = MumbleBot()
bot_instance.startBot()
bot_instance.mainLoop()
