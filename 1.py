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
            g0_items.append((idx, orig, disc, price))
        elif sel == 1:
            g1_items.append((idx, orig, disc, price))
        elif sel == 2:
            g2_items.append((idx, orig, disc, price))
        elif sel == 3:
            g3_items.append((idx, orig, disc, price))
        elif sel == 4:
            g4_items.append((idx, orig, disc, price))
        elif sel == 5:
            g5_items.append((idx, orig, disc, price))

    def sum_price(lst):
        return sum(p for _, o, d, p in lst)

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
    for _, orig, disc, p in items:
        if disc == 100:
            parts.append(f"{orig}")
        else:
            rate_str = str(float(disc / 100)).rstrip('0').rstrip('.') if '.' in str(float(disc / 100)) else str(float(disc / 100))
            parts.append(f"[{orig}×{rate_str}={p}]")
    return "+".join(parts)

# ===================== session初始化 =====================
if "result_pack" not in st.session_state:
    st.session_state.result_pack = None
if "result_msg" not in st.session_state:
    st.session_state.result_msg = ""
if "hit_ids" not in st.session_state:
    st.session_state.hit_ids = set()
# 版本号：清空时+1，强制重建所有输入控件
if "ui_version" not in st.session_state:
    st.session_state.ui_version = 0

st.set_page_config(page_title="价格计算（同活动多次满减）", layout="wide")
st.title("价格计算（同活动多次满减）")

col_left, col_right = st.columns([3.4, 2])
item_data = []
v = st.session_state.ui_version

with col_left:
    st.subheader("商品列表（共30条）")
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

    for idx in range(30):
        r_cols = st.columns([0.4, 1, 1, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.6])
        r_cols[0].write(f"{idx+1:02d}")
        # key带上版本号，清空就换key，控件销毁重建
        price_str = r_cols[1].text_input("", value="", key=f"p_{idx}_{v}", label_visibility="collapsed")
        disc_str = r_cols[2].text_input("", value="", key=f"d_{idx}_{v}", label_visibility="collapsed")
        sel = r_cols[3].radio("", options=[0,1,2,3,4,5], index=0, key=f"sel_{idx}_{v}", horizontal=True, label_visibility="collapsed")
        item_data.append( (idx, price_str, disc_str, sel) )
        # 标记：从hit_ids读取，hit_ids唯一来源是result_pack
        if idx in st.session_state.hit_ids:
            r_cols[9].markdown("✅")
        else:
            r_cols[9].write("")

with col_right:
    st.subheader("参数设置")
    target_val = st.text_input("目标额度", value="", key=f"target_{v}")

    st.markdown("#### 5组满减规则")
    rule_data = []
    rule_texts = []
    default_rules = [["50","5"],["200","20"],["300","30"],["250","15"],["400","20"]]
    for i in range(5):
        c1, c2 = st.columns(2)
        f_txt = c1.text_input(f"满减{i+1}：满", value=default_rules[i][0], key=f"rule_full_{i}_{v}")
        r_txt = c2.text_input(f"满减{i+1}：减", value=default_rules[i][1], key=f"rule_reduce_{i}_{v}")
        rule_data.append((f_txt, r_txt))
        if f_txt.strip() and r_txt.strip():
            rule_texts.append(f"满{f_txt}减{r_txt}")
        else:
            rule_texts.append("")

    btn_col1, btn_col2 = st.columns(2)
    run_btn = btn_col1.button("开始计算", type="primary")
    clear_btn = btn_col2.button("清空全部")

    st.divider()
    result_area = st.container()

# ========== 清空按钮逻辑 ==========
if clear_btn:
    st.session_state.ui_version += 1
    st.session_state.result_pack = None
    st.session_state.result_msg = ""
    st.session_state.hit_ids = set()
    st.rerun()

# ========== 计算逻辑 ==========
if run_btn:
    with result_area:
        with st.spinner("正在计算，请稍候..."):
            try:
                target = Decimal(target_val.strip())
            except:
                st.session_state.result_msg = "❌ 目标额度输入错误！"
                st.session_state.result_pack = None
                st.session_state.hit_ids = set()
            else:
                rule_list = []
                rule_err = False
                for f_txt, r_txt in rule_data:
                    if f_txt.strip() == "" or r_txt.strip() == "":
                        rule_list.append(None)
                    else:
                        try:
                            f = Decimal(f_txt.strip())
                            r = Decimal(r_txt.strip())
                            rule_list.append((f, r))
                        except:
                            rule_err = True
                            break
                if rule_err:
                    st.session_state.result_msg = "❌ 满减规则数字非法！"
                    st.session_state.result_pack = None
                    st.session_state.hit_ids = set()
                else:
                    item_pool = []
                    item_err = False
                    for idx, price_str, disc_str, sel in item_data:
                        if price_str.strip() == "":
                            continue
                        try:
                            val = Decimal(price_str.strip())
                            disc = Decimal(disc_str.strip()) if disc_str.strip() else Decimal("100")
                            price_disc = val * disc / Decimal("100")
                            item_pool.append((idx, val, disc, price_disc, sel))
                        except:
                            st.session_state.result_msg = f"❌ 第{idx+1}行单价/折扣格式错误！"
                            st.session_state.result_pack = None
                            st.session_state.hit_ids = set()
                            item_err = True
                            break
                    if item_err:
                        pass
                    elif len(item_pool) == 0:
                        st.session_state.result_msg = "⚠️ 没有录入有效商品！"
                        st.session_state.result_pack = None
                        st.session_state.hit_ids = set()
                    else:
                        res_pack = meet_in_the_middle(item_pool, rule_list, target)
                        st.session_state.result_pack = res_pack
                        if res_pack is None:
                            st.session_state.result_msg = f"❌ **没有找到满减后正好等于 {target} 的商品组合！**"
                            st.session_state.hit_ids = set()
                        else:
                            # ✅ 唯一来源：从算法返回的pack提取，不再二次遍历页面控件
                            hit_id_set = {x[0] for x in res_pack}
                            st.session_state.hit_ids = hit_id_set
                            total, detail, group_items = calc_total_after_group_reduce(res_pack, rule_list)
                            g0, g1, g2, g3, g4, g5, r1, r2, r3, r4, r5 = detail
                            g0_items, g1_items, g2_items, g3_items, g4_items, g5_items = group_items
                            # 选中价格直接从res_pack取，和hit_ids同源，绝对一致
                            selected_prices = [str(x[1]) for x in res_pack]
                            msg_lines = []
                            msg_lines.append(f"🎯 目标额度：**{target}**")
                            msg_lines.append(f"✅ 最终合计（分组汇总后分别满减）：**{total}**")
                            msg_lines.append("🔢 选中价格：<span style='color:red'>" + ",".join(selected_prices) + "</span>")
                            msg_lines.append("📋 分组明细：")
                            if g0_items:
                                msg_lines.append(f"<b>无满减组：</b>{fmt_group(g0_items)} = {g0} → 结算：{g0}")
                            if rule_texts[0] and g1_items:
                                msg_lines.append(f"<b>{rule_texts[0]}：</b>{fmt_group(g1_items)} = {g1} → 结算：{r1}")
                            if rule_texts[1] and g2_items:
                                msg_lines.append(f"<b>{rule_texts[1]}：</b>{fmt_group(g2_items)} = {g2} → 结算：{r2}")
                            if rule_texts[2] and g3_items:
                                msg_lines.append(f"<b>{rule_texts[2]}：</b>{fmt_group(g3_items)} = {g3} → 结算：{r3}")
                            if rule_texts[3] and g4_items:
                                msg_lines.append(f"<b>{rule_texts[3]}：</b>{fmt_group(g4_items)} = {g4} → 结算：{r4}")
                            if rule_texts[4] and g5_items:
                                msg_lines.append(f"<b>{rule_texts[4]}：</b>{fmt_group(g5_items)} = {g5} → 结算：{r5}")
                            st.session_state.result_msg = "\n\n".join(msg_lines)

# 展示结果
with result_area:
    if st.session_state.result_msg:
        st.markdown(st.session_state.result_msg, unsafe_allow_html=True)
