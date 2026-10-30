from PIL import Image, ImageDraw
from pathlib import Path
p = Path('upload/presidency_360_dataset/video_extract')
frames = sorted(p.glob('frame_*.jpg'))
print('frames', len(frames))
W, H, per = 384, 260, 24
for start in range(0, len(frames), per):
    group = frames[start:start+per]
    sheet = Image.new('RGB', (W*6, H*4), 'white')
    draw = ImageDraw.Draw(sheet)
    for j, frame in enumerate(group):
        im = Image.open(frame)
        im.thumbnail((W, H-24))
        x, y = (j % 6)*W, (j // 6)*H
        sheet.paste(im, (x, y+24))
        draw.text((x+6, y+5), f'{(start+j)*3}s', fill='black')
    sheet.save(p / f'contact_{start//per+1:02}.jpg', quality=88)
