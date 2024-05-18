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

token = os.environ.get("TOKEN")
@bot.event
async def on_ready():
    print("✅ El bot está en línea")

async def stream_youtube_audio(ctx, url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
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
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=lambda e: asyncio.run_coroutine_threadsafe(after_play(ctx), bot.loop))

    except Exception as e:
        await ctx.send(f"Ocurrió un error: {e}")

async def after_play(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client and not voice_client.is_playing():
        if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
            next_url = queues[ctx.guild.id].pop(0)
            await stream_youtube_audio(ctx, next_url)
        else:
            await voice_client.disconnect()

@bot.command()
async def play(ctx, *, url: str = None):
    # Verifica si se proporciona una URL
    if url is None:
        await ctx.reply("¡Debes proporcionar una URL para reproducir!")
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
            await stream_youtube_audio(ctx, queues[ctx.guild.id].pop(0))
    else:
        await ctx.reply("❌ Necesitas estar en el canal de voz para reproduccir Música. ❌")

@bot.command()
async def q(ctx):
    if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
        queue_content = []
        for i, url in enumerate(queues[ctx.guild.id], start=1):
            try:
                yt = YouTube(url)
                title = yt.title
                queue_content.append(f"{i}. {title}")
            except Exception as e:
                queue_content.append(f"{i}. Error obteniendo título para {url}: {e}")
        
        queue_text = "\n".join(queue_content)
        await ctx.reply(f"**Próximas canciones a reproducir:**\n{queue_text}")
    else:
        await ctx.reply("No hay elementos en la cola de reproducción.")

bot.run(token)
