from decimal import Decimal, getcontext
import streamlit as st

getcontext().prec = 20

# ===================== 核心计算函数 =====================
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
    item_pool_sorted = sorted(item_pool, key=lambda x: x[0])
    n = len(item_pool_sorted)
    if n == 0:
        return None
    mid = n // 2
    left_arr = item_pool_sorted[:mid]
    right_arr = item_pool_sorted[mid:]

    def gen_subset(arr):
        res = []
        m = len(arr)
        for mask in range(0, 1 << m):
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
        if disc == 100:
            parts.append(f"{orig}")
        else:
            rate_str = str(float(disc / 100)).rstrip('0').rstrip('.') if '.' in str(float(disc / 100)) else str(float(disc / 100))
            parts.append(f"[{orig}×{rate_str}={p}]")
    return "+".join(parts)

# ===================== 网页界面 =====================
st.set_page_config(page_title="价格计算（同活动多次满减）", layout="wide")
st.title("价格计算（同活动只减一次）")

test_rows = [
    (1, 100, "90", 2), (2, 20, "", 1), (3, 30, "", 1), (4, 40, "", 5), (5, 50, "", 1),
    (6, 60, "", 2), (7, 70, "", 2), (8, 80, "", 2), (9, 90, "", 2), (10,10, "", 1),
    (11,110,"90",3), (12,125,"88",3), (13,130,"50",3), (14,145,"88",3), (15,155,"88",3),
    (16,160,"80",0), (17,175,"88",0), (18,180,"80",5), (19,190,"",5), (20,200,"",5),
    (21,210,"",5), (22,88, "", 0), (23,135,"80",4), (24,220,"85",4), (25,230,"90",3),
    (26,240,"88",4), (27,250,"82",4), (28,260,"",4), (29,270,"",0), (30,280,"",1),
]

col_left, col_right = st.columns([3.4, 2])

# 右侧面板
with col_right:
    st.subheader("参数设置")
    target_val = st.text_input("目标额度", value="1401", key="target_input")

    st.markdown("#### 5组满减规则")
    rule_data = []
    rule_texts = []
    default_rules = [["50","5"],["200","20"],["300","30"],["250","15"],["400","20"]]
    for i in range(5):
        c1, c2 = st.columns(2)
        f_txt = c1.text_input(f"满减{i+1}：满", value=default_rules[i][0], key=f"rule_full_{i}")
        r_txt = c2.text_input(f"满减{i+1}：减", value=default_rules[i][1], key=f"rule_reduce_{i}")
        rule_data.append((f_txt, r_txt))
        if f_txt.strip() and r_txt.strip():
            rule_texts.append(f"满{f_txt}减{r_txt}")
        else:
            rule_texts.append("")

    # 按钮行：开始计算 + 清空全部
    btn_col1, btn_col2 = st.columns(2)
    run_btn = btn_col1.button("开始计算", type="primary")
    clear_btn = btn_col2.button("清空全部")

    st.divider()
    result_area = st.container()

# 清空逻辑：清空所有session_state，页面刷新重置
if clear_btn:
    st.session_state.clear()
    st.rerun()

# 左侧商品列表
hit_id_set = set()
if run_btn:
    try:
        target = Decimal(target_val.strip())
    except:
        with result_area:
            st.error("目标额度输入错误！")
        st.stop()

    rule_list = []
    for f_txt, r_txt in rule_data:
        if f_txt.strip() == "" or r_txt.strip() == "":
            rule_list.append(None)
        else:
            try:
                f = Decimal(f_txt.strip())
                r = Decimal(r_txt.strip())
                rule_list.append((f, r))
            except:
                with result_area:
                    st.error("满减规则数字非法！")
                st.stop()

    item_pool = []
    for idx, price_str, disc_str, sel in item_data:
        if price_str.strip() == "":
            continue
        try:
            val = Decimal(price_str.strip())
            disc = Decimal(disc_str.strip()) if disc_str.strip() else Decimal("100")
            price_disc = val * disc / Decimal("100")
            item_pool.append((idx, val, disc, price_disc, sel))
        except:
            with result_area:
                st.error(f"第{idx+1}行单价/折扣格式错误！")
            st.stop()

    if len(item_pool) == 0:
        with result_area:
            st.warning("没有录入有效商品！")
        st.stop()

    res_pack = meet_in_the_middle(item_pool, rule_list, target)
    if res_pack is not None:
        hit_id_set = {x[0] for x in res_pack}

    with result_area:
        if res_pack is None:
            st.markdown(f"❌ **没有找到满减后正好等于 {target} 的商品组合！**")
        else:
            selected_prices = [str(i[1]) for i in res_pack]
            total, detail, group_items = calc_total_after_group_reduce(res_pack, rule_list)
            g0, g1, g2, g3, g4, g5, r1, r2, r3, r4, r5 = detail
            g0_items, g1_items, g2_items, g3_items, g4_items, g5_items = group_items

            st.markdown(f"🎯 目标额度：**{target}**")
            st.markdown(f"✅ 最终合计（分组汇总后分别满减）：**{total}**")
            st.markdown("🔢 选中价格：<span style='color:red'>" + ",".join(selected_prices) + "</span>", unsafe_allow_html=True)
            st.markdown("📋 分组明细：")
            if g0_items:
                st.markdown(f"<b>无满减组：</b>{fmt_group(g0_items)} = {g0} → 结算：{g0}", unsafe_allow_html=True)
                st.write("")
            if rule_texts[0] and g1_items:
                st.markdown(f"<b>{rule_texts[0]}：</b>{fmt_group(g1_items)} = {g1} → 结算：{r1}", unsafe_allow_html=True)
                st.write("")
            if rule_texts[1] and g2_items:
                st.markdown(f"<b>{rule_texts[1]}：</b>{fmt_group(g2_items)} = {g2} → 结算：{r2}", unsafe_allow_html=True)
                st.write("")
            if rule_texts[2] and g3_items:
                st.markdown(f"<b>{rule_texts[2]}：</b>{fmt_group(g3_items)} = {g3} → 结算：{r3}", unsafe_allow_html=True)
                st.write("")
            if rule_texts[3] and g4_items:
                st.markdown(f"<b>{rule_texts[3]}：</b>{fmt_group(g4_items)} = {g4} → 结算：{r4}", unsafe_allow_html=True)
                st.write("")
            if rule_texts[4] and g5_items:
                st.markdown(f"<b>{rule_texts[4]}：</b>{fmt_group(g5_items)} = {g5} → 结算：{r5}", unsafe_allow_html=True)
                st.write("")

with col_left:
    st.subheader("商品列表（共30条）")
    # 表头增加【标记】列
    h_cols = st.columns([0.4, 1, 1, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.6])
    h_cols[0].write("序号")
    h_cols[1].write("单价")
    h_cols[2].write("折扣")
    h_cols[3].write("无满减")
    h_cols[4].write("满减1")
    h_cols[5].write("满减2")
    h_cols[6].write("满减3")
    h_cols[7].write("满减4")
    h_cols[8].write("满减5")
    h_cols[9].write("标记")
    st.divider()

    item_data = []
    for idx in range(30):
        seq, default_price, default_disc, default_sel = test_rows[idx]
        r_cols = st.columns([0.4, 1, 1, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.6])
        r_cols[0].write(f"{seq:02d}")
        price_str = r_cols[1].text_input("", value=default_price, key=f"p_{idx}", label_visibility="collapsed")
        disc_str = r_cols[2].text_input("", value=default_disc, key=f"d_{idx}", label_visibility="collapsed")
        sel = None
        options = [0,1,2,3,4,5]
        keys_radio = [f"sel_{idx}_0",f"sel_{idx}_1",f"sel_{idx}_2",f"sel_{idx}_3",f"sel_{idx}_4",f"sel_{idx}_5"]
        for opt_i, opt_val in enumerate(options):
            if r_cols[3 + opt_i].radio("", [opt_val], index=0 if default_sel==opt_val else None, key=keys_radio[opt_i], label_visibility="collapsed") is not None:
                sel = opt_val
        if sel is None:
            sel = default_sel
        item_data.append( (idx, price_str, disc_str, sel) )
        # 标记列：命中就打✅
        if idx in hit_id_set:
            r_cols[9].markdown("✅")
        else:
            r_cols[9].write("")
