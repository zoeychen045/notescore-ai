import html
import json
import os
import re
from typing import Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="NoteScore AI",
    page_icon="📝",
    layout="wide"
)

# =========================
# App Copy
# =========================
APP_TITLE = "📝 NoteScore AI"
APP_SUBTITLE = "面向小红书内容场景的 AI 内容发布前诊断与优化 Demo"
APP_DESC = "帮助创作者与品牌运营在发布前快速评估笔记质量、识别风险并生成优化版本。"
APP_NOTE = "说明：本 Demo 基于内容质量信号进行分析，用于辅助内容优化，不代表平台真实推荐机制。"

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)
st.caption(APP_DESC)
st.caption(APP_NOTE)

# =========================
# Secrets
# =========================
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))

# =========================
# Constants
# =========================
WEIGHTS = {
    "hook_strength": 0.25,
    "authenticity": 0.25,
    "information_density": 0.20,
    "interaction_potential": 0.15,
    "conversion_potential": 0.15,
}

CATEGORY_OPTIONS = ["美妆", "护肤", "时尚", "穿搭", "食品", "生活方式", "旅行", "其他"]
GOAL_OPTIONS = ["提升点击率", "提升互动率", "提升收藏率", "提升转化意图"]

EXAMPLES = {
    "美妆｜较强内容示例": {
        "category": "美妆",
        "goal": "提升互动率",
        "title": "黄黑皮通勤口红分享｜这支真的比我想象中更提气色",
        "body": """最近早八通勤一直在用这支豆沙棕调口红。
我本身黄黑皮，平时淡妆比较多，最怕颜色显脏或者太挑皮。
这支上嘴是很稳的日常提气色类型，薄涂更自然，厚涂会更有氛围感。
优点是通勤不夸张、素颜也不会太突兀，缺点是吃完饭还是要补一下。
如果你也是黄皮、想找一支不容易出错的日常色，可以去柜台试试类似色调。"""
    },
    "护肤｜广告感偏强示例": {
        "category": "护肤",
        "goal": "提升点击率",
        "title": "全网最强面霜！闭眼入就对了！",
        "body": """这款面霜真的绝了，谁不用我都会伤心！
保湿、修护、提亮、抗老全部一步到位，任何肤质都适合！
这是我今年用过最最最厉害的产品，没有之一，赶紧冲！
现在买最划算，真的无脑入！"""
    },
    "生活方式｜可优化示例": {
        "category": "生活方式",
        "goal": "提升收藏率",
        "title": "租房党收纳好物分享",
        "body": """最近买了几个收纳用品，感觉还不错。
有些挺方便的，也比较适合小空间。
简单分享一下，之后有时间再详细说。"""
    },
}

AD_WORDS = [
    "全网最", "闭眼入", "速冲", "必须买", "无脑买", "赶紧冲", "冲就完了",
    "100%有效", "立刻下单", "最低价", "官方认证", "没有之一"
]
SCENE_WORDS = [
    "通勤", "熬夜", "黄黑皮", "油皮", "干皮", "敏感肌", "学生党", "打工人",
    "约会", "旅行", "换季", "早八", "军训", "租房党"
]
AUTH_WORDS = [
    "我", "自己", "实测", "亲测", "回购", "踩雷", "空瓶", "用了",
    "对比", "反馈", "复盘", "上脸", "上嘴", "我觉得"
]
INFO_WORDS = [
    "成分", "质地", "妆效", "持妆", "步骤", "教程", "对比", "优缺点",
    "价格", "色号", "肤质", "建议", "避雷", "清单", "使用感", "适合"
]
ENGAGE_WORDS = [
    "你们", "姐妹", "有人", "有没有", "吗？", "吗?", "求推荐", "哪个更",
    "评论区", "欢迎讨论"
]
CONVERT_WORDS = [
    "适合", "不适合", "推荐给", "值得买", "平替", "预算", "性价比",
    "回购", "入手", "拔草", "种草", "试试"
]

# =========================
# Helpers
# =========================
def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))

def dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        item = str(item).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result

def safe_list(value, max_len: int = 5) -> List[str]:
    if not isinstance(value, list):
        value = [str(value)]
    return dedupe_keep_order(value)[:max_len]

def render_copy_button(text: str, label: str, key: str):
    safe_text = json.dumps(text)

    components.html(
        f"""
        <div style="
            width: 100%;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            padding-top: 2px;
            padding-bottom: 6px;
            box-sizing: border-box;
        ">
            <button id="copy-btn-{key}" style="
                width: 108px;
                height: 42px;
                border-radius: 10px;
                border: 1px solid #D0D5DD;
                background: #FFFFFF;
                color: #111827;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                white-space: nowrap;
            ">
                {label}
            </button>
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
                setTimeout(() => {{
                    btn.innerText = "{label}";
                }}, 1200);
            }}
        }}
        </script>
        """,
        height=58,
    )

def render_content_box(text: str, min_height: int = 0):
    safe_text = html.escape(text).replace("\n", "<br>")

    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            padding: 16px 18px;
            color: #111827;
            font-size: 16px;
            line-height: 1.75;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
            min-height: {min_height}px;
            margin-bottom: 8px;
            white-space: normal;
            word-break: break-word;
        ">
            {safe_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

def heuristic_signals(title: str, body: str) -> Dict:
    text = f"{title}\n{body}"
    strengths = []
    risks = []
    adjustments = {
        "hook_strength": 0,
        "authenticity": 0,
        "information_density": 0,
        "interaction_potential": 0,
        "conversion_potential": 0,
    }

    title_len = len(title.strip())
    if 8 <= title_len <= 24:
        adjustments["hook_strength"] += 4
        strengths.append("标题长度较适中，更像平台原生笔记标题")
    elif title_len < 6:
        adjustments["hook_strength"] -= 6
        risks.append("标题过短，信息量不足")
    elif title_len > 30:
        adjustments["hook_strength"] -= 4
        risks.append("标题偏长，首屏抓力可能下降")

    if re.search(r"[0-9一二三四五六七八九十]", title):
        adjustments["hook_strength"] += 3
        strengths.append("标题包含具体信息或数字，利于建立预期")

    if any(word in text for word in SCENE_WORDS):
        adjustments["hook_strength"] += 3
        adjustments["authenticity"] += 4
        strengths.append("内容包含具体使用场景/人群，真实感更强")

    auth_hits = sum(word in text for word in AUTH_WORDS)
    if auth_hits >= 2:
        adjustments["authenticity"] += 6
        strengths.append("内容包含较强个人体验表达")
    elif auth_hits == 0:
        adjustments["authenticity"] -= 5
        risks.append("个人体验痕迹偏弱，像泛化文案")

    ad_hits = sum(word in text for word in AD_WORDS)
    if ad_hits >= 2:
        adjustments["authenticity"] -= 12
        adjustments["conversion_potential"] -= 3
        risks.append("营销腔较重，容易削弱平台原生感")
    elif ad_hits == 1:
        adjustments["authenticity"] -= 6
        risks.append("存在明显促销化表达")

    info_hits = sum(word in text for word in INFO_WORDS)
    if info_hits >= 3:
        adjustments["information_density"] += 8
        strengths.append("内容信息密度较高，有收藏价值")
    elif info_hits <= 1:
        adjustments["information_density"] -= 6
        risks.append("内容较泛，缺少具体细节或判断依据")

    if "\n" in body or "1." in body or "①" in body or "优点" in body or "缺点" in body:
        adjustments["information_density"] += 4
        strengths.append("结构较清晰，便于快速阅读")

    engage_hits = sum(word in text for word in ENGAGE_WORDS)
    if engage_hits >= 1 or "？" in text or "?" in text:
        adjustments["interaction_potential"] += 6
        strengths.append("具备一定互动触发点")
    else:
        adjustments["interaction_potential"] -= 3
        risks.append("互动钩子偏弱，评论意愿可能不足")

    convert_hits = sum(word in text for word in CONVERT_WORDS)
    if convert_hits >= 2:
        adjustments["conversion_potential"] += 6
        strengths.append("具备一定种草或决策辅助信息")
    elif convert_hits == 0:
        adjustments["conversion_potential"] -= 4
        risks.append("离“帮助决策”还有距离")

    return {
        "strengths": dedupe_keep_order(strengths),
        "risks": dedupe_keep_order(risks),
        "adjustments": adjustments,
    }

def get_client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        raise ValueError("未检测到 DEEPSEEK_API_KEY。请先在 .streamlit/secrets.toml 或环境变量中配置。")
    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )

def call_deepseek_analysis(
    client: OpenAI,
    title: str,
    body: str,
    category: str,
    goal: str,
    heuristics: Dict,
    include_rewrite: bool = True,
) -> Dict:
    rewrite_instruction = """
- 需要输出 rewrite_title 和 rewrite_caption
- 改写标题和改写正文必须是可直接展示给用户的最终版本
- 不要出现“可补充”“可填写”“可提及”“可替换”“可写成”等占位符或备注语气
- 不要用括号给作者留提醒，不要输出半成品草稿
""" if include_rewrite else """
- rewrite_title 返回空字符串
- rewrite_caption 返回空字符串
"""

    system_prompt = """
你是一个面向小红书内容场景的AI内容评估助手。
你需要评估一篇笔记草稿的内容质量，并返回严格 JSON。
你不能声称自己知道平台真实推荐算法，只能基于内容质量信号做判断。
输出内容必须全部使用简体中文。
返回必须是有效 json。
"""

    user_prompt = f"""
请评估下面这篇小红书笔记草稿。

【输入信息】
标题：{title}
正文：{body}
品类：{category}
目标：{goal}

【评估维度】
请分别给出 0-100 分：
1. hook_strength：首屏吸引力 / 标题抓力
2. authenticity：真实感 / 原生感
3. information_density：信息价值 / 具体程度
4. interaction_potential：互动潜力（评论/收藏/讨论）
5. conversion_potential：种草 / 决策辅助潜力

【评估原则】
- 优先奖励：具体场景、真实体验、清晰结构、可收藏的信息、自然的互动触发
- 重点扣分：明显广告腔、夸张空泛、缺少细节、像硬广不像笔记
- 建议要务实，像产品中的内容诊断结果
- strengths、risks、suggestions 尽量避免语义重复，每项都要有明显区分
- 请结合下方启发式信号参考，但不要机械重复

【改写要求】
{rewrite_instruction}

【启发式信号，仅供参考，不是最终结论】
{json.dumps(heuristics, ensure_ascii=False)}

【返回格式】
请严格返回 json，不要 markdown，不要额外解释：
{{
  "one_sentence_summary": "一句话总结",
  "dimension_scores": {{
    "hook_strength": 0,
    "authenticity": 0,
    "information_density": 0,
    "interaction_potential": 0,
    "conversion_potential": 0
  }},
  "strengths": ["", ""],
  "risks": ["", ""],
  "suggestions": ["", "", ""],
  "rewrite_title": "",
  "rewrite_caption": ""
}}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.6,
        max_tokens=1200,
    )

    raw = (response.choices[0].message.content or "").strip()
    if not raw:
        raise ValueError("模型返回为空，请重试一次。")

    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]

    try:
        parsed = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"模型返回的 JSON 解析失败：{e}")

    required_top_keys = [
        "one_sentence_summary",
        "dimension_scores",
        "strengths",
        "risks",
        "suggestions",
        "rewrite_title",
        "rewrite_caption",
    ]
    for key in required_top_keys:
        if key not in parsed:
            raise ValueError(f"模型返回缺少字段：{key}")

    dims = parsed.get("dimension_scores", {})
    for key in WEIGHTS.keys():
        if key not in dims:
            dims[key] = 60
        try:
            dims[key] = clamp(float(dims[key]))
        except Exception:
            dims[key] = 60
    parsed["dimension_scores"] = dims

    parsed["strengths"] = safe_list(parsed.get("strengths", []), 5)
    parsed["risks"] = safe_list(parsed.get("risks", []), 5)
    parsed["suggestions"] = safe_list(parsed.get("suggestions", []), 5)

    parsed["one_sentence_summary"] = str(parsed.get("one_sentence_summary", "")).strip()
    parsed["rewrite_title"] = str(parsed.get("rewrite_title", "")).strip()
    parsed["rewrite_caption"] = str(parsed.get("rewrite_caption", "")).strip()

    return parsed

def blend_result(llm_result: Dict, heuristics: Dict) -> Dict:
    dims = llm_result["dimension_scores"].copy()

    for key, adj in heuristics["adjustments"].items():
        dims[key] = clamp(dims.get(key, 60) + adj)

    overall = 0
    for key, weight in WEIGHTS.items():
        overall += dims[key] * weight

    result = llm_result.copy()
    result["dimension_scores"] = dims
    result["overall_score"] = clamp(overall)
    result["strengths"] = dedupe_keep_order(
        llm_result.get("strengths", []) + heuristics.get("strengths", [])
    )[:5]
    result["risks"] = dedupe_keep_order(
        llm_result.get("risks", []) + heuristics.get("risks", [])
    )[:5]
    result["suggestions"] = dedupe_keep_order(
        llm_result.get("suggestions", [])
    )[:5]
    return result

def get_publish_decision(result: Dict) -> Tuple[str, str, str]:
    overall = result["overall_score"]
    dims = result["dimension_scores"]
    auth = dims["authenticity"]
    info = dims["information_density"]
    hook = dims["hook_strength"]

    if overall >= 82 and auth >= 75 and info >= 65 and hook >= 70:
        return "建议发布", "#e8f5e9", "#2e7d32"
    elif overall >= 68:
        return "建议修改后发布", "#fff8e1", "#b26a00"
    else:
        return "建议重写", "#ffebee", "#c62828"

def render_decision(label: str, bg: str, fg: str):
    st.markdown(
        f"""
        <div style="
            background:{bg};
            color:{fg};
            padding:12px 16px;
            border-radius:12px;
            font-weight:700;
            display:inline-block;
            font-size:18px;
            margin-top:4px;
            margin-bottom:8px;
        ">
            {label}
        </div>
        """,
        unsafe_allow_html=True
    )

def compare_scores(before: Dict, after: Dict) -> Dict:
    keys = list(WEIGHTS.keys())
    diff = {}
    for key in keys:
        diff[key] = after["dimension_scores"][key] - before["dimension_scores"][key]
    diff["overall_score"] = after["overall_score"] - before["overall_score"]
    return diff

# =========================
# Sidebar
# =========================
with st.sidebar:
    st.subheader("适用场景")
    st.write("适用于创作者、品牌内容运营及种草投放场景，用于在发布前快速判断一篇笔记的内容质量与优化方向。")

    st.markdown("**建议体验路径**")
    st.markdown("- 输入一篇较强笔记，查看内容优势")
    st.markdown("- 输入一篇偏广告笔记，查看风险识别")
    st.markdown("- 对比原文与改写版本，观察优化方向")

    st.markdown("**核心输出**")
    st.markdown("- 五维评分")
    st.markdown("- 风险诊断")
    st.markdown("- 优化建议")
    st.markdown("- 改写版本")
    st.markdown("- 优化前后对比")

    st.markdown("---")
    if DEEPSEEK_API_KEY:
        st.success("分析服务可用")
    else:
        st.warning("分析服务不可用")

# =========================
# Session State
# =========================
if "title_input" not in st.session_state:
    st.session_state.title_input = ""
if "body_input" not in st.session_state:
    st.session_state.body_input = ""
if "category_input" not in st.session_state:
    st.session_state.category_input = CATEGORY_OPTIONS[0]
if "goal_input" not in st.session_state:
    st.session_state.goal_input = GOAL_OPTIONS[0]
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# =========================
# Input Area
# =========================
st.subheader("1) 输入待优化笔记")

example_name = st.selectbox(
    "快速体验示例",
    ["不使用示例"] + list(EXAMPLES.keys())
)

col_ex1, col_ex2 = st.columns([1, 1])
with col_ex1:
    if st.button("载入示例内容"):
        if example_name != "不使用示例":
            st.session_state.title_input = EXAMPLES[example_name]["title"]
            st.session_state.body_input = EXAMPLES[example_name]["body"]
            st.session_state.category_input = EXAMPLES[example_name]["category"]
            st.session_state.goal_input = EXAMPLES[example_name]["goal"]
            st.session_state.analysis_result = None
with col_ex2:
    if st.button("清空内容"):
        st.session_state.title_input = ""
        st.session_state.body_input = ""
        st.session_state.category_input = CATEGORY_OPTIONS[0]
        st.session_state.goal_input = GOAL_OPTIONS[0]
        st.session_state.analysis_result = None

col1, col2 = st.columns(2)
with col1:
    category = st.selectbox("内容品类", CATEGORY_OPTIONS, key="category_input")
with col2:
    goal = st.selectbox("优化目标", GOAL_OPTIONS, key="goal_input")

title = st.text_input(
    "标题",
    key="title_input",
    placeholder="例如：黄黑皮通勤口红分享｜这支真的很提气色"
)
body = st.text_area(
    "正文",
    key="body_input",
    height=220,
    placeholder="输入小红书笔记正文，建议 80-400 字，更容易看出评分差异。"
)

run = st.button("生成内容诊断", type="primary")

# =========================
# Run Analysis
# =========================
if run:
    if not title.strip() or not body.strip():
        st.warning("请先输入标题和正文。")
    elif not DEEPSEEK_API_KEY:
        st.error("没有检测到 API Key。请先配置 DEEPSEEK_API_KEY。")
    else:
        with st.spinner("正在生成内容诊断与优化版本..."):
            try:
                client = get_client()

                original_heuristics = heuristic_signals(title, body)
                original_llm = call_deepseek_analysis(
                    client=client,
                    title=title,
                    body=body,
                    category=category,
                    goal=goal,
                    heuristics=original_heuristics,
                    include_rewrite=True,
                )
                original_result = blend_result(original_llm, original_heuristics)

                rewrite_title = original_result["rewrite_title"]
                rewrite_caption = original_result["rewrite_caption"]

                optimized_heuristics = heuristic_signals(rewrite_title, rewrite_caption)
                optimized_llm = call_deepseek_analysis(
                    client=client,
                    title=rewrite_title,
                    body=rewrite_caption,
                    category=category,
                    goal=goal,
                    heuristics=optimized_heuristics,
                    include_rewrite=False,
                )
                optimized_result = blend_result(optimized_llm, optimized_heuristics)

                score_diff = compare_scores(original_result, optimized_result)
                publish_label, publish_bg, publish_fg = get_publish_decision(original_result)
                optimized_publish_label, optimized_publish_bg, optimized_publish_fg = get_publish_decision(optimized_result)

                st.session_state.analysis_result = {
                    "category": category,
                    "goal": goal,
                    "original_title": title,
                    "original_body": body,
                    "original_result": original_result,
                    "optimized_title": rewrite_title,
                    "optimized_body": rewrite_caption,
                    "optimized_result": optimized_result,
                    "score_diff": score_diff,
                    "publish_decision": (publish_label, publish_bg, publish_fg),
                    "optimized_publish_decision": (optimized_publish_label, optimized_publish_bg, optimized_publish_fg),
                }

            except Exception as e:
                st.error(f"分析失败：{e}")
                st.stop()

# =========================
# Render Result
# =========================
result_bundle = st.session_state.analysis_result

if result_bundle:
    category = result_bundle["category"]
    goal = result_bundle["goal"]
    original_result = result_bundle["original_result"]
    optimized_result = result_bundle["optimized_result"]
    score_diff = result_bundle["score_diff"]
    publish_label, publish_bg, publish_fg = result_bundle["publish_decision"]
    optimized_publish_label, optimized_publish_bg, optimized_publish_fg = result_bundle["optimized_publish_decision"]

    st.markdown("---")
    st.subheader("2) 内容诊断结果")

    decision_col1, decision_col2 = st.columns(2)
    with decision_col1:
        st.markdown("**当前发布建议**")
        render_decision(publish_label, publish_bg, publish_fg)
    with decision_col2:
        st.markdown("**优化后预期建议**")
        render_decision(optimized_publish_label, optimized_publish_bg, optimized_publish_fg)

    c1, c2, c3 = st.columns(3)
    c1.metric("综合评分", f"{original_result['overall_score']}/100")
    c2.metric("内容品类", category)
    c3.metric("优化目标", goal)

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("吸引力", original_result["dimension_scores"]["hook_strength"])
    d2.metric("真实感", original_result["dimension_scores"]["authenticity"])
    d3.metric("信息价值", original_result["dimension_scores"]["information_density"])
    d4.metric("互动潜力", original_result["dimension_scores"]["interaction_potential"])
    d5.metric("转化潜力", original_result["dimension_scores"]["conversion_potential"])

    st.info(f"**一句话判断：** {original_result['one_sentence_summary']}")

    left, right = st.columns(2)

    with left:
        st.success("识别到的优点")
        for item in original_result["strengths"]:
            st.write(f"- {item}")

        st.warning("主要风险")
        for item in original_result["risks"]:
            st.write(f"- {item}")

    with right:
        st.subheader("优化建议")
        for i, item in enumerate(original_result["suggestions"], start=1):
            st.write(f"{i}. {item}")

    st.subheader("优化后建议版本")

    title_label_col, title_btn_col = st.columns([8.8, 1.2], vertical_alignment="center")
    with title_label_col:
        st.markdown("**改写标题**")
    with title_btn_col:
        render_copy_button(result_bundle["optimized_title"], "复制标题", "optimized-title")

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
    render_content_box(result_bundle["optimized_title"], min_height=72)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    body_label_col, body_btn_col = st.columns([8.8, 1.2], vertical_alignment="center")
    with body_label_col:
        st.markdown("**改写正文**")
    with body_btn_col:
        render_copy_button(result_bundle["optimized_body"], "复制正文", "optimized-body")

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
    render_content_box(result_bundle["optimized_body"], min_height=180)

    st.markdown("---")
    st.subheader("3) 优化前后对比评分")

    cmp1, cmp2, cmp3 = st.columns(3)
    cmp1.metric(
        "综合评分变化",
        f"{optimized_result['overall_score']}/100",
        delta=f"{score_diff['overall_score']:+d}"
    )
    cmp2.metric("优化前发布建议", publish_label)
    cmp3.metric("优化后发布建议", optimized_publish_label)

    dd1, dd2, dd3, dd4, dd5 = st.columns(5)
    dd1.metric(
        "吸引力",
        optimized_result["dimension_scores"]["hook_strength"],
        delta=f"{score_diff['hook_strength']:+d}"
    )
    dd2.metric(
        "真实感",
        optimized_result["dimension_scores"]["authenticity"],
        delta=f"{score_diff['authenticity']:+d}"
    )
    dd3.metric(
        "信息价值",
        optimized_result["dimension_scores"]["information_density"],
        delta=f"{score_diff['information_density']:+d}"
    )
    dd4.metric(
        "互动潜力",
        optimized_result["dimension_scores"]["interaction_potential"],
        delta=f"{score_diff['interaction_potential']:+d}"
    )
    dd5.metric(
        "转化潜力",
        optimized_result["dimension_scores"]["conversion_potential"],
        delta=f"{score_diff['conversion_potential']:+d}"
    )

    st.info(f"**优化后一句话判断：** {optimized_result['one_sentence_summary']}")