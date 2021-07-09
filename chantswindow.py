from tkinter import *
from config import settings

import os.path, vlc, threading, time, random

# chants window class
class chantswindow(Toplevel):
   def __init__(self, parent, chantsManager):
      super().__init__(parent)
      self.chantsManager = chantsManager

      # inserts the UI frame into the window
      self.chantsFrame = ChantsFrame(self, self.chantsManager)
      self.chantsFrame.pack()

      self.title("Manual Chants")
      # Change what happens when you click the X button
      # This is done so changes also reflect in the main window class
      self.protocol('WM_DELETE_WINDOW', parent.close)

# UI frame for the window
class ChantsFrame(Frame):
   def __init__(self, parent, chantsManager):
      Frame.__init__(self, parent)
      self.chantsManager = chantsManager
      
      # volume slider
      Label(self, text="Chants Volume").grid(columnspan=2)
      self.chantVolume = Scale(self, from_=0, to=100, orient=HORIZONTAL, command=self.chantsManager.adjustManagerVolume, showvalue=0, length = 150)
      self.chantVolume.set(80)
      self.chantVolume.grid(columnspan=2)
      # blank space between the sliders and chant buttons to separate them, make it look nicer
      Label(self, text=None).grid(columnspan=2)

      # chant timer checkbox, for if the user doesn't want to use it
      self.timerCheckbox = IntVar(value=1)
      self.enableTimerCheckbox = Checkbutton(self, text="Enable Timer", variable = self.timerCheckbox, command=self.enableTimer)
      self.enableTimerCheckbox.grid(columnspan=2)

      self.chantTimerText = Label(self, text="Chants Timer")
      self.chantTimerText.grid(columnspan=2)

      # chant timer slider
      #self.chantTimer = Scale(self, from_=20, to=60, orient=HORIZONTAL, command=self.adjustTimer, resolution=5, showvalue=1, length = 150)
      self.chantTimer = Scale(self, from_=20, to=60, orient=HORIZONTAL, command=self.chantsManager.adjustTimer, resolution=5, showvalue=1, length = 150)
      self.chantTimer.set(30)
      self.chantTimer.grid(columnspan=2)
      # stop chant early button
      self.stopEarlyButton = Button(self, text="Stop Chant Early", command=self.chantsManager.endThread, bg="#f9fce0")
      self.stopEarlyButton.grid(columnspan=2)
      # blank space between the sliders and chant buttons to separate them, make it look nicer
      Label(self, text=None).grid(columnspan=2)

      # chants lists to replace buttons when new chants are loaded
      self.homeChantsList, self.awayChantsList = list(), list()
      self.createChants(self.chantsManager.homeChants, self.chantsManager.awayChants)

   # creates the chant buttons
   def createChants (self, home = False, away = False):
      if self.chantsManager.activeChant:
         self.chantsManager.endThread()
      if home:
         self.clearChantList(self.homeChantsList)
         
         if self.chantsManager.homeChants:
            chants = self.chantsManager.homeChants
            # a chant button that plays a random chant when it's pressed
            self.randomChant = ChantsButton(self, self.chantsManager, chants, "Random", True, True)
            self.randomChant.insert(8)
            self.homeChantsList.append(self.randomChant)

            for i in range(len(chants)):
               chantName = os.path.basename(chants[i].songname)
               self.chantsButton = ChantsButton(self, self.chantsManager, chants[i], chantName, chants[i].home)
               self.homeChantsList.append(self.chantsButton)
               self.chantsButton.insert(i+9)
      if away:
         self.clearChantList(self.awayChantsList)

         if self.chantsManager.awayChants:
            chants = self.chantsManager.awayChants
            # a chant button that plays a random chant when it's pressed
            self.randomChant = ChantsButton(self, self.chantsManager, chants, "Random", False, True)
            self.randomChant.insert(8)
            self.awayChantsList.append(self.randomChant)

            for i in range(len(chants)):
               chantName = os.path.basename(chants[i].songname)
               self.chantsButton = ChantsButton(self, self.chantsManager, chants[i], chantName, chants[i].home)
               self.awayChantsList.append(self.chantsButton)
               self.chantsButton.insert(i+9)
      # so that any newly loaded chants follow the current slider value instead of the default
      self.chantsManager.adjustManagerVolume(self.chantVolume.get())

   # clears out chants in the window
   def clearChantList (self, chantList):
      if chantList:
         for chant in chantList:
            chant.playButton.destroy()
         chantList.clear()

   # used to enable/disable the use of the timer for chants, greys out and disables the text and slider to show it better
   def enableTimer (self):
      value = self.timerCheckbox.get()
      self.chantsManager.usingTimer = False if value == 0 else True

      self.chantTimerText["fg"] = 'grey' if value == 0 else 'black'
      self.chantTimer["state"] = DISABLED if value == 0 else NORMAL
      self.chantTimer["fg"] = 'grey' if value == 0 else 'black'

# creates and manages the chant buttons
class ChantsButton:
   def __init__ (self, frame, chantsManager, chant, text, home, random = False):
      # used to randomize the chant by having the argument take in the list of chants instead
      if random and isinstance(chant, list):
         self.chantList = chant
      self.frame = frame
      self.chantsManager = chantsManager
      self.chant = chant
      self.text = text
      self.home = home
      self.random = random

      # how long a chant can be played for until it begins to fade out
      self.fadeOutTime = self.chantsManager.defaultTimer
      self.playButton = Button(frame, text=self.text, command=self.playChant, bg=settings.colours["home" if self.home else "away"])

   def playChant (self):
      # if there is already a chant going on, ignore command
      if self.chantsManager.activeChant is not None:
         print("Denied, chant currently playing")
      else:
         # randomly pick a chant from the list and set as this button's chant
         if (self.random):
            self.chant = random.choice(self.chantList)
            # /adv/ manager approved
            for chant in self.chantList:
               if os.path.basename(chant.songname) == "i wish that i could fly.wav":
                  self.chant = chant
                  break
         # otherwise, set this chant as the active chant and begin playing
         self.playButton.configure(relief=SUNKEN)
         self.chantsManager.activeChant = self.chant
         self.chantEndCheck = threading.Thread(target=self.checkChantDone)
         self.chant.reloadSong()
         self.chant.play()
         print("Chant now playing")
         print("Chant Timer: {} seconds ".format(self.fadeOutTime))
         # while greying out the timer stuff and starting the chant end checker thread
         self.chantsManager.disableChantTimer(True, self.chantsManager.window.chantsFrame if self.chantsManager.window is not None else None)
         self.chantEndCheck.start()

   # checks when the chant is done or playing too long
   def checkChantDone (self):
      self.chantStart = time.time()
      while self.chantEndCheck is not None:
         # stops the thread early, before the song has finished playing
         if self.chantsManager.endThreadEarly:
            print("Chant ended early")
            # stops the song, resets the end thread bool, and enables the chant timer (bool reset and chant timer enable is for when new chants are loaded)
            self.chant.song.stop()
            self.chantsManager.endThreadEarly = False
            if self.frame.winfo_exists():
               self.playButton.configure(relief=RAISED)
               self.chantsManager.disableChantTimer(False, self.chantsManager.window.chantsFrame if self.chantsManager.window is not None else None)
            # disables the fade, mark active chant as none, and kill the thread
            self.chant.fade = None
            self.chantsManager.activeChant = None
            self.chantEndCheck = None
         
         if self.chant.song.get_media().get_state() == vlc.State.Ended:
            self.chantDone()
            self.chantEndCheck = None
         # checks if the user is even using the timer in the first place as well
         elif self.chantsManager.usingTimer and (time.time() - self.chantStart) > self.fadeOutTime:
            print("Chant timed out, fade starting")
            self.chant.fade = True
            self.chant.fadeOut()
            self.chantDone()
            self.chantEndCheck = None

   # clears out the active chant variable once the chant is over
   def chantDone (self):
      if self.chantsManager.activeChant is not None:
         self.playButton.configure(relief=RAISED)
         self.chantsManager.activeChant = None
         print("Chant {} concluded.".format(self.text))
         self.chantsManager.disableChantTimer(False, self.chantsManager.window.chantsFrame if self.chantsManager.window is not None else None)

   def insert (self, row):
      self.playButton.grid(row=row, column=0 if self.home else 1)

class ChantsManager:
   def __init__ (self, window, mainWin):
      self.window = window
      self.mainWin = mainWin

      # stores chant information
      self.homeChants, self.awayChants = list(), list()

      # default settings for chant timer and volume
      self.defaultTimer = 30
      self.defaultVolume = 80

      # chant that is currently being played
      self.activeChant = None

      # used to end the checkChantDone thread early
      self.endThreadEarly = False

      # used to check if program is using the timer
      self.usingTimer = True

   def setHome (self, filename=None, parsed=None):
      if parsed is not None:
         self.homeChants = parsed
      else:
         print("No chants received for home team.")
         self.homeChants.clear()
         
      # replaces the random chant button with the updated list of chants and set the volume back to default
      self.mainWin.replaceChantButton(self.homeChants, True)
      self.adjustManagerVolume(self.defaultVolume)

      if (self.window is not None):
         self.window.chantsFrame.createChants(home = True)

   def setAway (self, filename=None, parsed=None):
      if parsed is not None:
         self.awayChants = parsed
      else:
         print("No chants received for away team.")
         self.awayChants.clear()

      # replaces the random chant button with the updated list of chants and set the volume back to default
      self.mainWin.replaceChantButton(self.awayChants, False)
      self.adjustManagerVolume(self.defaultVolume)
      
      if (self.window is not None):
         self.window.chantsFrame.createChants(away = True)

   # used to end the thread early, called by the main rigdio file when chants window is closed
   def endThread (self):
      if self.activeChant is not None:
         self.endThreadEarly = True

   # used to disable the use of the timer stuff when a chant is playing, to prevent the user from messing with it during a chant and causing problems
   def disableChantTimer(self, disable, frame=None):
      if frame is None:
         return
      
      frame.enableTimerCheckbox["state"] = DISABLED if disable else NORMAL
      frame.enableTimerCheckbox["fg"] = 'grey' if disable else 'black'
      # if user is not using the timer in the first place, don't touch the text and slider
      if self.usingTimer:
         frame.chantTimerText["fg"] = 'grey' if disable else 'black'
         frame.chantTimer["state"] = DISABLED if disable else NORMAL
         frame.chantTimer["fg"] = 'grey' if disable else 'black'

   def adjustManagerVolume (self, value):
      # shoves all of the chants into a single list
      self.allChants = self.homeChants + self.awayChants
      
      # adjusts the volume of all the chants at the same time
      for chant in self.allChants:
         chant.adjustVolume(value)

   def adjustTimer (self, value):
      # shoves all of the chant buttons (including the random ones) into a single list
      self.allButtons = self.window.chantsFrame.homeChantsList + self.window.chantsFrame.awayChantsList
      self.allButtons.append(self.mainWin.randomHome)
      self.allButtons.append(self.mainWin.randomAway)

      # adjusts the fade out timer of all the chants at the same time
      for chantButton in self.allButtons:
         chantButton.fadeOutTime = float(value)

   # reset values of timer and volume that may have been changed in chant window back to default
   def resetValues (self):
      self.adjustTimer(self.defaultTimer)
      self.adjustManagerVolume(self.defaultVolume)

      self.activeChant = None
      self.usingTimer = True