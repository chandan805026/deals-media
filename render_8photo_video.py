import os
import re
import requests
import json
import time
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
import io

SLIDES = [
    {
        'title': 'ECOFLOW DELTA 2',
        'sub': '1024WH PORTABLE POWER STATION',
        'url': 'https://m.media-amazon.com/images/I/61iaV79e+4L._AC_SL1500_.jpg'
    },
    {
        'title': '3D RUGGED DESIGN',
        'sub': 'DUAL GRIP HANDLES & PORTS',
        'url': 'https://m.media-amazon.com/images/I/71WwWvF8IkL._AC_SL1500_.jpg'
    },
    {
        'title': 'CAMPING & OFF-GRID',
        'sub': 'SOLAR & CAR FAST RECHARGING',
        'url': 'https://m.media-amazon.com/images/I/71mi1pltXaL._AC_SL1500_.jpg'
    },
    {
        'title': 'X-STREAM FAST CHARGE',
        'sub': '0 TO 80% IN 50 MINUTES',
        'url': 'https://m.media-amazon.com/images/I/71PjGLS+-aL._AC_SL1500_.jpg'
    },
    {
        'title': 'LIFEPO4 BATTERY SPECS',
        'sub': '3000+ CYCLES (10-YEAR LIFE)',
        'url': 'https://m.media-amazon.com/images/I/71VtlrjTfWL._AC_SL1500_.jpg'
    },
    {
        'title': '1800W AC POWER',
        'sub': 'RUNS 90% HOME APPLIANCES',
        'url': 'https://m.media-amazon.com/images/I/712iJNbH1rL._AC_SL1500_.jpg'
    },
    {
        'title': 'SMART APP CONTROL',
        'sub': 'WI-FI & BLUETOOTH MONITORING',
        'url': 'https://m.media-amazon.com/images/I/71prsiSvXTL._AC_SL1500_.jpg'
    },
    {
        'title': 'WHAT IN THE BOX',
        'sub': 'FULL CABLES & ACCESSORIES',
        'url': 'https://m.media-amazon.com/images/I/71FojCiDEFL._AC_SL1500_.jpg'
    }
]

VOICE_TEXT = (
    "Amazon flash deal alert! The EcoFlow Delta 2 power station just crashed in price. "
    "50-minute fast charging, 10-year LiFePO4 battery, and massive 1800W power output. "
    "Tap the verified link in bio before it sells out!"
)

async def generate_voice(text, out_path):
    com = edge_tts.Communicate(text, 'en-US-ChristopherNeural', rate='+14%')
    await com.save(out_path)

def get_audio_duration(file_path):
    probe = subprocess.run(['ffmpeg', '-i', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', probe.stderr)
    if m:
        return float(m.group(1))*3600 + float(m.group(2))*60 + float(m.group(3))
    return 16.0

def make_overlay(title, sub, out_path, font_path):
    im = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    try:
        font_headline = ImageFont.truetype(font_path, 68)
        font_sub = ImageFont.truetype(font_path, 42)
        font_cta = ImageFont.truetype(font_path, 52)
    except Exception:
        font_headline = font_sub = font_cta = ImageFont.load_default()

    # Top Bar (Red badge)
    d.rounded_rectangle([60, 130, 1020, 270], radius=24, fill=(225, 29, 72, 240))
    d.text((540, 175), 'AMAZON PRICE DROP', font=font_headline, fill='white', anchor='mm')
    d.text((540, 235), 'LIMITED TIME VIRAL DEAL', font=font_sub, fill=(254, 240, 138), anchor='mm')

    # Middle Feature Card (Slate dark)
    d.rounded_rectangle([60, 1380, 1020, 1580], radius=24, fill=(15, 23, 42, 235))
    d.text((540, 1445), title, font=font_headline, fill='white', anchor='mm')
    d.text((540, 1520), sub, font=font_sub, fill=(56, 189, 248), anchor='mm')

    # Bottom CTA Bar (Amber gold)
    d.rounded_rectangle([60, 1640, 1020, 1770], radius=24, fill=(245, 158, 11, 245))
    d.text((540, 1705), 'CHECK VERIFIED LINK IN BIO / PIN', font=font_cta, fill=(15, 23, 42), anchor='mm')

    im.save(out_path)

def main():
    print('=== Starting Cloud 8-Photo Video Generation ===')
    work_dir = 'build_tmp'
    os.makedirs(work_dir, exist_ok=True)

    # 1. Download Font
    font_path = os.path.join(work_dir, 'BebasNeue.ttf')
    if not os.path.exists(font_path):
        print('Downloading BebasNeue font...')
        r = requests.get('https://raw.githubusercontent.com/google/fonts/main/ofl/bebasneue/BebasNeue-Regular.ttf', timeout=10)
        with open(font_path, 'wb') as f:
            f.write(r.content)

    # 2. Generate Voiceover
    print('Generating edge-tts voiceover...')
    voice_path = os.path.join(work_dir, 'voice.mp3')
    asyncio.run(generate_voice(VOICE_TEXT, voice_path))
    voice_dur = get_audio_duration(voice_path)
    print(f'Voiceover duration: {voice_dur:.2f}s')

    # Calculate timing
    n_slides = len(SLIDES)
    clip_dur = max(1.8, voice_dur / n_slides)
    fps = 25
    clip_frames = int(clip_dur * fps)
    print(f'Rendering {n_slides} slides: {clip_dur:.2f}s ({clip_frames} frames each)')

    # 3. Process Each Slide
    clip_files = []
    for idx, s in enumerate(SLIDES):
        print(f"Processing slide {idx+1}/{n_slides}: {s['title']}")
        # Download image
        img_path = os.path.join(work_dir, f'img_{idx}.jpg')
        r = requests.get(s['url'], timeout=12)
        im = Image.open(io.BytesIO(r.content)).convert('RGB')
        im.save(img_path, 'JPEG')

        # Make Overlay
        overlay_path = os.path.join(work_dir, f'overlay_{idx}.png')
        make_overlay(s['title'], s['sub'], overlay_path, font_path)

        # Alternating Ken Burns zoom
        if idx % 2 == 0:
            zoom_expr = f"zoompan=z='min(zoom+0.002,1.12)':d={clip_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=880x880:fps=25[fg];"
        else:
            zoom_expr = f"zoompan=z='if(lte(zoom,1.0),1.12,max(1.0,zoom-0.002))':d={clip_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=880x880:fps=25[fg];"

        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.22,loop=loop={clip_frames}:size=1:start=0[bg];"
            f"[0:v]scale=880:880:force_original_aspect_ratio=decrease,pad=880:880:(ow-iw)/2:(oh-ih)/2:color=black@0,"
            + zoom_expr +
            f"[bg][fg]overlay=(W-w)/2:460:shortest=1[base];"
            f"[base][1:v]overlay=0:0[v]"
        )

        out_clip = os.path.join(work_dir, f'clip_{idx}.mp4')
        cmd = [
            'ffmpeg', '-y',
            '-i', img_path,
            '-i', overlay_path,
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-frames:v', str(clip_frames),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            out_clip
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f'Error rendering clip {idx}:', res.stderr[-200:])
            raise RuntimeError(f'Clip {idx} render failed')
        clip_files.append(out_clip)

    # 4. Concatenate Clips
    print('Concatenating 8 motion clips...')
    concat_txt = os.path.join(work_dir, 'concat.txt')
    with open(concat_txt, 'w') as f:
        for c in clip_files:
            f.write(f"file '{os.path.abspath(c)}'\n")

    merged_mp4 = os.path.join(work_dir, 'merged.mp4')
    subprocess.run([
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_txt,
        '-c', 'copy',
        merged_mp4
    ], check=True)

    # 5. Master Pass: Mix Audio + Background Music
    print('Final Master Assembly (Voice + BGM)...')
    bgm_path = 'bgm.mp3'
    final_output = 'ecoflow_8images_pro_video.mp4'

    if os.path.exists(bgm_path):
        audio_filter = '[1:a]volume=1.0[voice];[2:a]volume=0.15[bgm];[voice][bgm]amix=inputs=2:duration=first[aout]'
        cmd = [
            'ffmpeg', '-y',
            '-i', merged_mp4,
            '-i', voice_path,
            '-stream_loop', '-1', '-i', bgm_path,
            '-filter_complex', audio_filter,
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            final_output
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-i', merged_mp4,
            '-i', voice_path,
            '-map', '0:v',
            '-map', '1:a',
            '-c:v', 'copy',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            final_output
        ]

    subprocess.run(cmd, check=True)
    size_mb = os.path.getsize(final_output) / (1024 * 1024)
    print(f'🎉 SUCCESS! Rendered Master Video: {final_output} ({size_mb:.2f} MB)')

if __name__ == '__main__':
    main()
