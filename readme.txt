
---

Samsung Electronics Extractor - Instructions

Hello! 👋
Thank you for downloading my program.

To use the application, follow these simple steps:


---

1️⃣ Install Termux X11

1. Install TermuxX11.apk, which is included with the program.


2. Launch Termux X11 and grant all necessary permissions.


3. Do not close it — let it run in the background.




---

2️⃣ Install the program

1. Navigate to the folder with the application.


2. Open the terminal and run:



python installer.py

This will install all required dependencies.


---

3️⃣ If you encounter errors when launching the GUI

If after installation you try to run the interface:

python ui.py

and an error occurs, do the following:

export DISPLAY=:0
termux-x11 :0 &
python ui.py


---

4️⃣ Launch the interface

1. Switch to Termux X11.


2. You will see the program interface there.


3. You can now use all the features! 🎉




---

✅ Tips:

Termux X11 must always run in the background; otherwise, the GUI will not appear.

To display images, the program uses Python and Pillow — they will be installed automatically via installer.py.



---