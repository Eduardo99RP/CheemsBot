import asyncio
import discord
from discord.ext import commands
from discord.utils import get
from pytube import YouTube
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, description="Tengo ansiedad")

queues = {}

@bot.event
async def on_ready():
    print("✅ El bot esta en linea")

async def download_and_play_audio(ctx, url):
    try:
        # Obtener el directorio actual del script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Cambiar al directorio del script
        os.chdir(script_dir)

        # Descargar el video de YouTube
        yt = YouTube(url)
        video = yt.streams.get_highest_resolution()
        video_filename = f"{ctx.guild.id}_video_descargado.mp4"
        audio_filename = f"{ctx.guild.id}_audio_extraido.mp3"

        # Verificar si el archivo de audio ya existe y eliminarlo si es necesario
        if os.path.exists(audio_filename):
            os.remove(audio_filename)

        video.download(filename=video_filename)

        # Extraer el audio del video
        os.system(f'ffmpeg -y -i "{video_filename}" -vn -acodec libmp3lame "{audio_filename}"')

        # Reproducir el audio en el canal de voz del autor
        voice_channel = ctx.author.voice.channel
        voice_client = get(bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_connected():
            await voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect()

        voice_client.play(discord.FFmpegPCMAudio(audio_filename), after=lambda e: print('done', e))

        # Esperar hasta que la reproducción del audio termine
        while voice_client.is_playing():
            await asyncio.sleep(1)

        # Eliminar los archivos después de reproducir el audio
        print("Archivos eliminados: ", video_filename, audio_filename)
        os.remove(video_filename)
        os.remove(audio_filename)

        # Revisar si hay más elementos en la cola
        if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
            next_url = queues[ctx.guild.id].pop(0)
            await download_and_play_audio(ctx, next_url)

    except Exception as e:
        await ctx.send(f"Ocurrió un error: {e}")

@bot.command()
async def play(ctx, *, url: str = None):
    # Verifica si se proporciona una URL
    if url is None:
        await ctx.send("¡Debes proporcionar una URL para reproducir!")
        return

    # Verifica si el autor del mensaje está en un canal de voz
    if ctx.author.voice:
        # Verificar si hay una cola de reproducción para este servidor
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []

        # Agregar la URL a la cola de reproducción
        queues[ctx.guild.id].append(url)

        # Si no hay ningún audio reproduciéndose, iniciar la reproducción
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await download_and_play_audio(ctx, queues[ctx.guild.id].pop(0))
    else:
        await ctx.send("¡Debes estar en un canal de voz para usar este comando!")

@bot.command()
async def q(ctx):
    if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
        queue_content = "\n".join(queues[ctx.guild.id])
        await ctx.send(f"**Cola de reproducción:**\n{queue_content}")
    else:
        await ctx.send("No hay elementos en la cola de reproducción.")

bot.run(os.environ.get("TOKEN"))
