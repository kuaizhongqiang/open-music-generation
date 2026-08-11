# 阶段路线图与乐谱结构

## 阶段路线

每阶段以"可听到/可验证的产物"收尾。

| 阶段 | 内容 | 验收 | 状态 |
|---|---|---|---|
| **P0 数据基础** | VSCO2 导入器（方言适配器）+ SQLite 索引 | 全库可解析率 >99%（实际 100%），钢琴 MappingChart 正确 | ✅ |
| **P1 单轨渲染引擎** | 乐谱模型 v1 + 采样器（lookup/pitch/envelope/rr/cache）+ render CLI | FFT 音高断言、渲染闭环、音阶可听 | ✅ |
| **P2 多轨合成** | 乐谱模型完整版（每轨 gain/pan）+ 混音器 + mp3 导出 | 三轨混出一首、导出 mp3/wav | ✅ |
| **P3 技法精细化** | legato 衔接、staccato 缩短、力度交叉淡化、卷积混响 | 同旋律不同技法听感差异正确 | ✅ |
| **P4 多库架构** | 厂商无关适配器 + Salamander 钢琴 + 跨库乐器切换 | 钢琴可跨库渲染对比 | ⏳ |
| **P5 交互界面** | CLI server + MCP server + 可选可视化编辑 | agent 通过 MCP 完成创作-编辑-导出 | ⏳ |

### 核心原则

1. 每阶段有可听/可验证产物，绝不堆"半成品"
2. 方言适配器从 P0 内置（多库支持靠它，不是后补）
3. 乐谱模型是贯穿全链路的核心工件，P1 定 v1、P2 扩展
4. 最小依赖：stdlib + numpy + soundfile + samplerate

## 乐谱 JSON 结构（v1）

时间基用"拍"+ 全局 tempo，渲染时换算秒。

```json
{
  "version": 1,
  "title": "demo",
  "tempo_bpm": 90.0,
  "tracks": [
    {
      "id": "violin",
      "name": "violin melody",
      "instrument": "solo_violin",
      "notes": [
        {"start_beat": 0.0, "duration": 1.0, "pitch": 60, "velocity": 100, "technique": "arco_vib"}
      ]
    }
  ]
}
```

- `pitch`：MIDI 键号（C4=60）
- `technique`：技法 id，合法取值 = 索引中该乐器的 `articulation` 去重集
- `velocity`：0-127，渲染侧按力度层匹配 + gain 曲线补偿

扩展口（向后兼容）：Note 加 `tie_to/legato_group`（P3）；Track 加 `gain_db/pan`（P2）；Score 加 `libraries/renderer_options`（P2/P4）。

## 渲染管线

```
乐谱 JSON → 每轨: 音符按拍排序 → lookup 四层匹配(技法→音高→力度→轮次)
  → 变调(samplerate/numpy) → 包络(attack/release) → 叠加到轨道缓冲
  → soft-clip → 写 stereo 44100 wav
```
