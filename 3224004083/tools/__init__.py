# -*- coding: utf-8 -*-
"""开发与分析脚本包。

这里的脚本都是**开发期的辅助工具**，不参与评测：

* ``make_samples.py``  生成自测样例
* ``run_samples.py``   批量验收样例
* ``batch_check.py``   对多个抄袭版文件批量查重
* ``perf_analysis.py`` 性能分析（cProfile）与图表
* ``test_coverage.py`` 单元测试与覆盖率报告
* ``code_quality.py``  代码质量分析（pylint）
* ``plotting.py``      绘图公共代码

统一用 ``python tools/<脚本名>.py`` 的方式运行（脚本内部会把项目根目录加进
模块搜索路径），例如::

    python tools/run_samples.py
"""
