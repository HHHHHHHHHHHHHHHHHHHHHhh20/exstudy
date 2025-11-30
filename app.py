# DaiP智能聊天室 - 主应用文件
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import random
import re
from config import *

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 存储在线用户信息
online_users = {}
# 存储房间信息
room_users = {}

# 电影搜索模拟数据
movie_database = {
    "阿甘正传": "https://example.com/movies/forrest_gump.mp4",
    "肖申克的救赎": "https://example.com/movies/shawshank_redemption.mp4",
    "泰坦尼克号": "https://example.com/movies/titanic.mp4",
    "星际穿越": "https://example.com/movies/interstellar.mp4",
    "盗梦空间": "https://example.com/movies/inception.mp4"
}

# AI助手回复逻辑
def ai_assistant_response(message):
    message = message.lower()
    
    # 检查是否是关于其他学校的问题
    other_schools = ["清华", "北大", "复旦", "交大", "浙大", "南京大学"]
    for school in other_schools:
        if school in message:
            return "哼，我只关心四川农业大学！😜"
    
    # 检查是否是关于四川农业大学的问题
    if any(keyword in message for keyword in ["四川农业大学", "川农", "川农大", "四川农大"]):
        # 生成与四川农业大学相关的回答
        responses = [
            "四川农业大学是一所以生物科技为特色，农业科技为优势的重点大学。",
            "四川农业大学有三个校区：雅安、成都和都江堰校区。",
            "四川农业大学的前身是1906年创办的四川通省农业学堂。",
            "四川农业大学是国家'双一流'建设高校。",
            "四川农业大学拥有兽医学、作物学、畜牧学等多个优势学科。"
        ]
        return random.choice(responses)
    
    # 检查是否要求生成古诗
    if any(keyword in message for keyword in ["古诗", "写诗", "七言", "诗句"]):
        # 生成七言风格的古诗
        poems = [
            "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。",
            "床前明月光，疑是地上霜。举头望明月，低头思故乡。",
            "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。",
            "两个黄鹂鸣翠柳，一行白鹭上青天。窗含西岭千秋雪，门泊东吴万里船。",
            "日照香炉生紫烟，遥看瀑布挂前川。飞流直下三千尺，疑是银河落九天。"
        ]
        return random.choice(poems)
    
    # 检查是否要求生成通知
    if any(keyword in message for keyword in ["通知", "公告", "告示"]):
        # 生成学校通知格式
        notice_types = ["举办学术讲座", "开展校园活动", "发放奖学金", "进行安全检查", "组织体检"]
        notice_type = random.choice(notice_types)
        return f"关于{notice_type}的通知\n\n全校师生：\n\t为了丰富校园文化生活，提升同学们的综合素质，学校决定{notice_type}。请相关同学积极参与，准时参加。\n\t特此通知。\n\t四川农业大学学生处\n\t{random.randint(2024, 2025)}年{random.randint(1, 12)}月{random.randint(1, 28)}日"
    
    # 默认回复
    return "这个问题我不知道呀~"

# 电影搜索功能
def search_movie(movie_name):
    # 在模拟数据库中查找电影
    if movie_name in movie_database:
        return movie_database[movie_name]
    else:
        # 模拟返回第一个结果
        return next(iter(movie_database.values()))

@app.route('/')
def index():
    # 渲染登录页面
    return render_template('login.html', servers=SERVERS)

@app.route('/chat')
def chat():
    # 获取查询参数中的用户名和服务器地址
    username = request.args.get('username')
    server = request.args.get('server')
    
    if not username or not server:
        # 如果参数不完整，重定向到登录页
        return render_template('login.html', servers=SERVERS, error="用户名和服务器地址不能为空")
    
    # 渲染聊天室页面
    return render_template('chat.html', username=username, server=server)

# 检查用户名是否已存在
@app.route('/check_username', methods=['POST'])
def check_username():
    username = request.json.get('username')
    return jsonify({
        'exists': username in online_users.values()
    })

# WebSocket事件处理

@socketio.on('connect')
def handle_connect():
    print('客户端已连接')

@socketio.on('disconnect')
def handle_disconnect():
    # 获取断开连接的用户信息
    user_session = request.sid
    username = None
    
    # 查找用户名
    for session_id, name in online_users.items():
        if session_id == user_session:
            username = name
            break
    
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
            'online_users': list(online_users.values())
        }, broadcast=True)
        
        print(f'用户 {username} 已离开')

@socketio.on('join')
def handle_join(data):
    username = data['username']
    server = data['server']
    
    # 存储用户信息
    online_users[request.sid] = username
    
    # 将用户加入聊天室
    room = 'chat_room'
    join_room(room)
    
    # 更新房间用户列表
    if room not in room_users:
        room_users[room] = []
    room_users[room].append(username)
    
    # 发送加入成功消息给当前用户
    emit('join_success', {
        'message': f'欢迎 {username} 加入聊天室！',
        'online_users': list(online_users.values())
    })
    
    # 广播新用户加入消息给其他用户
    emit('user_joined', {
        'username': username,
        'message': f'{username} 加入了聊天室',
        'online_users': list(online_users.values())
    }, broadcast=True, skip_sid=request.sid)
    
    print(f'用户 {username} 加入了聊天室')

@socketio.on('send_message')
def handle_message(data):
    username = data['username']
    message = data['message']
    timestamp = data['timestamp']
    
    # 检查是否是@电影指令
    if message.startswith('@电影'):
        # 提取电影名称或URL
        movie_input = message[3:].strip()
        if movie_input:
            # 模拟搜索电影
            movie_url = search_movie(movie_input)
            # 生成解析后的URL
            parsed_url = MOVIE_API_URL + movie_url
            
            # 广播电影播放消息
            emit('movie_play', {
                'username': username,
                'movie_name': movie_input,
                'movie_url': parsed_url,
                'timestamp': timestamp
            }, broadcast=True)
        return
    
    # 检查是否是@川小农指令
    if message.startswith('@川小农'):
        # 提取用户问题
        question = message[4:].strip()
        
        # 生成AI回复
        response = ai_assistant_response(question)
        
        # 广播AI回复消息
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
            'online_users': list(online_users.values())
        }, broadcast=True)
        
        print(f'用户 {username} 离开了聊天室')

if __name__ == '__main__':
    # 启动服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=DEBUG)