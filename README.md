# AI 伯克希尔 · Codex 社区版

基于 AI Berkshire 和 AI Value Investing Agents 的价值投资研究工作流，适用于支持本地插件的 Codex 桌面环境。包含 **伯克希尔团队 2.2.5** 和 **AIVA 1.2.1** 的社区分发版本。

- **伯克希尔团队**组织公司背景、商业模式、长期财务、估值和证据复核。
- **AIVA**提供投资报告的分析与表达标准，也可独立运行专项工作流。
- **伯克希尔资料库**在用户指定的工作区登记和检索研究材料。

这是社区维护的源码分发版，与伯克希尔哈撒韦、文中投资人和上游作者无官方隶属或背书关系。内容供学习和研究使用，不构成投资建议。

## 安装和试用

已安装 Codex CLI 的用户可添加本仓库作为插件来源：

```sh
codex plugin marketplace add goldmansachs687-ctrl/ai-berkshire-codex
```

重启 ChatGPT 桌面应用后，在 Codex 的插件目录选择 **AI 伯克希尔 · 社区版**，安装伯克希尔团队。需要联合模式时同时安装并启用 AIVA。也可以下载源码，在 Codex 打开仓库根目录后从本地插件市场安装。[OpenAI 官方安装文档](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually)

首次可以试「用伯克希尔团队介绍一家指定公司的业务和发展历史，附来源」。完整团队研究需要宿主具备子代理和联网能力。基础核验脚本使用 Python 标准库，部分行情和财报功能需要单独配置数据依赖或连接器，详见[团队说明](plugins/berkshire-team/README.md)。

## 数据与隐私

研究报告、资料库和原始数据输出保存在用户工作区。联网研究会按任务查询公开来源，或使用用户已经授权的外部数据工具。使用外部服务时请遵守该服务的访问和数据使用规则，输出中的事实和估值应分别核对。仓库只提供代码、工作流、说明和测试，不提供账户凭证、持仓、私人原文或可再分发的行情数据。

发现安全问题请通过 GitHub 的私密漏洞报告提交。普通问题和改进建议可用 Issues。不要在公开 Issue 附上密钥、账户信息或私人研究文件。详见 [SECURITY.md](SECURITY.md)。

## 许可与来源

代码和随附的原项目文档保留 [MIT 许可证](LICENSE)及各包的版权声明。伯克希尔团队来自 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire)，AIVA 来自 [FernandoAbishai/ai-value-investing-agents](https://github.com/FernandoAbishai/ai-value-investing-agents)。具体上游提交、第三方归属与社区版调整见 [NOTICE.md](NOTICE.md)。

## 本地测试

```sh
python3 -m unittest discover -s plugins/berkshire-team/tests
```
