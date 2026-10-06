# -*- coding: utf-8 -*-
"""qujing-daka: 国庆档电影取景地打卡模拟器.

致敬 2026 年国庆真实热点"从看客变主角"：国庆档电影取景地成为出游新选择。
片中全部电影与取景地均为虚构，与任何真实影片、真实地点无关。

纯标准库: argparse / random / sys / time / select
"""
import argparse
import random
import sys
import time

try:
    import select
except ImportError:  # pragma: no cover
    select = None

DAYS = 3
BUDGET = 6000
MAX_SPOTS_PER_DAY = 2

# 全部虚构：(电影名, 类型, 取景地, 路费, 门票, 出片率 0-100, 人从众指数 0-100)
SPOTS = [
    {"movie": "《雪域缉凶》", "genre": "悬疑刑侦", "spot": "冰雪之城",
     "fare": 1800, "ticket": 400, "photo": 90, "crowd": 70},
    {"movie": "《欢喜岭南》", "genre": "喜剧", "spot": "岭南古镇",
     "fare": 900, "ticket": 150, "photo": 75, "crowd": 85},
    {"movie": "《人间烟火气》", "genre": "美食", "spot": "西北影视小镇",
     "fare": 1200, "ticket": 200, "photo": 80, "crowd": 60},
    {"movie": "《水乡精灵》", "genre": "动画", "spot": "江南水乡",
     "fare": 700, "ticket": 120, "photo": 85, "crowd": 90},
    {"movie": "《星际戈壁》", "genre": "科幻", "spot": "戈壁影视城",
     "fare": 1500, "ticket": 250, "photo": 88, "crowd": 35},
    {"movie": "《海风情书》", "genre": "爱情", "spot": "海滨老街",
     "fare": 800, "ticket": 100, "photo": 70, "crowd": 75},
]
SPOT_INDEX = {s["spot"]: i for i, s in enumerate(SPOTS)}


class IllegalSpot(ValueError):
    """取景地名称非法或已打卡。"""


class Game:
    """一局 3 天打卡行程。"""

    def __init__(self, rng=None, budget=BUDGET, days=DAYS):
        self.rng = rng or random.Random()
        self.budget = budget
        self.total_budget = budget
        self.days = days
        self.day = 1
        self.spent = 0
        self.visited = []        # 已打卡取景地名
        self.photo_total = 0.0   # 出片总分（含事件修正）
        self.crowd_total = 0.0   # 人从众惩罚累计（0.3*人从众）
        self.happy = 0.0         # 快乐值
        self.log = []

    @staticmethod
    def cost(spot):
        return spot["fare"] + spot["ticket"]

    def plan_day(self, names):
        """第 day 天打卡 1-2 个取景地。names 为取景地名列表。"""
        if self.day > self.days:
            raise IllegalSpot("假期已经结束了")
        if not (1 <= len(names) <= MAX_SPOTS_PER_DAY):
            raise IllegalSpot("每天只能打卡 1-2 个取景地")
        picked = []
        for name in names:
            if name not in SPOT_INDEX:
                raise IllegalSpot("没有这个取景地：%s" % name)
            if name in self.visited:
                raise IllegalSpot("已经打卡过：%s" % name)
            picked.append(SPOTS[SPOT_INDEX[name]])
        total = sum(self.cost(s) for s in picked)
        if total > self.budget:
            raise IllegalSpot("预算不够：需要 %d，手头 %d" % (total, self.budget))
        self.budget -= total
        self.spent += total
        self.log.append("第 %d 天：%s（花费 %d）" % (
            self.day, "、".join(n for n in names), total))
        for s in picked:
            self._visit(s)
        self.day += 1

    def _visit(self, spot):
        photo = float(spot["photo"])
        crowd_pen = 0.3 * spot["crowd"]
        self.visited.append(spot["spot"])
        self.photo_total += photo
        self.crowd_total += crowd_pen
        msg = "  打卡「%s」（%s·%s）：出片 %d，人从众 %d" % (
            spot["spot"], spot["movie"], spot["genre"], spot["photo"], spot["crowd"])
        msg = self._event(msg)
        self.log.append(msg)

    def _event(self, msg):
        roll = self.rng.random()
        if roll < 0.25:
            # 偶遇剧组路透：快乐暴击
            self.happy += 20
            self.photo_total += 10
            msg += " ｜★偶遇剧组路透！蹭到一张同框照，快乐+20、出片+10"
        elif roll < 0.45:
            # 电影同款套餐被宰
            fee = 300
            self.budget = max(0, self.budget - fee)
            self.spent += fee
            self.happy -= 10
            msg += " ｜景区「电影同款套餐」被宰 300 元，快乐-10"
        elif roll < 0.65:
            # NPC 戏中人换装
            self.photo_total += 15
            self.happy += 10
            msg += " ｜NPC「戏中人」换装体验：出片+15、快乐+10"
        return msg

    @property
    def finished(self):
        return self.day > self.days

    @property
    def score(self):
        return self.photo_total - self.crowd_total + 0.2 * self.happy

    def title(self):
        """结算称号。"""
        n = len(self.visited)
        avg_photo = (self.photo_total / n) if n else 0
        if n >= 5 and self.score >= 300:
            return ("取景地之王",
                    "三天跑遍五个取景地，从看客彻底变成主角——导演都该给你发盒饭！")
        if n >= 3 and avg_photo >= 75:
            return ("朋友圈摄影大赛冠军",
                    "张张都是电影剧照质感，朋友圈点赞收到手软，摄影师本人都沉默了。")
        if self.crowd_total >= 80 or (n and self.score < 100):
            return ("人从众受害者",
                    "人人人人人……你的镜头里只有后脑勺。下次记得错峰，或者 P 图。")
        return ("快乐打卡游客",
                "不求制霸朋友圈，但求快乐不打折——这趟值了！")


# ---------- AI 自动规划（性价比贪心） ----------

def ai_plan(g):
    """每天按 (出片-0.3*人从众)/成本 的性价比贪心选 1-2 个。"""
    remaining = [s for s in SPOTS if s["spot"] not in g.visited]
    remaining.sort(
        key=lambda s: (s["photo"] - 0.3 * s["crowd"]) / (s["fare"] + s["ticket"]),
        reverse=True)
    picks = []
    cost = 0
    for s in remaining:
        c = s["fare"] + s["ticket"]
        if len(picks) < MAX_SPOTS_PER_DAY and cost + c <= g.budget:
            picks.append(s["spot"])
            cost += c
    if not picks and remaining:
        # 预算只够最便宜的：至少打一个卡
        cheapest = min(remaining, key=lambda s: s["fare"] + s["ticket"])
        if cheapest["fare"] + cheapest["ticket"] <= g.budget:
            picks = [cheapest["spot"]]
    return picks


def auto_game(seed, verbose=False):
    g = Game(random.Random(seed))
    while not g.finished:
        picks = ai_plan(g)
        if not picks:
            g.day += 1  # 实在没钱了，空过一天
            continue
        g.plan_day(picks)
    if verbose:
        for line in g.log:
            print(line)
    title, comment = g.title()
    if verbose:
        print("结算：打卡 %d 个，预算剩余 %d，总分 %.1f" % (
            len(g.visited), g.budget, g.score))
        print("称号：%s —— %s" % (title, comment))
    return g


# ---------- 交互 ----------

def _timed_input(prompt, timeout):
    if select is None:
        return input(prompt)
    sys.stdout.write(prompt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        return None
    return sys.stdin.readline().rstrip("\n")


def show_spots():
    print("国庆档 6 部电影 × 取景地（全部虚构）：")
    for i, s in enumerate(SPOTS, 1):
        print("  %d. %s「%s」（%s）路费%d+门票%d | 出片率%d | 人从众%d" % (
            i, s["spot"], s["movie"], s["genre"],
            s["fare"], s["ticket"], s["photo"], s["crowd"]))


def interactive():
    if not sys.stdin.isatty():
        print("需要交互终端运行；非交互模式请使用 --auto。", file=sys.stderr)
        sys.exit(2)
    g = Game()
    print("=== 取景地打卡模拟器 ===")
    print("你有 %d 天假期，预算 %d 元。每天选 1-2 个取景地打卡！" % (DAYS, BUDGET))
    show_spots()
    while not g.finished:
        print("\n—— 第 %d 天（剩余预算 %d）——" % (g.day, g.budget))
        raw = _timed_input("输入取景地名（多个用空格隔开，q 退出）：", 120)
        if raw is None:
            print("\n超时，自动结束。")
            break
        raw = raw.strip()
        if raw.lower() == "q":
            break
        names = raw.split()
        try:
            g.plan_day(names)
        except IllegalSpot as e:
            print("  规划失败：%s" % e)
            continue
    title, comment = g.title()
    print("\n=== 结算 ===")
    for line in g.log:
        print(line)
    print("打卡 %d 个取景地，花费 %d 元，剩余 %d 元，总分 %.1f" % (
        len(g.visited), g.spent, g.budget, g.score))
    print("称号：%s —— %s" % (title, comment))


def main(argv=None):
    ap = argparse.ArgumentParser(description="国庆档电影取景地打卡模拟器")
    ap.add_argument("--auto", action="store_true", help="AI 自动演示")
    ap.add_argument("--games", type=int, default=1, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42, help="随机种子")
    ap.add_argument("--verbose", action="store_true", help="打印每日战报")
    args = ap.parse_args(argv)
    if args.auto:
        for i in range(args.games):
            if args.verbose or args.games > 1:
                print("=== 第 %d 局（seed=%d）===" % (i + 1, args.seed + i))
            g = auto_game(args.seed + i, verbose=args.verbose)
            title, _ = g.title()
            print("局 %d：打卡 %d 个，剩余 %d 元，总分 %.1f，称号：%s" % (
                i + 1, len(g.visited), g.budget, g.score, title))
    else:
        interactive()


if __name__ == "__main__":
    main()
