import bisect
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, getcontext
import threading

getcontext().prec = 20
stop_flag = False

# ========== 原有计算逻辑，只删除排序！ ==========
def calc_total_after_group_reduce(selected_items, rule_list):
    g0_items = []
    g1_items = []
    g2_items = []
    g3_items = []
    g4_items = []
    g5_items = []
    for row_idx, orig, disc, price, sel in selected_items:
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
    n = len(item_pool)
    if n == 0:
        return None
    mid = n // 2
    left_arr = item_pool[:mid]   # 重点：直接按原始顺序切分，不排序！！
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
            parts.append(f"{orig}")
        else:
            rate = disc / Decimal("100")
            rate_str = str(float(rate)).rstrip('0').rstrip('.') if '.' in str(float(rate)) else str(float(rate))
            parts.append(f"[{orig}×{rate_str}={p}]")
    return "+".join(parts)

# ========== GUI主程序 ==========
root = tk.Tk()
root.title("价格计算（同活动只减一次）")
root.geometry("800x820")

entry_price = []
entry_disc = []
radio_var_list = []
result_text = None
hit_row_set = set()   # 保存【原始行号】，用来标记
running = False

# 测试数据，不需要就注释 load_test_data()
test_data = [
    (100, "90", 2), (20, "", 1), (30, "", 1), (40, "", 5), (50, "", 1),
    (60, "", 2), (70, "", 2), (80, "", 2), (90, "", 2), (10, "", 1),
    (110, "90", 3), (125, "88", 3), (130, "50", 3), (145, "88", 3), (155, "88", 3),
    (160, "80", 0), (175, "88", 0), (180, "80", 5), (190, "", 5), (200, "", 5),
    (210, "", 5), (88, "", 0), (135, "80", 4), (220, "85", 4), (230, "90", 3),
    (240, "88", 4), (250, "82", 4), (260, "", 4), (270, "", 0), (280, "", 1),
]

def load_test_data():
    for i in range(30):
        p, d, sel = test_data[i]
        entry_price[i].delete(0, tk.END)
        entry_price[i].insert(0, str(p))
        entry_disc[i].delete(0, tk.END)
        entry_disc[i].insert(0, d)
        radio_var_list[i].set(sel)

def stop_calc():
    global stop_flag
    stop_flag = True

def calc_thread():
    global stop_flag, running, hit_row_set
    running = True
    stop_flag = False
    result_text.config(state=tk.NORMAL)
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, "正在计算...\n")
    result_text.config(state=tk.DISABLED)
    root.update()

    try:
        target_str = target_entry.get().strip()
        target = Decimal(target_str)
    except:
        result_text.config(state=tk.NORMAL)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "❌ 目标额度输入错误！")
        result_text.config(state=tk.DISABLED)
        running = False
        return

    rule_list = []
    for i in range(5):
        f_str = rule_full_entry[i].get().strip()
        r_str = rule_reduce_entry[i].get().strip()
        if f_str == "" or r_str == "":
            rule_list.append(None)
            continue
        try:
            f = Decimal(f_str)
            r = Decimal(r_str)
            rule_list.append((f, r))
        except:
            result_text.config(state=tk.NORMAL)
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, "❌ 满减规则数字非法！")
            result_text.config(state=tk.DISABLED)
            running = False
            return

    item_pool = []
    for row_idx in range(30):
        p_str = entry_price[row_idx].get().strip()
        d_str = entry_disc[row_idx].get().strip()
        sel = radio_var_list[row_idx].get()
        if p_str == "":
            continue
        try:
            orig_val = Decimal(p_str)
            disc_val = Decimal(d_str) if d_str else Decimal("100")
            price_after_disc = orig_val * disc_val / Decimal("100")
            item_pool.append((row_idx, orig_val, disc_val, price_after_disc, sel))
        except Exception as e:
            result_text.config(state=tk.NORMAL)
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, f"❌ 第{row_idx+1}行单价/折扣格式错误！")
            result_text.config(state=tk.DISABLED)
            running = False
            return

    if len(item_pool) == 0:
        result_text.config(state=tk.NORMAL)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "⚠️ 没有录入有效商品！")
        result_text.config(state=tk.DISABLED)
        running = False
        return

    res_pack = meet_in_the_middle(item_pool, rule_list, target)

    hit_row_set.clear()
    if res_pack is None:
        msg = f"❌ 没有找到满减后正好等于 {target} 的商品组合！"
    else:
        # 直接拿原始行号，精准标记，不怕重复价格
        hit_row_set = {item[0] for item in res_pack}
        total, detail, group_items = calc_total_after_group_reduce(res_pack, rule_list)
        g0, g1, g2, g3, g4, g5, r1, r2, r3, r4, r5 = detail
        g0_items, g1_items, g2_items, g3_items, g4_items, g5_items = group_items
        selected_prices = [str(i[1]) for i in res_pack]
        msg_lines = []
        msg_lines.append(f"🎯 目标额度：{target}")
        msg_lines.append(f"✅ 最终合计（分组汇总后分别满减）：{total}")
        msg_lines.append("🔢 选中价格：" + ",".join(selected_prices))
        msg_lines.append("📋 分组明细：")
        if g0_items:
            msg_lines.append(f"\n<b>无满减组：</b>{fmt_group(g0_items)} = {g0} → 结算：{g0}")
        rule_text = []
        for i in range(5):
            f_str = rule_full_entry[i].get().strip()
            r_str = rule_reduce_entry[i].get().strip()
            if f_str and r_str:
                rule_text.append(f"满{f_str}减{r_str}")
            else:
                rule_text.append("")
        if rule_text[0] and g1_items:
            msg_lines.append(f"\n<b>{rule_text[0]}：</b>{fmt_group(g1_items)} = {g1} → 结算：{r1}")
        if rule_text[1] and g2_items:
            msg_lines.append(f"\n<b>{rule_text[1]}：</b>{fmt_group(g2_items)} = {g2} → 结算：{r2}")
        if rule_text[2] and g3_items:
            msg_lines.append(f"\n<b>{rule_text[2]}：</b>{fmt_group(g3_items)} = {g3} → 结算：{r3}")
        if rule_text[3] and g4_items:
            msg_lines.append(f"\n<b>{rule_text[3]}：</b>{fmt_group(g4_items)} = {g4} → 结算：{r4}")
        if rule_text[4] and g5_items:
            msg_lines.append(f"\n<b>{rule_text[4]}：</b>{fmt_group(g5_items)} = {g5} → 结算：{r5}")
        msg = "\n".join(msg_lines)

    result_text.config(state=tk.NORMAL)
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, msg)
    result_text.config(state=tk.DISABLED)
    running = False
    refresh_mark()

# 刷新标记：行号匹配，100%精准
def refresh_mark():
    for r in range(30):
        mark_label = mark_label_list[r]
        if r in hit_row_set:
            mark_label.config(text="✅")
        else:
            mark_label.config(text="")

def start_calc():
    global running
    if running:
        return
    t = threading.Thread(target=calc_thread, daemon=True)
    t.start()

# ---------------- 布局构建 ----------------
main_frame = ttk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

left_frame = ttk.Frame(main_frame)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

right_frame = ttk.Frame(main_frame, width=240)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10,0))

# 表头
header_frame = ttk.Frame(left_frame)
header_frame.pack(fill=tk.X)
ttk.Label(header_frame, text="序号", width=4).grid(row=0, column=0)
ttk.Label(header_frame, text="单价", width=8).grid(row=0, column=1)
ttk.Label(header_frame, text="折扣", width=8).grid(row=0, column=2)
ttk.Label(header_frame, text="无满减", width=6).grid(row=0, column=3)
ttk.Label(header_frame, text="满减1", width=6).grid(row=0, column=4)
ttk.Label(header_frame, text="满减2", width=6).grid(row=0, column=5)
ttk.Label(header_frame, text="满减3", width=6).grid(row=0, column=6)
ttk.Label(header_frame, text="满减4", width=6).grid(row=0, column=7)
ttk.Label(header_frame, text="满减5", width=6).grid(row=0, column=8)
ttk.Label(header_frame, text="标记", width=4).grid(row=0, column=9)

row_container = ttk.Frame(left_frame)
row_container.pack(fill=tk.BOTH, expand=True)
canvas = tk.Canvas(row_container)
scrollbar = ttk.Scrollbar(row_container, orient="vertical", command=canvas.yview)
scroll_frame = ttk.Frame(canvas)
scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# 30行商品，横向单选
mark_label_list = []
for i in range(30):
    var = tk.IntVar(value=0)
    radio_var_list.append(var)
    e_p = ttk.Entry(scroll_frame, width=8)
    entry_price.append(e_p)
    e_d = ttk.Entry(scroll_frame, width=8)
    entry_disc.append(e_d)
    ttk.Label(scroll_frame, text=f"{i+1:02d}").grid(row=i, column=0, padx=1)
    e_p.grid(row=i, column=1, padx=1)
    e_d.grid(row=i, column=2, padx=1)
    ttk.Radiobutton(scroll_frame, text="", variable=var, value=0).grid(row=i, column=3)
    ttk.Radiobutton(scroll_frame, text="", variable=var, value=1).grid(row=i, column=4)
    ttk.Radiobutton(scroll_frame, text="", variable=var, value=2).grid(row=i, column=5)
    ttk.Radiobutton(scroll_frame, text="", variable=var, value=3).grid(row=i, column=6)
    ttk.Radiobutton(scroll_frame, text="", variable=var, value=4).grid(row=i, column=7)
    ttk.Radiobutton(scroll_frame, text="", variable=var, value=5).grid(row=i, column=8)
    m_lab = ttk.Label(scroll_frame, text="")
    m_lab.grid(row=i, column=9)
    mark_label_list.append(m_lab)

# 右侧面板
ttk.Label(right_frame, text="参数设置", font=("SimHei",11,"bold")).pack()
ttk.Label(right_frame, text="目标额度").pack()
target_entry = ttk.Entry(right_frame, width=14)
target_entry.pack(pady=2)
target_entry.insert(0, "1401")

ttk.Label(right_frame, text="5组满减规则", font=("SimHei",10,"bold")).pack(pady=(6,2))
rule_full_entry = []
rule_reduce_entry = []
default_rule = [("50","5"),("200","20"),("300","30"),("250","15"),("400","20")]
for f, r in default_rule:
    line_f = ttk.Entry(right_frame, width=8)
    line_f.insert(0, f)
    line_r = ttk.Entry(right_frame, width=8)
    line_r.insert(0, r)
    f_f = ttk.Frame(right_frame)
    ttk.Label(f_f, text="满:").pack(side=tk.LEFT)
    line_f.pack(side=tk.LEFT)
    ttk.Label(f_f, text="减:").pack(side=tk.LEFT)
    line_r.pack(side=tk.LEFT)
    f_f.pack()
    rule_full_entry.append(line_f)
    rule_reduce_entry.append(line_r)

btn_frame = ttk.Frame(right_frame)
btn_frame.pack(pady=6)
ttk.Button(btn_frame, text="开始计算", command=start_calc).pack(side=tk.LEFT, padx=2)
ttk.Button(btn_frame, text="停止", command=stop_calc).pack(side=tk.LEFT, padx=2)

ttk.Label(right_frame, text="结果：").pack()
result_text = tk.Text(right_frame, width=28, height=16)
result_text.pack()
result_text.config(state=tk.DISABLED)

load_test_data()

root.mainloop()
