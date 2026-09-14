# -*- coding: utf-8 -*-
"""绘图公共代码。

``matplotlib`` 只是开发/分析阶段的工具，程序本身运行时并不需要它。这里在
模块顶层用 ``try/except`` 探测：装了就得到可用的绘图对象，没装就让调用方
跳过绘图，而不是让整个脚本崩掉。

把这段代码单独抽出来的另一个好处是：性能分析与覆盖率两个脚本不再各自复制
一份"配置中文字体 + 保存图片"的样板，消除了重复代码。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import matplotlib

    matplotlib.use("Agg")  # 无界面后端，脚本里不需要弹窗
    from matplotlib import font_manager
    from matplotlib import pyplot as plt
except ImportError:  # pragma: no cover - 取决于本机是否安装了 matplotlib
    plt = None  # type: ignore[assignment]
    font_manager = None  # type: ignore[assignment]


# 优先使用系统里的中文字体，否则图表标题与标签会显示成方框。
_CJK_FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def available() -> bool:
    """返回 matplotlib 是否可用。"""
    return plt is not None


def pyplot() -> Any:
    """返回 ``matplotlib.pyplot``；未安装 matplotlib 时返回 ``None``。

    调用方先取一次这个句柄，就不需要在函数体里再写导入语句了。
    """
    return plt


def prepare() -> bool:
    """配置中文字体与负号显示，返回是否可以进行绘图。"""
    if plt is None or font_manager is None:
        return False

    for candidate in _CJK_FONT_CANDIDATES:
        if Path(candidate).exists():
            font_manager.fontManager.addfont(candidate)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=candidate).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    return True


def save(figure: Any, out_path: Path) -> None:
    """把图保存到指定路径（自动创建上级目录）并释放资源。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(out_path)
    if plt is not None:
        plt.close(figure)
