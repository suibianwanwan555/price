import streamlit as st
from decimal import Decimal, getcontext

getcontext().prec = 20
stop_flag = False

# ========== 【计算逻辑，和你上面tk版本完全一致，只移除排序】 ==========
def calc_total_after_group_reduce(selected_items, rule_list):
    g0_items = []
    g1_items = []
    g2_items = []
    g3_items = []
    g4_items = []
    g5_items = []
    for idx, orig, disc, price, sel in selected_items:
        if sel == 0:
            g0_items.append((orig, disc, price))
        elif sel == 1:
            g1_items.append((orig, disc, price))
        elif sel == 2:
            g2_items.append((orig, disc, price))
        elif sel == 3:
            g3_items.append((orig, disc, price))
        elif sel == 4:
            g4_items.append((orig, disc, price))
        elif sel == 5:
            g5_items.append((orig, disc, price))

    def sum_price(lst):
        return sum(p for o, d, p in lst)

    g0_sum = sum_price(g0_items)
    g1_sum = sum_price(g1_items)
    g2_sum = sum_price(g2_items)
    g3_sum = sum_price(g3_items)
    g4_sum = sum_price(g4_items)
    g5_sum = sum_price(g5_items)

    def apply_rule(total, rule):
        if rule is None:
            return total
        full, reduce_val = rule
        if full <= 0:
            return total
        cnt = int(total // full)
        return total - cnt * reduce_val

    r1 = apply_rule(g1_sum, rule_list[0])
    r2 = apply_rule(g2_sum, rule_list[1])
    r3 = apply_rule(g3_sum, rule_list[2])
    r4 = apply_rule(g4_sum, rule_list[3])
    r5 = apply_rule(g5_sum, rule_list[4])
    total = g0_sum + r1 + r2 + r3 + r4 + r5
    return total, (g0_sum, g1_sum, g2_sum, g3_sum, g4_sum, g5_sum, r1, r2, r3, r4, r5), (g0_items, g1_items, g2_items, g3_items, g4_items, g5_items)

def meet_in_the_middle(item_pool, rule_list, target):
    global stop_flag
    n = len(item_pool)
    if n == 0:
        return None
    mid = n // 2
    left_arr = item_pool[:mid]
    right_arr = item_pool[mid:]

    def gen_subset(arr):
        res = []
        m = len(arr)
        for mask in range(0, 1 << m):
            if stop_flag:
                return []
            pack = []
            for i in range(m):
                if mask & (1 << i):
                    pack.append(arr[i])
            sum_final, _, _ = calc_total_after_group_reduce(pack, rule_list)
            res.append((sum_final, pack))
        return res

    sub_left = gen_subset(left_arr)
    sub_right = gen_subset(right_arr)

    right_dict = {}
    for s_r, pack_r in sub_right:
        if s_r not in right_dict:
            right_dict[s_r] = []
        right_dict[s_r].append(pack_r)

    for s_l, pack_l in sub_left:
        if stop_flag:
            return None
        need = target - s_l
        if need in right_dict:
            for pack_r in right_dict[need]:
                combined = pack_l + pack_r
                real_total, _, _ = calc_total_after_group_reduce(combined, rule_list)
                if real_total == target:
                    return combined
    return None

def fmt_group(items):
    parts = []
    for orig, disc, p in items:
        if disc == Decimal("100"):
            parts.append(f"<span style='color:red'>{orig}</span>")
        else:
            rate = disc / Decimal("100")
            rate_str = str(float(rate)).rstrip('0').rstrip('.') if '.' in str(float(rate)) else str(float(rate))
            parts.append(f"<span style='color:red'>[{orig}×{rate_str}={p}]</span>")
    return "+".join(parts)

# ========== Streamlit 网页界面 ==========
st.set_page_config(page_title="价格计算（同活动只减一次）", layout="wide")
st.title("价格计算（同活动只减一次）")

# 测试数据
test_data = [
    (100, "90", 2), (20, "", 1), (30, "", 1), (40, "", 5), (50, "", 1),
    (60, "", 2), (70, "", 2), (80, "", 2), (90, "", 2), (10, "", 1),
    (110, "90", 3), (125, "88", 3), (130, "50", 3), (145, "88", 3), (155, "88", 3),
    (160, "80", 0), (175, "88", 0), (180, "80", 5), (190, "", 5), (200, "", 5),
    (210, "", 5), (88, "", 0), (135, "80", 4), (220, "85", 4), (230, "90", 3),
    (240, "88", 4), (250, "82", 4), (260, "", 4), (270, "", 0), (280, "", 1),
]

if "price_list" not in st.session_state:
    st.session_state.price_list = [str(x[0]) for x in test_data]
if "discount_list" not in st.session_state:
    st.session_state.discount_list = [x[1] for x in test_data]
if "sel_list" not in st.session_state:
    st.session_state.sel_list = [x[2] for x in test_data]
if "hit_rows" not in st.session_state:
    st.session_state.hit_rows = set()
if "result_msg" not in st.session_state:
    st.session_state.result_msg = ""
if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = False

# 侧边栏：参数
with st.sidebar:
    st.header("参数设置")
    target = st.number_input("目标额度", min_value=0.0, value=1401.0, step=0.01)
    st.subheader("5组满减规则")
    rule_data = []
    for i in range(5):
        c1, c2 = st.columns(2)
        full = c1.number_input(f"满减{i+1} - 满", min_value=0.0, value=0.0, step=0.01, key=f"full{i}")
        reduce = c2.number_input(f"满减{i+1} - 减", min_value=0.0, value=0.0, step=0.01, key=f"red{i}")
        if full > 0:
            rule_data.append((Decimal(full), Decimal(reduce)))
        else:
            rule_data.append(None)
    st.divider()
    run_btn = st.button("开始计算", type="primary")
    stop_btn = st.button("停止计算")

# 商品表头
col_head = st.columns([0.07,0.11,0.11,0.08,0.08,0.08,0.08,0.08,0.08,0.06])
col_head[0].write("序号")
col_head[1].write("单价")
col_head[2].write("折扣")
col_head[3].write("无满减")
col_head[4].write("满减1")
col_head[5].write("满减2")
col_head[6].write("满减3")
col_head[7].write("满减4")
col_head[8].write("满减5")
col_head[9].write("选中")

# 30行商品
for i in range(30):
    c = st.columns([0.07,0.11,0.11,0.08,0.08,0.08,0.08,0.08,0.08,0.06])
    c[0].write(f"{i+1:02d}")
    st.session_state.price_list[i] = c[1].text_input("p", value=st.session_state.price_list[i], label_visibility="collapsed", key=f"p{i}")
    st.session_state.discount_list[i] = c[2].text_input("d", value=st.session_state.discount_list[i], label_visibility="collapsed", key=f"d{i}")
    sel = c[3].radio("sel", [0,1,2,3,4,5], index=st.session_state.sel_list[i], label_visibility="collapsed", horizontal=True, key=f"s{i}")
    st.session_state.sel_list[i] = sel
    # ✅标记：判断行号
    if i in st.session_state.hit_rows:
        c[9].write("✅")
    else:
        c[9].write("")

# 停止逻辑
if stop_btn:
    st.session_state.stop_flag = True
    st.warning("已停止计算！")

# 开始计算
if run_btn:
    st.session_state.stop_flag = False
    st.session_state.hit_rows.clear()
    item_pool = []
    err = False
    for row_idx in range(30):
        p_str = st.session_state.price_list[row_idx].strip()
        d_str = st.session_state.discount_list[row_idx].strip()
        sel = st.session_state.sel_list[row_idx]
        if not p_str:
            continue
        try:
            orig_val = Decimal(p_str)
            disc_val = Decimal(d_str) if d_str else Decimal("100")
            price_after_disc = orig_val * disc_val / Decimal("100")
            item_pool.append((row_idx, orig_val, disc_val, price_after_disc, sel))
        except Exception as e:
            st.error(f"第{row_idx+1}行数字格式错误！")
            err = True
            break
    if err:
        st.session_state.result_msg = "❌ 输入格式错误！"
    else:
        with st.spinner("正在计算..."):
            res_pack = meet_in_the_middle(item_pool, rule_data, Decimal(target))
        if res_pack is None:
            st.session_state.result_msg = f"❌ 没有找到满减后正好等于 {target} 的商品组合！"
        else:
            # 核心修复：保存行号，不是价格！
            hit_rows = {item[0] for item in res_pack}
            st.session_state.hit_rows = hit_rows
            total, detail, group_items = calc_total_after_group_reduce(res_pack, rule_data)
            g0, g1, g2, g3, g4, g5, r1, r2, r3, r4, r5 = detail
            g0_items, g1_items, g2_items, g3_items, g4_items, g5_items = group_items
            selected_prices = [str(i[1]) for i in res_pack]
            msg_parts = [
                f"🎯 目标额度：{target}",
                f"✅ 最终合计（分组汇总后分别满减）：{total}",
                f"🔢 选中价格：{','.join(selected_prices)}",
                "📋 分组明细："
            ]
            if g0_items:
                msg_parts.append(f"\n**无满减组：**{fmt_group(g0_items)} = {g0} → 结算：{g0}")
            rule_text = []
            for r in rule_data:
                if r is not None:
                    rule_text.append(f"满{r[0]}减{r[1]}")
                else:
                    rule_text.append("")
            if rule_text[0] and g1_items:
                msg_parts.append(f"\n**{rule_text[0]}：**{fmt_group(g1_items)} = {g1} → 结算：{r1}")
            if rule_text[1] and g2_items:
                msg_parts.append(f"\n**{rule_text[1]}：**{fmt_group(g2_items)} = {g2} → 结算：{r2}")
            if rule_text[2] and g3_items:
                msg_parts.append(f"\n**{rule_text[2]}：**{fmt_group(g3_items)} = {g3} → 结算：{r3}")
            if rule_text[3] and g4_items:
                msg_parts.append(f"\n**{rule_text[3]}：**{fmt_group(g4_items)} = {g4} → 结算：{r4}")
            if rule_text[4] and g5_items:
                msg_parts.append(f"\n**{rule_text[4]}：**{fmt_group(g5_items)} = {g5} → 结算：{r5}")
            st.session_state.result_msg = "\n".join(msg_parts)

st.markdown("---")
st.subheader("计算结果")
st.markdown(st.session_state.result_msg, unsafe_allow_html=True)
