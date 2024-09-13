from random import choice
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


DIFFERNT_COLOURS_TELL_APART_FROM_EACH_OTHER = (
    (76, 255, 0),
    (88, 24, 69),
    (173, 35, 35),
    (255, 0, 110),
    (41, 208, 208),
    (255, 205, 243),
    (0, 63, 0),
    (255, 146, 51),
    (42, 75, 215),
    (233, 222, 187),
    (87, 87, 87),
    (157, 175, 255),
    (160, 160, 160),
    (255, 238, 51),
    (129, 74, 25),
    (129, 197, 122)
)


def unique_level_badge_image() -> Image:
    level_icon_time = Image.new('RGBA', (512, 512), (0,0,0,255))
    I1 = ImageDraw.Draw(level_icon_time)

    # "88:88:88am\n88/88/8888"
    I1.text((66, 180),datetime.utcnow().strftime("%I:%M:%S%p\n%d/%m/%Y"), fill=(0xFF, 0xFF, 0xFF), font=ImageFont.truetype('arial.ttf', 73))


    start_x_bottom = [115,325]
    start_y_bottom = [154,353]
    for _ in range(2):
        SQUARE_LENGHT = start_y_bottom[0] - start_x_bottom[0]
        SQUARE_HEIGHT = start_y_bottom[1] - start_x_bottom[1]

        start_x = list(start_x_bottom)
        start_y = list(start_y_bottom)

        for i in range(7):
            draw = ImageDraw.Draw(level_icon_time)
            draw.rectangle((tuple(start_x), tuple(start_y)), fill=choice(DIFFERNT_COLOURS_TELL_APART_FROM_EACH_OTHER))
            
            start_x[0] += SQUARE_LENGHT
            start_y[0] += SQUARE_LENGHT


        start_x = list(start_x_bottom)
        start_y = list(start_y_bottom)

        start_x[1] += SQUARE_HEIGHT
        start_y[1] += SQUARE_HEIGHT

        for i in range(7):
            draw = ImageDraw.Draw(level_icon_time)
            draw.rectangle((tuple(start_x), tuple(start_y)), fill=choice(DIFFERNT_COLOURS_TELL_APART_FROM_EACH_OTHER))
            
            start_x[0] += SQUARE_LENGHT
            start_y[0] += SQUARE_LENGHT
        
        start_x_bottom[1] = 132
        start_y_bottom[1] = 159
    return level_icon_time


if __name__ == '__main__':
    unique_level_badge_image().show()
