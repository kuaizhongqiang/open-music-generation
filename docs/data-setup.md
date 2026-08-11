# 数据准备与拉取（换电脑指南）

原始采样库与派生索引**不进 git**（见根目录 `.gitignore` 的 `data/`）。换电脑时按本页步骤重新拉取即可，全部可复现。

## 1. 下载 VSCO-2-CE

> 开源管弦乐采样库（CC0 公共领域），约 2.2GB，全部为原始 wav。

- 来源（任选其一）：
  - GitHub 镜像：[schollz/VSCO-2-CE](https://github.com/schollz/VSCO-2-CE) → 绿色 **Code → Download ZIP**
  - 官方站：[Versilian Studios VSCO 2 Community](https://versilian-studios.com/vsco-community/)（下载 **Raw WAV** 版本）
- 解压到 `data/VSCO-2-CE-master/`（顶层应含 `Brass/ Strings/ Woodwinds/ Keys/ Percussion/` 等目录）

## 2. 安装与初始化

```bash
python -m pip install -e ".[dev]"          # 安装包与开发依赖
python -m omg.library.cli import --root data/VSCO-2-CE-master --db data/vsco2.sqlite3
```

导入完成后生成索引 `data/vsco2.sqlite3`（预期：2948 文件、可解析率 100%）。

## 3. 验证

```bash
python -m omg.library.cli list-instruments --db data/vsco2.sqlite3
python -m omg.library.cli query --db data/vsco2.sqlite3 --instrument solo_violin --note 60
```

## 4. 目录说明

| 路径 | 用途 | 是否入库 |
|---|---|---|
| `data/VSCO-2-CE-master/` | 原始采样库（下载） | 否 |
| `data/vsco2.sqlite3` | 导入生成的索引（可重建） | 否 |
| `out/` | 渲染输出 | 否 |

## 5. 索引重建

删除 `data/vsco2.sqlite3` 后重跑第 2 步导入命令即可，幂等。
