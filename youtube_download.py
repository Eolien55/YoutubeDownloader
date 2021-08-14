from subprocess import call
from typing import Union, Generator
from pytube import YouTube, Playlist, Stream, StreamQuery
from os import getlogin, remove, makedirs
from os.path import join, exists, dirname
from html import unescape
from werkzeug.utils import secure_filename
from threading import Thread
import click
from frontend import Frontend

user: str = getlogin()


def get_highest_resolution(
    streams: StreamQuery, absolutebest: bool
) -> Union[Stream, tuple[Stream]]:
    true_best: Stream
    if (
        streams.get_highest_resolution().resolution
        != (true_best := streams.order_by("resolution").last()).resolution
    ) and absolutebest:
        return (true_best, streams.order_by("abr").last())
    return streams.get_highest_resolution()


def download(
    video: Union[Stream, tuple[Stream]], path: str, name: str, format: str
) -> str:
    if type(video) == tuple:
        video_stream: Stream = video[0]
        audio_stream: Stream = video[1]
        video_name: str = video_stream.download(path, filename=secure_filename(name))
        audio_name: str = audio_stream.download(
            path, filename="0" + secure_filename(name)
        )
        call(
            [
                "ffmpeg-bar",
                "-i",
                video_name,
                "-i",
                audio_name,
                join(path, "00" + secure_filename(name)) + "." + format,
            ]
        )
        remove(video_name)
        remove(audio_name)

    # YouTube sometimes have videos with th wrong codecs. make_format fixes it

    video_dir: str = dirname(video.download(path, filename=secure_filename(name)))
    make_format(secure_filename(name), name + "." + format, video_dir)


def make_format(name: str, name_second: str, path: str) -> None:
    """Function that uses ffmpeg to convert a video from one format to another.

    name is the name of the file to convert

    name_second is the name of the file once converted

    path is the directory where both name and name_second files are"""
    call(
        [
            "ffmpeg",
            "-i",
            join(path, name),
            "-loglevel",
            "error",
            join(path, name_second),
        ],
    )
    remove(join(path, name))


def rundownload(
    link: Union[str, tuple],
    suffix: str = "",
    format: str = "mp4",
    thread_nb: int = 0,
    absolutebest: bool = False,
    search: bool = False,
) -> Generator[tuple[str], None]:
    """Actual function for downloading a youtube video

    link can be wether a string, which is then interpreted as an url, or a tuple, and it then searches the url matching for search the content of it

    suffix is the sub folder, for playlist downloads, for example

    format is the format that the file should have"""
    try:
        # Check if the link is to search or to interpret as an url
        # Once we got the good url, we can just call again this function, as it will download the video
        if search:
            results: list = YoutubeSearch(link[0]).to_dict()
            assert results, "Aucun résultats"
            result: dict = results[0]
            link = "https://youtube.com/" + result["url_suffix"]
            rundownload(link, format=format)
            return

        if link.startswith("https://www.youtube.com/playlist"):
            # Here, we get the Playlist object, which contains a list of the videos' URLs
            # We then just call the same function to download them
            playlist: Playlist = Playlist(link)
            yield (
                f"[{thread_nb}] Let's download '{playlist.title}{' as ' + format} files !",
                "",
            )

            url: str

            for url in playlist.video_urls:
                rundownload(url, unescape(playlist.title), format=format)

            yield (
                f"[{thread_nb}] Done downloading '{playlist.title}{' as ' + format} files !",
                "",
            )

            return

        if not exists(join(f"/home/{user}/Desktop/YoutubeVideos", suffix)):
            makedirs(join(f"/home/{user}/Desktop/YoutubeVideos", suffix))

        video: YouTube = YouTube(link)

        # Here, we change a little bit the video name for us to be able to download it
        name: str = video.title.replace("/", "")

        download_video: Union[Stream, tuple[Stream]] = get_highest_resolution(
            video.streams, absolutebest
        )
        yield (
            f"[{thread_nb}] Let's download '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
            "",
        )
        download(
            download_video,
            join(f"/home/{user}/Desktop/YoutubeVideos", suffix),
            name,
            format,
        )

        yield (
            f"[{thread_nb}] Done downloading '{video.title}' with a resolution of '{download_video.resolution}'{' as a ' + format} !",
            "",
        )
    except Exception as e:
        # Showing error (probably temporary, i should make error management)
        yield (f"[{thread_nb}] Error " + str(e), "")

    return


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
    default="mp4",
)
@click.option(
    "--absolutebest/ --notabsolutebest",
    "-a/ -b",
    help="Sets the video to the highest quality possible (if false, it will just get (in the worse cases) an 360p video)",
    is_flag=True,
    default=False,
)
def maincommand(
    urls: tuple[str], searches: tuple[bool], format: str, absolutebest: bool
) -> None:
    if len(searches) != len(urls):
        print(
            "You must have done something wrong, the amount of urls and of search/nosearch flag isn't concordant"
        )
        exit(1)

    if True in searches:
        global YoutubeSearch
        from youtube_search import YoutubeSearch

    thread_nb: int = 0
    frontend: function = Frontend(print, rundownload)
    url: str
    search: bool
    for url, the_search in zip(urls, search):
        url.replace("+", " ")
        Thread(
            target=frontend, args=(url, "", format, thread_nb, absolutebest, the_search)
        ).start()

        thread_nb += 1


if __name__ == "__main__":
    maincommand()
