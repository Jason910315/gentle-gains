from contextvars import ContextVar

"""
這個程式負責定義 ContextVar 容器，讓其他程式可以方便地使用。
"""

# 定義一個放字串的 ContextVar 容器，名稱標籤為 current_image_url使用者傳給 chat 圖片時，用這個容器去存取 image_url
# 使用 ContextVar 可以確保非同步併發時，不同使用者的 image_url 不會干擾
current_image_ctx: ContextVar[str] = ContextVar("current_image_url", default=None)