# DaiP智能聊天室 - 主应用文件
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
from functools import wraps

# 登录检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import random
import re
import requests
from datetime import datetime
from config import *
import os
import base64
from flask_cors import CORS
import sqlite3
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG
app.config['DATABASE'] = 'users.db'

# 初始化数据库
def init_db():
    with app.app_context():
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 检查是否已有管理员用户，如果没有则创建
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
        if cursor.fetchone()[0] == 0:
            # 创建默认管理员用户，密码为admin888
            hashed_password = hashlib.sha256('admin888'.encode()).hexdigest()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_password))
            print('已创建默认管理员账户: admin/admin888')
        conn.commit()
        conn.close()

# 数据库连接助手函数
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# 密码哈希函数
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 初始化SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=False  # 让Flask管理会话
)

# 会话中间件，确保会话持久化
@app.before_request
def make_session_permanent():
    session.permanent = True

# 存储在线用户信息
online_users = {}  # session_id -> username
# 存储房间信息
room_users = {}  # room -> [usernames]

# 电影搜索API地址（示例地址，请根据实际情况修改）
MOVIE_SEARCH_API = "https://api.example.com/search"
# 电影解析服务地址
MOVIE_PARSER_URL = "https://x.m3u8.tv/jiexi/?url="

# 音乐API地址
MUSIC_API_URL = "https://v2.xxapi.cn/api/randomkuwo"

# AI助手配置
AI_API_KEY = "sk-oefvpllopkqejwazfmaqdysoffcdcpcvtoxqdconizqxpoah"
AI_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
AI_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
AI_ASSISTANT_NAME = "川小农"

# 存储AI会话上下文
ai_conversation_history = []

# AI助手回复逻辑 - 对接SiliconFlow大模型API
def ai_assistant_response(message):
    # 准备优化的系统提示词，强调精准回答问题
    system_prompt = """
    你是四川农业大学的智能助手川小农，乐于为用户提供帮助。
    你的首要任务是精准理解用户意图，并直接回答问题。
    回答时，必须先给出问题的核心答案，再视情况补充相关信息。
    保持对话的自然性与亲和力，避免机械复述。
    使用准确、有用的信息，避免答非所问。
    记住：回答必须以'川小农：'开头
    """
    
    # 构建消息列表，包含系统提示和历史对话
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # 添加历史对话，最多保留最近5轮对话以维持上下文
    recent_history = ai_conversation_history[-10:]  # 保留最近10条消息（5轮对话）
    messages.extend(recent_history)
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": message})
    
    try:
        # 调用SiliconFlow AI模型API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}"
        }
        
        # 构建请求数据，按照SiliconFlow API文档格式
        payload = {
            "model": AI_MODEL_NAME,
            "messages": messages,
            "stream": True  # 启用SSE流式响应
        }
        
        print(f"准备调用SiliconFlow API: {AI_API_URL}")
        print(f"使用模型: {AI_MODEL_NAME}")
        print(f"请求消息数量: {len(messages)}")
        
        # 发送POST请求，启用流式响应
        response = requests.post(
            AI_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60  # 设置超时时间
        )
        
        # 检查响应状态
        if response.status_code == 200:
            response_text = ""
            # 处理SSE响应流
            for chunk in response.iter_lines():
                if chunk:
                    # 解码响应块
                    chunk_str = chunk.decode('utf-8')
                    # 处理SSE格式的数据块
                    if chunk_str.startswith('data:'):
                        chunk_data = chunk_str[5:].strip()
                        if chunk_data == '[DONE]':
                            break
                        try:
                            # 解析JSON数据
                            json_chunk = json.loads(chunk_data)
                            # 按照SiliconFlow API文档的响应格式提取内容
                            if 'choices' in json_chunk and json_chunk['choices']:
                                choice = json_chunk['choices'][0]
                                if 'message' in choice:
                                    # 非流式响应格式
                                    response_text += choice['message'].get('content', '')
                                elif 'delta' in choice:
                                    # 流式响应格式
                                    response_text += choice['delta'].get('content', '')
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {e}, 数据: {chunk_data}")
                            continue
                        except Exception as e:
                            print(f"处理响应块错误: {e}")
                            continue
            
            # 如果成功获取到回复，返回它
            if response_text.strip():
                print(f"AI回复内容: {response_text[:100]}...")
                # 确保回复以"川小农："开头
                if not response_text.strip().startswith("川小农："):
                    response_text = "川小农：" + response_text.strip()
                
                # 更新会话历史
                ai_conversation_history.append({"role": "user", "content": message})
                ai_conversation_history.append({"role": "assistant", "content": response_text})
                
                # 限制历史记录长度
                if len(ai_conversation_history) > 20:  # 最多保留10轮对话
                    ai_conversation_history = ai_conversation_history[-20:]
                
                return response_text.strip()
            else:
                print("未获取到AI回复内容")
        else:
            print(f"API调用失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"HTTP请求错误: {str(e)}")
        # 详细错误信息
        if hasattr(e, 'response'):
            print(f"响应状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
    except Exception as e:
        print(f"AI API调用其他错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 备用逻辑 - 如果API调用失败，使用本地回复
    print("使用备用本地回复逻辑")
    message_lower = message.lower()
    
    # 确保所有回复都以"川小农："开头
    response = ""
    
    # 检查是否是关于其他学校的问题
    other_schools = ["清华", "北大", "复旦", "交大", "浙大", "南京大学"]
    for school in other_schools:
        if school in message_lower:
            response = "川小农：哼，我只关心四川农业大学！😜"
            break
    
    # 检查是否是关于四川农业大学的问题
    if not response and any(keyword in message_lower for keyword in ["四川农业大学", "川农", "川农大", "四川农大"]):
        # 生成与四川农业大学相关的回答，确保直接回答问题
        if "在哪" in message_lower or "地址" in message_lower:
            response = "川小农：四川农业大学有三个校区：主校区位于四川省雅安市雨城区新康路46号，成都校区位于成都市温江区惠民路211号，都江堰校区位于都江堰市建设路288号。"
        elif "历史" in message_lower or "前身" in message_lower:
            response = "川小农：四川农业大学的前身是1906年创办的四川通省农业学堂，是中国西南地区最早的高等农业学府之一。2017年入选国家'双一流'建设高校。"
        elif "特色" in message_lower or "优势" in message_lower or "学科" in message_lower:
            response = "川小农：四川农业大学是以生物科技为特色，农业科技为优势的重点大学。兽医学、作物学、畜牧学等学科是学校的优势学科，其中畜牧学、作物学、兽医学入选国家'双一流'建设学科。"
        else:
            response = "川小农：四川农业大学是国家'双一流'建设高校，拥有三个校区：雅安、成都和都江堰。学校以生物科技为特色，农业科技为优势，是一所在国内外具有重要影响力的农业高等学府。"
    
    # 检查是否要求生成古诗
    if not response and any(keyword in message_lower for keyword in ["古诗", "写诗", "七言", "诗句"]):
        # 生成七言风格的古诗
        poems = [
            "川小农：春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。",
            "川小农：床前明月光，疑是地上霜。举头望明月，低头思故乡。",
            "川小农：白日依山尽，黄河入海流。欲穷千里目，更上一层楼。",
            "川小农：两个黄鹂鸣翠柳，一行白鹭上青天。窗含西岭千秋雪，门泊东吴万里船。",
            "川小农：日照香炉生紫烟，遥看瀑布挂前川。飞流直下三千尺，疑是银河落九天。"
        ]
        response = random.choice(poems)
    
    # 检查是否要求生成通知
    if not response and any(keyword in message_lower for keyword in ["通知", "公告", "告示"]):
        # 生成学校通知格式
        notice_types = ["举办学术讲座", "开展校园活动", "发放奖学金", "进行安全检查", "组织体检"]
        notice_type = random.choice(notice_types)
        response = f"川小农：关于{notice_type}的通知\n\n全校师生：\n\t为了丰富校园文化生活，提升同学们的综合素质，学校决定{notice_type}。请相关同学积极参与，准时参加。\n\t特此通知。\n\t四川农业大学学生处\n\t{random.randint(2024, 2025)}年{random.randint(1, 12)}月{random.randint(1, 28)}日"
    
    # 默认回复
    if not response:
        response = "川小农：这个问题我不知道呀~"
    
    # 更新会话历史
    ai_conversation_history.append({"role": "user", "content": message})
    ai_conversation_history.append({"role": "assistant", "content": response})
    
    # 限制历史记录长度
    if len(ai_conversation_history) > 20:  # 最多保留10轮对话
        ai_conversation_history = ai_conversation_history[-20:]
    
    return response

# 天气查询功能
def get_weather(city):
    # 调用天气API
    try:
        # 使用提供的天气API接口
        weather_api_url = "https://v2.xxapi.cn/api/weatherDetails"
        params = {"city": city, "key": "42f2fb6b4b032edd"}
        headers = {'User-Agent': 'xiaoxiaoapi/1.0.0'}
        response = requests.get(weather_api_url, params=params, headers=headers, timeout=10)
        
        # 检查响应状态
        if response.status_code == 200:
            data = response.json()
            print(f"天气API响应: {data}")
            # 解析天气数据
            if data.get("code") == 200 and data.get("data"):
                weather_data = data["data"]
                city_name = weather_data.get("city", city)
                
                # 获取当天的天气数据
                if weather_data.get("data") and isinstance(weather_data["data"], list) and weather_data["data"]:
                    today_data = weather_data["data"][0]
                    
                    # 获取实时天气数据（使用最新的一个）
                    real_time_data = None
                    if today_data.get("real_time_weather") and isinstance(today_data["real_time_weather"], list) and today_data["real_time_weather"]:
                        real_time_data = today_data["real_time_weather"][0]  # 使用最新的实时数据
                    
                    # 提取关键信息
                    weather_desc = real_time_data.get("weather", "未知") if real_time_data else today_data.get("weather_from", "未知")
                    temperature = f"{real_time_data.get('temperature')}°C" if real_time_data and real_time_data.get('temperature') else f"{today_data.get('high_temp')}°C"
                    humidity = real_time_data.get("humidity", "未知") if real_time_data else "未知"
                    wind = f"{real_time_data.get('wind_dir', '')} {real_time_data.get('wind_speed', '')}" if real_time_data else f"{today_data.get('wind_from', '')} {today_data.get('wind_level_from', '')}"
                    
                    # 返回格式化的天气信息
                    weather_info = {
                        "city": city_name,
                        "weather": weather_desc,
                        "temperature": temperature,
                        "humidity": humidity,
                        "wind": wind,
                        "status": "晴"  # 默认状态
                    }
                    
                    # 根据天气描述判断天气状态
                    weather_desc_lower = weather_desc.lower()
                    if any(word in weather_desc_lower for word in ["晴", "sun"]):
                        weather_info["status"] = "晴"
                    elif any(word in weather_desc_lower for word in ["雨", "rain"]):
                        weather_info["status"] = "雨"
                    elif any(word in weather_desc_lower for word in ["雪", "snow"]):
                        weather_info["status"] = "雪"
                    elif any(word in weather_desc_lower for word in ["阴", "cloudy"]):
                        weather_info["status"] = "阴"
                    elif any(word in weather_desc_lower for word in ["雾", "fog"]):
                        weather_info["status"] = "雾"
                    
                    return weather_info
            else:
                print(f"天气API返回错误: {data.get('msg', '未知错误')}")
        else:
            print(f"天气API请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"天气查询错误: {str(e)}")
    
    # 模拟天气数据（备用）
    # 根据不同城市生成不同的随机天气
    # 使用城市名的哈希值来确保同一城市总是返回相同的模拟天气
    import hashlib
    city_hash = int(hashlib.md5(city.encode()).hexdigest(), 16) % 100
    
    weather_options = ["晴", "雨", "雪", "阴", "多云", "雾"]
    # 根据城市哈希值选择天气，确保同一城市总是返回相同的天气
    weather_status = weather_options[city_hash % len(weather_options)]
    
    weather_descs = {
        "晴": "晴朗",
        "雨": "小雨",
        "雪": "小雪",
        "阴": "阴天",
        "多云": "多云",
        "雾": "雾"
    }
    
    # 根据天气设置不同的温度范围
    temperature_ranges = {
        "晴": (20, 35),
        "雨": (10, 20),
        "雪": (-10, 5),
        "阴": (15, 25),
        "多云": (18, 30),
        "雾": (5, 15)
    }
    
    # 使用城市哈希值生成温度，确保同一城市温度一致
    min_temp, max_temp = temperature_ranges[weather_status]
    temp_hash = int(hashlib.md5((city + weather_status).encode()).hexdigest(), 16) % 100
    temperature = min_temp + (temp_hash / 100) * (max_temp - min_temp)
    temperature_str = f"{round(temperature)}°C"
    
    # 生成湿度
    humidity_options = ["45%", "55%", "65%", "75%", "85%"]
    humidity = humidity_options[city_hash % len(humidity_options)]
    
    # 生成风力
    wind_options = ["微风", "北风3级", "东风2级", "西南风4级", "东北风1级"]
    wind = wind_options[city_hash % len(wind_options)]
    
    return {
        "city": city,
        "weather": weather_descs[weather_status],
        "temperature": temperature_str,
        "humidity": humidity,
        "wind": wind,
        "status": weather_status
    }

# 音乐API地址
MUSIC_API_URL = 'https://v2.xxapi.cn/api/randomkuwo'

# 音乐获取功能
def get_music():
    # 直接返回小幸运的音乐信息，不调用API
    xiaoxingyun_music = {
        "title": "小幸运",
        "artist": "田馥甄",
        "album": "我的少女时代 电影原声带",
        "cover": "/temp_cover.jpg",
        "play_url": "https://music.163.com/song/media/outer/url?id=1436702243.mp3"
    }
    
    print(f"直接返回音乐数据: {xiaoxingyun_music['title']} - {xiaoxingyun_music['artist']}")
    return xiaoxingyun_music

# 每日新闻获取功能
import urllib.parse

def get_news():
    # 每日新闻API URL
    NEWS_API_URL = 'http://apis.uctb.cn/api/60s?format=json'
    # 百度搜索引擎URL
    BAIDU_SEARCH_URL = 'https://www.baidu.com/s?wd='
    
    try:
        # 添加必要的headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }
        
        response = requests.get(NEWS_API_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查返回的数据格式是否正确
            if data.get('code') == 200 and data.get('data'):
                news_data = data['data']
                
                # 确保news字段存在并且是列表
                if 'news' in news_data and isinstance(news_data['news'], list):
                    formatted_news = []
                    for news_item in news_data['news']:
                        # 统一处理不同格式的新闻项
                        if isinstance(news_item, dict):
                            # 如果是对象格式，确保有title和search_url
                            title = news_item.get('title', str(news_item))
                        else:
                            # 如果是字符串格式，转换为对象格式
                            title = str(news_item)
                        
                        # 确保为每个新闻项添加搜索链接
                        encoded_title = urllib.parse.quote(title)
                        formatted_news.append({
                            "title": title,
                            "search_url": BAIDU_SEARCH_URL + encoded_title
                        })
                    
                    # 替换原始新闻列表为格式化后的列表
                    news_data['news'] = formatted_news
                
                return news_data
        
    except Exception:
        # 静默处理所有异常
        pass
    
    # 返回默认的新闻数据作为备用
    backup_news = [
        "今日暂无新闻数据，请稍后再试。",
        "您可以通过点击@每日新闻按钮随时获取最新资讯。",
        "感谢使用每日新闻功能！"
    ]
    
    # 为备用新闻添加搜索链接
    news_with_search = []
    for news_item in backup_news:
        encoded_title = urllib.parse.quote(news_item)
        news_with_search.append({
            "title": news_item,
            "search_url": BAIDU_SEARCH_URL + encoded_title
        })
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "news": news_with_search,
        "tip": "保持信息更新，洞察世界变化。"
    }



# 电影搜索功能
def search_movie(movie_name):
    try:
        # 1. 调用电影搜索API
        search_params = {'q': movie_name}
        search_response = requests.get(MOVIE_SEARCH_API, params=search_params, timeout=10)
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            
            # 假设API返回的数据结构中包含playUrl字段
            if 'playUrl' in search_data:
                play_url = search_data['playUrl']
                return play_url
        
        # 搜索失败或无结果时返回示例视频
        return 'https://v.qq.com/x/cover/mzc002007v41t9b.html'
    except Exception as e:
        print(f"电影搜索错误: {str(e)}")
        # 异常情况下返回示例视频
        return 'https://v.qq.com/x/cover/mzc002007v41t9b.html'

# 哈希密码函数
# 验证用户函数
def validate_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and user[0] == hash_password(password):
        return True
    return False

@app.route('/')
def index():
    # 清除可能的旧会话，确保用户从登录页面开始
    if 'logged_in' in session:
        session.clear()
    # 渲染登录页面
    return render_template('login.html', servers=SERVERS)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        server = request.form.get('server')
        
        if not username or not password or not server:
            return render_template('login.html', servers=SERVERS, error="用户名、密码和服务器地址不能为空")
        
        # 验证用户
        if validate_user(username, password):
            # 清除旧会话并创建新会话
            session.clear()
            session['logged_in'] = True
            session['username'] = username
            session['server'] = server
            print(f"用户 {username} 登录成功")
            return redirect(url_for('chat'))
        else:
            print(f"用户 {username} 登录失败")
            return render_template('login.html', servers=SERVERS, error="用户名或密码错误")
    
    return render_template('login.html', servers=SERVERS)

@app.route('/chat')
@login_required
def chat():
    # 确保登录状态有效
    if 'logged_in' not in session or not session['logged_in'] or 'username' not in session:
        print("会话无效，重定向到登录页面")
        return redirect(url_for('login'))
    
    # 获取会话中的服务器地址
    server = session.get('server', 'localhost:9999')  # 使用当前端口
    
    # 渲染聊天室页面
    return render_template('chat.html', username=session['username'], server=server)

@app.route('/logout')
def logout():
    # 清除会话
    session.clear()
    return redirect(url_for('login'))

@app.route('/check_username', methods=['POST'])
def check_username():
    username = request.json.get('username')
    # 检查数据库中是否已存在该用户名
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
    db_exists = cursor.fetchone()[0] > 0
    conn.close()
    # 同时检查在线用户列表
    online_exists = username in online_users.values()
    return jsonify({
        'exists': db_exists or online_exists
    })

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', servers=SERVERS, register_error="用户名和密码不能为空")
        
        # 检查用户名是否已存在
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return render_template('login.html', servers=SERVERS, register_error="用户名已存在")
        
        # 哈希密码
        hashed_password = hash_password(password)
        
        # 将新用户插入数据库
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            print(f"新用户 {username} 注册成功")
            # 注册成功后自动登录
            session.clear()
            session['logged_in'] = True
            session['username'] = username
            session['server'] = request.form.get('server', 'localhost:5010')
            return redirect(url_for('chat'))
        except sqlite3.Error as e:
            conn.close()
            print(f"注册失败: {e}")
            return render_template('login.html', servers=SERVERS, register_error="注册失败，请稍后重试")
    
    return render_template('login.html', servers=SERVERS)

# 获取服务器列表
@app.route('/get_servers', methods=['GET'])
def get_servers():
    # 返回配置文件中的服务器列表
    return jsonify({
        'servers': SERVERS
    })

@app.route('/temp_cover.jpg')
def temp_cover():
    # 从static/images目录返回temp_cover.jpg文件
    static_images_path = os.path.join(os.getcwd(), 'static', 'images')
    return send_from_directory(static_images_path, 'temp_cover.jpg')

@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(os.getcwd(), 'static')
    return send_from_directory(static_dir, filename)

# WebSocket事件处理

@socketio.on('connect')
def handle_connect():
    print(f'客户端连接: {request.sid}')
    # 不立即验证，等待join事件
    return True  # 允许所有连接尝试

@socketio.on('disconnect')
def handle_disconnect():
    # 获取断开连接的用户信息
    user_session = request.sid
    username = online_users.get(user_session)
    
    if username:
        # 从在线用户列表中移除
        del online_users[user_session]
        
        # 从房间用户列表中移除
        if 'chat_room' in room_users:
            if username in room_users['chat_room']:
                room_users['chat_room'].remove(username)
        
        # 广播用户离开消息
        emit('user_left', {
            'username': username,
            'online_users': room_users.get('chat_room', [])
        }, broadcast=True)
        
        print(f'用户 {username} 已离开')
        # 清除会话
        session.clear()

@socketio.on('join')
def handle_join(data):
    # 验证用户登录状态
    if 'logged_in' not in session or not session['logged_in']:
        print(f"未登录用户尝试加入聊天室: {request.sid}")
        emit('login_required', {'error': '请先登录'})
        return
    
    # 从session中获取用户名和服务器
    username = session.get('username')
    server = session.get('server')
    
    # 检查用户名是否有效
    if not username:
        emit('error', {'message': '用户未登录，请重新登录'})
        return
    
    # 检查用户名是否已被其他会话使用
    if username in online_users.values():
        emit('error', {'message': '用户名已被使用，请重新登录'})
        return
    
    # 将用户添加到在线用户列表
    online_users[request.sid] = username
    
    # 如果房间不存在，则创建房间
    if 'chat_room' not in room_users:
        room_users['chat_room'] = []
    
    # 将用户添加到房间
    room_users['chat_room'].append(username)
    join_room('chat_room')
    
    # 广播用户加入消息
    emit('user_joined', {'username': username}, broadcast=True)
    
    # 更新在线用户列表
    emit('join_success', {
        'message': f'{username} 进入了聊天室',
        'online_users': room_users['chat_room']
    }, broadcast=True)
    
    # 发送历史消息
    # 注意：如果messages变量在代码中不存在，这个功能可能需要额外实现
    # emit('history_messages', {
    #     'messages': [message for message in messages if message['room'] == 'chat_room']
    # })
    
    # 发送用户进入通知
    emit('notification', {
        'message': f'{username} 进入了聊天室',
        'type': 'join'
    }, broadcast=True)
    
    print(f'用户 {username} 已加入聊天室')

@socketio.on('send_message')
def handle_message(data):
    username = data['username']
    message = data['message']
    timestamp = data['timestamp']
    
    # 检查是否是@听音乐指令
    if message == '@听音乐':
        # 先将用户消息正常广播出去
        emit('new_message', {
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'at_user': '听音乐'  # 标记为@听音乐的消息
        }, broadcast=True)
        
        # 调用音乐获取函数
        music_info = get_music()
        
        # 广播音乐信息
        emit('music_response', {
            'username': username,
            'music_info': music_info,
            'timestamp': timestamp
        }, broadcast=True)
        return
        
    # 检查是否是@每日新闻指令
    if message == '@每日新闻':
        # 先将用户消息正常广播出去
        emit('new_message', {
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'at_user': '每日新闻'  # 标记为@每日新闻的消息
        }, broadcast=True)
        
        # 调用每日新闻获取函数
        news_data = get_news()
        
        # 广播新闻信息
        emit('news_response', {
            'username': username,
            'news_data': news_data,
            'timestamp': timestamp
        }, broadcast=True)
        return
    
    # 检查是否是@电影指令（注意@电影后有空格）
    if message.startswith('@电影 '):
        # 提取URL（以@电影 开头后的完整内容）
        movie_url = message[4:].strip()
        if movie_url and (movie_url.startswith('http://') or movie_url.startswith('https://')):
            # 使用正确的解析服务获取可播放地址
            import urllib.parse
            encoded_movie_url = urllib.parse.quote(movie_url)
            # 使用指定的解析地址
            final_movie_url = f"https://jx.m3u8.tv/jiexi/?url={encoded_movie_url}"
            
            # 广播电影播放消息
            emit('movie_play', {
                'username': username,
                'movie_name': movie_url,
                'movie_url': final_movie_url,
                'timestamp': timestamp,
                'size': '400x400'  # 播放器尺寸固定为400x400
            }, broadcast=True)
        return
    
    # 检查是否是@查天气指令
    if message.startswith('@查天气') and len(message) > 4:
        # 提取城市名
        city = message[5:].strip()
        
        # 先将用户消息正常广播出去
        emit('new_message', {
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'at_user': '查天气'  # 标记为@查天气的消息
        }, broadcast=True)
        
        # 调用天气查询函数
        weather_info = get_weather(city)
        
        # 格式化天气回复消息
        weather_response = f"""{weather_info['city']} 天气情况：
天气状况：{weather_info['weather']}
温度：{weather_info['temperature']}
湿度：{weather_info['humidity']}
风力：{weather_info['wind']}"""
        
        # 广播天气查询结果
        emit('weather_response', {
            'username': username,
            'city': city,
            'weather_info': weather_info,  # 确保包含weather_info字段，其中已包含status信息
            'response': weather_response,
            'timestamp': timestamp
        }, broadcast=True)
        
        # 根据天气状况发送背景更换事件
        background_type_mapping = {
            '晴': 'sunny',
            '雨': 'rainy',
            '雪': 'snowy',
            '多云': 'cloudy',
            '阴': 'overcast',
            '雾': 'foggy'
        }
        
        weather_status = weather_info.get('status')
        if weather_status and weather_status in background_type_mapping:
            emit('change_background', {
                'background_type': background_type_mapping[weather_status],
                'weather_info': weather_info
            }, broadcast=True)
        
        return
    
    # 检查是否是@川小农指令，只有当@川小农后面有实际问题内容时才调用AI助手
    if message.startswith('@川小农') and len(message) > 4 and message[4:].strip():
        # 提取用户问题
        question = message[4:].strip()
        
        # 先将用户消息正常广播出去
        emit('new_message', {
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'at_user': '川小农'  # 标记为@川小农的消息
        }, broadcast=True)
        
        # 然后生成AI回复
        response = ai_assistant_response(question)
        
        # 最后广播AI回复消息
        emit('ai_response', {
            'assistant': AI_ASSISTANT_NAME,
            'question': question,
            'response': response,
            'timestamp': timestamp
        }, broadcast=True)
        return
    
    # 检查是否是@用户指令
    at_match = re.search(r'@(\S+)', message)
    if at_match:
        at_user = at_match.group(1)
        # 处理@用户的消息
        emit('new_message', {
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'at_user': at_user
        }, broadcast=True)
    else:
        # 普通消息
        emit('new_message', {
            'username': username,
            'message': message,
            'timestamp': timestamp
        }, broadcast=True)

@socketio.on('leave')
def handle_leave():
    username = online_users.get(request.sid)
    if username:
        # 离开房间
        room = 'chat_room'
        leave_room(room)
        
        # 从在线用户列表中移除
        del online_users[request.sid]
        
        # 从房间用户列表中移除
        if room in room_users and username in room_users[room]:
            room_users[room].remove(username)
        
        # 广播用户离开消息
        emit('user_left', {
            'username': username,
            'online_users': room_users.get('chat_room', [])
        }, broadcast=True)
        
        print(f'用户 {username} 离开了聊天室')

# 服务器启动代码

if __name__ == '__main__':
    print('正在启动服务器...')
    # 初始化数据库
    init_db()
    print('数据库初始化完成')
    # 启动SocketIO服务器
    # 使用端口5011
    PORT = 5011
    print(f'准备在端口{PORT}上启动服务器')
    # 简化启动配置
    socketio.run(app, host='127.0.0.1', port=PORT, debug=False)