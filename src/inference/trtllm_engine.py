"""
TensorRT-LLM 推理引擎封装
支持三种部署模式：
  - trtllm-serve : 单实例快速部署，OAI 兼容，适合原型验证
  - Dynamo       : 数据中心级多实例，适合生产环境
  - LLM API      : Python 直接集成，最大灵活性
"""
import os
from enum import Enum
from openai import OpenAI

MODELS_DIR = os.getenv("MODELS_DIR", "/home/xsuper/models")


class DeployMode(str, Enum):
    SERVE = "serve"    # trtllm-serve，单实例，OAI 兼容
    DYNAMO = "dynamo"  # Dynamo，多实例，生产级
    API = "api"        # LLM Python API，直接集成


class TRTLLMEngine:
    """
    TensorRT-LLM 推理引擎。
    默认使用 SERVE 模式（trtllm-serve 已在 :8000 运行），
    通过 OpenAI 兼容接口调用本地模型。
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen3-next-80b-a3b-thinking",
        mode: DeployMode = DeployMode.SERVE,
    ):
        self.model = model
        self.mode = mode
        self._client = OpenAI(base_url=base_url, api_key="local")

    def chat(self, messages: list[dict], temperature: float = 0.1, max_tokens: int = 4096) -> str:
        """调用本地 TRT-LLM 服务，返回模型回复文本"""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def generate(self, prompt: str, **kwargs) -> str:
        """单轮生成，便捷接口"""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)


class VLMEngine:
    """
    Qwen2.5-VL 视觉语言模型引擎。
    用于屏幕截图语义理解，监听 :8001。
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001/v1",
        model: str = "Qwen2.5-VL-7B-Instruct",
    ):
        self.model = model
        self._client = OpenAI(base_url=base_url, api_key="local")

    def describe_image(self, image_url: str, prompt: str = "请描述这张截图的内容") -> str:
        """分析图片/截图，返回语义描述"""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=1024,
        )
        return response.choices[0].message.content


# 单例，全局复用
_llm: TRTLLMEngine | None = None
_vlm: VLMEngine | None = None


def get_llm() -> TRTLLMEngine:
    global _llm
    if _llm is None:
        _llm = TRTLLMEngine()
    return _llm


def get_vlm() -> VLMEngine:
    global _vlm
    if _vlm is None:
        _vlm = VLMEngine()
    return _vlm
