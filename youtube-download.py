from subprocess import PIPE, Popen
from typing import Union
import pytube
from pytube import YouTube, Playlist, Stream, StreamQuery
import os
from html import unescape
from werkzeug.utils import secure_filename as sane_file
import ffmpeg
from multiprocessing import Process as Thread
import click
import shutil

user = os.getlogin()


def get_highest_resolution(streams: StreamQuery) -> Union[Stream, tuple[Stream]]:
    if (
        streams.get_highest_resolution().resolution
        != (true_best := streams.order_by("resolution").last()).resolution
    ):
        return (true_best, streams.order_by("abr").last())
    return true_best


def download(
    video: Union[Stream, tuple[Stream]], path: str, name: str, thread_nb
) -> str:
    if type(video) == tuple:
        video_stream = video[0]
        audio_stream = video[1]
        video_name = video_stream.download(path, filename="0" + sane_file(name))
        audio_name = audio_stream.download(path, filename=sane_file(name))
        Popen(
            [
                "ffmpeg-bar",
                "-i",
                video_name,
                "-i",
                audio_name,
                os.path.join(path, "00" + sane_file),
            ],
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )
        os.remove(video_name)
        os.remove(audio_name)
        return os.path.join(path, "00" + sane_file)

    return video.download(path, filename=name)


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


def rundownload(
    link: Union[str, tuple], suffix: str = "", format: str = "mp4", thread_nb: int = 0
) -> None:
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
                f"[{thread_nb}] Let's download '{playlist.title}{' as ' + format} files !",
                "",
            )
            for url in playlist.video_urls:
                rundownload(url, unescape(playlist.title), format=format)

            print(
                f"[{thread_nb}] Done downloading '{playlist.title}{' as ' + format} files !",
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

        download_video = get_highest_resolution(video.streams)
        print(
            f"[{thread_nb}] Let's download '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
            "",
        )
        name = download(
            download_video,
            os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
            name,
            thread_nb,
        ).strip("/")[-1]

        # As pytube downloads videos as mp4 files, we don't need further processing
        # if the target format already is mp4
        if format != "mp4":
            make_format(
                name,
                name_second,
                os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
            )
        else:
            shutil.move(
                os.path.join(
                    os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix), name
                ),
                os.path.join(
                    os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
                    name_second,
                ),
            )
        print(
            f"[{thread_nb}] Done downloading '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
            "",
        )
    except Exception as e:
        # Showing error (probably temporary, i should make error management)
        print(f"[{thread_nb}] Error", e)


@click.command()
@click.option(
    "--url",
    "-u",
    required=True,
    help="Which url to download",
    multiple=True,
    metavar="URL",
)
@click.option(
    "--search/ --nosearch",
    "-s/ -n",
    is_flag=True,
    multiple=True,
    help="Sets wether the video has to be searched for or not",
)
@click.option(
    "--format",
    "-f",
    help="Sets in which format the video has to be saved",
    metavar="FORMAT",
)
def main(url, search, format):
    if len(search) != len(url):
        print(
            "You must have done something wrong, the amount of urls and of search/nosearch flag isn't concordant"
        )
        exit(1)
    thread_nb = 0
    for the_url, the_search in zip(url, search):
        if the_search:
            the_url = (the_url,)
        Thread(target=rundownload, args=(the_url, "", format, thread_nb)).start()
        thread_nb += 1
