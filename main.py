from typing import Any
import gi
from threading import Thread
from youtube_download import rundownload
from frontend import Frontend

gi.require_version("Gtk", "3.0")

from gi.overrides import Gtk, GLib


def show(title: str, text: Any) -> None:
    """Function that displays a message with : a title, and a main text (title and text)"""
    title, text = str(title), str(text)
    dialog: Gtk.MessageDialog = Gtk.MessageDialog(
        transient_for=window,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    dialog.format_secondary_text(text)
    dialog.run()

    dialog.destroy()


def help_me(*args) -> None:
    """Function triggered by the help button, it displays a notice about this app"""
    show(
        "Aide",
        """search:[requête] : va chercher l'url correspondant à la requête
        
        En activant "qualité maximale", vous obligez l'application à télécharger la meilleure version possible.
        Pour certaines vidéos, c'est en 4k qu'elle seront téléchargées. Autrement, la qualité maximale, sans cocher cette option
        est de 720p.
        
        Cet utilitaire télécharge des vidéos youtube en fonction de l'url (et des playlists, aussi).""",
    )


frontend: function = Frontend(
    lambda *i: GLib.idle_add(show, *i),
    rundownload,
)


def run(*args):
    """Function triggered by pressing enter in both entrys of the app. It fetches the data used to actually download the file"""
    global thread_nb
    link: str = entry.get_text()
    format: str = entryformat.get_text()
    absolutebest: bool = absolutebest_combobox.get_active()
    if not format:
        format = "mp4"
    if link.startswith("search:"):
        # Link is a tuple, for search
        search: bool = True

    # Starting the function, for being able to process multiple downloads at a time
    thread: Thread = Thread(
        target=frontend, args=(link, "", format, thread_nb, absolutebest, search)
    )
    thread.start()
    thread_nb += 1


thread_nb: int = 0

# Creating the window object and setting attributes,
# like titles (there are several title placement)
window = Gtk.Window()
window.set_title("Youtube Downloader")
window.set_wmclass("Youtube Downloader", "Youtube Downloader")

window.set_icon_name("youtube-dl-gui")
window.set_default_size(300, 0)
window.set_resizable(False)

# In gtk, you can use only one widget per window ; Box allows to use multiple widgets
box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.VERTICAL)
label = Gtk.Label(label="Entrez l'url puis la touche entrer")
buttonhelp = Gtk.Button(label="Aide")
buttonhelp.set_halign(Gtk.Align.CENTER)
entry = Gtk.Entry()
entry.set_halign(Gtk.Align.CENTER)
entryformat = Gtk.Entry()
entryformat.set_halign(Gtk.Align.CENTER)
labelformat = Gtk.Label(label="Choisissez un format (par défaut, mp4)")
labelformat.set_halign(Gtk.Align.CENTER)
absolutebest_combobox = Gtk.CheckButton(label="Qualité maximale")
absolutebest_combobox.set_halign(Gtk.Align.CENTER)

box.pack_start(label, False, False, 0)
box.pack_start(entry, False, False, 0)
box.pack_start(labelformat, False, False, 0)
box.pack_start(entryformat, False, False, 0)
box.pack_start(absolutebest_combobox, False, False, 0)
box.pack_start(buttonhelp, False, False, 0)

window.add(box)

entry.connect("activate", run)
entryformat.connect("activate", run)
buttonhelp.connect("clicked", help_me)
window.connect("delete-event", Gtk.main_quit)

window.show_all()

Gtk.main()
