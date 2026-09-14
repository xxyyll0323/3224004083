# 第一次个人编程作业：论文查重

> 作业 GitHub 链接：<https://github.com/xxyyll0323/3224004083>

| 项目 | 内容 |
|---|---|
| 这个作业属于哪个课程 | <https://edu.cnblogs.com/campus/gdgy/Class56-Grade2024-CS> |
| 这个作业要求在哪里 | <https://edu.cnblogs.com/campus/gdgy/Class56-Grade2024-CS/homework/15693> |
| 学号 | 3224004083 |
| 开发语言 | Python 3（零第三方运行时依赖） |
| 入口文件 | `3224004083/main.py` |

## 仓库结构

按作业要求，仓库中新建了以学号命名的文件夹，代码与测试全部放在里面：

```text
.
├── README.md                   本文件
└── 3224004083/                 学号文件夹
    ├── main.py                 程序入口（命令行三参数）
    ├── requirements.txt        运行时依赖（无第三方依赖）
    ├── requirements-dev.txt    开发工具（覆盖率 / 代码质量 / 性能图表）
    ├── .pylintrc               代码质量分析配置
    ├── plagiarism/             计算模块
    │   ├── errors.py           自定义异常
    │   ├── reader.py           文件读取、编码识别、HTML 噪声剥离
    │   ├── normalize.py        文本规范化
    │   ├── similarity.py       核心算法：字符 n-gram 词频向量的余弦相似度
    │   └── writer.py           答案格式化与写出
    ├── tests/                  73 个单元测试
    ├── tools/                  样例生成、批量查重、性能分析、质量分析、覆盖率
    ├── sample/                 自造测试样例 12 份
    └── docs/                   博客随笔、性能报告、覆盖率报告、代码质量报告
```

## 运行方式

```bash
cd 3224004083
python main.py <原文文件> <抄袭版论文文件> <答案文件>

# 示例
python main.py sample/orig.txt sample/orig_0.8_dis_2.txt answer.txt
```

答案写入第三个参数指定的文件，内容为保留两位小数的浮点数（如 `0.93`）。

详细说明见 [`3224004083/README.md`](3224004083/README.md)。
