import re
from typing import Dict, List

import streamlit as st

st.set_page_config(
    page_title="NoteScore AI",
    page_icon="📝",
    layout="wide"
)

st.title("📝 NoteScore AI")
st.caption("面向小红书内容场景的UGC内容质量评分 Demo")
st.caption("说明：本 Demo 使用模拟的内容质量信号，不代表平台真实推荐算法。")

# ---------- Constants ----------
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
    "美妆-较强版本": {
        "title": "黄黑皮通勤口红分享｜这支真的比我想象中更提气色",
        "body": """最近早八通勤一直在用这支豆沙棕调口红。
我本身黄黑皮，平时淡妆比较多，最怕颜色显脏或者太挑皮。
这支上嘴是很稳的日常提气色类型，薄涂更自然，厚涂会更有氛围感。
优点是通勤不夸张、素颜也不会太突兀，缺点是吃完饭还是要补一下。
如果你也是黄皮、想找一支不容易出错的日常色，可以去柜台试试类似色调。"""
    },
    "护肤-偏广告版本": {
        "title": "全网最强面霜！闭眼入就对了！",
        "body": """这款面霜真的绝了，谁不用我都会伤心！
保湿、修护、提亮、抗老全部一步到位，任何肤质都适合！
这是我今年用过最最最厉害的产品，没有之一，赶紧冲！
现在买最划算，真的无脑入！"""
    },
    "生活方式-可优化版本": {
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

# ---------- Helpers ----------
def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))

def dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result

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

# ---------- Mock Model ----------
def call_deepseek(title: str, body: str, category: str, goal: str, heuristics: Dict) -> Dict:
    text = f"{title}\n{body}"

    # 根据内容稍微做一点动态 mock，让不同输入看起来更合理
    ad_hits = sum(word in text for word in AD_WORDS)
    info_hits = sum(word in text for word in INFO_WORDS)
    scene_hits = sum(word in text for word in SCENE_WORDS)
    engage_hits = sum(word in text for word in ENGAGE_WORDS)

    if ad_hits >= 2:
        return {
            "one_sentence_summary": "这篇内容营销感较强，首屏有冲击力，但原生感与可信度偏弱。",
            "dimension_scores": {
                "hook_strength": 76,
                "authenticity": 48,
                "information_density": 52,
                "interaction_potential": 58,
                "conversion_potential": 66
            },
            "strengths": [
                "标题情绪强，首屏容易抓住注意力",
                "具备一定直接转化导向"
            ],
            "risks": [
                "广告腔较重，像硬广不像笔记",
                "缺少真实体验和具体使用细节"
            ],
            "suggestions": [
                "减少夸张表达，改成更像个人经验分享的口吻",
                "加入肤质、场景、使用前后变化等细节",
                "补充优缺点或适用人群，提高可信度"
            ],
            "rewrite_title": "这罐面霜我用了两周｜适合干皮，但不是所有人都适合",
            "rewrite_caption": "最近连续用了两周这款面霜，先说结论：保湿力不错，更适合偏干或换季容易起皮的时候用。它的优点是上脸比较舒服，晚上厚涂第二天不会太紧绷，但油皮可能会觉得略厚。比起“闭眼入”，我更建议大家先看自己肤质再决定。你们最近有用到类似的保湿面霜吗？"
        }

    if scene_hits >= 1 and info_hits >= 2:
        return {
            "one_sentence_summary": "这篇内容有较好的场景感和真实感，整体更接近平台原生笔记。",
            "dimension_scores": {
                "hook_strength": 80,
                "authenticity": 84,
                "information_density": 78,
                "interaction_potential": 70,
                "conversion_potential": 77
            },
            "strengths": [
                "标题较自然，有一定场景感",
                "正文包含个人体验和判断依据"
            ],
            "risks": [
                "互动触发点还可以更强",
                "记忆点和差异化表达还能加强"
            ],
            "suggestions": [
                "增加一句面向同类人群的提问，提升评论意愿",
                "补充更具体的对比信息或踩雷点",
                "把最核心卖点前置，让开头更抓人"
            ],
            "rewrite_title": "黄黑皮通勤口红分享｜日常提气色但不夸张的一支",
            "rewrite_caption": "最近通勤一直在用这支豆沙棕调口红。对黄黑皮来说，它最大的优点是比较稳，不容易显脏，淡妆或素颜也能撑住气色。薄涂自然，厚涂更有氛围感，比较适合通勤或日常出门。缺点是吃完饭还是需要补一下。如果你也在找一支不容易出错的通勤色，这类棕调豆沙色真的值得去试试。你们最近有没有用到类似的口红？"
        }

    return {
        "one_sentence_summary": "这篇内容方向是对的，但信息量和互动设计还有提升空间。",
        "dimension_scores": {
            "hook_strength": 72,
            "authenticity": 76,
            "information_density": 64,
            "interaction_potential": 62,
            "conversion_potential": 68
        },
        "strengths": [
            "主题比较清晰，适合继续打磨",
            "内容语气相对自然，不算生硬"
        ],
        "risks": [
            "细节偏少，暂时不够有收藏价值",
            "互动触发点不足，讨论感较弱"
        ],
        "suggestions": [
            "补充具体使用场景、适用人群或实际体验",
            "加入优缺点或对比信息，增强判断依据",
            "结尾增加一个自然提问，提升互动率"
        ],
        "rewrite_title": "租房党收纳好物分享｜小空间里真的更实用的几样",
        "rewrite_caption": "最近买了几样适合小空间的收纳用品，用下来感觉确实更适合租房党。最大的感受是桌面会清爽很多，日常找东西也更方便。它们不一定是“必买”，但如果你房间不大、东西又比较杂，这类收纳真的会提高生活效率。后面我也可以单独整理一篇，把好用和踩雷的地方都写清楚。你们有没有买过真正不占地方又实用的收纳好物？"
    }

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
    result["suggestions"] = dedupe_keep_order(llm_result.get("suggestions", []))[:5]
    return result

# ---------- Sidebar ----------
with st.sidebar:
    st.subheader("Demo 设置")
    st.write("当前为本地测试版，不调用真实 API。")
    st.markdown("**建议展示路径**")
    st.markdown("- 输入一篇较强笔记")
    st.markdown("- 输入一篇明显偏广告的笔记")
    st.markdown("- 对比优化前后结果")

# ---------- Example Loader ----------
st.subheader("1) 输入待评估内容")

example_name = st.selectbox("选择示例（可直接载入）", ["不使用示例"] + list(EXAMPLES.keys()))

if "title_input" not in st.session_state:
    st.session_state.title_input = ""
if "body_input" not in st.session_state:
    st.session_state.body_input = ""

if st.button("载入示例"):
    if example_name != "不使用示例":
        st.session_state.title_input = EXAMPLES[example_name]["title"]
        st.session_state.body_input = EXAMPLES[example_name]["body"]

col1, col2 = st.columns(2)
with col1:
    category = st.selectbox("内容品类", CATEGORY_OPTIONS, index=0)
with col2:
    goal = st.selectbox("优化目标", GOAL_OPTIONS, index=0)

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

run = st.button("开始分析", type="primary")

# ---------- Analysis ----------
if run:
    if not title.strip() or not body.strip():
        st.warning("请先输入标题和正文。")
    else:
        heuristics = heuristic_signals(title, body)

        with st.spinner("正在分析内容质量..."):
            try:
                llm_result = call_deepseek(title, body, category, goal, heuristics)
                result = blend_result(llm_result, heuristics)
            except Exception as e:
                st.error(f"分析失败：{e}")
                st.stop()

        st.markdown("---")
        st.subheader("2) 评分结果")

        c1, c2, c3 = st.columns(3)
        c1.metric("综合评分", f"{result['overall_score']}/100")
        c2.metric("内容品类", category)
        c3.metric("优化目标", goal)

        d1, d2, d3, d4, d5 = st.columns(5)
        d1.metric("吸引力", result["dimension_scores"]["hook_strength"])
        d2.metric("真实感", result["dimension_scores"]["authenticity"])
        d3.metric("信息价值", result["dimension_scores"]["information_density"])
        d4.metric("互动潜力", result["dimension_scores"]["interaction_potential"])
        d5.metric("转化潜力", result["dimension_scores"]["conversion_potential"])

        st.info(f"**一句话判断：** {result['one_sentence_summary']}")

        left, right = st.columns(2)

        with left:
            st.success("识别到的优点")
            for item in result["strengths"]:
                st.write(f"- {item}")

            st.warning("主要风险")
            for item in result["risks"]:
                st.write(f"- {item}")

        with right:
            st.subheader("优化建议")
            for i, item in enumerate(result["suggestions"], start=1):
                st.write(f"{i}. {item}")

        st.subheader("建议改写")
        st.markdown("**改写标题**")
        st.write(result["rewrite_title"])
        st.markdown("**改写正文**")
        st.write(result["rewrite_caption"])

        with st.expander("查看本次识别到的启发式信号"):
            st.json(heuristics)