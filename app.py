import hashlib
import html
import json
import os
import re
from typing import Any, Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="NotePilot for XHS",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================
# Product Copy
# =========================
APP_VERSION = "v6.0"
APP_TITLE = "NotePilot for XHS"
APP_SUBTITLE = "小红书笔记发布前诊断与优化工作台"
APP_DESC = "30 秒判断这篇笔记是否值得发布，并获得可执行的优化方向。"
APP_NOTE = "说明：本工具基于内容质量信号进行辅助判断，不代表小红书真实推荐机制或平台内部规则。"


# =========================
# Secrets
# =========================
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))


# =========================
# Constants
# =========================
CATEGORY_OPTIONS = ["美妆", "护肤", "时尚", "穿搭", "食品", "生活方式", "旅行", "母婴", "数码", "其他"]
GOAL_OPTIONS = ["提升点击率", "提升互动率", "提升收藏率", "提升转化意图"]
PERSONA_OPTIONS = ["个人创作者", "品牌内容运营", "MCN / 代理商"]
TONE_OPTIONS = ["保留个人口吻", "更像真实测评", "更像攻略清单", "更适合品牌种草"]

DIMENSIONS = {
    "hook_strength": "首屏吸引力",
    "authenticity": "真实感",
    "information_density": "信息密度",
    "interaction_potential": "互动潜力",
    "conversion_potential": "决策辅助",
}

WEIGHTS_BY_GOAL = {
    "提升点击率": {
        "hook_strength": 0.31,
        "authenticity": 0.21,
        "information_density": 0.19,
        "interaction_potential": 0.15,
        "conversion_potential": 0.14,
    },
    "提升互动率": {
        "hook_strength": 0.20,
        "authenticity": 0.25,
        "information_density": 0.18,
        "interaction_potential": 0.25,
        "conversion_potential": 0.12,
    },
    "提升收藏率": {
        "hook_strength": 0.17,
        "authenticity": 0.22,
        "information_density": 0.31,
        "interaction_potential": 0.13,
        "conversion_potential": 0.17,
    },
    "提升转化意图": {
        "hook_strength": 0.18,
        "authenticity": 0.23,
        "information_density": 0.22,
        "interaction_potential": 0.10,
        "conversion_potential": 0.27,
    },
}

EXAMPLES = {
    "美妆｜真实测评型": {
        "persona": "个人创作者",
        "category": "美妆",
        "goal": "提升互动率",
        "tone": "保留个人口吻",
        "title": "黄黑皮通勤口红分享｜这支比我想象中更提气色",
        "body": """最近早八通勤一直在用这支豆沙棕调口红。
我本身黄黑皮，平时淡妆比较多，最怕颜色显脏或者太挑皮。
这支上嘴是很稳的日常提气色类型，薄涂自然，厚涂会更有氛围感。
优点是通勤不夸张、素颜也不会太突兀，缺点是吃完饭还是要补一下。
如果你也是黄皮、想找一支不容易出错的日常色，可以去柜台试试类似色调。""",
    },
    "生活方式｜信息不足型": {
        "persona": "个人创作者",
        "category": "生活方式",
        "goal": "提升收藏率",
        "tone": "更像攻略清单",
        "title": "租房党收纳好物分享",
        "body": """最近买了几个收纳用品，感觉还不错。
有些挺方便的，也比较适合小空间。
简单分享一下，之后有时间再详细说。""",
    },
    "品牌种草｜广告感偏强": {
        "persona": "品牌内容运营",
        "category": "护肤",
        "goal": "提升转化意图",
        "tone": "更适合品牌种草",
        "title": "全网最强面霜！闭眼入就对了！",
        "body": """这款面霜真的绝了，谁不用我都会伤心！
保湿、修护、提亮、抗老全部一步到位，任何肤质都适合！
这是我今年用过最最最厉害的产品，没有之一，赶紧冲！
现在买最划算，真的无脑入！""",
    },
    "旅行｜决策辅助型": {
        "persona": "个人创作者",
        "category": "旅行",
        "goal": "提升收藏率",
        "tone": "更像攻略清单",
        "title": "第一次去冰岛要不要报三天团？我的真实体验",
        "body": """第一次去冰岛我一开始很纠结要不要自驾，最后还是报了三天团。
优点是省心，尤其是冬天路况不熟的时候，跟团确实更稳。
但如果你很在意自由度，或者特别想慢慢拍照，那跟团会有点赶。
我这次觉得最值的是南岸和冰河湖，斯奈山半岛如果时间有限可以后放。
比较建议第一次去、不会开雪地车、又不想做太多攻略的人考虑这种玩法。""",
    },
}

GENERIC_AD_WORDS = [
    "全网最", "闭眼入", "速冲", "必须买", "无脑买", "赶紧冲", "冲就完了", "100%有效",
    "最低价", "官方认证", "没有之一", "绝绝子", "封神", "天花板", "必入", "无限回购",
]
CATEGORY_AD_WORDS = {
    "美妆": ["黄皮救星", "谁涂谁好看", "显白绝了", "素颜神器", "本命口红"],
    "护肤": ["烂脸救星", "修护天花板", "抗老封神", "敏感肌闭眼入", "谁用谁夸"],
    "时尚": ["高级感绝了", "谁穿谁好看", "氛围感拉满", "气质拉满"],
    "穿搭": ["显瘦绝了", "小个子救星", "谁穿谁瘦", "梨形身材必入"],
    "食品": ["巨巨巨好吃", "不好吃来骂我", "一口封神", "不允许还有人没吃过"],
    "生活方式": ["租房党救星", "提升幸福感", "后悔没早点买", "用了就回不去"],
    "旅行": ["一生必去", "随手拍都出片", "朋友圈问爆", "人生照片"],
    "母婴": ["妈妈必备", "宝宝必入", "闭眼囤"],
    "数码": ["生产力神器", "闭眼买", "同价位无敌"],
}

SCENE_WORDS = [
    "通勤", "熬夜", "黄黑皮", "油皮", "干皮", "敏感肌", "学生党", "打工人", "约会",
    "旅行", "换季", "早八", "军训", "租房党", "新手", "第一次", "预算", "小户型",
]
AUTH_WORDS = [
    "我", "自己", "实测", "亲测", "回购", "踩雷", "空瓶", "用了", "体验", "对比",
    "复盘", "上脸", "上嘴", "我觉得", "这次", "最后", "纠结", "缺点", "优点",
]
INFO_WORDS = [
    "成分", "质地", "妆效", "持妆", "步骤", "教程", "对比", "优缺点", "价格", "色号",
    "肤质", "建议", "避雷", "清单", "使用感", "适合", "不适合", "地点", "店名",
    "行程", "路线", "体验", "推荐", "攻略", "原因", "预算", "尺寸", "型号", "口感",
]
ENGAGE_WORDS = [
    "你们", "姐妹", "有人", "有没有", "吗？", "吗?", "求推荐", "哪个更", "评论区",
    "欢迎讨论", "你会", "你觉得",
]
CONVERT_WORDS = [
    "适合", "不适合", "推荐给", "值得买", "平替", "预算", "性价比", "回购", "入手",
    "拔草", "种草", "试试", "考虑", "决策", "选择",
]


# =========================
# Styling
# =========================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1180px;
    }
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    div[data-testid="stMetric"] label {
        color: #475467;
    }
    .np-hero {
        background: linear-gradient(135deg, #111827 0%, #2A2F3A 52%, #F2557A 100%);
        color: #FFFFFF;
        padding: 18px 24px;
        border-radius: 8px;
        margin-bottom: 14px;
    }
    .np-hero h1 {
        margin: 0 0 6px 0;
        font-size: 30px;
        line-height: 1.18;
        letter-spacing: 0;
    }
    .np-hero p {
        margin: 3px 0;
        color: rgba(255, 255, 255, 0.88);
        font-size: 14px;
        line-height: 1.55;
    }
    .np-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        margin-bottom: 12px;
    }
    .np-card-title {
        font-size: 14px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 8px;
    }
    .np-muted {
        color: #667085;
        font-size: 14px;
        line-height: 1.65;
    }
    .np-pill {
        display: inline-flex;
        align-items: center;
        min-height: 30px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 700;
        margin: 2px 6px 6px 0;
        border: 1px solid #E5E7EB;
        background: #F9FAFB;
        color: #344054;
    }
    .np-section-label {
        color: #F2557A;
        font-weight: 800;
        font-size: 13px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .np-copy {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px 18px;
        color: #101828;
        font-size: 15px;
        line-height: 1.75;
        min-height: 72px;
        white-space: normal;
        word-break: break-word;
    }
    .np-score-row {
        display: grid;
        grid-template-columns: 112px 1fr 48px;
        gap: 12px;
        align-items: center;
        margin: 11px 0;
    }
    .np-bar-bg {
        height: 10px;
        background: #EAECF0;
        border-radius: 999px;
        overflow: hidden;
    }
    .np-bar-fill {
        height: 10px;
        border-radius: 999px;
    }
    .np-small {
        font-size: 13px;
        color: #667085;
        line-height: 1.55;
    }
    .np-label-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 14px 16px;
        min-height: 88px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        overflow-wrap: anywhere;
    }
    .np-label-card .np-label {
        color: #667085;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .np-label-card .np-value {
        color: #111827;
        font-size: 24px;
        font-weight: 800;
        line-height: 1.25;
    }
    .np-label-card .np-caption {
        color: #667085;
        font-size: 13px;
        line-height: 1.45;
        margin-top: 6px;
    }
    .np-decision {
        background: #EFF6FF;
        border: 1px solid #B2DDFF;
        border-radius: 8px;
        padding: 16px 18px;
        margin: 14px 0 16px 0;
        color: #1849A9;
        line-height: 1.65;
    }
    .np-decision .np-decision-title {
        font-size: 18px;
        font-weight: 900;
        color: #123C7C;
        margin-bottom: 4px;
    }
    .np-decision .np-decision-body {
        font-size: 15px;
        font-weight: 650;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="np-hero">
        <div class="np-section-label">Content Quality Copilot</div>
        <h1>{APP_TITLE}</h1>
        <p>{APP_SUBTITLE}</p>
        <p>{APP_DESC}</p>
        <p>{APP_NOTE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# Helpers
# =========================
def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def dedupe_keep_order(items: List[Any]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def safe_list(value: Any, max_len: int = 5) -> List[str]:
    if isinstance(value, list):
        return dedupe_keep_order(value)[:max_len]
    if value is None:
        return []
    return [str(value).strip()][:max_len]


def make_cache_key(*parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        raise ValueError("未检测到 DEEPSEEK_API_KEY。请先在 .streamlit/secrets.toml 或环境变量中配置。")
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def render_copy_button(text: str, label: str, key: str):
    safe_text = json.dumps(text)
    components.html(
        f"""
        <div style="width:100%;display:flex;justify-content:flex-end;padding-top:2px;padding-bottom:6px;">
            <button id="copy-btn-{key}" style="width:108px;height:40px;border-radius:8px;border:1px solid #D0D5DD;background:#FFFFFF;color:#111827;cursor:pointer;font-size:14px;font-weight:700;">{label}</button>
        </div>
        <script>
        const btn = document.getElementById("copy-btn-{key}");
        btn.onclick = async () => {{
            try {{
                await navigator.clipboard.writeText({safe_text});
                const originalText = btn.innerText;
                btn.innerText = "已复制";
                btn.style.background = "#ECFDF3";
                btn.style.border = "1px solid #A6F4C5";
                btn.style.color = "#027A48";
                setTimeout(() => {{
                    btn.innerText = originalText;
                    btn.style.background = "#FFFFFF";
                    btn.style.border = "1px solid #D0D5DD";
                    btn.style.color = "#111827";
                }}, 1200);
            }} catch (err) {{
                btn.innerText = "复制失败";
                setTimeout(() => {{ btn.innerText = "{label}"; }}, 1200);
            }}
        }}
        </script>
        """,
        height=56,
    )


def render_text_box(text: str, min_height: int = 72):
    safe_text = html.escape(text or "").replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="np-copy" style="min-height:{min_height}px;">
            {safe_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_style(status: str) -> Tuple[str, str, str]:
    if status == "可发布":
        return "#E8F5E9", "#2E7D32", "可发布"
    if status == "建议优化后发布":
        return "#FFF8E1", "#B26A00", "建议优化后发布"
    return "#FFEBEE", "#C62828", "不建议直接发布"


def render_status_badge(status: str):
    bg, fg, label = status_style(status)
    st.markdown(
        f"""
        <div style="display:inline-block;background:{bg};color:{fg};padding:10px 14px;border-radius:8px;font-weight:800;font-size:15px;">
            {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_decision_callout(status: str, summary: str):
    safe_status = html.escape(status)
    safe_summary = html.escape(summary)
    st.markdown(
        f"""
        <div class="np-decision">
            <div class="np-decision-title">{safe_status}</div>
            <div class="np-decision-body">{safe_summary}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_color(score: int) -> str:
    if score >= 78:
        return "#12B76A"
    if score >= 62:
        return "#F79009"
    return "#F04438"


def render_score_bars(scores: Dict[str, int]):
    rows = []
    for key, label in DIMENSIONS.items():
        score = clamp(scores.get(key, 0))
        rows.append(
            f"""
            <div class="np-score-row">
                <div class="np-small" style="font-weight:700;color:#344054;">{label}</div>
                <div class="np-bar-bg"><div class="np-bar-fill" style="width:{score}%;background:{score_color(score)};"></div></div>
                <div style="font-weight:800;color:#111827;text-align:right;">{score}</div>
            </div>
            """
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def render_card(title: str, body: str, min_height: int = 0):
    safe_title = html.escape(title)
    safe_body = html.escape(body).replace("\n", "<br>")
    height_style = f"min-height:{min_height}px;" if min_height else ""
    st.markdown(
        f"""
        <div class="np-card" style="{height_style}">
            <div class="np-card-title">{safe_title}</div>
            <div class="np-muted">{safe_body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_label_card(label: str, value: str, caption: str = "", min_height: int = 0):
    safe_label = html.escape(label)
    safe_value = html.escape(value)
    safe_caption = html.escape(caption)
    caption_html = f'<div class="np-caption">{safe_caption}</div>' if caption else ""
    height_style = f"min-height:{min_height}px;" if min_height else ""
    st.markdown(
        f"""
        <div class="np-label-card" style="{height_style}">
            <div class="np-label">{safe_label}</div>
            <div class="np-value">{safe_value}</div>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def describe_content_signals(signals: Dict[str, int]) -> str:
    descriptions = []
    info_hits = signals.get("info_hits", 0)
    auth_hits = signals.get("auth_hits", 0)
    scene_hits = signals.get("scene_hits", 0)
    engage_hits = signals.get("engage_hits", 0)
    ad_hits = signals.get("ad_hits", 0)

    if auth_hits >= 4:
        descriptions.append("真实体验较强")
    elif auth_hits >= 2:
        descriptions.append("有一定个人体验")
    else:
        descriptions.append("真实体验待加强")

    if scene_hits >= 2:
        descriptions.append("场景较明确")
    elif scene_hits == 1:
        descriptions.append("已有基础场景")
    else:
        descriptions.append("目标场景不够清晰")

    if info_hits >= 5:
        descriptions.append("信息密度较高")
    elif info_hits >= 2:
        descriptions.append("信息密度中等")
    else:
        descriptions.append("收藏细节不足")

    if engage_hits >= 1:
        descriptions.append("具备互动入口")
    else:
        descriptions.append("互动钩子偏弱")

    if ad_hits >= 2:
        descriptions.append("营销感需收敛")
    elif ad_hits == 0:
        descriptions.append("表达较自然")

    return "｜".join(descriptions[:5])


def build_rewrite_comparison(
    original_title: str,
    original_body: str,
    rewrite_title: str,
    rewrite_body: str,
    category: str,
    goal: str,
    persona: str,
) -> Dict[str, Any]:
    original = heuristic_scores(original_title, original_body, category, goal, persona)
    rewritten = heuristic_scores(rewrite_title, rewrite_body, category, goal, persona)
    deltas = {
        key: rewritten["dimension_scores"][key] - original["dimension_scores"][key]
        for key in DIMENSIONS
    }
    deltas["overall_score"] = rewritten["overall_score"] - original["overall_score"]
    return {"original": original, "rewritten": rewritten, "deltas": deltas}


def delta_text(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def tokenize_hits(text: str, words: List[str]) -> int:
    return sum(1 for word in words if word and word in text)


def content_length_score(body: str) -> int:
    length = len(re.sub(r"\s+", "", body or ""))
    if 120 <= length <= 450:
        return 8
    if 70 <= length < 120 or 450 < length <= 650:
        return 3
    if length < 40:
        return -8
    return -3


def heuristic_scores(title: str, body: str, category: str, goal: str, persona: str) -> Dict[str, Any]:
    text = f"{title}\n{body}"
    ad_words = GENERIC_AD_WORDS + CATEGORY_AD_WORDS.get(category, [])
    scene_hits = tokenize_hits(text, SCENE_WORDS)
    auth_hits = tokenize_hits(text, AUTH_WORDS)
    info_hits = tokenize_hits(text, INFO_WORDS)
    engage_hits = tokenize_hits(text, ENGAGE_WORDS) + int("?" in text or "？" in text)
    convert_hits = tokenize_hits(text, CONVERT_WORDS)
    ad_hits = tokenize_hits(text, ad_words)

    scores = {
        "hook_strength": 64,
        "authenticity": 66,
        "information_density": 64,
        "interaction_potential": 58,
        "conversion_potential": 58,
    }
    strengths: List[str] = []
    risks: List[str] = []
    suggestions: List[str] = []

    title_len = len(re.sub(r"\s+", "", title or ""))
    if 8 <= title_len <= 28:
        scores["hook_strength"] += 7
        strengths.append("标题长度和信息承载较适中，首屏理解成本较低")
    elif title_len < 6:
        scores["hook_strength"] -= 9
        risks.append("标题偏短，缺少让用户停留的具体信息")
        suggestions.append("把标题从泛泛主题改成“对象 + 场景/问题 + 判断”的结构")
    elif title_len > 34:
        scores["hook_strength"] -= 5
        risks.append("标题偏长，移动端首屏聚焦度可能下降")

    if re.search(r"[0-9一二三四五六七八九十]", title):
        scores["hook_strength"] += 3
        scores["information_density"] += 2

    length_adj = content_length_score(body)
    scores["information_density"] += length_adj

    if scene_hits:
        scores["hook_strength"] += 3
        scores["authenticity"] += 5
        strengths.append("内容有具体场景或人群，平台原生感更强")
    else:
        risks.append("场景和对象不够明确，读者较难判断与自己是否相关")
        suggestions.append("补充适合谁、在哪个场景使用/体验、为什么会有这个判断")

    if auth_hits >= 4:
        scores["authenticity"] += 10
        strengths.append("第一人称体验和取舍判断较充分")
    elif auth_hits >= 2:
        scores["authenticity"] += 5
    else:
        scores["authenticity"] -= 8
        risks.append("个人体验痕迹偏弱，容易像泛化文案")
        suggestions.append("加入真实经历、使用前后感受或明确的优缺点")

    if info_hits >= 6:
        scores["information_density"] += 13
        scores["conversion_potential"] += 6
        strengths.append("信息点比较密集，具备收藏和决策价值")
    elif info_hits >= 3:
        scores["information_density"] += 8
        scores["conversion_potential"] += 3
    else:
        scores["information_density"] -= 7
        risks.append("细节和判断依据不足，收藏价值偏弱")
        suggestions.append("补充 2-3 个具体判断依据，例如优缺点、对比、价格/路线/肤质等")

    if any(marker in body for marker in ["优点", "缺点", "但", "不过", "如果", "适合", "不适合", "建议"]):
        scores["information_density"] += 5
        scores["authenticity"] += 3
        scores["conversion_potential"] += 3

    if "\n" in body or re.search(r"(^|\n)\s*[1-9①②③]", body):
        scores["information_density"] += 3
        strengths.append("正文结构较清晰，适合快速扫读")

    if engage_hits >= 2:
        scores["interaction_potential"] += 10
        strengths.append("具备自然互动触发点")
    elif engage_hits == 1:
        scores["interaction_potential"] += 5
    else:
        scores["interaction_potential"] -= 4
        risks.append("互动钩子偏弱，用户评论理由不够明确")

    if convert_hits >= 4:
        scores["conversion_potential"] += 10
    elif convert_hits >= 2:
        scores["conversion_potential"] += 6
    else:
        scores["conversion_potential"] -= 4

    if ad_hits >= 3:
        scores["authenticity"] -= 18
        scores["hook_strength"] -= 5
        scores["conversion_potential"] -= 5
        risks.append("营销腔较重，可能削弱真实感和信任感")
        suggestions.append("把“闭眼入/全网最”等绝对化表达改成具体体验和适用边界")
    elif ad_hits >= 1:
        scores["authenticity"] -= 7
        risks.append("存在一定营销化表达，需要降低夸张感")

    if persona == "品牌内容运营":
        scores["conversion_potential"] += 3
        scores["authenticity"] -= 1
    elif persona == "个人创作者":
        scores["authenticity"] += 2
        scores["interaction_potential"] += 2

    scores = {key: clamp(value) for key, value in scores.items()}
    overall = compute_overall(scores, goal)
    return {
        "dimension_scores": scores,
        "overall_score": overall,
        "overall_status": infer_status(overall, scores),
        "strengths": dedupe_keep_order(strengths)[:4],
        "risks": dedupe_keep_order(risks)[:4],
        "suggestions": dedupe_keep_order(suggestions)[:4],
        "signals": {
            "scene_hits": scene_hits,
            "auth_hits": auth_hits,
            "info_hits": info_hits,
            "engage_hits": engage_hits,
            "convert_hits": convert_hits,
            "ad_hits": ad_hits,
            "body_chars": len(re.sub(r"\s+", "", body or "")),
        },
    }


def compute_overall(scores: Dict[str, int], goal: str) -> int:
    weights = WEIGHTS_BY_GOAL.get(goal, WEIGHTS_BY_GOAL["提升收藏率"])
    return clamp(sum(scores.get(key, 60) * weight for key, weight in weights.items()))


def infer_status(overall: int, scores: Dict[str, int]) -> str:
    if overall >= 80 and scores.get("authenticity", 0) >= 72 and scores.get("information_density", 0) >= 68:
        return "可发布"
    if overall >= 64:
        return "建议优化后发布"
    return "不建议直接发布"


def normalize_scores(raw: Any) -> Dict[str, int]:
    if not isinstance(raw, dict):
        raw = {}
    scores = {}
    for key in DIMENSIONS:
        try:
            scores[key] = clamp(float(raw.get(key, 62)))
        except Exception:
            scores[key] = 62
    return scores


def blend_scores(llm_scores: Dict[str, int], heuristic: Dict[str, Any], goal: str) -> Dict[str, int]:
    h_scores = heuristic["dimension_scores"]
    blended = {}
    for key in DIMENSIONS:
        blended[key] = clamp(llm_scores.get(key, 62) * 0.64 + h_scores.get(key, 62) * 0.36)
    if heuristic["signals"]["ad_hits"] >= 3:
        blended["authenticity"] = min(blended["authenticity"], h_scores["authenticity"] + 3)
    if heuristic["signals"]["info_hits"] >= 6 and blended["information_density"] < h_scores["information_density"] - 4:
        blended["information_density"] = clamp(h_scores["information_density"] * 0.75 + blended["information_density"] * 0.25)
    _ = goal
    return blended


def simple_local_rewrite(title: str, body: str, category: str, goal: str) -> Tuple[str, str]:
    clean_body = "\n".join(line.strip() for line in (body or "").splitlines() if line.strip())
    clean_title = (title or "").strip()
    if not clean_title:
        first = re.split(r"[。！？!?\n]", clean_body)[0].strip()
        clean_title = first[:28] if first else f"{category}体验复盘"

    clean_title = re.sub(r"(全网最强|闭眼入|无脑买|赶紧冲|没有之一|天花板|封神)", "", clean_title).strip("｜丨 -")
    if len(clean_title) < 8:
        if goal == "提升收藏率":
            clean_title = f"{category}真实体验复盘｜适合谁先看这篇"
        elif goal == "提升转化意图":
            clean_title = f"{category}值不值得入手？我的真实判断"
        else:
            clean_title = f"{category}真实体验｜我会怎么选"

    sentences = []
    for line in clean_body.splitlines() or [clean_body]:
        parts = re.split(r"(?<=[。！？!?])", line)
        sentences.extend([p.strip() for p in parts if p.strip()])
    if len(sentences) <= 1:
        rewritten_body = clean_body
    else:
        rewritten_body = "\n\n".join(sentences)
    return clean_title, rewritten_body


def local_fallback_result(title: str, body: str, category: str, goal: str, persona: str) -> Dict[str, Any]:
    heuristic = heuristic_scores(title, body, category, goal, persona)
    rewrite_title, rewrite_caption = simple_local_rewrite(title, body, category, goal)
    strategy_canvas = {
        "target_reader": "对该品类已有兴趣、但需要更具体判断依据的潜在读者",
        "content_promise": "用真实体验和适用边界帮助读者判断是否值得继续看或收藏",
        "proof_points": heuristic["strengths"][:3] or ["补充具体场景", "补充优缺点", "补充适合/不适合人群"],
        "comment_hook": "可以在结尾抛出一个与选择困难、同类经验或踩雷点相关的问题",
    }
    return {
        "overall_score": heuristic["overall_score"],
        "overall_status": heuristic["overall_status"],
        "one_sentence_summary": "内容已有基础，但需要围绕真实体验、具体信息和发布目标继续收敛。",
        "dimension_scores": heuristic["dimension_scores"],
        "strengths": heuristic["strengths"] or ["内容主题明确，具备继续优化的基础"],
        "risks": heuristic["risks"] or ["核心风险不突出，建议继续增强具体判断依据"],
        "action_suggestions": heuristic["suggestions"] or ["保留原有真实表达，优先补充具体场景、优缺点和适合人群"],
        "rewrite_title": rewrite_title,
        "rewrite_caption": rewrite_caption,
        "rewrite_rationale": "优先去除夸张表达、整理段落结构，不新增原文没有的信息。",
        "strategy_canvas": strategy_canvas,
        "risk_priority": [
            {"risk": item, "impact": "中", "effort": "低", "first_action": "先做局部措辞或信息补充"}
            for item in (heuristic["risks"][:3] or ["信息不够具体"])
        ],
        "experiment_idea": "后续可把标题钩子、开头信息密度、结尾互动问题做 A/B 对比，观察点击、收藏和评论质量。",
        "used_fallback": True,
    }


def build_system_prompt(category: str, goal: str, persona: str, tone: str) -> str:
    return f"""
你是一个面向小红书内容场景的 AI 内容产品助手。
你的目标不是模拟平台真实推荐算法，而是帮助创作者或品牌运营在发布前做内容质量诊断、风险识别和改写决策。
所有输出必须是简体中文，并严格返回 JSON。

当前使用者：{persona}
内容品类：{category}
优化目标：{goal}
期望改写语气：{tone}

产品原则：
- 首轮只返回最关键、可行动的诊断，不要长篇说教。
- 评分要稳定，奖励真实体验、具体场景、明确取舍、可收藏信息和自然互动。
- 扣分重点是广告腔、绝对化承诺、信息空泛、缺少适用边界、互动钩子生硬。
- 改写必须基于原文已有事实，不得补充未出现的价格、成分、地点、时间、功效、数据、购买入口或具体步骤。
- 改写稿要能直接发布，不要出现“可补充”“建议写”“这里可以”等半成品提示。
- 品牌内容也要像平台原生笔记，避免硬广和夸张营销。

请返回这些字段：
overall_score: 0-100 整数
overall_status: "可发布" / "建议优化后发布" / "不建议直接发布"
one_sentence_summary: 一句话判断
dimension_scores: 五维分数 hook_strength/authenticity/information_density/interaction_potential/conversion_potential
strengths: 最多 3 条
risks: 最多 3 条
action_suggestions: 最多 3 条，必须可执行
rewrite_title: 可直接发布的标题
rewrite_caption: 可直接发布的正文
rewrite_rationale: 一句话说明改写策略
strategy_canvas: 包含 target_reader/content_promise/proof_points/comment_hook
risk_priority: 最多 3 个对象，每个包含 risk/impact/effort/first_action
experiment_idea: 一个后续 A/B 或迭代验证想法
"""


def call_ai_analysis(
    title: str,
    body: str,
    category: str,
    goal: str,
    persona: str,
    tone: str,
    heuristic: Dict[str, Any],
) -> Dict[str, Any]:
    client = get_client()
    system_prompt = build_system_prompt(category, goal, persona, tone)
    user_prompt = f"""
请诊断下面这篇小红书笔记草稿。

标题：{title}
正文：{body}

本地启发式信号，仅用于辅助你校准，不要机械复述：
{json.dumps(heuristic, ensure_ascii=False)}

请只返回 JSON，格式如下：
{{
  "overall_score": 0,
  "overall_status": "建议优化后发布",
  "one_sentence_summary": "",
  "dimension_scores": {{
    "hook_strength": 0,
    "authenticity": 0,
    "information_density": 0,
    "interaction_potential": 0,
    "conversion_potential": 0
  }},
  "strengths": ["", ""],
  "risks": ["", ""],
  "action_suggestions": ["", "", ""],
  "rewrite_title": "",
  "rewrite_caption": "",
  "rewrite_rationale": "",
  "strategy_canvas": {{
    "target_reader": "",
    "content_promise": "",
    "proof_points": ["", "", ""],
    "comment_hook": ""
  }},
  "risk_priority": [
    {{"risk": "", "impact": "高", "effort": "低", "first_action": ""}}
  ],
  "experiment_idea": ""
}}
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=1500,
    )
    raw = (response.choices[0].message.content or "").strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    parsed = json.loads(raw.strip())

    llm_scores = normalize_scores(parsed.get("dimension_scores", {}))
    blended_scores = blend_scores(llm_scores, heuristic, goal)
    overall = compute_overall(blended_scores, goal)

    status = str(parsed.get("overall_status", "")).strip()
    if status not in ["可发布", "建议优化后发布", "不建议直接发布"]:
        status = infer_status(overall, blended_scores)
    else:
        status = infer_status(overall, blended_scores)

    rewrite_title = str(parsed.get("rewrite_title", "")).strip()
    rewrite_caption = str(parsed.get("rewrite_caption", "")).strip()
    if not rewrite_title or not rewrite_caption:
        rewrite_title, rewrite_caption = simple_local_rewrite(title, body, category, goal)

    canvas = parsed.get("strategy_canvas", {})
    if not isinstance(canvas, dict):
        canvas = {}
    strategy_canvas = {
        "target_reader": str(canvas.get("target_reader", "")).strip() or "对该主题有兴趣、但需要具体判断依据的读者",
        "content_promise": str(canvas.get("content_promise", "")).strip() or "帮助读者快速判断内容是否与自己相关",
        "proof_points": safe_list(canvas.get("proof_points", []), 3),
        "comment_hook": str(canvas.get("comment_hook", "")).strip() or "用一个真实选择问题引导评论",
    }

    risk_priority = parsed.get("risk_priority", [])
    if not isinstance(risk_priority, list):
        risk_priority = []
    normalized_risks = []
    for item in risk_priority[:3]:
        if not isinstance(item, dict):
            continue
        normalized_risks.append({
            "risk": str(item.get("risk", "")).strip(),
            "impact": str(item.get("impact", "中")).strip() or "中",
            "effort": str(item.get("effort", "低")).strip() or "低",
            "first_action": str(item.get("first_action", "")).strip(),
        })
    if not normalized_risks:
        normalized_risks = [
            {"risk": risk, "impact": "中", "effort": "低", "first_action": "优先做局部信息补充或措辞收敛"}
            for risk in heuristic["risks"][:3]
        ]

    return {
        "overall_score": overall,
        "overall_status": status,
        "one_sentence_summary": str(parsed.get("one_sentence_summary", "")).strip() or "内容有一定基础，建议围绕目标做定向优化。",
        "dimension_scores": blended_scores,
        "strengths": dedupe_keep_order(safe_list(parsed.get("strengths", []), 3) + heuristic["strengths"])[:3],
        "risks": dedupe_keep_order(safe_list(parsed.get("risks", []), 3) + heuristic["risks"])[:3],
        "action_suggestions": safe_list(parsed.get("action_suggestions", []), 3) or heuristic["suggestions"][:3],
        "rewrite_title": rewrite_title,
        "rewrite_caption": rewrite_caption,
        "rewrite_rationale": str(parsed.get("rewrite_rationale", "")).strip() or "保留原文事实，强化标题抓力、结构层次和适用边界。",
        "strategy_canvas": strategy_canvas,
        "risk_priority": normalized_risks[:3],
        "experiment_idea": str(parsed.get("experiment_idea", "")).strip() or "后续可对比不同标题钩子对点击和收藏的影响。",
        "used_fallback": False,
    }


def analyze_cached(title: str, body: str, category: str, goal: str, persona: str, tone: str) -> Dict[str, Any]:
    key = make_cache_key(APP_VERSION, title.strip(), body.strip(), category, goal, persona, tone)
    cache = st.session_state.setdefault("analysis_cache", {})
    if key in cache:
        return cache[key]

    heuristic = heuristic_scores(title, body, category, goal, persona)
    if not DEEPSEEK_API_KEY:
        result = local_fallback_result(title, body, category, goal, persona)
    else:
        result = call_ai_analysis(title, body, category, goal, persona, tone, heuristic)

    result["heuristic_signals"] = heuristic["signals"]
    cache[key] = result
    return result


def compare_local_versions(
    versions: List[Dict[str, str]],
    category: str,
    goal: str,
    persona: str,
) -> List[Dict[str, Any]]:
    rows = []
    for version in versions:
        if not version["title"].strip() or not version["body"].strip():
            continue
        h = heuristic_scores(version["title"], version["body"], category, goal, persona)
        rows.append({
            "版本": version["label"],
            "综合评分": h["overall_score"],
            "发布建议": h["overall_status"],
            "首屏吸引力": h["dimension_scores"]["hook_strength"],
            "真实感": h["dimension_scores"]["authenticity"],
            "信息密度": h["dimension_scores"]["information_density"],
            "互动潜力": h["dimension_scores"]["interaction_potential"],
            "决策辅助": h["dimension_scores"]["conversion_potential"],
        })
    return sorted(rows, key=lambda x: x["综合评分"], reverse=True)


def init_session_state():
    defaults = {
        "persona_input": PERSONA_OPTIONS[0],
        "category_input": CATEGORY_OPTIONS[0],
        "goal_input": GOAL_OPTIONS[0],
        "tone_input": TONE_OPTIONS[0],
        "title_input": "",
        "body_input": "",
        "analysis_result": None,
        "manual_title": "",
        "manual_body": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.subheader("体验路径")
    st.markdown("- 选择内容品类与优化目标")
    st.markdown("- 输入一篇待发布笔记")
    st.markdown("- 查看发布建议与核心风险")
    st.markdown("- 参考内容建议和改写稿")
    st.markdown("- 对比原稿、改写稿和手动版本")
    st.markdown("---")
    st.subheader("适用场景")
    st.markdown("- 创作者发布前自查")
    st.markdown("- 品牌种草内容质检")
    st.markdown("- 多版本标题与正文筛选")


# =========================
# Tabs
# =========================
tab_main, tab_compare, tab_product = st.tabs(["发布前诊断", "多版本对比", "产品方案"])


# =========================
# Main Tab
# =========================
with tab_main:
    st.subheader("1) 发布前内容检查")
    st.caption("建议输入 80-500 字正文。内容越接近真实发布稿，诊断和改写越有参考价值。")

    example_name = st.selectbox("快速体验示例", ["不使用示例"] + list(EXAMPLES.keys()))
    e1, e2 = st.columns(2)
    with e1:
        if st.button("载入示例内容"):
            if example_name != "不使用示例":
                example = EXAMPLES[example_name]
                st.session_state.persona_input = example["persona"]
                st.session_state.category_input = example["category"]
                st.session_state.goal_input = example["goal"]
                st.session_state.tone_input = example["tone"]
                st.session_state.title_input = example["title"]
                st.session_state.body_input = example["body"]
                st.session_state.analysis_result = None
    with e2:
        if st.button("清空内容"):
            st.session_state.persona_input = PERSONA_OPTIONS[0]
            st.session_state.category_input = CATEGORY_OPTIONS[0]
            st.session_state.goal_input = GOAL_OPTIONS[0]
            st.session_state.tone_input = TONE_OPTIONS[0]
            st.session_state.title_input = ""
            st.session_state.body_input = ""
            st.session_state.analysis_result = None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        persona = st.selectbox("使用者角色", PERSONA_OPTIONS, key="persona_input")
    with c2:
        category = st.selectbox("内容品类", CATEGORY_OPTIONS, key="category_input")
    with c3:
        goal = st.selectbox("优化目标", GOAL_OPTIONS, key="goal_input")
    with c4:
        tone = st.selectbox("改写方向", TONE_OPTIONS, key="tone_input")

    title = st.text_input(
        "标题",
        key="title_input",
        placeholder="例如：黄黑皮通勤口红分享｜这支真的很提气色",
    )
    body = st.text_area(
        "正文",
        key="body_input",
        height=230,
        placeholder="输入小红书笔记正文。请尽量保留你的真实体验、场景、优缺点和判断依据。",
    )

    run = st.button("生成发布前诊断", type="primary", width="stretch")

    if run:
        if not title.strip() or not body.strip():
            st.warning("请先输入标题和正文。")
        else:
            try:
                with st.spinner("正在生成诊断、风险优先级和改写稿..."):
                    st.session_state.analysis_result = analyze_cached(
                        title=title,
                        body=body,
                        category=category,
                        goal=goal,
                        persona=persona,
                        tone=tone,
                    )
            except Exception as e:
                st.error(f"分析失败：{e}")

    result = st.session_state.get("analysis_result")
    if result:
        st.markdown("---")
        st.subheader("2) 发布决策")
        render_decision_callout(result["overall_status"], result["one_sentence_summary"])

        m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
        m1.metric("综合评分", f"{result['overall_score']}/100")
        with m2:
            st.markdown("**发布建议**")
            render_status_badge(result["overall_status"])
        with m3:
            render_label_card("优化目标", st.session_state.goal_input, "当前评分按该目标调整权重")
        with m4:
            render_label_card("内容品类", st.session_state.category_input, "用于校准场景与表达边界")

        if result.get("used_fallback"):
            st.info("当前使用基础分析模式，可先查看评分、风险和改写方向。")

        left, right = st.columns([1.05, 0.95])
        with left:
            render_card("目标读者", result["strategy_canvas"]["target_reader"])
            render_card("这篇笔记要传达什么", result["strategy_canvas"]["content_promise"])
            proof = "；".join(result["strategy_canvas"].get("proof_points", [])) or "需要补充更具体的证明点"
            render_card("支撑用户相信的理由", proof)
            render_card("适合放在结尾的互动问题", result["strategy_canvas"]["comment_hook"])
        with right:
            st.markdown("**五维评分**")
            render_score_bars(result["dimension_scores"])
            signals = result.get("heuristic_signals", {})
            st.caption(f"内容特征：{describe_content_signals(signals)}")

        st.subheader("3) 关键问题与行动建议")
        a, b, c = st.columns(3)
        with a:
            st.markdown("**已识别优势**")
            for item in result["strengths"][:3]:
                st.write(f"- {item}")
        with b:
            st.markdown("**核心风险**")
            for item in result["risks"][:3]:
                st.write(f"- {item}")
        with c:
            st.markdown("**下一步动作**")
            for idx, item in enumerate(result["action_suggestions"][:3], start=1):
                st.write(f"{idx}. {item}")

        with st.expander("优先改这 3 件事", expanded=True):
            for item in result.get("risk_priority", [])[:3]:
                render_card(
                    f"问题：{item.get('risk', '风险项')}",
                    f"为什么重要：影响 {item.get('impact', '中')}，修改成本 {item.get('effort', '低')}\n先改哪里：{item.get('first_action', '先做局部优化。')}",
                )

        st.subheader("4) AI 改写稿")
        st.caption(result.get("rewrite_rationale", "保留原文事实，强化结构与表达。"))
        st.caption("改写稿用于提供优化方向，建议保留原文中更真实、有个人识别度的表达。")

        rt1, rt2 = st.columns([8.8, 1.2], vertical_alignment="center")
        with rt1:
            st.markdown("**改写标题**")
        with rt2:
            render_copy_button(result["rewrite_title"], "复制标题", "rewrite-title")
        render_text_box(result["rewrite_title"], min_height=68)

        rb1, rb2 = st.columns([8.8, 1.2], vertical_alignment="center")
        with rb1:
            st.markdown("**改写正文**")
        with rb2:
            render_copy_button(result["rewrite_caption"], "复制正文", "rewrite-body")
        render_text_box(result["rewrite_caption"], min_height=190)

        rewrite_comparison = build_rewrite_comparison(
            original_title=st.session_state.title_input,
            original_body=st.session_state.body_input,
            rewrite_title=result["rewrite_title"],
            rewrite_body=result["rewrite_caption"],
            category=st.session_state.category_input,
            goal=st.session_state.goal_input,
            persona=st.session_state.persona_input,
        )
        st.subheader("5) 改写方向预估")
        cmp1, cmp2, cmp3, cmp4 = st.columns(4)
        cmp1.metric(
            "综合评分",
            f"{rewrite_comparison['rewritten']['overall_score']}/100",
            delta=delta_text(rewrite_comparison["deltas"]["overall_score"]),
        )
        cmp2.metric(
            "信息密度",
            rewrite_comparison["rewritten"]["dimension_scores"]["information_density"],
            delta=delta_text(rewrite_comparison["deltas"]["information_density"]),
        )
        cmp3.metric(
            "互动潜力",
            rewrite_comparison["rewritten"]["dimension_scores"]["interaction_potential"],
            delta=delta_text(rewrite_comparison["deltas"]["interaction_potential"]),
        )
        cmp4.metric(
            "决策辅助",
            rewrite_comparison["rewritten"]["dimension_scores"]["conversion_potential"],
            delta=delta_text(rewrite_comparison["deltas"]["conversion_potential"]),
        )
        st.caption("用于比较表达方向，不代表真实发布表现。")

        st.subheader("6) 后续验证想法")
        st.success(result.get("experiment_idea", "后续可对比不同标题钩子对点击和收藏的影响。"))


# =========================
# Compare Tab
# =========================
with tab_compare:
    st.subheader("多版本对比")
    st.caption("当你不确定用原稿、AI 改写稿还是自己调整版时，用同一套评分框架做快速筛选。")

    result = st.session_state.get("analysis_result")
    if not result:
        st.info("请先在“发布前诊断”页生成一次结果。")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("手动版本标题", key="manual_title")
            st.text_area("手动版本正文", key="manual_body", height=180)
        with c2:
            render_card(
                "对比逻辑",
                "原稿和 AI 改写稿会自动纳入对比；如果你填写手动版本，系统会用同一套评分框架计算目标导向得分。",
            )
            render_card(
                "选择建议",
                "优先选择综合评分更高、真实感和信息密度更稳的版本；如果目标是转化，也要重点看决策辅助得分。",
            )

        versions = [
            {"label": "原稿", "title": st.session_state.title_input, "body": st.session_state.body_input},
            {"label": "AI 改写稿", "title": result["rewrite_title"], "body": result["rewrite_caption"]},
        ]
        if st.session_state.manual_title.strip() and st.session_state.manual_body.strip():
            versions.append({
                "label": "手动版本",
                "title": st.session_state.manual_title,
                "body": st.session_state.manual_body,
            })

        rows = compare_local_versions(
            versions=versions,
            category=st.session_state.category_input,
            goal=st.session_state.goal_input,
            persona=st.session_state.persona_input,
        )
        if rows:
            winner = rows[0]
            st.success(f"当前评分最高：{winner['版本']}（{winner['综合评分']}/100，{winner['发布建议']}）")
            st.dataframe(rows, width="stretch", hide_index=True)


# =========================
# Product Tab
# =========================
with tab_product:
    st.subheader("产品方案")
    st.caption("围绕“发布前内容决策”设计，让创作者和品牌运营在发布前更快判断内容是否值得发、哪里需要改。")

    st.markdown("**项目说明**")
    project1, project2 = st.columns(2)
    with project1:
        render_card(
            "为什么做",
            "小红书内容生产里，很多创作者和品牌运营并不缺文案灵感，真正困难的是发布前判断：这篇内容够不够真实、是否有收藏价值、哪里最值得先改。",
            min_height=132,
        )
        render_card(
            "用户定义",
            "优先服务有明确发布目标的人：个人创作者关注真实表达和互动，品牌运营关注原生感、风险控制和转化辅助，MCN / 代理商关注多版本筛选效率。",
            min_height=132,
        )
    with project2:
        render_card(
            "关键取舍",
            "首版不做批量生成和账号运营建议，而是聚焦单篇笔记的发布前决策；先把“能不能发、为什么、怎么改”这条链路做清楚。",
            min_height=132,
        )
        render_card(
            "验证计划",
            "先观察建议采纳率和改写后可发布率，再接入发布后的点击、收藏和评论质量，持续校准不同品类、不同目标下的评分权重。",
            min_height=132,
        )

    st.markdown("**产品机制**")
    flow1, flow2 = st.columns(2)
    with flow1:
        render_card(
            "核心流程",
            "输入笔记草稿与发布目标 → 获得发布建议、五维评分和关键风险 → 查看内容建议与下一步动作 → 参考改写稿 → 对比不同版本。",
            min_height=132,
        )
        render_card(
            "评分框架",
            "围绕首屏吸引力、真实感、信息密度、互动潜力和决策辅助五个维度评估，并根据点击、互动、收藏、转化等目标调整权重。",
            min_height=132,
        )
    with flow2:
        render_card(
            "MVP 范围",
            "优先覆盖单篇笔记诊断、风险识别、改写建议和多版本对比；暂不覆盖批量选题、账号运营策略或真实投放归因。",
            min_height=132,
        )
        render_card(
            "体验原则",
            "首屏先给结论，再给证据和动作；建议具体可执行，改写保留原文事实，不用夸张表达换取短期吸引。",
            min_height=132,
        )

    st.markdown("**衡量指标**")
    metric1, metric2, metric3 = st.columns(3)
    with metric1:
        render_label_card("核心指标", "建议采纳率", "用户是否愿意按诊断结果修改内容", min_height=126)
    with metric2:
        render_label_card("质量指标", "有效发布率", "优化后内容是否更接近可发布状态", min_height=126)
    with metric3:
        render_label_card("长期指标", "反馈闭环", "发布后互动质量回流评分体系", min_height=126)

    st.markdown("**能力边界**")
    boundary1, boundary2, boundary3 = st.columns(3)
    with boundary1:
        render_card("不模拟平台算法", "基于内容质量信号辅助判断，不声称知道真实推荐机制。", min_height=112)
    with boundary2:
        render_card("不鼓励夸张表达", "避免夸大功效、绝对化承诺或为了吸引点击牺牲信任感。", min_height=112)
    with boundary3:
        render_card("不新增未经提供的信息", "改写基于原文已有事实，不补充未出现的价格、功效、数据或承诺。", min_height=112)
