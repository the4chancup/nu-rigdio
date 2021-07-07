from tkinter import *
import tkinter.messagebox as messagebox
from rigparse import reserved
from rigdio_except import UnloadSong, SongNotFound
from legacy import PlayerManager
from config import settings

from time import sleep, time

class PlayerButtons:
   def __init__ (self, frame, clists, home, game, text = None):
      # song information
      self.clists = PlayerManager(clists,home,game)
      self.game = game
      # derived information
      self.song = None
      self.pname = clists[0].pname
      # text and buttons
      self.text = text
      self.frame = frame
      # timer stuff
      self.victoryAnthem = (self.pname == "victory")
      if self.victoryAnthem:
         # vlc takes some time to retrieve song duration, so a sleep delay is needed
         self.sleepDelay = 1
         self.timer = Timer(self.frame, self, self.sleepDelay)
         self.songDuration = int()
      # check if text is none (most players)
      if self.text is None:
         self.text = "\n".join([x.lstrip() for x in self.pname.split(",")])
         self.reserved = False
      else:
         self.reserved = True
      # used for anthem handling
      ## determine if this is an anthem button
      self.anthem = self.text == "Anthem"
      ## Home anthem button is hooked to this by the main client, to stop it when it starts
      self.awayButtonHook = None
      # text was specified, so this is a button for a reserved keyword
      self.listButton = Button(self.frame, text="?", command=self.showSongs, bg=settings.colours["home" if home else "away"])
      self.playButton = Button(self.frame, text=self.text, command=self.playSong, bg=settings.colours["home" if home else "away"])
      self.resetButton = Button(self.frame, text="⟲", command=self.resetSong, bg=settings.colours["home" if home else "away"])
      self.volume = Scale(self.frame, from_=0, to=100, orient=HORIZONTAL, command=self.clists.adjustVolume, showvalue=0)
      self.volume.set(80)

   def resetSong (self):
      self.clists.resetLastPlayed()
      self.playButton.configure(relief=RAISED)
      # reset the VA timer
      if self.victoryAnthem:
         self.timer.resetTimer()

   def playSong (self):
      # if home team anthem, pause away team anthem
      if self.anthem and self.awayButtonHook != None:
         self.awayButtonHook.clists.pauseSong()
         self.awayButtonHook.playButton.configure(relief=RAISED)
      if self.clists.song is None:
         # score points if it's a goalhorn
         if self.pname not in reserved or self.pname == "goal":
            self.game.score(self.pname, self.clists.home)
         # pass it up to the list manager
         try:
            # if this is the first time this song is being played and it has a custom playback speed set, set the slider to that speed
            # the playback speed will still use the exact value specified in the .4cc, it's just to show that it's been modified
            # after the first time, if the playback speed slider has been moved, it will use the value of the slider instead
            if self.clists.playSong():
               self.frame.master.playbackSpeedMenu.set(self.clists.song.playbackSpeed)
            else:
               self.clists.song.song.set_rate(self.frame.master.playbackSpeedMenu.get())
            self.frame.master.disablePlaybackSpeedSlider(True)

            # if the song is the victory anthem, have a sleep delay to retrieve song duration before starting up the timer
            if self.victoryAnthem:
               sleep(self.sleepDelay)
               self.songDuration = int(self.clists.song.song.get_length()/1000)
               self.timer.timerStart()

         # no song found
         except SongNotFound as e:
            print(e)
            messagebox.showwarning(e)
            return
         # set the button as sunken
         self.playButton.configure(relief=SUNKEN)
      else:
         # enable the playback slider and pause the song
         self.frame.master.disablePlaybackSpeedSlider(False)
         self.clists.pauseSong()
         # pause the VA timer
         if self.victoryAnthem:
            self.timer.timerPause()
         # set the button as raised
         self.playButton.configure(relief=RAISED)

   def showSongs (self):
      text = self.text
      if not self.reserved:
         text = "Player {}".format(self.text)
      title = "Listing Songs for {}".format(text)
      text = ""
      for clist in self.clists:
         if len(text) == 0:
            text = str(clist)
         else:
            text = "\n".join([text, str(clist)])
      messagebox.showinfo(title, text)

   def insert (self, row):
      self.listButton.grid(row=row,column=0,sticky=N+S, padx=2, pady=(5,0))
      self.playButton.grid(row=row,column=1,sticky=NE+SW, padx=2, pady=(5,0))
      self.resetButton.grid(row=row,column=2,sticky=N+S, padx=2, pady=(5,0))
      self.volume.grid(row=row+1,column=0,columnspan=3,sticky=E+W, pady=(0,5))

class Timer:
   def __init__ (self, frame, songui, delay):
      self.frame = frame
      self.songui = songui
      self.delay = delay
      self.timer = int()
      self.stopCounting = False

   def timerStart (self):
      # increases the timer by the sleep delay (that occurs when starting the VA) before starting the counting loop
      self.timer += self.delay
      self.frame.updateSongTimer(self.timer, self.songui.songDuration)
      self.frame.after(1000, self.timerCountSecond)

   # used to stop the timer loop
   def timerPause (self):
      self.stopCounting = True

   # updates the song timer by one second in a loop
   def timerCountSecond (self):
      # if the song is paused, don't loop instead and reset the bool
      if self.stopCounting:
         self.stopCounting = False
      else:
         self.timer += 1
         self.frame.updateSongTimer(self.timer, self.songui.songDuration)
         self.frame.after(1000, self.timerCountSecond)

   # resets the internal and UI timers to 0
   def resetTimer (self):
      self.timer = 0
      self.frame.updateSongTimer(0, 0)

class TeamMenuLegacy (Frame):
   def __init__ (self, master, tname, players, home, game):
      Frame.__init__(self, master)
      # store information from constructor
      self.master = master
      self.tname = tname
      self.players = players
      self.home = home
      self.game = game
      # list of player names for use in buttons
      self.playerNames = [x for x in self.players.keys() if x not in reserved]
      self.playerNames.sort()
      # tkinter frame containing menu
      # button for anthem
      self.buildAnthemButtons()
      # buttons for victory anthems
      startRow = self.buildVictoryAnthemMenu() + 2
      # buttons for goalhorns
      timerRow = self.buildGoalhornMenu(startRow)
      # victory song timer at the end
      self.buildSongTimer(timerRow)

   def buildAnthemButtons (self):
      self.anthemButtons = PlayerButtons(self, self.players["anthem"], self.home, self.game, "Anthem")
      self.anthemButtons.insert(2)

   def buildVictoryAnthemMenu (self):
      if "victory" in self.players:
         PlayerButtons(self, self.players["victory"], self.home, self.game, "Victory Anthem").insert(4)
         return 4
      else:
         return 0

   def buildGoalhornMenu (self, startRow):
      Label(self, text="Goalhorns").grid(row=startRow, column=0, columnspan=2)
      PlayerButtons(self, self.players["goal"], self.home, self.game, "Standard Goalhorn").insert(startRow+1)
      for i in range(len(self.playerNames)):
         name = self.playerNames[i]
         PlayerButtons(self, self.players[name], self.home, self.game).insert(startRow+3+2*i)
      # returns the row right after the goalhorns are built, for the song timer
      return startRow+3+(2*len(self.playerNames))
   
   def buildSongTimer (self, timerRow):
      self.timerFrame = Frame(self)
      Label(self.timerFrame, text="Victory Song Duration - ").grid(row=0, column=0)
      self.timeText = Label(self.timerFrame)
      self.updateSongTimer(0, 0)
      self.timeText.grid(row=0, column=1)
      self.timerFrame.grid(row=timerRow, column=0, columnspan=3)

   # updates the UI timer
   def updateSongTimer (self, timer, duration):
      timerMins = int(timer/60)
      timerSecs = timer%60
      durationMins = int(duration/60)
      durationSecs = duration%60
      self.timeText.config(text = "{}:{} / {}:{}".format(timerMins, str(timerSecs).zfill(2), durationMins, str(durationSecs).zfill(2)))

   def clear (self):
      for player in self.players.keys():
         for clist in self.players[player]:
            clist.disable()