from typing import Union
from pytube import YouTube, Playlist
import os
from html import unescape
import re
from werkzeug.utils import secure_filename as sane_file
import ffmpeg
import gi
from threading import Thread

gi.require_version("Gtk", "3.0")

user = os.getlogin()

from gi.repository import Gtk, GLib


def show(title: str, text: Union[str, Exception]) -> None:
    """Function that displays a message with : a title, and a main text (title and text)"""
    title, text = str(title), str(text)
    dialog = Gtk.MessageDialog(
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
        "Help",
        """search:[query]   will replace search:[query] by the url of a video that matches with the query\n\nGlobally, it downloads videos that have the good URL, and you can set the format (ex: mp4, mov for videos or mp3 and wav for audio). You should keep in mind that you can't cancel a download without killing the process.""",
    )


def make_format(name: str, name_second: str, path: str) -> None:
    """Function that uses ffmpeg to convert a video from one format to another.

    name is the name of the file to convert

    name_second is the name of the file once converted

    path is the directory where both name and name_second files are"""
    try:
        ffmpeg.input(os.path.join(path, name)).output(
            os.path.join(path, name_second)
        ).run()
    except:
        pass
    os.remove(os.path.join(path, name))


def run(*args):
    """Function triggered by pressing enter in both entrys of the app. It fetches the data used to actually download the file"""
    link = entry.get_text()
    format = entryformat.get_text()
    if not format:
        format = "mp4"
    if "search:" in link:
        # Link is a tuple, for search
        link = (re.sub(r"(^|:).+\:", "", link),)

    # Starting the function, for being able to process multiple downloads at a time
    thread = Thread(target=rundownload, args=(link, "", format))
    thread.start()


def rundownload(link: Union[str, tuple], suffix: str = "", format: str = "mp4") -> None:
    """Actual function for downloading a youtube video

    link can be wether a string, which is then interpreted as an url, or a tuple, and it then searches the url matching for search the content of it

    suffix is the sub folder, for playlist downloads, for example

    format is the format that the file should have"""

    # Here, we use GLib.idle_add instead of a direct function call
    # for being able to display messages in another thread
    GLib.idle_add(entry.set_text, "")
    try:
        # Check if the link is to search or to interpret as an url
        # Once we got the good url, we can just call again this function, as it will download the video
        if isinstance(link, tuple):
            from youtube_search import YoutubeSearch

            results = YoutubeSearch(link[0]).to_dict()
            assert results, "Aucun résultats"
            result = results[0]
            link = "https://youtube.com/" + result["url_suffix"]
            rundownload(link, format=format)
            return

        if link.startswith("https://www.youtube.com/playlist"):
            # Here, we get the Playlist object, which contains a list of the videos' URLs
            # We then just call the same function to download them
            playlist = Playlist(link)
            GLib.idle_add(
                show,
                f"Let's download '{playlist.title}{' as ' + format} files !",
                "",
            )
            for url in playlist.video_urls:
                rundownload(url, unescape(playlist.title), format=format)

            GLib.idle_add(
                show,
                f"Done downloading '{playlist.title}{' as ' + format} files !",
                "",
            )

            return

        if not os.path.exists(
            os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix)
        ):
            os.makedirs(os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix))

        video = YouTube(link)

        # Here, we change a little bit the video name for us to be able to download it
        name = video.title.replace("/", "")
        name_second = name + "." + format

        # If the target format is mp4, we don't have to sanitize the file name
        # because we won't use it again. But if we did, it would be way easier to sanitize
        # the file name manually than to letting the os do it itself
        if format != "mp4":
            name = sane_file(name).replace(".", "")

        download_video = video.streams.get_highest_resolution()
        GLib.idle_add(
            show,
            f"Let's download '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
            "",
        )
        download_video.download(
            os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix), filename=name
        )
        name = name + ".mp4"

        # As pytube downloads videos as mp4 files, we don't need further processing
        # if the target format already is mp4
        if format != "mp4":
            make_format(
                name,
                name_second,
                os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
            )
        GLib.idle_add(
            show,
            f"Done downloading '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
            "",
        )
    except Exception as e:
        # Showing error (probably temporary, i should make error management)
        GLib.idle_add(show, "Error", e)


# Creating the window object and setting attributes,
# like titles (there are several title placement)
window = Gtk.Window()
window.set_title("Youtube Downloader")
window.set_title("Explications")
window.set_wmclass("Youtube Downloader", "Youtube Downloader")
window.set_default_size(300, 0)
window.set_resizable(False)

# In gtk, you can use only one widget per window ; Box allows to use multiple widgets
box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.VERTICAL)
label = Gtk.Label(label="Entrez l'url puis la touche entrer")
button = Gtk.Button(label="help")
button.set_halign(Gtk.Align.CENTER)
entry = Gtk.Entry()
entry.set_halign(Gtk.Align.CENTER)
entryformat = Gtk.Entry()
entryformat.set_halign(Gtk.Align.CENTER)
labelformat = Gtk.Label(label="Choisissez un format (par défaut, mp4)")
labelformat.set_halign(Gtk.Align.CENTER)

box.pack_start(label, False, False, 0)
box.pack_start(entry, False, False, 0)
box.pack_start(labelformat, False, False, 0)
box.pack_start(entryformat, False, False, 0)
box.pack_start(button, False, False, 0)

window.add(box)

entry.connect("activate", run)
entryformat.connect("activate", run)
button.connect("clicked", help_me)
window.connect("delete-event", Gtk.main_quit)

window.show_all()

Gtk.main()
