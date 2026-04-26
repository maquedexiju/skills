import base64
import sys
import os
import requests
from openai import OpenAI

# --- 配置加载 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.py")

if os.path.exists(CONFIG_PATH):
    import importlib.util
    spec = importlib.util.spec_from_file_location("config", CONFIG_PATH)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    API_KEY = getattr(config, "OPENAI_API_KEY", "ollama")
    BASE_URL = getattr(config, "OPENAI_BASE_URL", "http://localhost:11434/v1/")
    MODEL_NAME = getattr(config, "MODEL_NAME", "qwen3.5:9b")
else:
    # 默认配置
    API_KEY = "ollama"
    BASE_URL = "http://localhost:11434/v1/"
    MODEL_NAME = "qwen3.5:9b"

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)
# ----------------

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def download_image(url, save_path):
    """下载图片到本地"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(response.content)
    return save_path

def main():
    args = sys.argv[1:]
    if not (1 <= len(args) <= 2):
        print("用法: python recongize_business_card_url.py <图片路径或URL> [图片路径或URL2]")
        sys.exit(1)

    # 构建多模态内容列表
    content = [{"type": "text", "text": "请识别并提取名片信息，以 JSON 格式输出。包含：姓名、公司、职位、电话、邮箱、地址、网站等信息。"}]
    
    temp_files = []
    
    for path in args:
        # 检查是否是URL
        if path.startswith('http://') or path.startswith('https://'):
            # 下载图片
            temp_path = f"/tmp/business_card_{len(temp_files)}.jpg"
            try:
                download_image(path, temp_path)
                temp_files.append(temp_path)
                path = temp_path
            except Exception as e:
                print(f"下载图片失败: {e}")
                continue
        
        if os.path.exists(path):
            base64_str = encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_str}"}
            })

    if len(content) == 1:
        print("没有有效的图片")
        sys.exit(1)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"}, 
            max_tokens=1000
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 清理临时文件
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass

if __name__ == "__main__":
    main()
