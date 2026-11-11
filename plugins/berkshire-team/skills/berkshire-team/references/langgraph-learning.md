# 本地资料学习与新案例验收

学习入口由社区版的 `scripts/research_run.py graph-learn` 提供。它等待真实的 Codex 学员、老师和独立评分员交稿，并在本地验证文件指纹和角色独立性。角色由协调者派工，图本身不调用模型。原文、笔记、时间戳转写和验收结果存于工作区。

## 重跑一次

1. 在新轮次目录下准备 `case/question.md`、`case/evidence.md` 和 `grading/rubric.md`。用 SHA-256 封存这三份文件，写入 `seal.json` 的 `files` 映射及带时区的 `sealed_at`。派学员时先仅提供同一题目与证据。不要把评分标准放进学员提示。
2. 用 `.runtime/langgraph/bin/python <技能目录>/scripts/research_run.py graph-learn init --run <轮次目录>` 启动。查看 `progress.html` 或 `learning-result.json`。每次派工时用同一入口的 `start --run … --stage … --role … --agent … --note …`。角色确实提交文件后用 `submit` 和同样参数。进展备注写明实际阅读页码、退回理由或收到的产物。保存的参与者标识必须与实际派工一致。中断后用 `resume --run …` 检查和继续。
3. 通过资料登记工具记录原件、文本、来源链接和实际阅读范围。PDF 可以用 `learning_media.py pdf --source <本地PDF> --first 80 --last 115 --output <新文本文件>` 逐页提取，公式、图表和专名仍回原页。音频用同一脚本的 `audio --source <本地录音> --start <秒> --end <秒> --whisper <whisper-cli> --model <本地权重> --output <新文件前缀>`。此入口用安装 Docling 和 imageio-ffmpeg 的独立 Python 运行。原声、片段 WAV、片段时间 SRT、原声时间 TXT 和原始 JSON 都保留。按原声时间核对引语、数字和单位；听不清的地方标记。
4. `materials/sources.json` 含资料库路径 `library`、`sources`（每条有已登记的 `id`、`locator_kind`（`page` 或 `time`）与完全匹配登记的 `locator`）、`files`（轮次内原件与核对文件的 SHA-256 映射）。资料变动应重新登记和阅读。
5. 按下表交接。老师先批改后复核修订，再提交可进入本地原则卡的核准稿。案例评分员不参与出题、教学和学员作答。可先匿名提交四份答案，评分保存后才解盲。最后将老师核准且经案例验收的规则复制到资料库原则卡，记录保留条件和可追溯的案例结果。复验保留旧答案与评分，另存新增答案和判定。

| 阶段 | 角色 | 文件（相对轮次目录） |
| --- | --- | --- |
| before | A、B | submissions/A-before.md、submissions/B-before.md |
| materials | coordinator | materials/sources.json |
| draft | A、B | submissions/A-draft.md、submissions/B-draft.md |
| critique | teacher | submissions/teacher-critique.md |
| revision | A、B | submissions/A-revision.md、submissions/B-revision.md |
| approval | teacher | submissions/teacher-approval.md、submissions/principle.md |
| after | A、B | submissions/A-after.md、submissions/B-after.md |
| grading | grader | grading/independent-grading.md |

学习阶段复用研究进度面板的本地更新和 SQLite 断点。流程完成表示已收到并核对各阶段产物，案例分数和局限以独立验收为准。每轮按香港时间留存 `learning-feedback-<日期>.md`，说明材料、版本、页码及时间段、原则卡、前后变化、复验和实际缺口。不得把一轮同题复做推断为投资效果或模型训练。

## English overview

Use `graph-learn` with the pinned LangGraph dependencies to checkpoint a local study. Seal the common question, evidence and grading rubric before the exercise. Give learners the same question and evidence, then record a baseline, actual source reading, independent drafts, teacher critique, revisions and teacher approval. Ask the same question again and have a separate grader score the saved work. Use the command sequence and file table above, and resume the same run with `graph-learn resume --run <directory>`.

Register page or time locators against the originals in the library. PDF extraction and local audio transcription are optional. Compare quotes and figures with the original page or audio. Keep source files, transcripts, grades and the teacher-approved principle in your workspace. A completed run records the submissions and scores for that exercise.
