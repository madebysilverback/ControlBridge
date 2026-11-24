ControlBridge - prototype v0.7
Made by Silverback
==============================

Play keyboard-only PC games with a PS5 DualSense, using the buttons the
PlayStation version of the game used. First game: Splinter Cell: Pandora
Tomorrow (Steam), with the PS2 layout.

DualSense and PlayStation are trademarks of Sony Interactive Entertainment
Inc. ControlBridge is an independent project and is not affiliated with or
endorsed by Sony.

Installed with ControlBridge-Setup.exe? Use the Start menu shortcuts.
Running from the zip? Use Start.bat and Button Prompts.bat (they need
Python: https://www.python.org/downloads/ - tick "Add python.exe to PATH").


ONE-TIME SETUP
--------------
1. Turn off Steam Input for the game (otherwise Steam grabs the controller):
   Steam > Library > right-click Splinter Cell: Pandora Tomorrow >
   Properties > Controller > choose "Disable Steam Input".
2. Connect the DualSense by USB cable or Bluetooth.
3. Open ControlBridge. Press buttons: they light up blue on the controller
   picture, so you can check everything works.
4. (Optional) Click "Button prompts" (game closed). Choose 1 to preview,
   then 2 to apply. On-screen hints like "Press Space" become
   "Press Cross". Choose 3 any time to undo.


PLAYING
-------
1. Open ControlBridge and leave it open.
2. Start the game from Steam.
3. When the game window is in front, the right side of ControlBridge shows
   "Playing now" and the PS2 layout. Alt+Tab away and it pauses itself.
4. HOLD THE PS BUTTON to see the button list over the game. (Shows when
   the game is in a window or borderless window; Alt+Enter switches.)

Analog speed: like on PS2, push the left stick further to move faster.


THE GAME LIBRARY
----------------
ControlBridge downloads new game layouts from the online library when it
starts and every 6 hours while it's open (when you're online). New layouts
never switch in the middle of a game: they load once you leave it. While no game is in front, it lists the
games you have installed that it has a layout for.

Library layouts don't fix the keys: when a game starts, ControlBridge reads
that game's own settings file on your PC and uses YOUR keys. Under each key
it says where the key came from:
  From your game      read from the game's settings on this PC
  Normal key          the game's usual key (no settings file found yet)
  Not found           check this one in the game's Controls menu

Something wrong? Click "Report a problem". It opens a ready-filled post;
after two reports for the same game the layout is rebuilt automatically.


IF A BUTTON DOES THE WRONG THING
--------------------------------
Keys marked "Check in game" were best guesses.
1. In the game: Options > Controls, note the key for that action.
2. Click "Game profiles". Copy the game's .json file from the "library"
   folder into the profiles folder itself (your copy always wins over the
   library), and open your copy in Notepad.
3. Add a "key" for that button, e.g. "key": "R". Save.
   ControlBridge reloads it straight away. Then run Button prompts > 2
   again so the on-screen hints match.

Even easier: Button prompts > 4 makes prompt_scan_report.txt - send it to
me. It lists the game's real key bindings so the guesses can be fixed.

Key names you can use: A-Z, 0-9, F1-F12, SPACE, ENTER, ESCAPE, TAB,
LSHIFT, RSHIFT, LCTRL, RCTRL, LALT, UP, DOWN, LEFT, RIGHT, INSERT, DELETE,
HOME, END, PAGEUP, PAGEDOWN, NUMPAD0-NUMPAD9, NUMPAD_PERIOD, NUMPAD_ENTER,
MOUSE_LEFT, MOUSE_RIGHT, MOUSE_MIDDLE, WHEEL_UP, WHEEL_DOWN, NONE.


MAKING A PROFILE FOR ANOTHER GAME (AI HELP)
-------------------------------------------
Click "Make a profile" (or Profile Maker.bat from the zip).
1. Type the game's name and which PlayStation version to copy (e.g. PS2).
2. It finds the game and reads the PC key bindings from the game's own
   settings files.
3. Paste the PlayStation controls (from the manual, GameFAQs, a wiki),
   then type END on its own line.
4. Copy-and-paste mode (free, the default): Notepad opens with a prompt.
   Copy it, paste it into Claude (claude.ai), paste Claude's reply into
   the second Notepad window, save, and press Enter in the tool.
   Automatic mode (also free): option 2, add a free Gemini key from
   aistudio.google.com (no card needed) and the tool asks the AI by itself.
5. The new profile is saved in the profiles folder and ControlBridge uses
   it straight away. Buttons the AI wasn't sure about say "Check in game".
Tip: if no bindings are found, open the game, change any key in its
Controls menu and change it back, then quit and try again.
Any AI key you add is stored in the profile_maker folder on this PC only.


KNOWN LIMITS OF THIS PROTOTYPE
------------------------------
- Prompts show button names as words (Cross, Triangle...), not symbols:
  old game fonts can't draw the PlayStation shapes.
- If Steam "verifies" or updates the game, run Button prompts > 2 again.
- If the game is run "as administrator", run ControlBridge that way too.
- Don't use with online games that have anti-cheat.
- Uninstalling ControlBridge puts the games' original prompts back.
