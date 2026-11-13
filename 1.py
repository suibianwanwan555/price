import bisect
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, getcontext
import threading

getcontext().prec = 20
stop_flag = False

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
        return sum(p for _, _, _, p in lst)

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
    item_pool_sorted = item_pool
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
    if stop_flag:
        return None
    sub_right = gen_subset(right_arr)
    if stop_flag:
        return None

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
    for _, orig, disc, p in items:
        d_num = float(disc)
        if d_num == 100:
            parts.append(f"{orig}")
        else:
            s = str(d_num / 100).rstrip("0").rstrip(".") if "." in str(d_num / 100) else str(d_num / 100)
            parts.append(f"[{orig}×{s}={p}]")
    return "+".join(parts)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("价格计算（同活动只减一次）")
        self.root.geometry("800x720")
        self.hit_index_set = set()

        self.price_ents = []
        self.disc_ents = []
        self.sel_vars = []
        self.mark_vars = []

        left_frame = tk.Frame(root)
        left_frame.grid(row=0, column=0, padx=5, pady=5, sticky="n")
        right_frame = tk.Frame(root)
        right_frame.grid(row=0, column=1, padx=5, pady=5, sticky="n")

        headers = ["序号","单价","折扣","无满减","满减1","满减2","满减3","满减4","满减5","标记"]
        for col,txt in enumerate(headers):
            tk.Label(left_frame, text=txt, font=("SimSun",9)).grid(row=0, column=col, padx=2)

        for row in range(1, 31):
            idx = row - 1
            tk.Label(left_frame, text=f"{row:02d}", font=("SimSun",9)).grid(row=row, column=0)
            e_p = tk.Entry(left_frame, width=6)
            e_p.grid(row=row, column=1, padx=1)
            e_d = tk.Entry(left_frame, width=6)
            e_d.grid(row=row, column=2, padx=1)
            self.price_ents.append(e_p)
            self.disc_ents.append(e_d)

            var_r = tk.IntVar(value=0)
            self.sel_vars.append(var_r)
            for c in range(3,9):
                tk.Radiobutton(left_frame, variable=var_r, value=c-3, text="").grid(row=row, column=c)
            var_m = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(left_frame, variable=var_m, state=tk.DISABLED)
            cb.grid(row=row, column=9)
            self.mark_vars.append(var_m)

        tk.Label(right_frame, text="控制面板 & 计算结果", font=("SimSun",10,"bold")).grid(row=0, column=0, columnspan=2)
        tk.Label(right_frame, text="目标额度：").grid(row=1, column=0, sticky="w")
        self.target_ent = tk.Entry(right_frame, width=12)
        self.target_ent.grid(row=1, column=1)

        tk.Label(right_frame, text="【全局5套满减规则】").grid(row=2, column=0, columnspan=2, pady=(8,0))
        self.rule_full = []
        self.rule_reduce = []
        default_rule = [("50","5"),("200","20"),("300","30"),("250","15"),("400","20")]
        for i in range(5):
            f_e = tk.Entry(right_frame, width=6)
            f_e.insert(0, default_rule[i][0])
            r_e = tk.Entry(right_frame, width=6)
            r_e.insert(0, default_rule[i][1])
            tk.Label(right_frame, text=f"满减{i+1}: 满").grid(row=3+i, column=0, sticky="e")
            f_e.grid(row=3+i, column=1)
            tk.Label(right_frame, text="减").grid(row=3+i, column=2)
            r_e.grid(row=3+i, column=3)
            self.rule_full.append(f_e)
            self.rule_reduce.append(r_e)

        btn_frame = tk.Frame(right_frame)
        btn_frame.grid(row=8, column=0, columnspan=4, pady=8)
        self.calc_btn = tk.Button(btn_frame, text="开始计算", command=self.start_calc)
        self.calc_btn.grid(row=0, column=0, padx=3)
        self.stop_btn = tk.Button(btn_frame, text="停止", command=self.do_stop)
        self.stop_btn.grid(row=0, column=1, padx=3)
        self.clear_btn = tk.Button(btn_frame, text="清空全部", command=self.clear_all)
        self.clear_btn.grid(row=0, column=2, padx=3)

        tk.Label(right_frame, text="结果：").grid(row=9, column=0, sticky="w")
        self.result_text = tk.Text(right_frame, width=42, height=18)
        self.result_text.grid(row=10, column=0, columnspan=4)
        self.result_text.tag_config("red", foreground="#ff0000")
        self.result_text.tag_config("bold", font=("SimSun",10,"bold"))

    def clear_mark(self):
        for v in self.mark_vars:
            v.set(False)
        self.hit_index_set.clear()

    def clear_all(self):
        self.clear_mark()
        for e in self.price_ents:
            e.delete(0, tk.END)
        for e in self.disc_ents:
            e.delete(0, tk.END)
        for v in self.sel_vars:
            v.set(0)
        self.result_text.delete(1.0, tk.END)

    def do_stop(self):
        global stop_flag
        stop_flag = True

    def worker_calc(self):
        global stop_flag
        stop_flag = False
        self.result_text.delete(1.0, tk.END)
        self.clear_mark()
        try:
            target = Decimal(self.target_ent.get().strip())
        except:
            self.result_text.insert(tk.END, "目标额度输入错误！\n")
            self.calc_btn.config(state=tk.NORMAL)
            return

        rule_list = []
        rule_name_list = []
        for i in range(5):
            ft = self.rule_full[i].get().strip()
            rt = self.rule_reduce[i].get().strip()
            if ft == "" or rt == "":
                rule_list.append(None)
                rule_name_list.append("")
            else:
                ff = Decimal(ft)
                rr = Decimal(rt)
                rule_list.append((ff, rr))
                rule_name_list.append(f"满{ff}减{rr}")

        item_pool = []
        for idx in range(30):
            p_str = self.price_ents[idx].get().strip()
            d_str = self.disc_ents[idx].get().strip()
            sel = self.sel_vars[idx].get()
            if not p_str:
                continue
            orig = Decimal(p_str)
            disc = Decimal(d_str) if d_str else Decimal("100")
            price = orig * disc / Decimal("100")
            item_pool.append((idx, orig, disc, price, sel))

        if len(item_pool) == 0:
            self.result_text.insert(tk.END, "没有录入有效商品！\n")
            self.calc_btn.config(state=tk.NORMAL)
            return

        res = meet_in_the_middle(item_pool, rule_list, target)
        if stop_flag:
            self.result_text.insert(tk.END, "计算已停止\n")
            self.calc_btn.config(state=tk.NORMAL)
            return
        if res is None:
            self.result_text.insert(tk.END, f"❌ 没有找到满减后正好等于 {target} 的商品组合！\n")
            self.calc_btn.config(state=tk.NORMAL)
            return

        hit_idx = [x[0] for x in res]
        self.hit_index_set = set(hit_idx)
        for i in hit_idx:
            self.mark_vars[i].set(True)

        total, detail, group_items = calc_total_after_group_reduce(res, rule_list)
        g0, g1, g2, g3, g4, g5, r1, r2, r3, r4, r5 = detail
        g0i, g1i, g2i, g3i, g4i, g5i = group_items
        selected_price_txt = ",".join([str(x[1]) for x in res])

        self.result_text.insert(tk.END, f"目标额度：{target}\n")
        self.result_text.insert(tk.END, f"最终合计（分组汇总后分别满减）：{total}\n")
        self.result_text.insert(tk.END, "选中价格：", "bold")
        self.result_text.insert(tk.END, selected_price_txt + "\n\n", "red")
        self.result_text.insert(tk.END, "分组明细：\n", "bold")

        if g0i:
            self.result_text.insert(tk.END, f"无满减组：{fmt_group(g0i)} = {g0} → 结算：{g0}\n\n")
        if rule_name_list[0] and g1i:
            self.result_text.insert(tk.END, f"{rule_name_list[0]}：{fmt_group(g1i)} = {g1} → 结算：{r1}\n\n")
        if rule_name_list[1] and g2i:
            self.result_text.insert(tk.END, f"{rule_name_list[1]}：{fmt_group(g2i)} = {g2} → 结算：{r2}\n\n")
        if rule_name_list[2] and g3i:
            self.result_text.insert(tk.END, f"{rule_name_list[2]}：{fmt_group(g3i)} = {g3} → 结算：{r3}\n\n")
        if rule_name_list[3] and g4i:
            self.result_text.insert(tk.END, f"{rule_name_list[3]}：{fmt_group(g4i)} = {g4} → 结算：{r4}\n\n")
        if rule_name_list[4] and g5i:
            self.result_text.insert(tk.END, f"{rule_name_list[4]}：{fmt_group(g5i)} = {g5} → 结算：{r5}\n\n")

        self.calc_btn.config(state=tk.NORMAL)

    def start_calc(self):
        self.calc_btn.config(state=tk.DISABLED)
        t = threading.Thread(target=self.worker_calc, daemon=True)
        t.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
