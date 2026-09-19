# Covalent Generation

一个面向开源协作的共价小分子生成与结构评估最小工作流。项目只保留
**基础步骤、稳定的数据接口和一个 AutoDock Vina 示例**，便于研究者替换自己的
生成模型、过滤器和分子对接工具。

> **定位**：这是一个可扩展的工程模板，不是完整的药物发现平台，也不提供
> 已训练模型、靶点数据、商业软件或实验结论。

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

每一步只传递小型、可序列化的数据。候选分子使用 `candidate_id`、SMILES、来源
和可选 `metadata` 标识；工具返回统一的 `status`、`score`、`pose_path` 和
`message`。这样可以在不改动流程代码的情况下替换模型或工具。

## 仓库结构

```text
src/covalent_generation/
├── interfaces.py   # Candidate、Generator、DockingTool 等最小协议
├── pipeline.py     # CSV 输入、批量运行、JSON 输出
├── vina.py         # AutoDock Vina 命令行适配器
└── cli.py          # covalent-generation 命令
examples/
├── candidates.csv
└── docking_config.json
```

仓库刻意不包含大型数据集、模型权重、靶点结构、对接结果和内部运行环境。

## 安装

项目运行时只使用 Python 标准库；建议使用 Python 3.10 或更高版本。

```bash
git clone --branch v1.0 https://github.com/JamesKInner/Covalent-MAS.git
cd Covalent-MAS
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e .
```

对接示例需要用户另外安装 [AutoDock Vina](https://github.com/ccsb-scripps/AutoDock-Vina)，
并确保 `vina` 在 `PATH` 中。项目不替用户下载受许可约束的软件或模型。

## 最小运行示例

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

## 自定义生成模型和工具

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

## 每一步如何做基础评估

这里提供的是工程层面的最小检查，实际研究应根据靶点、反应类型和数据集补充验证：

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

## 推荐的扩展顺序

1. 替换 `CandidateGenerator`，接入已有生成模型并保留模型/seed 元数据。
2. 增加一个轻量过滤器，输出明确的 `reject_reason`。
3. 用项目所需的对接程序实现 `DockingTool`，保持 `DockingResult` 格式不变。
4. 添加重复运行、参数记录和小规模基准集，再决定是否接入更复杂的结构评估。

## 可复现性与边界

- 输入结构准备、质子化、力场和原子类型会显著影响结果，应在项目外明确记录。
- 对接分数适合在固定协议内比较，不应跨工具、跨口袋或跨参数直接比较。
- 生成结果需要人工/计算复核；本项目不替代药化判断、实验验证或安全评估。
- 示例代码不包含任何受限数据、模型权重、API 密钥或内部路径。

## 开源协议

本项目采用 [MIT License](LICENSE)。第三方软件（例如 AutoDock Vina）仍受其
各自许可证约束。
