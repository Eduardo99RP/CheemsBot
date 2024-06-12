import asyncio
import discord
from discord.ext import commands
from discord.utils import get
from pytube import YouTube
from pytube import Search
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import re
from dotenv import load_dotenv

load_dotenv()


intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True  # Para recibir eventos de cambio de estado de voz

bot = commands.Bot(command_prefix="!", intents=intents,
                   description="Tengo ansiedad", help_command=None)

queues = {}
last_text_channels = {}  # Diccionario para almacenar el último canal de texto usado

# Configura las credenciales de la API de Spotify
client_id = os.environ.get("CLIENT_ID_SP")
client_secret = os.environ.get("CLIENT_SECRECT")

# Inicializa el cliente de autenticación
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(name="🎵 Temgo Amsiedad 🎧"))
    print("✅ El bot está en línea")


@bot.event
async def on_voice_state_update(member, before, after):
    # Verificar si un usuario ha cambiado de estado de voz en un canal de voz
    if member.bot:
        return

    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)

    if voice_client and voice_client.channel:
        # Verificar si el canal está vacío (solo el bot queda en el canal)
        if len(voice_client.channel.members) == 1 and voice_client.channel.members[0] == bot.user:
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            if member.guild.id in queues:
                queues[member.guild.id].clear()
            # Enviar el mensaje al último canal de texto utilizado
            if member.guild.id in last_text_channels:
                last_channel = last_text_channels[member.guild.id]
                await last_channel.send("❌ Me desconecto, no hay nadie conectado ❌")
            await voice_client.disconnect()


async def stream_youtube_audio(ctx, url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(
            only_audio=True).order_by('abr').desc().first()
        audio_url = audio_stream.url

        voice_channel = ctx.author.voice.channel
        voice_client = get(bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_connected():
            await voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect()

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel error',
            'options': '-vn',
            'stderr': open(os.devnull, 'w')
        }
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
                          after=lambda e: asyncio.run_coroutine_threadsafe(after_play(ctx), bot.loop))

    except Exception as e:
        await ctx.send(f"Ocurrió un error: {e}")


@bot.command()
async def skip(ctx, song_id: int = None):
    last_text_channels[ctx.guild.id] = ctx.channel  # Guardar el canal de texto
    voice_client = get(bot.voice_clients, guild=ctx.guild)

    if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 1 and song_id != None:
        try:
            queues[ctx.guild.id].pop(song_id)
        except IndexError:
            await ctx.reply("❌ No existe ese ID")
            return
            
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.reply("⏭️ Canción saltada.")


async def after_play(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_connected() and not voice_client.is_playing():
        if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
            next_url = queues[ctx.guild.id].pop(0)
            await stream_youtube_audio(ctx, next_url)


@bot.command()
async def pause(ctx):
    last_text_channels[ctx.guild.id] = ctx.channel  # Guardar el canal de texto
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.reply("⏸️ Canción en pausa.")
    else:
        await ctx.reply("❌ No hay nada reproduciendo actualmente para pausar.")


@bot.command()
async def resume(ctx):
    last_text_channels[ctx.guild.id] = ctx.channel  # Guardar el canal de texto
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.reply("▶️ Reproducción reanudada.")
    else:
        await ctx.reply("❌ No hay ninguna canción en pausa para reanudar.")


@bot.command()
async def play(ctx, *, search_term: str = None):
    last_text_channels[ctx.guild.id] = ctx.channel  # Guardar el canal de texto
    url = None
    # Verifica si el autor del mensaje está en un canal de voz
    if ctx.author.voice:
        # Verifica si se proporciona un término de búsqueda
        if search_term:
            # Verifica si el término de búsqueda es una URL de Spotify
            if re.match(r'https?://(?:open\.)?spotify\.com/.+', search_term):
                track_id = search_term.split('/')[-1].split('?')[0]

                track_info = sp.track(track_id)

                # Extrae el nombre de la pista y el nombre del artista
                nombre_cancion = track_info['name']
                nombre_artista = track_info['artists'][0]['name']

                await ctx.send(f"Canción: {nombre_cancion}\nArtista: {nombre_artista}")
                spot = Search(nombre_cancion + " " + nombre_artista)
                results = spot.results

                if results:
                    url = results[0].watch_url
                    await ctx.reply(f"**Canción a reproducir:**\n{url}")
                else:
                    await ctx.reply("❌ No se encontraron resultados. ❌")
                    return

                # Verificar si hay una cola de reproducción para este servidor
                if ctx.guild.id not in queues:
                    queues[ctx.guild.id] = []

                # Agregar la URL a la cola de reproducción
                queues[ctx.guild.id].append(url)

                # Si no hay ningún audio reproduciéndose, iniciar la reproducción
                if not ctx.voice_client or not ctx.voice_client.is_playing():
                    await stream_youtube_audio(ctx, queues[ctx.guild.id].pop(0))

            else:
                # Verifica si el término de búsqueda es una URL de YouTube
                if re.match(r'https?://(?:www\.)?youtube\.com/.+', search_term) or re.match(r'https?://(?:www\.)?youtu\.be/.+', search_term):
                    url = search_term
                else:
                    s = Search(search_term)
                    results = s.results
                    if results:
                        url = results[0].watch_url
                        await ctx.reply(f"**Canción a reproducir:**\n{url}")
                    else:
                        await ctx.reply("❌ No se encontraron resultados. ❌")
                        return

                # Verificar si hay una cola de reproducción para este servidor
                if ctx.guild.id not in queues:
                    queues[ctx.guild.id] = []

                # Agregar la URL a la cola de reproducción
                queues[ctx.guild.id].append(url)

                # Si no hay ningún audio reproduciéndose, iniciar la reproducción
                if not ctx.voice_client or not ctx.voice_client.is_playing():
                    await stream_youtube_audio(ctx, queues[ctx.guild.id].pop(0))
        else:
            await ctx.reply("❌ Debes proporcionar una URL o un término de búsqueda. ❌")
    else:
        await ctx.reply("❌ Necesitas estar en el canal de voz para reproducir música. ❌")


@bot.command()
async def stop(ctx):
    last_text_channels[ctx.guild.id] = ctx.channel  # Guardar el canal de texto
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
        await ctx.reply("🛑 Reproducción detenida y cola eliminada.")
    else:
        await ctx.reply("❌ No hay nada reproduciendo actualmente para detener.")


@bot.command()
async def q(ctx):
    last_text_channels[ctx.guild.id] = ctx.channel  # Guardar el canal de texto
    if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
        queue_content = []
        for i, url in enumerate(queues[ctx.guild.id], start=1):
            try:
                yt = YouTube(url)
                title = yt.title
                queue_content.append(f"{i}. {title}")
            except Exception as e:
                queue_content.append(
                    f"{i}. Error obteniendo título para {url}: {e}")

        queue_text = "\n".join(queue_content)
        await ctx.reply(f"**Próximas canciones a reproducir:**\n`{queue_text}`")
    else:
        await ctx.reply("No hay elementos en la cola de reproducción.")


@bot.command()
async def help(ctx):
    help_text = """
    **Comandos disponibles:**
    `!play <URL o término de búsqueda>`: Reproduce una canción de YouTube o Spotify.
    `!skip`: Salta la canción actual.
    `!pause`: Pausa la canción actual.
    `!resume`: Reanuda la reproducción de la canción pausada.
    `!stop`: Detiene la reproducción y limpia la cola.
    `!q`: Muestra la cola de canciones.
    `!help`: Muestra este mensaje de ayuda.
    """
    await ctx.send(help_text)


# comando para hacer pruebas de codigo, este codigo no es necesario que este el bot
@bot.command()
async def ping(ctx):
    await ctx.reply("pong")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply("❌ Ese comando no existe. Usa `!help` para ver la lista de comandos disponibles.")
    else:
        raise error


bot.run(os.environ.get("TOKEN"))
