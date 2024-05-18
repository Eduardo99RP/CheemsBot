from pytube import Playlist

# URL de la lista de reproducción de YouTube
playlist_url = 'https://www.youtube.com/watch?v=hYgJAN1Ol5g&list=PLezS2-icsLly4y9GFBId0LMUM4NjTJYYW&ab_channel=hadirostamisahzabi'

# Instanciar la clase Playlist
playlist = Playlist(playlist_url)

# Iterar sobre los vídeos en la lista de reproducción y obtener sus URLs
for video_url in playlist.video_urls:
    print(video_url)
