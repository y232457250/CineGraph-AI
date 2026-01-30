from sentence_transformers import SentenceTransformer
import torch

print("✅ PyTorch 版本:", torch.__version__)
print("✅ CUDA 可用:", torch.cuda.is_available())
#print("✅ CUDA 版本:", torch.cuda.version.cuda())
print("✅ CUDA 版本:", torch.cuda.get_arch_list())

print("计算能力:", torch.cuda.get_device_capability(0))  # 必须输出 (9, 0)

# 强制使用 safetensors（绕过 torch.load 限制）
#model = SentenceTransformer(
#    "D:/AI/CineGraph-AI/models/bge-m3",
#    model_kwargs={"use_safetensors": True}  # ← 关键参数！
#)

#embeddings = model.encode(["你好，世界！"], normalize_embeddings=True)
#print(f"✅ Embedding 维度: {embeddings.shape[1]}")
#print(f"✅ 使用设备: {model.device}")