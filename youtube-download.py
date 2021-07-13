import click
from typing import Union
from pytube import YouTube, Playlist
import os
from html import unescape
from werkzeug.utils import secure_filename as sane_file
import ffmpeg

user = os.getlogin()


def make_format(name: str, name_second: str, path: str) -> None:
    """Function that uses ffmpeg to convert a video from one format to another.

    name is the name of the file to convert

    name_second is the name of the file once converted

    path is the directory where both name and name_second files are"""
    try:
        ffmpeg.input(os.path.join(path, name)).output(
            os.path.join(path, name_second)
        ).global_args("-loglevel", "error").run()
    except:
        pass
    os.remove(os.path.join(path, name))


def rundownload(link: Union[str, tuple], suffix: str = "", format: str = "mp4") -> None:
    """Actual function for downloading a youtube video

    link can be wether a string, which is then interpreted as an url, or a tuple, and it then searches the url matching for search the content of it

    suffix is the sub folder, for playlist downloads, for example

    format is the format that the file should have"""

    # Here, we use GLib.idle_add instead of a direct function call
    # for being able to display messages in another thread
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
            print(
                f"Let's download '{playlist.title}{' as ' + format} files !",
            )
            for url in playlist.video_urls:
                rundownload(url, unescape(playlist.title), format=format)

            print(
                f"Done downloading '{playlist.title}{' as ' + format} files !",
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
        print(
            f"Let's download '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
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
        print(
            f"Done downloading '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
        )
    except Exception as e:
        # Showing error (probably temporary, i should make error management)
        print("Error : ", e)


@click.command(help="Downloads youtube video based on the given url")
@click.argument("url")
@click.option(
    "--format", "-f", default="mp4", help="Sets which format to save the video to"
)
@click.option(
    "--search", "-s", is_flag=True, help="Search for the url before downloading"
)
def main(url, format, search):
    if search:
        url = (url,)
    rundownload(url, "", format)


main()
