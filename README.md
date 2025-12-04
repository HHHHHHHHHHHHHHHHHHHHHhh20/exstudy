# 智能聊天应用

一个基于Flask和SocketIO的实时聊天应用，集成了天气查询、音乐播放、每日新闻和电影播放等功能。

## 功能特性

### 1. 实时聊天
- 用户注册和登录
- 实时消息发送和接收
- 在线用户显示
- 消息时间戳

### 2. 天气查询
- 使用`@查天气 城市名`指令查询指定城市的天气
- 支持不同城市显示不同的天气信息
- 天气状况包括：晴朗、小雨、小雪、阴天、多云、雾等
- 根据天气类型自动切换聊天界面背景和视觉效果

### 3. 音乐播放
- 使用`@听音乐`指令获取随机音乐
- 支持音乐播放、暂停、音量调节
- 显示音乐封面和基本信息

### 4. 每日新闻
- 使用`@每日新闻`指令获取当天的热点新闻
- 显示新闻标题和摘要
- 支持点击查看新闻详情

### 5. 电影播放
- 使用`@电影 URL`指令解析电影链接
- 支持在线播放电影
- 自适应播放器尺寸

## 技术栈

- **后端框架**：Flask + SocketIO
- **前端技术**：HTML5 + CSS3 + JavaScript
- **数据库**：SQLite
- **API集成**：天气API、音乐API、新闻API
- **环境管理**：Python虚拟环境

## 项目结构

```
exstudy/
├── app.py                    # 主应用程序入口
├── config.py                 # 配置文件
├── init_db.py                # 数据库初始化
├── users.db                  # SQLite数据库文件
├── static/
│   ├── css/                  # CSS样式文件
│   ├── images/               # 静态图片资源
│   └── js/                   # JavaScript文件
├── templates/
│   ├── chat.html             # 聊天界面模板
│   ├── login.html            # 登录界面模板
│   └── chat_input_component.html  # 聊天输入组件
├── venv/                     # Python虚拟环境
└── README.md                 # 项目说明文档
```

## 安装和运行

### 1. 环境要求
- Python 3.11+
- pip

### 2. 安装步骤

1. **克隆或下载项目**
   ```bash
   cd exstudy
   ```

2. **激活虚拟环境**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```
   （如果没有requirements.txt文件，请手动安装所需依赖）

### 3. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5011` 启动

## 使用说明

### 1. 登录
- 打开浏览器访问 `http://localhost:5011`
- 输入用户名登录聊天系统

### 2. 发送消息
- 在输入框中输入消息内容，点击发送按钮
- 支持Enter键发送消息

### 3. 使用特殊功能

- **查询天气**：输入 `@查天气 北京`
- **播放音乐**：输入 `@听音乐`
- **获取新闻**：输入 `@每日新闻`
- **播放电影**：输入 `@电影 https://example.com/movie.mp4`

## 开发说明

### 数据库初始化
```bash
python init_db.py
```

### 天气API配置
天气查询功能使用了第三方API，配置位于 `app.py` 中的 `get_weather` 函数：
```python
weather_api_url = "https://v2.xxapi.cn/api/weatherDetails"
params = {"city": city, "key": "42f2fb6b4b032edd"}
```

### 模拟天气数据
当API调用失败时，系统会使用基于城市名哈希的模拟天气数据，确保不同城市显示不同的天气信息。

## 浏览器支持

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 许可证

MIT License

## 开发者

该项目由人工智能助手开发，用于学习和演示实时Web应用的开发技术。
