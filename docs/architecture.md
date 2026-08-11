# 架构决策记录

关键技术决策与理由，随阶段更新。

## ADR-001：自研 wavetable 采样器（而非 SoundFont/神经网络）

**决策**：渲染方案为自研采样器引擎，直接读取采样库原始 wav。
**理由**：README 把"比较高级的采样库"列为卖点，需要支撑专业级四维采样
（音高×力度×技法×轮次）。SoundFont(.sf2) 格式老旧、技法/力度层表达能力受限；
纯神经网络（如 MusicGen）无法精确控制单乐器与多轨编辑。自研引擎对"换库"零耦合——
P4 接入商业库只是灌数据。

## ADR-002：变调用重采样（排除相位声码器）

**决策**：变调 = 重采样（`samplerate`/libsamplerate sinc_best），numpy 线性回退。
**理由**：这是重采样采样器，正确语义是"播放速率变化"（共振峰随动，像磁带变速）。
相位声码器改变共振峰导致音色走样，原理不符。单次重采样合并变调与采样率转换比率，
避免级联损失。实测两种后端 D4 偏差 +0.08 半音（FFT 分辨率内）。

## ADR-003：方言适配器从 P0 内置（VSCO2 是 25 个迷你库的拼盘）

**决策**：导入器按"方言适配器"设计，一个通用令牌解析器 + 专用适配器
（钢琴 MappingChart、定音鼓固定音高、无音高）。
**理由**：实测 VSCO2 内部有 10+ 种命名变体（`LLVln_ArcoVib_A3_f` /
`MOHorn_stac_A#1_v1_rr1` / `Player_dyn1_rr1_000`+MappingChart /
`Timpani1_Hit_v1_rr1_Sum` …）。多库支持（P4）依赖这套抽象，不是后补。
真实库 2948 文件解析率 100%。

## ADR-004：SQLite 索引，schema 自始带 library_id 外键

**决策**：索引用 SQLite（stdlib），`samples` 表带 `library_id` 外键。
**理由**：几千样本 + 快速查询，避免 JSON 全量载入内存；`library_id` 为 P4 多库
预留，避免后期迁移。乐器身份永远来自目录路径，不由文件名决定。

## ADR-005：乐谱时间基用拍 + 全局 tempo

**决策**：`Note.start_beat`（拍）+ `Score.tempo_bpm`，渲染时换算秒。
**理由**：未来时值/速度/小节编辑不需要改 schema；JSON 带 `version` 字段支持演进。

## ADR-006：数据不进 git，提供可复现拉取路径

**决策**：`data/`（原始采样库 + 索引）全部 gitignore；[data-setup.md](data-setup.md)
记录下载源与导入命令。
**理由**：2.2GB+ 二进制不入库；换电脑按文档重拉即可，索引可重建。

## ADR-007：混音用软限幅器（不做峰值归一化）

**决策**：多轨叠加后主输出用 `ceiling·tanh(x/ceiling)` 软限幅，保留轨间 gain 差异。
**理由**：若做峰值归一化会把 gain_db 调低/声像调偏的轨道拉回同样响度，抹掉混音意图。
小信号线性、大信号向 0.95 压缩防削波。

## ADR-008：mp3 导出走 ffmpeg（libmp3lame）

**决策**：mp3 用子进程调用 `ffmpeg -c:a libmp3lame`。
**理由**：本机已装 ffmpeg（winget），质量高、零额外 Python 依赖；`lameenc` 作为无 ffmpeg 环境的备选。

## ADR-009：技法语义按"请求技法"塑造

**决策**：时长/包络按**请求的技法**塑造，而非解析到的样本技法。
staccato/spiccato → 时长压缩到 ~60% 快起快收；pizzicato → 短尾自然衰减；
sustain/legato/arco → 名义时长 + 90ms 尾部重叠（连奏感，音符不硬切）。
**理由**：库可能没有请求的技法样本（如 solo_violin 无 staccato），回退到最近样本时
仍应保留请求技法的音乐语义，否则 staccato 请求会变成 sustain 听感。

## ADR-010：空间感用合成 IR 卷积混响

**决策**：混响 = 指数衰减噪声 IR 的 FFT 卷积（纯 numpy），mixer 按 wet 比例混合，
尾音完整保留（输出比输入长）。demo 默认 wet=0.25，可用 `--reverb` 调。
**理由**：VSCO2 干样本直出无空间感，是"难听"主因之一；FFT 卷积比 Schroeder
递归滤波简单且快，且无需 scipy。混响与增益归一化解耦，不抹混音意图。

## 未决

- **力度层边界**：f/p、v1-v3 到 MIDI 0-127 的区间是约定而非库内事实，
  存 `pitch_config.json` 可人工校准
- **定音鼓音高**：Timpani1-5 的音高目前是合理默认值（F2/C3/F3/C4/F4），可校准
- **超长音符**：仍按名义时长 + 尾音截断，未做 loop/sustain 段（P4/P5 候选）
- **混响参数**：tau/长度目前固定，未参数化暴露（后续可做成 Score renderer_options）
