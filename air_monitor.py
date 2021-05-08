#!/usr/bin/env python

import RPi.GPIO as GPIO
import time
import busio
import adafruit_bme280
import adafruit_ssd1306
import adafruit_ccs811

from board import SCL, SDA
from PIL import Image, ImageDraw, ImageFont

# 定数
FONT_1 = ImageFont.truetype("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", 18, encoding='unic')
FONT_2 = ImageFont.truetype("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", 20, encoding='unic')
FONT_3 = ImageFont.truetype("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", 44, encoding='unic')
DISP_STATE_ECO2 = 0
DISP_STATE_TEMP = 1
DISP_STATE_TIME = 2
DISP_STATE_INFO = 3     # 状態遷移の判定に使用している。状態を追加する場合にはこれより上に挿入すること

LED = 4
SWITCH = 17

# 変数
count_on = 0
count_off = 0
switch_state = False
switch_trigger = False
disp_timer = 0
disp_state = 0

# GPIOセットアップ
GPIO.setmode(GPIO.BCM)
GPIO.setup(SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED, GPIO.OUT)

# I2C インタフェースの生成
i2c = busio.I2C(SCL, SDA)

# I2C デバイスインタフェースの初期化
ccs811 = adafruit_ccs811.CCS811(i2c, 0x5a)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
ssd1306 = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

# CCS811 が利用可能になるのを待つ
while not ccs811.data_ready:
    time.sleep(1)

# OLEDディスプレイの消去
ssd1306.fill(0)
ssd1306.show() 

try:
    while True:
        # スイッチ入力処理
        if switch_state:
            count_on = 0
            if GPIO.input(SWITCH) == 1:          # OFFのとき      
                count_off = count_off + 1
                if count_off >= 5:
                    switch_state = False    # OFF判定
            else:
                count_off = 0
        else:
            count_off = 0
            if GPIO.input(SWITCH) == 0:          # ONのとき
                count_on = count_on + 1
                if count_on == 5:
                    switch_state = True     # ON判定
                    switch_trigger = True
                elif count_on > 5:
                    switch_state = True
            else:
                count_on = 0

        # LED点灯処理
        if switch_state:
            GPIO.output(LED, GPIO.HIGH)    
        else:
            GPIO.output(LED, GPIO.LOW)

        # 画面状態遷移
        if switch_trigger:
            switch_trigger = False

            disp_state = disp_state + 1
            if disp_state > DISP_STATE_INFO:
                disp_state = DISP_STATE_ECO2

        # 表示処理
        disp_timer = disp_timer + 1
        if disp_timer >= 5:
            disp_timer = 0
            
            image = Image.new('1', (ssd1306.width, ssd1306.height))
            draw = ImageDraw.Draw(image)
            
            # CO2濃度・TVOC濃度
            if disp_state == DISP_STATE_ECO2:
                draw.text((2, 0), "CO2", font=FONT_1, fill=1)
                draw.text((2, 20), "%4d" % ccs811.eco2, font=FONT_3, fill=1)
                #draw.text((2, 20), "TVOC: %4d" % ccs811.tvoc, font=FONT_3, fill=1)

            # 温度・湿度・気圧
            elif disp_state == DISP_STATE_TEMP:
                draw.text((0, 0), "温度： %0.1fC" % bme280.temperature, font=FONT_1, fill=1) 
                draw.text((0, 20), "湿度： %0.1f%%" % bme280.humidity, font=FONT_1, fill=1)
                draw.text((0, 40), "気圧： %4d" % bme280.pressure, font=FONT_1, fill=1)

            # 現在時刻
            elif disp_state == DISP_STATE_TIME:
                draw.text((2, 0), time.strftime('%Y/%m/%d'), font=FONT_2, fill=1)
                draw.text((2, 20), time.strftime('%H:%M'), font=FONT_3, fill=1)

            # 情報
            else:
                draw.text((10, 20), "CO2センサ", font=FONT_2, fill=1)
            
            # 画面表示
            ssd1306.image(image)
            ssd1306.show()

        # 100ms待ち
        time.sleep(0.1)

except KeyboardInterrupt:
    # OLEDディスプレイの消去
    ssd1306.fill(0)
    ssd1306.show() 
    GPIO.cleanup()