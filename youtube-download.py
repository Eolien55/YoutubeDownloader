import subprocess
import click
from typing import Union
from pytube import YouTube, Playlist, Stream
import os
from html import unescape
from werkzeug.utils import secure_filename as sane_file
import ffmpeg
from multiprocessing import Process as Thread
from shutil import move

user = os.getlogin()


def get_highest_resolution(video: YouTube, best):
    if (supposed_highest := video.streams.get_highest_resolution()) != (
        true_highest := video.streams.order_by("resolution").last()
    ) and best:
        return (
            true_highest,
            video.streams.order_by("abr").last(),
        ), true_highest.resolution
    return supposed_highest, supposed_highest.resolution


def download(video: Union[Stream, tuple], path, name, thread_nb):
    if type(video) == tuple:
        formats = (
            "." + video[0].mime_type.split("/")[1],
            "." + video[1].mime_type.split("/")[1],
        )
        audio_name, video_name = (
            sane_file(name) + formats[1],
            sane_file(name) + formats[0],
        )
        video[0].download(path, filename=sane_file(name))

        if len(set(formats)) == 1:
            move(os.path.join(path, video_name), os.path.join(path, "0" + video_name))
            video_name = "0" + video_name

        video[1].download(path, filename=sane_file(name))

        print(f"[{thread_nb}] Starting to re-encode video file")

        ffmpeg.input(os.path.join(path, video_name)).output(
            os.path.join(path, "0" + ".".join(video_name.split(".")[:-1]) + ".mp4")
        ).global_args("-y").global_args("-loglevel", "error").run()

        os.remove(os.path.join(path, video_name))
        video_name = "0" + ".".join(video_name.split(".")[:-1]) + ".mp4"
        print(f"[{thread_nb}]Starting to merge audio & video")

        subprocess.run(
            [
                "ffmpeg",
                "-i",
                os.path.join(path, video_name),
                "-i",
                os.path.join(path, audio_name),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-loglevel",
                "error",
                "-y",
                os.path.join(path, "000" + name + ".mp4"),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        os.remove(os.path.join(path, audio_name))
        os.remove(os.path.join(path, video_name))
        return "000" + name + ".mp4"
    video.download(path, filename=name)
    return name + ".mp4"


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
    link: Union[str, tuple],
    suffix: str = "",
    format: str = "mp4",
    thread_nb: int = 0,
    best: bool = False,
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
            rundownload(link, format=format, thread_nb=thread_nb)
            return

        if link.startswith("https://www.youtube.com/playlist"):
            # Here, we get the Playlist object, which contains a list of the videos' URLs
            # We then just call the same function to download them
            playlist = Playlist(link)
            print(
                f"[{thread_nb}] Let's download '{playlist.title}{' as ' + format} files !",
            )
            for url in playlist.video_urls:
                rundownload(
                    url, unescape(playlist.title), format=format, thread_nb=thread_nb
                )

            print(
                f"[{thread_nb}] Done downloading '{playlist.title}{' as ' + format} files !",
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

        download_video, resolution = get_highest_resolution(video, best)
        print(
            f"[{thread_nb}] Let's download '{video.title}' with a resolution of '{resolution}'{' as a ' + format} !",
        )
        name = download(
            download_video,
            os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
            name,
            thread_nb,
        )

        # As pytube downloads videos as mp4 files, we don't need further processing
        # if the target format already is mp4
        if format != "mp4":
            make_format(
                name,
                name_second,
                os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
            )
        else:
            move(
                os.path.join(
                    os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix), name
                ),
                os.path.join(
                    os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
                    video.title + ".mp4",
                ),
            )
        print(
            f"[{thread_nb}] Done downloading '{video.title}' with a resolution of '{resolution}'{' as a ' + format} !",
        )
    except Exception as e:
        # Showing error (probably temporary, i should make error management)
        print(f"[{thread_nb}] Error : ", e)


@click.command(help="Downloads youtube video based on the given url")
@click.option(
    "-u",
    "--url",
    type=str,
    metavar="URL",
    multiple=True,
    help="Sets the URL to download",
    required=True,
)
@click.option(
    "--format",
    "-f",
    default="mp4",
    help="Sets which format to save the video to",
    metavar="FORMAT",
)
@click.option(
    "--search/ --nosearch",
    "-s/ -n",
    is_flag=True,
    help="Search for the url before downloading",
    multiple=True,
)
@click.option(
    "--best", "-b", is_flag=True, help="Sets the video to be absolutely the best it can"
)
def main(url, format, search, best):
    if len(search) < len(url):
        print(
            "Uh, there are several options where you didn't set the search flag ; thus, i can't find out which ones need to be searched and which ones do not"
        )
        exit(1)
    search = search[: len(url)]
    thread_nb = 0
    for the_url, the_search in zip(url, search):
        the_url = the_url.replace("+", " ")
        if the_search:
            the_url = (the_url,)
        Thread(target=rundownload, args=(the_url, "", format, thread_nb, best)).start()
        thread_nb += 1


main()
