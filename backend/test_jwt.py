#!/usr/bin/env python3
"""
临时测试JWT decode
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.security import create_access_token
from app.core.config import settings
from jose import jwt, JWTError

# 打印配置
print(f"JWT_SECRET_KEY: {settings.JWT_SECRET_KEY}")
print(f"JWT_ALGORITHM: {settings.JWT_ALGORITHM}")

# 创建Token
data = {"sub": 1}
token = create_access_token(data)
print(f"\nCreated token: {token}")

# Decode Token（带异常处理）
try:
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    print(f"Decoded payload: {decoded}")
except JWTError as e:
    print(f"JWT Error: {e}")

# 测试真实Token
real_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImV4cCI6MTc2MzQ4MjA4M30.r9c23QLG3LcXtCQ7Hs4ZhflzfysfmKZ558499G-jdSk"
print(f"\nTesting real token...")
try:
    decoded_real = jwt.decode(real_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    print(f"Decoded real token: {decoded_real}")
except JWTError as e:
    print(f"JWT Error: {e}")
