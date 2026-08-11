# open-music-generation

通过 AI 生成多轨音频的开源项目。架构为 **"AI 编曲 → 采样库渲染"**：agent 通过 MCP/skill 对话 → 产出多轨乐谱 → 自研 wavetable 采样器引擎用乐器采样库渲染 → 混音 → 导出 mp3/wav → 项目存取。

- 语言：Python 3.10+
- 端：用户端 / CLI server / MCP 端（P5 规划中）
- **明确不做**：人声

## 能力与阶段进度

| 能力 | 状态 | 里程碑 |
|---|---|---|
| 高级乐器采样库（当前 VSCO-2-CE 管弦乐） | ✅ 已导入 | P0 |
| 单轨音频生成（采样器引擎） | ✅ 可用 | P1 |
| 乐谱模型 v1 + JSON 存取 | ✅ 可用 | P1 |
| 多轨合成与混音 | ✅ 可用 | P2 |
| 多轨编辑 | ⏳ 规划 | P2/P5 |
| 技法精细化（legato/staccato/力度交叉淡化） | ⏳ 规划 | P3 |
| 多库支持（Salamander 等商业库） | ⏳ 规划 | P4 |
| 输出 mp3/wav | ✅ 可用 | P2 |
| CLI server / MCP / 可视化编辑 | ⏳ 规划 | P5 |

阶段路线与完整方案见 [docs/roadmap.md](docs/roadmap.md)。

## 快速开始

```bash
python -m pip install -e ".[dev]"
```

### 1. 导入采样库（数据不随仓库分发，见 [docs/data-setup.md](docs/data-setup.md)）

```bash
python -m omg.library.cli import --root data/VSCO-2-CE-master --db data/vsco2.sqlite3
python -m omg.library.cli list-instruments --db data/vsco2.sqlite3
```

### 2. 渲染音频

```bash
# 生成并渲染 demo 乐谱（三轨：小提琴+大提琴+定音鼓），同时导出 mp3
python -m omg.render.cli demo --lib data/vsco2.sqlite3 --out out/ --mp3

# 渲染自定义乐谱 JSON（每轨输出 + 混音 mix.wav）
python -m omg.render.cli render out/demo.json --lib data/vsco2.sqlite3 --out out/
```

乐谱 JSON 结构见 [docs/roadmap.md](docs/roadmap.md) 或生成的 `out/demo.json`。

## 目录结构

```
src/omg/
  library/    # P0 采样库导入与索引（方言适配器 + SQLite）
  score/      # P1 乐谱模型 + JSON 存取
  render/     # P1 采样器渲染引擎（lookup/pitch/envelope/rr/cache/engine/track）
  cli/ mcp/   # 接口层（P5 规划）
data/         # 采样库与索引（gitignore，不入库）
docs/         # 设计与数据文档
```

## 技术选型（要点）

- **渲染**：自研 wavetable 采样器（非 SoundFont/非神经网络），支撑专业级四维采样（音高×力度×技法×轮次）
- **变调**：`samplerate`（libsamplerate，sinc_best）+ numpy 线性回退，符合重采样采样器语义
- **索引**：SQLite，schema 自始带 `library_id` 外键（为多库预留）
- **依赖**：numpy / soundfile / samplerate；测试 pytest

## 相关文档

- [docs/data-setup.md](docs/data-setup.md) — 数据下载与拉取（换电脑指南）
- [docs/roadmap.md](docs/roadmap.md) — 阶段路线与乐谱 JSON 结构
- [docs/architecture.md](docs/architecture.md) — 关键架构决策记录

## 里程碑

| 里程碑 | 内容 | 状态 |
|---|---|---|
| P0 数据基础 | VSCO2 导入（100% 解析率）+ SQLite 索引 | ✅ |
| P1 单轨渲染引擎 | 乐谱模型 + 采样器渲染 + render CLI | ✅ |
| P2 多轨合成 | 混音 + mp3 导出 | ✅ |
| P3 技法精细化 | legato/staccato/力度交叉淡化/变调质量 | ⏳ |
| P4 多库架构 | 商业采样库接入 | ⏳ |
| P5 交互界面 | CLI server / MCP / 可视化 | ⏳ |
