"""Unit tests for intent routing and image size extraction."""

from __future__ import annotations

from app.services.intent_service import detect_intent, parse_image_size


def test_code_generation_does_not_trigger_image_generation():
    intent = detect_intent("帮我生成一段 Python 快速排序代码")
    assert intent.kind == "chat"

    intent2 = detect_intent("帮我生成一份项目总结报告")
    assert intent2.kind == "chat"


def test_generic_questions_do_not_falsely_trigger_web_search():
    assert detect_intent("你怎么看待微积分的本质？").kind == "chat"
    assert detect_intent("如何写出更优雅的 FastAPI 代码").kind == "chat"
    assert detect_intent("什么是多态？").kind == "chat"


def test_real_web_search_and_explicit_toggle():
    assert detect_intent("今天北京天气怎么样").kind == "web_search"
    assert detect_intent("帮我搜索一下最新的 Python 3.13 特性").kind == "web_search"
    assert detect_intent("随便聊聊", web_search_mode="on").kind == "web_search"
    assert detect_intent("今天北京天气怎么样", web_search_mode="off").kind == "chat"


def test_image_generation_and_size_parsing():
    intent = detect_intent("帮我画一张赛博朋克雨夜猫咪 2K")
    assert intent.kind == "image_generate"
    assert intent.doubao_size == "2K"

    wanx_sz, doubao_sz = parse_image_size("生成 1280x720 的风景壁纸")
    assert wanx_sz == "1280*720"
    assert doubao_sz == "1280x720"

    assert detect_intent("海边日落", image_mode="generate").kind == "image_generate"
    assert detect_intent("帮我画一张猫", image_mode="off").kind == "chat"


def test_uploaded_images_route_to_vision_or_edit():
    assert detect_intent("这张图里有什么动物？", has_images=True).kind == "vision_chat"

    edit_intent = detect_intent("帮我把这张照片转换成水彩风格", has_images=True)
    assert edit_intent.kind == "image_edit"
    assert edit_intent.edit_type == "风格转换"
