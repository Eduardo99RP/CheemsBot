import asyncio
import nextcord
import time
from nextcord.ext import commands
from nextcord.utils import get
from pytubefix import YouTube, Search
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import re
from dotenv import load_dotenv
from nextcord import Interaction, SlashOption

current_song = {}

load_dotenv()

intents = nextcord.Intents.all()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, description="Tengo ansiedad", help_command=None)

queues = {}
last_text_channels = {}

client_id = os.environ.get("CLIENT_ID_SP")
client_secret = os.environ.get("CLIENT_SECRECT")
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

@bot.event
async def on_ready():
    await bot.change_presence(activity=nextcord.CustomActivity(name="🎵 Tengom Ansiemdamd 🎧"))
    print("✅ El bot está en línea")
    await bot.sync_all_application_commands()

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    voice_client = nextcord.utils.get(bot.voice_clients, guild=member.guild)

    if voice_client and voice_client.channel:
        if len(voice_client.channel.members) == 1 and voice_client.channel.members[0] == bot.user:
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            if member.guild.id in queues:
                queues[member.guild.id].clear()
            if member.guild.id in last_text_channels:
                last_channel = last_text_channels[member.guild.id]
                await last_channel.send("❌ Me desconecto, no hay nadie conectado ❌")
            await voice_client.disconnect()

async def stream_youtube_audio(interaction: Interaction, url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        audio_url = audio_stream.url

        duration = yt.length
        duration_str = time.strftime('%H:%M:%S', time.gmtime(duration))
        current_song[interaction.guild.id] = {
            'title': yt.title,
            'duration': duration_str,
            'url': url,
            'thumbnail': yt.thumbnail_url
        }

        voice_channel = interaction.user.voice.channel
        voice_client = get(bot.voice_clients, guild=interaction.guild)
        if voice_client and voice_client.is_connected():
            await voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect()

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel error',
            'options': '-vn',
            'stderr': open(os.devnull, 'w')
        }

        embed = nextcord.Embed(
            title="🎵 Reproduciendo ahora",
            description=f"[{yt.title}]({url})",
            color=nextcord.Color.blue()
        )
        embed.add_field(name="Duración", value=duration_str, inline=True)
        embed.set_thumbnail(url=yt.thumbnail_url)
        embed.set_footer(text=f"Solicitado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)

        voice_client.play(nextcord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
                          after=lambda e: asyncio.run_coroutine_threadsafe(after_play(interaction), bot.loop))

    except Exception as e:
        await interaction.followup.send(f"Ocurrió un error: {e}")

async def after_play(interaction: Interaction):
    voice_client = get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected() and not voice_client.is_playing():
        if interaction.guild.id in queues and len(queues[interaction.guild.id]) > 0:
            next_url = queues[interaction.guild.id].pop(0)
            current_song.pop(interaction.guild.id, None)
            await stream_youtube_audio(interaction, next_url)
        else:
            await asyncio.sleep(60)
            if voice_client and not voice_client.is_playing():
                await voice_client.disconnect()
                await interaction.channel.send("🔇 Me desconecto por inactividad.")

@bot.slash_command(name="play", description="Reproduce música desde YouTube o Spotify")
async def play_slash(interaction: Interaction, busqueda: str = SlashOption(description="URL o nombre de la canción", required=True)):
    await interaction.response.defer()
    last_text_channels[interaction.guild.id] = interaction.channel

    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal de voz para reproducir música. ❌")

    try:
        if re.match(r'https?://(?:open\.)?spotify\.com/.+', busqueda):
            track_id = busqueda.split('/')[-1].split('?')[0]
            track_info = sp.track(track_id)
            nombre_cancion = track_info['name']
            nombre_artista = track_info['artists'][0]['name']
            await interaction.followup.send(f"🔎 Buscando en YouTube: {nombre_cancion} - {nombre_artista}")
            spot = Search(nombre_cancion + " " + nombre_artista)
            results = spot.results
            if not results:
                return await interaction.followup.send("❌ No se encontraron resultados en YouTube. ❌")
            url = results[0].watch_url

        elif re.match(r'https?://(?:www\.)?youtube\.com/.+', busqueda) or re.match(r'https?://(?:www\.)?youtu\.be/.+', busqueda):
            url = busqueda
        else:
            await interaction.followup.send(f"🔎 Buscando: {busqueda}")
            s = Search(busqueda)
            results = s.results
            if not results:
                return await interaction.followup.send("❌ No se encontraron resultados. ❌")
            url = results[0].watch_url

        if interaction.guild.id not in queues:
            queues[interaction.guild.id] = []

        queues[interaction.guild.id].append(url)

        voice_client = get(bot.voice_clients, guild=interaction.guild)
        if not voice_client or not voice_client.is_playing():
            await stream_youtube_audio(interaction, queues[interaction.guild.id].pop(0))
        else:
            yt = YouTube(url)
            embed = nextcord.Embed(
                title="🎵 Añadido a la cola",
                description=f"[{yt.title}]({url})",
                color=nextcord.Color.green()
            )
            embed.add_field(name="Posición en cola", value=str(len(queues[interaction.guild.id])))
            embed.set_thumbnail(url=yt.thumbnail_url)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al procesar la solicitud: {str(e)}")

@bot.slash_command(name="skip", description="Salta la canción actual")
async def skip_slash(interaction: Interaction):
    await interaction.response.defer()
    last_text_channels[interaction.guild.id] = interaction.channel
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal para usar este comando ❌")

    voice_client = get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.followup.send("⏭️ Canción saltada.")
    else:
        await interaction.followup.send("❌ No hay nada reproduciendo actualmente.")

@bot.slash_command(name="pause", description="Pausa la reproducción actual")
async def pause_slash(interaction: Interaction):
    await interaction.response.defer()
    last_text_channels[interaction.guild.id] = interaction.channel
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal para usar este comando ❌")

    voice_client = get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.followup.send("⏸️ Canción en pausa.")
    else:
        await interaction.followup.send("❌ No hay nada reproduciendo actualmente para pausar.")

@bot.slash_command(name="resume", description="Reanuda la reproducción")
async def resume_slash(interaction: Interaction):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal para usar este comando ❌")

    voice_client = get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.followup.send("▶️ Reproducción reanudada.")
    else:
        await interaction.followup.send("❌ No hay ninguna canción en pausa para reanudar.")

@bot.slash_command(name="stop", description="Detiene la reproducción y limpia la cola")
async def stop_slash(interaction: Interaction):
    await interaction.response.defer()
    last_text_channels[interaction.guild.id] = interaction.channel
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal para usar este comando ❌")

    voice_client = get(bot.voice_clients, guild=interaction.guild)
    if voice_client:
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
        if interaction.guild.id in queues:
            queues[interaction.guild.id].clear()
        await voice_client.disconnect()
        await interaction.followup.send("🛑 Reproducción detenida y cola eliminada.")
    else:
        await interaction.followup.send("❌ No hay nada reproduciendo actualmente para detener.")

@bot.slash_command(name="queue", description="Muestra la cola de reproducción")
async def queue_slash(interaction: Interaction):
    await interaction.response.defer()
    last_text_channels[interaction.guild.id] = interaction.channel
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal para usar este comando ❌")
    
    embed = nextcord.Embed(title="🎶 Cola de Reproducción", color=nextcord.Color.gold())
    
    song_playing = current_song.get(interaction.guild.id)
    if song_playing:
        embed.add_field(
            name="🔊 Reproduciendo ahora",
            value=f"[{song_playing['title']}]({song_playing['url']})\nDuración: {song_playing['duration']}",
            inline=False
        )
        embed.set_thumbnail(url=song_playing['thumbnail'])
    else:
        embed.add_field(name="🔊 Reproduciendo ahora", value="Nada", inline=False)
    
    if interaction.guild.id in queues and queues[interaction.guild.id]:
        queue_list = []
        for i, url in enumerate(queues[interaction.guild.id], start=1):
            try:
                yt = YouTube(url)
                duration = time.strftime('%H:%M:%S', time.gmtime(yt.length))
                queue_list.append(f"{i}. [{yt.title}]({url}) ({duration})")
            except:
                queue_list.append(f"{i}. [Error al cargar información]")
        
        queue_text = "\n".join(queue_list[:10])
        if len(queues[interaction.guild.id]) > 10:
            queue_text += f"\n\n...y {len(queues[interaction.guild.id]) - 10} más"
        
        embed.add_field(name="📃 Próximas canciones", value=queue_text or "La cola está vacía", inline=False)
    else:
        embed.add_field(name="📃 Próximas canciones", value="La cola está vacía", inline=False)
    
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    await interaction.followup.send(embed=embed)

@bot.slash_command(name="now", description="Muestra la canción actual")
async def now_slash(interaction: Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal para usar este comando ❌")
    
    song_info = current_song.get(interaction.guild.id)
    if not song_info:
        return await interaction.followup.send("No hay ninguna canción reproduciéndose actualmente.")
    
    embed = nextcord.Embed(
        title="🎵 Reproduciendo ahora",
        description=f"[{song_info['title']}]({song_info['url']})",
        color=nextcord.Color.blue()
    )
    embed.add_field(name="Duración", value=song_info['duration'], inline=True)
    embed.set_thumbnail(url=song_info['thumbnail'])
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.followup.send(embed=embed)

@bot.slash_command(name="remove", description="Elimina una canción de la cola")
async def remove_slash(
    interaction: Interaction,
    numero: int = SlashOption(description="Número de la canción a eliminar", required=True)
):
    await interaction.response.defer()
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Necesitas estar en el canal para usar este comando ❌")

    if interaction.guild.id not in queues or not queues[interaction.guild.id]:
        return await interaction.followup.send("No hay elementos en la cola de reproducción.")

    try:
        index = numero - 1
        if 0 <= index < len(queues[interaction.guild.id]):
            url = queues[interaction.guild.id][index]
            yt = YouTube(url)
            title = yt.title
            del queues[interaction.guild.id][index]
            
            embed = nextcord.Embed(
                title="🗑️ Canción eliminada",
                description=f"**{title}** fue eliminada de la cola",
                color=nextcord.Color.red()
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("No hay ninguna canción con ese número. Prueba usar el comando **`/queue`**.")
    except Exception as e:
        await interaction.followup.send(f"Error al procesar la solicitud: {str(e)}")

@bot.slash_command(name="help", description="Muestra la ayuda del bot")
async def help_slash(interaction: Interaction):
    await interaction.response.defer()
    
    embed = nextcord.Embed(
        title="🎵 Ayuda del Bot de Música",
        description="Lista de comandos disponibles:",
        color=nextcord.Color.green()
    )
    
    commands_list = [
        ("/play [URL/búsqueda]", "Reproduce una canción de YouTube o Spotify"),
        ("/pause", "Pausa la canción actual"),
        ("/resume", "Reanuda la reproducción"),
        ("/skip", "Salta la canción actual"),
        ("/stop", "Detiene la reproducción y limpia la cola"),
        ("/queue", "Muestra la cola de reproducción"),
        ("/now", "Muestra la canción actual"),
        ("/remove [número]", "Elimina una canción específica de la cola"),
        ("/help", "Muestra este mensaje")
    ]
    
    for name, value in commands_list:
        embed.add_field(name=name, value=value, inline=False)
    
    embed.set_footer(text="¡Disfruta de la música!")
    await interaction.followup.send(embed=embed)

@bot.slash_command(name="sync", description="Sincroniza los comandos del bot")
async def sync_slash(interaction: Interaction):
    await interaction.response.defer()
    await bot.sync_all_application_commands()
    await interaction.followup.send("✅ Comandos sincronizados!")

@bot.slash_command(name="ping", description="Muestra la latencia del bot")
async def ping_slash(interaction: Interaction):
    await interaction.response.defer()
    latency = round(bot.latency * 1000)
    await interaction.followup.send(f"🏓 Pong! Latencia: {latency}ms")

bot.run(os.environ.get("TOKEN"))