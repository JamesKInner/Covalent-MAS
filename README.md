# Covalent-MAS

Covalent-MAS 提供了一个面向共价药物设计的模块化计算架构，覆盖靶点结构准备、
候选分子生成、化学过滤、分子对接和结果汇总。项目通过稳定的数据接口连接不同
计算阶段，使生成模型、筛选策略和结构评估工具能够独立开发、组合与扩展。

当前版本提供 AutoDock Vina 对接实现，并定义了候选生成与对接工具的标准接口，
可用于构建可复现的共价分子设计流程。

## 工作流

```text
靶点结构与反应位点
        │
        ├─ 1. 结构准备：质子化、加氢、生成 receptor PDBQT
        ├─ 2. 分子生成：接入任意 2D/3D/片段生长模型
        ├─ 3. 基础过滤：SMILES、重复、明显反应性/理化性质检查
        ├─ 4. 分子对接：通过统一接口调用 Vina 或自定义工具
        └─ 5. 结果汇总：保存 score、pose、运行状态和失败原因
```

各阶段通过可序列化的数据对象传递结果。候选分子使用 `candidate_id`、SMILES、来源
和可选 `metadata` 标识；工具返回统一的 `status`、`score`、`pose_path` 和
`message`，从而保持模型、计算工具和工作流编排之间的清晰边界。

## 仓库结构

```text
src/covalent_generation/
├── interfaces.py   # Candidate、Generator、DockingTool 数据协议
├── pipeline.py     # CSV 输入、批量运行、JSON 输出
├── vina.py         # AutoDock Vina 命令行适配器
└── cli.py          # covalent-generation 命令
examples/
├── candidates.csv
└── docking_config.json
```

## 安装

建议使用 Python 3.10 或更高版本。

```bash
git clone --branch v1.0 https://github.com/JamesKInner/Covalent-MAS.git
cd Covalent-MAS
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e .
```

使用对接功能前，请安装 [AutoDock Vina](https://github.com/ccsb-scripps/AutoDock-Vina)，
并确保 `vina` 命令位于 `PATH` 中。

## 快速开始

准备以下文件（示例数据不随仓库提供）：

```text
inputs/receptor.pdbqt
inputs/ligands/example_001.pdbqt
inputs/ligands/example_002.pdbqt
```

`examples/candidates.csv` 的每一行对应一个配体文件：

```csv
candidate_id,smiles,source
example_001,CCOc1ccc(NC(=O)C=C)cc1,my_generator
example_002,COc1ccc(NC(=O)C=C)cc1,my_generator
```

然后运行：

```bash
covalent-generation \
  --candidates examples/candidates.csv \
  --receptor inputs/receptor.pdbqt \
  --ligand-dir inputs/ligands \
  --center 10.0 12.0 8.0 \
  --box-size 20.0 20.0 20.0 \
  --exhaustiveness 8 \
  --output-dir outputs/docking \
  --results outputs/docking_results.json
```

结果 JSON 包含每个候选的状态、Vina 亲和力、输出 pose 路径和错误信息。Vina
通常以 kcal/mol 报告分数；在同一受体、口袋和参数下可以用它做初步排序，不能
直接当作结合自由能或活性预测。

## 扩展生成模型和计算工具

生成模型只需要实现 `CandidateGenerator` 协议：

```python
from covalent_generation import Candidate, CandidateGenerator


class MyGenerator:
    name = "my-model"

    def generate(self, target: dict, limit: int = 20):
        # 在这里调用 diffusion、REINVENT、LLM 或内部服务
        yield Candidate("mol-001", "CCOc1ccc(NC(=O)C=C)cc1", self.name)
```

对接工具实现 `DockingTool` 协议即可接入远程服务、GNINA、Schrödinger 或自研
程序：

```python
from covalent_generation import DockingRequest, DockingResult


class MyDockingTool:
    name = "my-docking-service"

    def run(self, request: DockingRequest) -> DockingResult:
        score, pose = call_my_service(request)
        return DockingResult(
            candidate_id=request.candidate.candidate_id,
            status="completed",
            score=score,
            pose_path=str(pose),
            tool=self.name,
        )
```

接口把工具执行和上层流程分开；建议自定义实现始终记录工具版本、参数、输入
文件哈希和失败原因，方便复现和审计。

## 评估框架

建议在各阶段记录以下指标，并根据具体靶点、反应类型和数据集扩展评价方案：

| 步骤 | 基础检查 | 示例输出 |
| --- | --- | --- |
| 结构准备 | 文件可读、链/残基编号明确、配体与受体格式正确 | `prepared receptor`、位点坐标 |
| 分子生成 | SMILES 可解析、分子去重、目标 warhead 存在 | 候选数、去重数、过滤原因 |
| 理化过滤 | MW、cLogP、TPSA、HBD/HBA 等是否落在项目设定范围 | 通过/拒绝及原因 |
| 对接 | 命令成功、产生 pose、分数可解析、搜索盒覆盖目标位点 | score、pose 文件、运行状态 |
| 汇总 | 保留完整参数、工具版本、失败信息和候选来源 | JSON/CSV 报告 |

对共价分子，普通 Vina 对接只能作为**反应前构象和口袋占据的初筛**。它不能
单独证明共价键形成。后续可在自定义工具中增加反应原子距离/角度、共价对接、
姿态几何检查、稳定性和实验验证，并在报告中明确这些证据的来源。

## 架构扩展

1. 通过 `CandidateGenerator` 接入生成模型，并记录模型版本、参数与随机种子。
2. 增加化学过滤模块，为每个筛选决策记录明确的 `reject_reason`。
3. 为所需的对接程序实现 `DockingTool`，保持 `DockingResult` 数据契约一致。
4. 引入基准数据集、重复运行和参数追踪，扩展结构评估与候选排序能力。

## 可复现性

- 输入结构准备、质子化、力场和原子类型会显著影响结果，应在项目外明确记录。
- 对接分数适合在固定协议内比较，不应跨工具、跨口袋或跨参数直接比较。
- 生成结果需要人工/计算复核；本项目不替代药化判断、实验验证或安全评估。

## 开源协议

本项目采用 [MIT License](LICENSE)。第三方软件（例如 AutoDock Vina）仍受其
各自许可证约束。
