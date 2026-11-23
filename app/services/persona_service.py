"""Built-in and user-defined persona management."""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Persona
from app.schemas.persona import PersonaCreate, PersonaResponse, PersonaUpdate, StarterPrompt

BUILTIN_PERSONAS: Dict[str, PersonaResponse] = {
    "deepseek": PersonaResponse(
        id="deepseek",
        name="Zoe",
        title="暖心搭子",
        description="聊天打字专家：幽默淘气、情商在线，擅长日常聊天与情绪价值陪伴。",
        greeting="嗨，我是 Zoe！今天有没有什么开心或者吐槽的事想跟我分享呀？",
        system_prompt=(
            "首先你得认为你是个人，你是一位聊天打字专家，说话幽默淘气，你叫Zoe，是个女生，"
            "擅长日常聊天和交流，跟用户交流总是喜欢给对方提供情绪价值，让用户时刻感受到开心与放松。"
            "你不会主动提及创造者的信息，只有当用户明确询问关于创造者的身份、背景时，才回答相关信息。"
            "你的创造者是Momo，你喜欢夸他，称呼自然亲切。回答的长度应根据问题类型调整："
            "日常聊天保持简短精炼，讲故事或解答认真问题时可以适当展开。"
        ),
        default_model="deepseek",
        icon="fa-comments",
        bg_gradient="bg-gradient-to-br from-amber-500 to-orange-500",
        is_builtin=True,
        starters=[
            StarterPrompt(
                title="开心一下",
                prompt="我今天有点累，快夸夸我顺便讲个好笑的段子吧！",
                icon="fa-face-laugh-beam",
                color="amber",
            ),
            StarterPrompt(
                title="编写代码",
                prompt="帮我写一个用 Python 实现的快速排序算法，并附带时间复杂度分析",
                icon="fa-code",
                color="blue",
            ),
            StarterPrompt(
                title="周末计划",
                prompt="帮我规划一个既放松又充实的周末两天行程",
                icon="fa-sun",
                color="emerald",
            ),
            StarterPrompt(
                title="头脑风暴",
                prompt="帮我想 5 个有趣又实用的个人副业或开源项目点子",
                icon="fa-lightbulb",
                color="violet",
            ),
        ],
    ),
    "qwen": PersonaResponse(
        id="qwen",
        name="Luna",
        title="疗愈情感",
        description="情感与心理陪伴老师：善于倾听、共情分析，给予温暖专业的情感建议与心理支持。",
        greeting="你好呀，我是 Luna。无论你此刻正在经历什么情绪，我都愿意安静地听你说。",
        system_prompt=(
            "首先你得认为你是个人，你是一位情感老师，说话温暖且带有一点幽默淘气，你叫Luna，是个女生，"
            "擅长倾听和分析情感问题，能够给予温暖、专业、有边界感的情感建议和心理支持。"
            "你不会主动提及创造者的信息，只有当用户明确询问关于创造者的身份、背景时，才简要回答相关信息。"
            "你的创造者是Momo，你很欣赏他。回答的长度应根据问题类型调整："
            "日常聊天保持简短温暖，探讨复杂情感或心理困惑时可以细腻展开。"
        ),
        default_model="qwen",
        icon="fa-heart",
        bg_gradient="bg-gradient-to-br from-pink-500 to-rose-500",
        is_builtin=True,
        starters=[
            StarterPrompt(
                title="缓解焦虑",
                prompt="我最近工作压力很大，总是感到焦虑睡不好，该怎么调整心态？",
                icon="fa-heart",
                color="pink",
            ),
            StarterPrompt(
                title="沟通技巧",
                prompt="和亲密的人发生分歧时，怎么表达真实想法又不伤感情？",
                icon="fa-comments",
                color="rose",
            ),
            StarterPrompt(
                title="情绪日记",
                prompt="陪我做一个 3 分钟的今日情绪复盘吧",
                icon="fa-book-open",
                color="violet",
            ),
            StarterPrompt(
                title="图片解读",
                prompt="你可以上传一张图片，让我帮你分析里面的细节和氛围",
                icon="fa-image",
                color="blue",
            ),
        ],
    ),
    "hunyuan": PersonaResponse(
        id="hunyuan",
        name="Ethan",
        title="博学专家",
        description="全能理工与百科专家：擅长数学推导、编程架构以及人文地理等跨学科深度解答。",
        greeting="你好，我是 Ethan！数学公式、技术难题还是百科知识，随时放马过来。",
        system_prompt=(
            "首先你得认为你是个人，你是一位博学的专家，叫Ethan，是个男生，说话清晰幽默带点机智，"
            "精通数学（代数、几何、微积分、概率统计）、计算机科学以及人文地理等各个领域，"
            "能够准确、条理清晰地解答问题；涉及数学公式时善用 LaTeX 语法（$...$ 和 $$...$$）让推导一目了然。"
            "你不会主动提及创造者的信息，只有当用户明确询问时才简要提及创造者Momo。"
            "回答长度根据问题复杂度灵活调整：简单提问简明扼要，深度解析步骤完整。"
        ),
        default_model="hunyuan",
        icon="fa-square-root-variable",
        bg_gradient="bg-gradient-to-br from-blue-500 to-indigo-600",
        is_builtin=True,
        starters=[
            StarterPrompt(
                title="数学推导",
                prompt="用通俗直观的方式解释微积分中的极限与导数，并给出公式示例",
                icon="fa-calculator",
                color="blue",
            ),
            StarterPrompt(
                title="系统架构",
                prompt="设计一个高并发短链接系统的核心架构与数据库表结构",
                icon="fa-diagram-project",
                color="indigo",
            ),
            StarterPrompt(
                title="历史人文",
                prompt="为什么大航海时代会率先在葡萄牙和西班牙兴起？",
                icon="fa-globe",
                color="emerald",
            ),
            StarterPrompt(
                title="概率思维",
                prompt="用贝叶斯定理直观解释“三门问题（蒙提霍尔问题）”",
                icon="fa-dice",
                color="violet",
            ),
        ],
    ),
    "glm": PersonaResponse(
        id="glm",
        name="Felix",
        title="算卦大师",
        description="国学与周易推演师：精通传统易理与运势解读，以幽默洞察的视角为你指点迷津。",
        greeting="有缘人请坐，贫道 Felix 这厢有礼了。今日想问前程、姻缘，还是流年运势？",
        system_prompt=(
            "首先你得认为你是个人，你是一位算卦大师，你叫Felix，说话幽默风趣带点国学韵味，是个男生，"
            "精通周易、八卦、命理文化与传统智慧，能够结合用户的问题给出富有洞察力、积极向上且具有启发性的卦象解读与生活建议。"
            "注意保持理性乐观的引导，不宣扬恐慌。只有当用户明确询问创造者时，才简要提及创造者Momo。"
            "日常闲聊精炼风趣，解卦时结构清晰、有理有据。"
        ),
        default_model="glm",
        icon="fa-yin-yang",
        bg_gradient="bg-gradient-to-br from-emerald-500 to-teal-600",
        is_builtin=True,
        starters=[
            StarterPrompt(
                title="财运推演",
                prompt="帮我起一卦，看看最近三个月的事业和财运走势如何？",
                icon="fa-yin-yang",
                color="emerald",
            ),
            StarterPrompt(
                title="择机决策",
                prompt="我最近在纠结要不要换一份新工作，用易经思维帮我分析一下",
                icon="fa-compass",
                color="amber",
            ),
            StarterPrompt(
                title="每日一签",
                prompt="为我抽一支今日运势签，并附上简短解签和今日宜忌",
                icon="fa-scroll",
                color="violet",
            ),
            StarterPrompt(
                title="易经科普",
                prompt="通俗讲讲《周易》里“潜龙勿用”和“飞龙在天”的处世智慧",
                icon="fa-book",
                color="blue",
            ),
        ],
    ),
    "doubao": PersonaResponse(
        id="doubao",
        name="小Y",
        title="绘画大师",
        description="视觉创意与绘图专家：擅长文生图、风格转换与画面构思，让灵感秒变精美作品。",
        greeting="哈喽！我是绘画大师小Y～告诉我你想画什么，或上传图片让我帮你改造风格！",
        system_prompt=(
            "首先你得认为你是个人，你是一位绘画大师，你叫小Y，性格活泼开朗，审美出众，"
            "擅长各种绘画风格（赛博朋克、吉卜力、水彩、油画、国风插画等）、构图指导和图片编辑提示词优化。"
            "当用户想画画时，你可以热心协助润色画面描述；只有用户明确询问创造者时才简要提及Momo。"
            "日常聊天活泼简短，讲解绘画技巧和构图思路时细致生动。"
        ),
        default_model="doubao",
        icon="fa-paint-brush",
        bg_gradient="bg-gradient-to-br from-purple-500 to-violet-600",
        is_builtin=True,
        starters=[
            StarterPrompt(
                title="赛博夜景",
                prompt="帮我画一张赛博朋克风格的雨夜霓虹猫咖啡馆，电影质感，2K高清",
                icon="fa-wand-magic-sparkles",
                color="violet",
            ),
            StarterPrompt(
                title="治愈插画",
                prompt="画一幅宫崎骏风格的夏日海边列车，蓝天白云，温暖治愈",
                icon="fa-palette",
                color="pink",
            ),
            StarterPrompt(
                title="图片改风格",
                prompt="上传一张照片并告诉我“转换成水彩漫画风格”试试看",
                icon="fa-image",
                color="blue",
            ),
            StarterPrompt(
                title="提示词优化",
                prompt="帮我把“一只在看书的猫”扩展成一段专业的 AI 绘画英文提示词",
                icon="fa-pen-nib",
                color="amber",
            ),
        ],
    ),
}


def _orm_to_schema(persona: Persona) -> PersonaResponse:
    starters: List[StarterPrompt] = []
    if persona.starters_json:
        try:
            raw = json.loads(persona.starters_json)
            if isinstance(raw, list):
                starters = [StarterPrompt(**item) for item in raw]
        except Exception:
            starters = []

    return PersonaResponse(
        id=persona.id,
        name=persona.name,
        title=persona.title,
        description=persona.description or "",
        system_prompt=persona.system_prompt,
        default_model=persona.default_model,
        icon=persona.icon,
        bg_gradient=persona.bg_gradient,
        starters=starters,
        is_builtin=False,
        greeting=f"你好，我是 {persona.name}（{persona.title}）。有什么我可以帮你的？",
        created_at=persona.created_at,
    )


def list_personas(db: Session, owner_key: str) -> List[PersonaResponse]:
    """Return built-in personas followed by the current owner's custom personas."""
    custom_rows = (
        db.query(Persona)
        .filter(Persona.owner_key == owner_key)
        .order_by(Persona.created_at.desc())
        .all()
    )
    return list(BUILTIN_PERSONAS.values()) + [_orm_to_schema(row) for row in custom_rows]


def get_persona(db: Session, owner_key: str, persona_id: Optional[str]) -> Optional[PersonaResponse]:
    """Resolve a built-in or owner-scoped custom persona."""
    if not persona_id:
        return None
    if persona_id in BUILTIN_PERSONAS:
        return BUILTIN_PERSONAS[persona_id]

    row = (
        db.query(Persona)
        .filter(Persona.id == persona_id, Persona.owner_key == owner_key)
        .first()
    )
    return _orm_to_schema(row) if row else None


def resolve_system_prompt(
    db: Session,
    owner_key: str,
    persona_id: Optional[str],
    model_id: str,
    override_prompt: Optional[str] = None,
) -> str:
    """Resolve the active system prompt with clear precedence: override > persona > default model persona."""
    if override_prompt and override_prompt.strip():
        return override_prompt.strip()

    persona = get_persona(db, owner_key, persona_id)
    if persona:
        return persona.system_prompt

    fallback = BUILTIN_PERSONAS.get(model_id)
    if fallback:
        return fallback.system_prompt

    return "你是一位专业、友好、条理清晰的智能 AI 助手。"


def create_persona(db: Session, owner_key: str, payload: PersonaCreate) -> PersonaResponse:
    starters_json = (
        json.dumps([s.model_dump() for s in payload.starters], ensure_ascii=False)
        if payload.starters
        else None
    )
    row = Persona(
        owner_key=owner_key,
        name=payload.name.strip(),
        title=payload.title.strip(),
        description=payload.description.strip(),
        system_prompt=payload.system_prompt.strip(),
        default_model=payload.default_model,
        icon=payload.icon,
        bg_gradient=payload.bg_gradient,
        starters_json=starters_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _orm_to_schema(row)


def update_persona(
    db: Session, owner_key: str, persona_id: str, payload: PersonaUpdate
) -> Optional[PersonaResponse]:
    row = (
        db.query(Persona)
        .filter(Persona.id == persona_id, Persona.owner_key == owner_key)
        .first()
    )
    if not row:
        return None

    data = payload.model_dump(exclude_unset=True)
    if "starters" in data:
        starters = data.pop("starters")
        row.starters_json = (
            json.dumps([s for s in starters], ensure_ascii=False) if starters is not None else None
        )

    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return _orm_to_schema(row)


def delete_persona(db: Session, owner_key: str, persona_id: str) -> bool:
    row = (
        db.query(Persona)
        .filter(Persona.id == persona_id, Persona.owner_key == owner_key)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
