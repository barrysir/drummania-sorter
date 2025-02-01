import logging

song_title = ''
def set_song(title):
    global song_title
    song_title = title

def warning(message):
    global song_title
    logging.warning(f"[{song_title}] {message}")