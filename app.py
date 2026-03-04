
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import gurobipy as gp
from gurobipy import GRB
import math
import json
from datetime import datetime
import itertools
import pandas as pd
import os
import io
import requests
import random
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from flask import send_file, request
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors


OPENWEATHER_API_KEY = os.environ.get("8ac59134c80b6ba9b1ebbed5c8b312d8")

# พิกัดอำเภอเมืองเชียงใหม่
LAT_MUEANG = 18.7883
LON_MUEANG = 98.9853

# พิกัดอำเภอแม่ริม
LAT_MAE_RIM = 18.8997
LON_MAE_RIM = 98.9440

def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&exclude=current,minutely,hourly,alerts&tz=+07:00"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()



app = Flask(__name__)
app.secret_key = 'chiang-mai-trip-planner-secret-key-2025'
CORS(app)

# ===============================
# Utility
# ===============================
def parse_hhmm(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m

def minutes_to_hhmm(m):
    h = int(m // 60)
    mm = int(m % 60)
    return f"{h:02d}:{mm:02d}"

# ============================================
# ข้อมูลโรงแรมและสถานที่ท่องเที่ยว (จากไฟล์ Jupyter)
# ============================================

HOTELS = [
    # --------- อำเภอเมือง ---------
    {"name": "โรงแรมเชียงใหม่ฮิลล์", "name_en": "Chiang Mai Hill Hotel", "location": "18.7971,98.9636", "district": "เมือง"},
    {"name": "โรงแรมฟูราม่า เชียงใหม่", "name_en": "Furama Chiang Mai", "location": "18.7996,98.9629", "district": "เมือง"},
    {"name": "โรงแรมยู นิมมาน เชียงใหม่", "name_en": "U Nimman Hotel Chiang Mai", "location": "18.8005,98.9677", "district": "เมือง"},
    {"name": "โรงแรมเชียงใหม่ออร์คิด", "name_en": "Chiang Mai Orchid Hotel", "location": "18.7952,98.9686", "district": "เมือง"},
    {"name": "โรงแรมโลตัส ปางสวนแก้ว", "name_en": "Lotus Pang Suan Kaew Hotel", "location": "18.7955,98.9685", "district": "เมือง"},
    {"name": "โรงแรมดวงตะวัน เชียงใหม่", "name_en": "Duang Tawan Hotel Chiang Mai", "location": "18.7860,98.9931", "district": "เมือง"},
    {"name": "โรงแรมเชียงใหม่พลาซ่า", "name_en": "Chiang Mai Plaza Hotel", "location": "18.7855,98.9954", "district": "เมือง"},
    {"name": "โรงแรมอโมรา ท่าแพ เชียงใหม่", "name_en": "Amoora Thapae Hotel Chiang Mai", "location": "18.7886,98.9931", "district": "เมือง"},
    {"name": "โรงแรมเดอะเอ็มเพรส เชียงใหม่", "name_en": "The Empress Hotel Chiang Mai", "location": "18.7768,98.9936", "district": "เมือง"},
    {"name": "โรงแรมเลอเมอริเดียน เชียงใหม่", "name_en": "Le Meridien Chiang Mai", "location": "18.7843,98.9944", "district": "เมือง"},
    {"name": "โรงแรมไอบิส สไตล์ เชียงใหม่", "name_en": "Ibis Styles Chiang Mai", "location": "18.8034,98.9720", "district": "เมือง"},
    {"name": "โรงแรมแคนทารี ฮิลส์ เชียงใหม่", "name_en": "Kantary Hills Hotel Chiang Mai", "location": "18.7998,98.9630", "district": "เมือง"},
    {"name": "โรงแรมวีเชียงใหม่", "name_en": "V Hotel Chiang Mai", "location": "18.7932,98.9963", "district": "เมือง"},

    # --------- อำเภอแม่ริม ---------
    {"name": "แม่ริมลากูนโฮเต็ล", "name_en": "Mae Rim Lagoon Hotel", "location": "18.9085,98.9362", "district": "แม่ริม"},
    {"name": "แม่ริมฮิลล์โฮเต็ล", "name_en": "Mae Rim Hill Hotel", "location": "18.8954,98.9448", "district": "แม่ริม"},
    {"name": "แม่ริมแพนชั่น", "name_en": "Mae Rim Pension", "location": "18.9001,98.9487", "district": "แม่ริม"},
    {"name": "บ้านแม่ริมรีสอร์ท", "name_en": "Ban Mae Rim Resort", "location": "18.9048,98.9403", "district": "แม่ริม"},
    {"name": "แม่ริมวิลล่า", "name_en": "Mae Rim Villa", "location": "18.9067,98.9422", "district": "แม่ริม"},
    {"name": "บ้านสวนแม่ริม", "name_en": "Ban Suan Mae Rim", "location": "18.8993,98.9505", "district": "แม่ริม"},
    {"name": "แม่ริมการ์เด้นโฮเต็ล", "name_en": "Mae Rim Garden Hotel", "location": "18.8990,98.9453", "district": "แม่ริม"},
    {"name": "แม่ริมบูทีคโฮเต็ล", "name_en": "Mae Rim Boutique Hotel", "location": "18.9022,98.9478", "district": "แม่ริม"},
    {"name": "โรงแรมริมธาร รีสอร์ท แม่ริม", "name_en": "Rimthar Resort Mae Rim", "location": "18.9039,98.9385", "district": "แม่ริม"},
    {"name": "โรงแรมภูวนาลี รีสอร์ท แม่ริม", "name_en": "Phuvanali Resort Mae Rim", "location": "18.9024,98.9408", "district": "แม่ริม"},
    {"name": "โรงแรมภูผา แม่ริม", "name_en": "Phu Pha Hotel Mae Rim", "location": "18.9080,98.9430", "district": "แม่ริม"},
    {"name": "โรงแรมบ้านสวน แม่ริม", "name_en": "Ban Suan Hotel Mae Rim", "location": "18.9042,98.9470", "district": "แม่ริม"},
    {"name": "โรงแรมต้นกล้า แม่ริม", "name_en": "Ton Gla Hotel Mae Rim", "location": "18.9017,98.9466", "district": "แม่ริม"},
]

# สถานที่ท่องเที่ยว 
PLACES = [
 # --------- ธรรมชาติ ---------
    {"name": "ห้วยตึงเฒ่า", "name_en": "Huai Tung Tao", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 20, "cost_thai_senior": 20,
     "cost_foreigner": 20, "cost_foreigner_adult": 20, "cost_foreigner_child": 20, "cost_foreigner_senior": 20,
     "open": "07:00", "close": "18:00", "day_close": "-", "recommend_time": 90,
     "location": "18.86849483,98.94027689", "district": "แม่ริม", "rating": 4.4},

    {"name": "อ่างแก้ว มช.", "name_en": "Ang Kaew MCU", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "05:00", "close": "22:00", "day_close": "-", "recommend_time": 60,
     "location": "18.80612291,98.95089494", "district": "เมือง", "rating": 4.7},

    {"name": "สวนพฤกษศาสตร์สมเด็จพระนางเจ้าสิริกิติ์", "name_en": "Suan Phak Sod Phra Nang Sirikit", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 40, "cost_thai_adult": 40, "cost_thai_child": 20, "cost_thai_senior": 40,
     "cost_foreigner": 100, "cost_foreigner_adult": 100, "cost_foreigner_child": 50, "cost_foreigner_senior": 100,
     "open": "08:30", "close": "16:30", "day_close": "-", "recommend_time":120,
     "location": "18.88823753,98.86185229", "district": "แม่ริม", "rating": 4.6},

    {"name": "ปางช้างแม่สา", "name_en": "Pang Chang Mae Sa", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 100, "cost_thai_adult": 100, "cost_thai_child": 100, "cost_thai_senior": 100,
     "cost_foreigner": 300, "cost_foreigner_adult": 300, "cost_foreigner_child": 300, "cost_foreigner_senior": 300,
     "open": "08:30", "close": "16:00", "day_close": "-", "recommend_time": 60,
     "location": "18.89999556,98.87562347", "district": "แม่ริม", "rating": 4.2},

    {"name": "น้ำตกแม่สา", "name_en": "Mae Sa Waterfall", "category": "ธรรมชาติ", "type": "outdoor",
      "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 10, "cost_thai_senior": 20,
      "cost_foreigner": 100, "cost_foreigner_adult": 100, "cost_foreigner_child": 50, "cost_foreigner_senior": 100,
      "open": "08:30", "close": "16:30", "day_close": "-", "recommend_time": 60,
      "location": "18.90645968,98.89719978", "district": "แม่ริม", "rating": 4.4},

    {"name": "สวนสัตว์เชียงใหม่", "name_en": "Chiang Mai Zoo", "category": "ธรรมชาติ", "type": "indoor",
     "cost": 130, "cost_thai_adult": 130, "cost_thai_child": 40, "cost_thai_senior": 130,
     "cost_foreigner": 350, "cost_foreigner_adult": 350, "cost_foreigner_child": 120, "cost_foreigner_senior": 350,
     "open": "08:00", "close": "17:00", "day_close": "-", "recommend_time": 120,
     "location": "18.81066322,98.94795790", "district": "เมือง", "rating": 3.9},

    {"name": "Tiger Kingdom", "name_en": "Tiger Kingdom", "category": "ธรรมชาติ", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "17:00", "day_close": "-", "recommend_time": 60,
     "location": "18.92481703,98.93202634", "district": "แม่ริม", "rating": 4.0,
     "price_note": "ราคาเป็นไปตามแพ็กเกจ"},

    {"name": "Elephant POOPOOPAPER Park Chiang Mai", "name_en": "Elephant POOPOOPAPER Park", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 150, "cost_thai_adult": 150, "cost_thai_child": 150, "cost_thai_senior": 150,
     "cost_foreigner": 150, "cost_foreigner_adult": 150, "cost_foreigner_child": 150, "cost_foreigner_senior": 150,
     "open": "08:30", "close": "17:15", "day_close": "-", "recommend_time": 60,
     "location": "18.92575681,98.93153906", "district": "แม่ริม", "rating": 4.5},

    {"name": "สวนสัตว์แมลงสยาม", "name_en": "Siam Insect Museum", "category": "ธรรมชาติ", "type": "indoor",
     "cost": 100, "cost_thai_adult": 100, "cost_thai_child": 60, "cost_thai_senior": 100,
     "cost_foreigner": 200, "cost_foreigner_adult": 200, "cost_foreigner_child": 150, "cost_foreigner_senior": 200,
     "open": "09:00", "close": "17:00", "day_close": "-", "recommend_time": 90,
     "location": "18.91822404,98.90850500", "district": "แม่ริม", "rating": 4.5},

    {"name": "Pongyang Jungle Coaster Zipline", "name_en": "Pongyang Jungle Coaster", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:30", "close": "17:00", "day_close": "-", "recommend_time": 120,
     "location": "18.91714823,98.82146999", "district": "แม่ริม", "rating": 4.4,
     "price_note": "ราคาเป็นไปตามแพ็กเกจ"},

    {"name": "น้ำตกมณฑาธาร", "name_en": "Montatharn Waterfall", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 10, "cost_thai_senior": 20,
     "cost_foreigner": 100, "cost_foreigner_adult": 100, "cost_foreigner_child": 50, "cost_foreigner_senior": 100,
     "open": "08:00", "close": "16:30", "day_close": "-", "recommend_time": 60,
     "location": "18.82271026,98.91733075", "district": "เมือง", "rating": 4.4},

    {"name": "อุทยานแห่งชาติสุเทพ-ปุย", "name_en": "Doi Suthep-Pui National Park", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 10, "cost_thai_senior": 20,
     "cost_foreigner": 100, "cost_foreigner_adult": 100, "cost_foreigner_child": 50, "cost_foreigner_senior": 100,
     "open": "08:30", "close": "16:30", "day_close": "-", "recommend_time": 60,
     "location": "18.80720832,98.91609596", "district": "เมือง", "rating": 4.5},

    {"name": "เส้นทางเดินป่าดอยเทพ (วัดผาลาด)", "name_en": "Doi Suthep Trail (Wat Pha Lad)", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 10, "cost_thai_senior": 20,
     "cost_foreigner": 100, "cost_foreigner_adult": 100, "cost_foreigner_child": 50, "cost_foreigner_senior": 100,
     "open": "00:00", "close": "23:59", "day_close": "-", "recommend_time": 180,
     "location": "18.79958763,98.93214330", "district": "เมือง", "rating": 4.2},

    {"name": "สวนสาธารณะ อบจ.เชียงใหม่", "name_en": "CMU Park", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "00:00", "close": "23:59", "day_close": "-", "recommend_time": 60,
     "location": "18.83218611,98.96746293", "district": "เมือง", "rating": 4.7},

    {"name": "ช้างทองเฮอริเทจพาร์ค", "name_en": "Chaang Thong Heritage Park", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 150, "cost_thai_adult": 150, "cost_thai_child": 150, "cost_thai_senior": 150,
     "cost_foreigner": 250, "cost_foreigner_adult": 250, "cost_foreigner_child": 250, "cost_foreigner_senior": 250,
     "open": "09:00", "close": "19:00", "day_close": "-", "recommend_time": 60,
     "location": "18.86199204,98.99234915", "district": "เมือง", "rating": 4.5},

    {"name": "บ้านแกะแม่ขิ", "name_en": "Baan Gaae Mae Khi", "category": "ธรรมชาติ", "type": "outdoor",
     "cost": 100, "cost_thai_adult": 100, "cost_thai_child": 100, "cost_thai_senior": 100,
     "cost_foreigner": 100, "cost_foreigner_adult": 100, "cost_foreigner_child": 100, "cost_foreigner_senior": 100,
     "open": "07:30", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.95544637,98.80066768", "district": "แม่ริม", "rating": 4.6},

    {"name": "เชียงใหม่ไนท์ซาฟาริ", "name_en": "Chiang Mai Night Safari", "category": "ธรรมชาติ", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "11:00", "close": "22:00", "day_close": "-", "recommend_time":120,
     "location": "18.74257382,98.91723290", "district": "เมือง", "rating": 4.2,
     "price_note": "ราคาเป็นไปตามแพ็กเกจ"},

    {"name": "อุทยานหลวงราชพฤกษ", "name_en": "Royal Agriculture Project", "category": "ธรรมชาติ", "type": "indoor",
     "cost": 100, "cost_thai_adult": 100, "cost_thai_child": 50, "cost_thai_senior": 100,
     "cost_foreigner": 200, "cost_foreigner_adult": 200, "cost_foreigner_child": 100, "cost_foreigner_senior": 200,
     "open": "08:00", "close": "18:00", "day_close": "-", "recommend_time": 120,
     "location": "18.74487301,98.92798398", "district": "เมือง", "rating": 4.5},
    {"name": "Merino Sheep Farm Chiang Mai", "name_en": "Merino Sheep Farm", "category": "ธรรมชาติ", "type": "indoor",
     "cost": 100, "cost_thai_adult": 100, "cost_thai_child": 100, "cost_thai_senior": 100,
     "cost_foreigner": 100, "cost_foreigner_adult": 100, "cost_foreigner_child": 100, "cost_foreigner_senior": 100,
     "open": "08:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.89273441,98.8557597", "district": "แม่ริม", "rating": 4.4},
       # --------- วัฒนธรรม ---------

    {"name": "วัดอุโมงค์", "name_en": "Wat Umong", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "04:00", "close": "20:00", "day_close": "-", "recommend_time": 60,
     "location": "18.78325112,98.95208180", "district": "เมือง", "rating": 4.6},

    {"name": "วัดผาลาด (สกิทาคามี)", "name_en": "Wat Pha Lad", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "06:00", "close": "17:30", "day_close": "-", "recommend_time": 60,
     "location": "18.80004563,98.93416733", "district": "เมือง", "rating": 4.8},

    {"name": "วัดพระธาตุดอยคำ", "name_en": "Wat Phra That Doi Kham", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "06:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.75968231,98.91869801", "district": "เมือง", "rating": 4.7},

    {"name": "วัดป่าแดด", "name_en": "Wat Pa Daed", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:30", "close": "17:00", "day_close": "-", "recommend_time": 60,
     "location": "18.75181567,98.98603349", "district": "เมือง", "rating": 4.7},

    {"name": "วัดพระสิงห์ วรมหาวิหาร", "name_en": "Wat Phra Singh", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "05:30", "close": "19:30", "day_close": "-", "recommend_time": 60,
     "location": "18.78861575,98.98214929", "district": "เมือง", "rating": 4.7},

    {"name": "วัดเชียงม่วน", "name_en": "Wat Chiang Mun", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "07:00", "close": "19:00", "day_close": "-", "recommend_time": 60,
     "location": "18.79393448,98.98927566", "district": "เมือง", "rating": 4.6},

    {"name": "พิพิธภัณฑ์พื้นถิ่นลานนา", "name_en": "Lanna Folklore Museum", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 10, "cost_thai_senior": 20,
     "cost_foreigner": 90, "cost_foreigner_adult": 90, "cost_foreigner_child": 40, "cost_foreigner_senior": 90,
     "open": "08:30", "close": "16:30", "day_close": "Monday,Tuesday", "recommend_time": 90,
     "location": "18.79038914,98.98842574", "district": "เมือง", "rating": 4.8},

    {"name": "พิพิธภัณฑสถานแห่งชาติ เชียงใหม่", "name_en": "Chiang Mai National Museum", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 20, "cost_thai_senior": 20,
     "cost_foreigner": 200, "cost_foreigner_adult": 200, "cost_foreigner_child": 200, "cost_foreigner_senior": 200,
     "open": "09:00", "close": "16:00", "day_close": "Monday,Tuesday", "recommend_time":90,
     "location": "18.81124305,98.97646252", "district": "เมือง", "rating": 4.2},

    {"name": "พิพิธภัณฑ์พระตำนักดารภิรมย์", "name_en": "Phra Tamnak Dara Bhirom", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 20, "cost_thai_adult": 20, "cost_thai_child": 20, "cost_thai_senior": 20,
     "cost_foreigner": 20, "cost_foreigner_adult": 20, "cost_foreigner_child": 20, "cost_foreigner_senior": 20,
     "open": "09:00", "close": "17:00", "day_close": "Monday,Tuesday", "recommend_time": 90,
     "location": "18.91305768,98.94256433", "district": "แม่ริม", "rating": 4.7},

    {"name": "วัดป่าดารภิรมย์", "name_en": "Wat Pa Dara Bhirom", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "06:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.91087395,98.94136742", "district": "แม่ริม", "rating": 4.8},

    {"name": "ประตูท่าแพ", "category": "วัฒนธรรม", "type": "outdoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "00:00", "close": "23:59", "day_close": "-", "recommend_time": 60,
     "location": "18.78791397,98.99334218", "district": "เมือง", "rating": 4.3},

    {"name": "ถนนคนเดินวัวลาย", "category": "วัฒนธรรม", "type": "outdoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "18:00", "close": "23:00", "day_close": "Monday,Tuesday,Wednesday,Thursday,Friday,Sunday", "recommend_time":90,
     "location": "18.78109836,98.98776256", "district": "เมือง", "rating": 4.5},

    {"name": "ถนนคนเดินท่าแพ", "name_en": "Tha Pae Walking Street", "category": "วัฒนธรรม", "type": "outdoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "17:00", "close": "22:30", "day_close": "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday", "recommend_time":90,
     "location": "18.78791397,98.99334218", "district": "เมือง", "rating": 4.5},

    {"name": "วัดโลกโมฬี", "name_en": "Wat Loke Molee", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "06:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.79615634,98.98273380", "district": "เมือง", "rating": 4.7},

    {"name": "วัดอินทราวาส (วัดต้นเกว๋น)", "name_en": "Wat Intravasi", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "06:00", "close": "17:00", "day_close": "-", "recommend_time": 60,
     "location": "18.72286331,98.92599004", "district": "เมือง", "rating": 4.8},

    {"name": "หมู่บ้านม้งดอยปุย", "name_en": "Hmong Village", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:00", "close": "17:00", "day_close": "-", "recommend_time":90,
     "location": "18.81668639,98.88351018", "district": "เมือง", "rating": 4.2},

    {"name": "ตลาดวโรรส", "name_en": "Warorot Market", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "06:00", "close": "18:00", "day_close": "-", "recommend_time": 90,
     "location": "18.79011348,99.00139873", "district": "เมือง", "rating": 4.4},

    {"name": "วัดเจดีย์หลวงวรวิหาร", "category": "วัฒนธรรม", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "05:00", "close": "22:30", "day_close": "-", "recommend_time": 60,
     "location": "18.78715213,98.98691836", "district": "เมือง", "rating": 4.7},
         # --------- สร้างสรรค์ ---------
    {"name": "The Baristro x Ping River", "name_en": "The Baristro x Ping River", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.81601271,99.00025561", "district": "เมือง", "rating": 4.6},

    {"name": "บ้านข้างวัด", "name_en": "Baan Khang Wad", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "10:00", "close": "18:00", "day_close": "Monday", "recommend_time":90,
     "location": "18.77656939,98.94885188", "district": "เมือง", "rating": 4.5},

    {"name": "ลานดิน", "name_en": "Laan Din", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:00", "close": "20:00", "day_close": "-", "recommend_time": 60,
     "location": "18.77463208,98.94671635", "district": "เมือง", "rating": 4.4},

    {"name": "วันนิมมาน", "name_en": "One Nimman", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "11:00", "close": "22:00", "day_close": "-", "recommend_time": 60,
     "location": "18.80010693,98.96748243", "district": "เมือง", "rating": 4.5},

    {"name": "Arte Café", "name_en": "Arte Café", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "17:00", "day_close": "Thursday", "recommend_time": 60,
     "location": "18.81080089,98.96705292", "district": "เมือง", "rating": 4.7},

    {"name": "Thong urai & Paw Made Painting", "name_en": "Thong urai & Paw Made Painting", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:30", "close": "17:00", "day_close": "-", "recommend_time": 60,
     "location": "18.78522662,98.96968804", "district": "เมือง", "rating": 4.9},

    {"name": "fringe.th", "name_en": "Fringe.th", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:30", "close": "00:00", "day_close": "-", "recommend_time": 60,
     "location": "18.79429360,99.00162522", "district": "เมือง", "rating": 4.6},

    {"name": "graph contemporary", "name_en": "Graph Contemporary", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "17:00", "day_close": "-", "recommend_time": 60,
     "location": "18.78723317,99.00877618", "district": "เมือง", "rating": 4.5},

    {"name": "early owls", "name_en": "Early Owls", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "18:30", "day_close": "Wednesday", "recommend_time": 60,
     "location": "18.80598327,98.98925987", "district": "เมือง", "rating": 4.6},

    {"name": "enough for life", "name_en": "Enough for Life", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:30", "close": "17:00", "day_close": "-", "recommend_time": 60,
     "location": "18.77297178,98.94898242", "district": "เมือง", "rating": 4.5},

    {"name": "Brewginning coffee", "name_en": "Brewginning Coffee", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "07:00", "close": "19:00", "day_close": "-", "recommend_time": 60,
     "location": "18.79047603,98.99477125", "district": "เมือง", "rating": 4.6},

    {"name": "จริงใจมาร์เก็ต เชียงใหม่", "name_en": "Jing Jai Market", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:00", "close": "10:00", "day_close": "Monday,Tuesday,Wednesday,Thursday,Friday", "recommend_time": 90,
     "location": "18.80613674,98.99566006", "district": "เมือง", "rating": 4.5},

    {"name": "Chic Ruedoo", "name_en": "Chic Ruedoo", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:00", "close": "17:00", "day_close": "Wednesday", "recommend_time": 60,
     "location": "18.76504895,98.99906774", "district": "เมือง", "rating": 4.8},

    {"name": "99 Villa café", "name_en": "99 Villa Cafe", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.76757046,98.93838687", "district": "เมือง", "rating": 4.9},

    {"name": "The Baristro Asian Style", "name_en": "The Baristro Asian Style", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.79025261,98.95170775", "district": "เมือง", "rating": 4.7},

    {"name": "Fernpresso at lake", "name_en": "Fernpresso at Lake", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "07:45", "close": "17:15", "day_close": "-", "recommend_time": 60,
     "location": "18.76167876,98.93495016", "district": "เมือง", "rating": 4.6},

    {"name": "Forest Bake", "name_en": "Forest Bake", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:30", "close": "17:00", "day_close": "Wednesday", "recommend_time": 60,
     "location": "18.79245894,99.00482539", "district": "เมือง", "rating": 4.2},

    {"name": "Think Park", "name_en": "Think Park", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "00:00", "day_close": "-", "recommend_time": 60,
     "location": "18.80156176,98.96761281", "district": "เมือง", "rating": 4.3},

    {"name": "More Space", "name_en": "More Space", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "17:00", "close": "00:00", "day_close": "Monday,Friday,Saturday,Sunday", "recommend_time":90   ,
     "location": "18.79473248,98.96408482", "district": "เมือง", "rating": 4.3},

    {"name": "Neighborhood Community", "name_en": "Neighborhood Community", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "12:00", "close": "00:00", "day_close": "-", "recommend_time": 60,
     "location": "18.79033704,98.99418875", "district": "เมือง", "rating": 4.7},

    {"name": "Mori Natural farm", "name_en": "Mori Natural Farm", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "08:00", "close": "22:00", "day_close": "Tuesday,Wednesday", "recommend_time": 60,
     "location": "18.86722629,98.8313452", "district": "แม่ริม", "rating": 4.4},

    {"name": "WTF coffee Camp", "name_en": "WTF Coffee Camp", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.87365129,98.81335585", "district": "แม่ริม", "rating": 4.5},

      {"name": "Fleur Café & Eatery", "name_en": "Fleur Cafe & Eatery", "category": "สร้างสรรค์", "type": "indoor",
     "cost": 0, "cost_thai_adult": 0, "cost_thai_child": 0, "cost_thai_senior": 0,
     "cost_foreigner": 0, "cost_foreigner_adult": 0, "cost_foreigner_child": 0, "cost_foreigner_senior": 0,
     "open": "09:00", "close": "18:00", "day_close": "-", "recommend_time": 60,
     "location": "18.90720065,98.90717316", "district": "แม่ริม", "rating": 4.7},
]

def minutes_to_hhmm(m):
    if m is None:
        return "-"
    h = int(m // 60)
    mm = int(m % 60)
    return f"{h:02d}:{mm:02d}"
# ============================================
# ฟังก์ชันช่วยเหลือ
# ============================================

def haversine_km(loc1: str, loc2: str) -> float:
    lat1, lon1 = map(float, loc1.split(","))
    lat2, lon2 = map(float, loc2.split(","))
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def parse_hhmm(s, default_min=8*60):
    try:
        h, m = map(int, s.split(":"))
        return h * 60 + m
    except:
        return default_min

def minutes_to_ampm(mins):
    if mins is None or mins < 0:
        return "00:00 AM"
    mins = int(round(mins))
    h = mins // 60
    m = mins % 60
    suffix = "AM" if h < 12 else "PM"
    display_h = h % 12
    if display_h == 0:
        display_h = 12
    return f"{display_h:02d}:{m:02d} {suffix}"

# ============================================
# Routes
# ============================================
def dist(a, b):
    R = 6371  # km
    dlat = math.radians(b["lat"] - a["lat"])
    dlon = math.radians(b["lon"] - a["lon"])
    x = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a["lat"]))
        * math.cos(math.radians(b["lat"]))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(x))
@app.route('/')
def cover():
    lang = request.args.get('lang', 'th')
    return render_template('cover.html', lang=lang)

@app.route('/main')
def main():

    lang = request.args.get('lang', 'th')
    # ส่งข้อมูลโรงแรมเป็น JSON string

    weather_mueang = get_weather(LAT_MUEANG, LON_MUEANG)
    weather_mae_rim = get_weather(LAT_MAE_RIM, LON_MAE_RIM)
    def estimate_rain_prob(w):
        main = w["weather"][0]["main"].lower()
        clouds = w.get("clouds", {}).get("all", 0)
        humidity = w.get("main", {}).get("humidity", 0)

        # ถ้ามีฝนจริง
        if "rain" in w:
            return 1

        # main เป็น rain
        if main in ["rain", "drizzle", "thunderstorm"]:
            return 0.8

        # เมฆเต็ม ฟ้าปิด และความชื้นสูง
        if clouds >= 90 and humidity >= 95:
            return 0.5

        # เมฆเยอะ
        if clouds >= 75:
            return 0.3

        # ปกติ
        return 0.1
    
#“ค่า probability ที่ตั้ง เช่น 0.1, 0.3, 0.5, 0.8
#เป็น heuristic ที่อิงตามแนวโน้มจากงาน Tompkins (2005) ว่า
#RH และ cloud cover สูงสัมพันธ์กับโอกาสฝนเพิ่มขึ้นแบบ non-linear”
#https://www.ecmwf.int/sites/default/files/elibrary/2005/16958-parametrization-cloud-cover.pdf

# ตัวอย่างประเมิน
    prob_mueang = estimate_rain_prob(weather_mueang)
    prob_mae_rim = estimate_rain_prob(weather_mae_rim)

    try:
        hotels_data = json.dumps(HOTELS, ensure_ascii=False)
        places_data = json.dumps(PLACES, ensure_ascii=False)
        print(f"Sending {len(HOTELS)} hotels to main.html")
        return render_template(
            'main.html', 
            lang=lang,
            hotels_data=json.dumps(HOTELS, ensure_ascii=False),
            places_data=json.dumps(PLACES, ensure_ascii=False)
        )
    except Exception as e:
        print(f"Error in /main route: {str(e)}")
        return render_template('main.html', 
                             lang=lang,
                             hotels_data='[]',
                             places_data='[]')

@app.route('/result')
def result():
    lang = request.args.get('lang', 'th')
    return render_template('result.html', lang=lang)

# ===============================
# API: PLAN TRIP
# ===============================
@app.route('/api/plan', methods=['POST'])
def plan():
    try:
        data = request.get_json() or {}

        # ===============================
        # 1) INPUT
        # ===============================
        hotel_name = data.get("hotel")
        days = data.get("days", [])
        places_count = int(data.get("placesCount", 3))
        budget_total = float(data.get("budget", 1000))
        mode = data.get("mode", "rating")

        DAY_START = parse_hhmm(data.get("departTime", "09:00"))
        DAY_END   = parse_hhmm(data.get("returnTime", "18:00"))

        categories = data.get("categories", {})
        visitors = data.get("visitors", {})

        if not days:
            return jsonify({"status": "error", "message": "กรุณาเลือกวันเดินทาง"}), 400

        D = days
        N = places_count
        L = {d: budget_total / len(D) for d in D}

        hotel = next((h for h in HOTELS if h["name"] == hotel_name), None)
        if not hotel:
            return jsonify({"status": "error", "message": "ไม่พบโรงแรม"}), 400

        hotel_loc = hotel["location"]

        # ===============================
        # 2) FILTER PLACES
        # ===============================
        S_all = []
        for p in PLACES:
            if categories.get("culture") and p["category"] == "วัฒนธรรม":
                S_all.append(p)
            elif categories.get("nature") and p["category"] == "ธรรมชาติ":
                S_all.append(p)
            elif categories.get("creative") and p["category"] == "สร้างสรรค์":
                S_all.append(p)

        if not S_all:
            return jsonify({"status": "error", "message": "กรุณาเลือกประเภทสถานที่"}), 400

        U = {p["name"]: p.get("rating", 0) for p in S_all}
        S = sorted(U, key=U.get, reverse=True)[:10]
        N = min(N, len(S))
        V = [hotel_name] + S

        # ===============================
        # 3) TIME / COST
        # ===============================
        O = {p["name"]: parse_hhmm(p.get("open", "08:00")) for p in S_all if p["name"] in S}
        C = {p["name"]: parse_hhmm(p.get("close", "17:00")) for p in S_all if p["name"] in S}
        Tvisit = {p["name"]: p.get("recommend_time", 60) for p in S_all if p["name"] in S}

        Rate = {}
        for p in PLACES:
            if p["name"] in S:
                Rate[p["name"]] = sum(
                    p.get(f"cost_{k}", 0) * v for k, v in visitors.items()
                )

        loc_map = {hotel_name: hotel_loc}
        for p in PLACES:
            if p["name"] in S:
                loc_map[p["name"]] = p["location"]

        AVG_SPEED_KMH = 30
        KM_TO_MIN = 60 / AVG_SPEED_KMH
        BAHT_PER_KM = 5

        Tij, Cij = {}, {}
        for i in V:
            for j in V:
                if i != j:
                    km = haversine_km(loc_map[i], loc_map[j])
                    Tij[i, j] = km * KM_TO_MIN
                    Cij[i, j] = km * BAHT_PER_KM

        # ===============================
        # 4) MODEL
        # ===============================
        m = gp.Model("Trip")
        m.setParam("OutputFlag", 0)
        M = 100000

        X = m.addVars([(i, j, d) for i in V for j in V for d in D if i != j], vtype=GRB.BINARY)
        Y = m.addVars([(i, d) for i in S for d in D], vtype=GRB.BINARY)
        Tarr = m.addVars([(i, d) for i in S for d in D], lb=0)
        Tdep = m.addVars([(i, d) for i in S for d in D], lb=0)
        Uord = m.addVars([(i, d) for i in S for d in D], lb=1, ub=N)

        for d in D:
            m.addConstr(gp.quicksum(X[hotel_name, j, d] for j in S) == 1)
            m.addConstr(gp.quicksum(X[i, hotel_name, d] for i in S) == 1)
            m.addConstr(gp.quicksum(Y[i, d] for i in S) == N)

        for i in S:
            m.addConstr(gp.quicksum(Y[i, d] for d in D) <= 1)

        for d in D:
            for i in S:
                m.addConstr(gp.quicksum(X[j, i, d] for j in V if j != i) == Y[i, d])
                m.addConstr(gp.quicksum(X[i, j, d] for j in V if j != i) == Y[i, d])

                m.addConstr(Tdep[i, d] == Tarr[i, d] + Tvisit[i] * Y[i, d])
                m.addConstr(Tarr[i, d] >= O[i] * Y[i, d])
                m.addConstr(Tdep[i, d] <= C[i] + M * (1 - Y[i, d]))

        # 🔥 สำคัญที่สุด: เวลาไหลต่อเนื่อง i → j
        for d in D:
            for i in S:
                for j in S:
                    if i != j:
                        m.addConstr(
                            Tarr[j, d] >= Tdep[i, d] + Tij[i, j]
                            - M * (1 - X[i, j, d])
                        )

        for d in D:
            for j in S:
                m.addConstr(
                    Tarr[j, d] >= DAY_START + Tij[hotel_name, j]
                    - M * (1 - X[hotel_name, j, d])
                )
            for i in S:
                m.addConstr(
                    Tdep[i, d] + Tij[i, hotel_name]
                    <= DAY_END + M * (1 - X[i, hotel_name, d])
                )

        for d in D:
            for i in S:
                for j in S:
                    if i != j:
                        m.addConstr(Uord[i, d] - Uord[j, d] + N * X[i, j, d] <= N - 1)

        for d in D:
            m.addConstr(
                gp.quicksum(Rate[i] * Y[i, d] for i in S) +
                gp.quicksum(Cij[i, j] * X[i, j, d] for i in V for j in V if i != j)
                <= L[d]
            )

        Z1 = gp.quicksum(U[i] * Y[i, d] for i in S for d in D)
        Z2 = gp.quicksum(Tij[i, j] * X[i, j, d] for (i, j, d) in X.keys())
        Z3 = gp.quicksum(Cij[i, j] * X[i, j, d] for (i, j, d) in X.keys())

        m.setObjective(
            Z1 if mode == "rating" else Z2 if mode == "time" else Z3,
            GRB.MAXIMIZE if mode == "rating" else GRB.MINIMIZE
        )

        m.optimize()

        # ===============================
        # 5) OUTPUT
        # ===============================
        days_out = []
        total_cost = 0
        total_dist = 0
        ratings = []

        for d in D:
            visited = sorted(
                [i for i in S if Y[i, d].X > 0.5],
                key=lambda x: Tarr[x, d].X
            )

            route = [{
                "type": "hotel_start",
                "name": hotel_name,
                "depart": minutes_to_hhmm(DAY_START)
            }]

            prev = hotel_name
            for i in visited:
                dist = haversine_km(loc_map[prev], loc_map[i])
                route.append({
                    "type": "place",
                    "name": i,
                    "arrive": minutes_to_hhmm(Tarr[i, d].X),
                    "depart": minutes_to_hhmm(Tdep[i, d].X),
                    "stay": Tvisit[i],
                    "rating": U[i],
                    "cost": int(Rate[i]),
                    "distance": round(dist, 2)
                })
                total_cost += Rate[i] + Cij[prev, i]
                total_dist += dist
                ratings.append(U[i])
                prev = i

            back_time = Tdep[prev, d].X + Tij[prev, hotel_name]
            route.append({
                "type": "hotel_end",
                "name": hotel_name,
                "arrive": minutes_to_hhmm(min(back_time, DAY_END))
            })

            days_out.append({"date": d, "route": route})

        return jsonify({
            "hotel": hotel_name,
            "summary": {
                "total_rating": round(sum(ratings)/len(ratings), 1) if ratings else 0,
                "max_rating": 5,
                "total_distance": round(total_dist, 2),
                "total_cost": int(round(total_cost))
            },
            "days": days_out
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
print("### THIS app.py IS RUNNING ###")
