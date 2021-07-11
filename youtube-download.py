import os
import sys
from html import unescape
from werkzeug.utils import secure_filename as file
from pytube import YouTube, Playlist

user = os.getlogin()


def run(link, soundonly=False, suffix=""):
    print(link)
    if isinstance(link, tuple):
        from youtube_search import YoutubeSearch

        results = YoutubeSearch(link[0]).to_dict()
        assert results, "Aucun résultats"
        result = results[0]
        link = "https://youtube.com/" + result["url_suffix"]
        run(link, soundonly)
        return

    if link.startswith("https://www.youtube.com/playlist"):
        playlist = Playlist(link)
        for url in playlist.video_urls:
            run(url, soundonly, unescape(playlist.title))
        return

    if soundonly:
        name, name_audio = run(link, False, suffix)
        with VideoFileClip(
            os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix, name),
        ) as video:
            video.audio.write_audiofile(
                os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix, name_audio)
            )
        os.remove(os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix, name))
        return

    if not os.path.exists(os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix)):
        os.makedirs(os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix))

    video = YouTube(link)

    name = video.title.replace("/", "")
    name_audio = name + ".mp3"

    if "--soundonly" in sys.argv:
        name = file(name).replace(".", "")

    download_video = video.streams.get_highest_resolution()
    print(
        f"Let's download '{video.title}' with a resolution of '{download_video.resolution}'{' as an mp3' if '--soundonly' in sys.argv else ''}"
    )
    download_video.download(
        os.path.join(f"/home/{user}/Desktop/YoutubeVideos", suffix), filename=name
    )
    name = name + ".mp4"
    return name, name_audio


if "-h" in sys.argv or "--help" in sys.argv:
    print(
        """
            SYNOPSIS : yt-dl [url | search [query] ] [OPTIONS]
                        Download the video that has the specified url or download a video that matches with the query
            OPTIONS :
                        -s --soundonly          download the video, but as a .mp3
                        -h --help               shows this
            """
    )
    exit()
if "search" in sys.argv[:2]:
    keys = sys.argv
    link = (keys[keys.index("search") + 1].replace("+", " "),)
else:
    link = sys.argv[1]
if "--soundonly" in sys.argv:
    from moviepy.editor import VideoFileClip
run(link, soundonly="--soundonly" in sys.argv)
