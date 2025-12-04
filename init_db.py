import sqlite3
import hashlib

# 连接到数据库（如果不存在则创建）
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# 创建用户表
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# 哈希密码函数
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 插入管理员用户（如果不存在）
try:
    admin_username = 'admin'
    admin_password = 'admin888'
    admin_password_hash = hash_password(admin_password)
    
    # 检查管理员是否已存在
    cursor.execute("SELECT * FROM users WHERE username = ?", (admin_username,))
    existing_admin = cursor.fetchone()
    
    if not existing_admin:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                      (admin_username, admin_password_hash))
        print(f"管理员账号创建成功: {admin_username}")
    else:
        print("管理员账号已存在")
        
    # 提交更改
    conn.commit()
    print("数据库初始化完成")
    
    # 显示所有用户
    print("\n用户列表:")
    cursor.execute("SELECT id, username, created_at FROM users")
    users = cursor.fetchall()
    for user in users:
        print(f"ID: {user[0]}, 用户名: {user[1]}, 创建时间: {user[2]}")
        
finally:
    # 关闭连接
    conn.close()