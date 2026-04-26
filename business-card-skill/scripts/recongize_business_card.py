import base64
import sys
import os
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

def main():
    args = sys.argv[1:]
    if not (1 <= len(args) <= 2):
        print("用法: python scan_card_sdk.py <图片路径1> [图片路径2]")
        sys.exit(1)

    # 构建多模态内容列表
    content = [{"type": "text", "text": "请识别并提取名片信息，以 JSON 格式输出。"}]
    
    for path in args:
        if os.path.exists(path):
            base64_str = encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_str}"}
            })

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": content}],
            # 强制要求模型输出 JSON 对象 (需要模型支持，如 gpt-4o, gpt-4-turbo)
            response_format={"type": "json_object"}, 
            max_tokens=1000
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()