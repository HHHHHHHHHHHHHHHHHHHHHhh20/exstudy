# DaiP智能聊天室配置文件

# 服务器地址列表，用户可以通过此配置文件修改服务器地址
SERVERS = [
    "http://localhost:5000",
    "http://127.0.0.1:5000"
]

# 电影解析API地址
MOVIE_API_URL = "https://jx.m3u8.tv/jiexi/?url="

# AI助手配置
AI_ASSISTANT_NAME = "川小农"
AI_ASSISTANT_GENDER = "女"
AI_ASSISTANT_ROLE = "四川农业大学的AI小助手"

# 服务器配置
SECRET_KEY = "your-secret-key-here"
DEBUG = True