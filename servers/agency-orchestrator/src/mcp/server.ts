/**
 * MCP Server — 通过 MCP 协议暴露工作流操作
 *
 * 6 个工具，每个都是对现有函数的薄封装。
 * 传输层: StdioServerTransport (stdin/stdout JSON-RPC)
 *
 * 重要: 所有日志必须输出到 stderr，stdout 是 MCP 协议通道。
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { resolve, relative, dirname } from 'node:path';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import * as yaml from 'js-yaml';

import { run } from '../index.js';
import { parseWorkflow, validateWorkflow } from '../core/parser.js';
import { buildDAG, formatDAG } from '../core/dag.js';
import { listAgents } from '../agents/loader.js';
import { composeWorkflow } from '../cli/compose.js';
import { readFileSync, readdirSync, statSync } from 'node:fs';

/** 递归扫描目录 */
function scanDir(dir: string, extensions: string[]): string[] {
  const results: string[] = [];
  if (!existsSync(dir)) return results;

  for (const entry of readdirSync(dir)) {
    const full = resolve(dir, entry);
    if (statSync(full).isDirectory()) {
      results.push(...scanDir(full, extensions));
    } else if (extensions.some(ext => entry.endsWith(ext))) {
      results.push(full);
    }
  }
  return results;
}

/** 自动查找 superpowers 目录 */
function findSuperpowersDir(hint?: string): string {
  if (hint && existsSync(resolve(hint))) return resolve(hint);
  const candidates = [
    resolve('superpowers-zh'),
    resolve('../superpowers-zh'),
    resolve('skills'),
    resolve('node_modules/superpowers-zh'),
    resolve(dirname(new URL(import.meta.url).pathname), '../../node_modules/superpowers-zh'),
  ];
  for (const dir of candidates) {
    if (existsSync(dir)) return dir;
  }
  return resolve(hint || './superpowers-zh');
}

/** 自动查找 agents 目录 */
function findAgentsDir(hint?: string): string {
  if (hint && existsSync(resolve(hint))) return resolve(hint);
  const candidates = [
    resolve('agency-agents-zh'),
    resolve('../agency-agents-zh'),
    resolve('agents'),
    resolve('node_modules/agency-agents-zh'),
    resolve(dirname(new URL(import.meta.url).pathname), '../../node_modules/agency-agents-zh'),
  ];
  for (const dir of candidates) {
    if (existsSync(dir)) return dir;
  }
  return resolve(hint || './agency-agents-zh');
}

/** 递归查找 YAML 文件 */
function findYamlFiles(dir: string, result: string[]): void {
  for (const entry of readdirSync(dir)) {
    const full = resolve(dir, entry);
    if (statSync(full).isDirectory()) {
      findYamlFiles(full, result);
    } else if (entry.endsWith('.yaml') || entry.endsWith('.yml')) {
      result.push(full);
    }
  }
}

/** 列出 workflows 目录下的 YAML 文件 */
function discoverWorkflows(): Array<{ file: string; name: string; description: string }> {
  const workflowsDir = resolve('workflows');
  if (!existsSync(workflowsDir)) return [];

  const files: string[] = [];
  findYamlFiles(workflowsDir, files);

  return files.map(f => {
    try {
      const content = readFileSync(f, 'utf-8');
      const doc = yaml.load(content) as Record<string, unknown>;
      return {
        file: relative(process.cwd(), f),
        name: (doc?.name as string) || '(unnamed)',
        description: (doc?.description as string) || '',
      };
    } catch {
      return { file: relative(process.cwd(), f), name: '(parse error)', description: '' };
    }
  });
}

/**
 * 静默执行函数 — 临时屏蔽 stdout 输出（引用计数，并发安全）
 * composeWorkflow 等函数内部有 console.log，会污染 MCP 协议通道
 */
let suppressCount = 0;
let origStdoutWrite: typeof process.stdout.write | null = null;

async function silentCall<T>(fn: () => Promise<T>): Promise<T> {
  if (suppressCount === 0) {
    origStdoutWrite = process.stdout.write.bind(process.stdout);
    process.stdout.write = () => true;
  }
  suppressCount++;
  try {
    return await fn();
  } finally {
    suppressCount--;
    if (suppressCount === 0 && origStdoutWrite) {
      process.stdout.write = origStdoutWrite;
      origStdoutWrite = null;
    }
  }
}

export async function startServer(verbose = false): Promise<void> {
  const require = createRequire(import.meta.url);
  const pkgPath = require.resolve('../../package.json');
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));

  const server = new McpServer({
    name: 'agency-orchestrator',
    version: pkg.version || '0.0.0',
    description: `Agency Orchestrator — 多智能体 YAML 工作流引擎

【9 个工具】
1. run_workflow: 执行 YAML 工作流文件，支持 DAG 并行执行、变量替换、多角色协作。触发：当用户提供工作流文件或要求运行特定工作流时。
2. validate_workflow: 校验 YAML 工作流文件的语法和结构，检查必填字段、依赖关系、变量引用。触发：在执行工作流前验证其正确性。
3. list_workflows: 列出所有可用的工作流模板（30 个内置模板）。触发：用户询问有哪些工作流可用。
4. plan_workflow: 显示工作流的 DAG 执行计划——哪些步骤可以并行、哪些必须串行。触发：用户想了解工作流的执行流程。
5. compose_workflow: 用自然语言描述需求，AI 自动生成 YAML 工作流文件。触发：用户想要创建工作流但不懂 YAML 语法。
6. list_roles: 列出 174 个 AI 角色，按 18 个部门分类（engineering/marketing/specialized/product/design/testing/support 等）。触发：用户查找特定角色或了解角色能力。
7. get_role: 获取指定角色的完整定义，包含角色说明、职责、行为规范。触发：用户需要了解某个角色的具体能力。
8. list_skills: 列出 20 个 superpowers 开发技能。触发：用户询问有哪些技能可用。
9. get_skill: 获取指定技能的完整内容（SKILL.md）。触发：用户需要查看技能详情。

【174 个 AI 角色分类】
- engineering (27): 前端/后端/AI/DevOps/安全/移动/数据/架构师
- marketing (33): 小红书/抖音/微信/B站/快手/TikTok/SEO/增长
- specialized (33): 智能体编排/提示词工程/MCP构建/文档生成
- product (5): 产品经理/Sprint排序/趋势研究/反馈分析
- design (8): UI/UX/品牌/视觉/图像提示词
- testing (9): API测试/性能基准/无障碍审核
- support (8): 客服/数据分析/法务合规/财务
- 其他: academic(6)/finance(3)/game-development(5)/hr(2)/legal(2)/paid-media(7)/project-management(6)/sales(8)/spatial-computing(6)/strategy(3)/supply-chain(3)

【30 个内置工作流模板】
- 开发类: tech-design-review, pr-review, tech-debt-audit, api-doc-gen, security-audit, release-checklist
- 营销类: competitor-analysis, xiaohongshu-content, seo-content-matrix
- 数据/设计/运维: data-pipeline-review, dashboard-design, ux-review, incident-postmortem, sre-health-check, weekly-report
- 战略/法务/HR: business-plan, contract-review, interview-questions
- 通用类: product-review, content-pipeline, story-creation, ai-opinion-article

【免 API key】使用已有 AI 会员：Claude Max、GitHub Copilot、ChatGPT Plus、Google 账号（免费）、本地 Ollama`,
  });

  // ─── Tool 1: run_workflow ───
  server.tool(
    'run_workflow',
    '执行一个 YAML 工作流文件（.yaml/.yml），支持 DAG 并行执行、变量替换、多角色协作。用于：当用户提供工作流文件或要求运行特定工作流时。',
    {
      path: z.string().describe('Path to workflow YAML file'),
      inputs: z.record(z.string(), z.string()).optional().describe('Key-value input variables'),
      provider: z.enum(['claude-code', 'gemini-cli', 'copilot-cli', 'codex-cli', 'openclaw-cli', 'deepseek', 'claude', 'openai', 'ollama']).optional().describe('LLM provider (default: claude-code，免 API key，使用 Claude Max 会员)'),
      model: z.string().optional().describe('Override model name'),
    },
    async ({ path: workflowPath, inputs, provider, model }) => {
      try {
        const absPath = resolve(workflowPath);
        if (!existsSync(absPath)) {
          return { content: [{ type: 'text' as const, text: `文件不存在: ${workflowPath}` }], isError: true };
        }

        // 默认使用 claude-code（免 API key，使用 Claude Max 会员）
        const llmOverride: Record<string, string> = {};
        llmOverride.provider = provider || 'claude-code';
        if (model) llmOverride.model = model;

        const result = await silentCall(() =>
          run(absPath, (inputs || {}) as Record<string, string>, {
            quiet: true,
            llmOverride,
          }),
        );

        const lastStep = result.steps[result.steps.length - 1];
        const output = lastStep?.output || '(no output)';
        const tokenSummary = `Tokens: ${result.totalTokens.input} in / ${result.totalTokens.output} out`;

        return {
          content: [{ type: 'text' as const, text: `${output}\n\n---\n${tokenSummary}` }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `执行失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 2: validate_workflow ───
  server.tool(
    'validate_workflow',
    '校验工作流 YAML 文件的有效性，检查语法、步骤、依赖关系等。用于：在执行工作流前验证其正确性。',
    {
      path: z.string().describe('Path to workflow YAML file'),
    },
    async ({ path: workflowPath }) => {
      try {
        const absPath = resolve(workflowPath);
        if (!existsSync(absPath)) {
          return { content: [{ type: 'text' as const, text: `文件不存在: ${workflowPath}` }], isError: true };
        }

        const workflow = parseWorkflow(absPath);
        const errors = validateWorkflow(workflow);

        if (errors.length === 0) {
          return {
            content: [{
              type: 'text' as const,
              text: `✅ ${workflow.name} — 校验通过\n步骤数: ${workflow.steps.length}\n输入数: ${(workflow.inputs || []).length}`,
            }],
          };
        } else {
          return {
            content: [{
              type: 'text' as const,
              text: `❌ ${workflow.name} — 校验失败:\n${errors.map(e => `  - ${e}`).join('\n')}`,
            }],
            isError: true,
          };
        }
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `校验错误: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 3: list_workflows ───
  server.tool(
    'list_workflows',
    '列出所有可用的工作流模板（.yaml 文件），包含每个工作流的名称和描述。用于：查看有哪些工作流可用、选择合适的工作流。',
    {},
    async () => {
      try {
        const workflows = discoverWorkflows();
        if (workflows.length === 0) {
          return { content: [{ type: 'text' as const, text: '未找到工作流文件（workflows/ 目录不存在或为空）' }] };
        }

        const lines = workflows.map(w => `- ${w.file}: ${w.name}${w.description ? ` — ${w.description}` : ''}`);
        return {
          content: [{ type: 'text' as const, text: `共 ${workflows.length} 个工作流:\n\n${lines.join('\n')}` }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `列出工作流失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 4: plan_workflow ───
  server.tool(
    'plan_workflow',
    '显示工作流的 DAG 执行计划——哪些步骤可以并行、哪些必须串行、执行顺序是怎样的。用于：在执行前了解工作流的执行流程。',
    {
      path: z.string().describe('Path to workflow YAML file'),
    },
    async ({ path: workflowPath }) => {
      try {
        const absPath = resolve(workflowPath);
        if (!existsSync(absPath)) {
          return { content: [{ type: 'text' as const, text: `文件不存在: ${workflowPath}` }], isError: true };
        }

        const workflow = parseWorkflow(absPath);
        const errors = validateWorkflow(workflow);
        if (errors.length > 0) {
          return {
            content: [{ type: 'text' as const, text: `校验失败:\n${errors.map(e => `  - ${e}`).join('\n')}` }],
            isError: true,
          };
        }

        const dag = buildDAG(workflow);
        const dagText = formatDAG(dag);
        return {
          content: [{ type: 'text' as const, text: `${workflow.name}\n\n${dagText}` }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `计划失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 5: compose_workflow ───
  server.tool(
    'compose_workflow',
    '用自然语言描述生成一个 YAML 工作流文件。利用 AI 将用户的需求转换为可执行的工作流定义。用于：当用户想要创建工作流但不懂 YAML 语法时。',
    {
      description: z.string().describe('One-sentence workflow description'),
      provider: z.enum(['claude-code', 'gemini-cli', 'copilot-cli', 'codex-cli', 'openclaw-cli', 'deepseek', 'claude', 'openai', 'ollama']).optional().describe('LLM provider (default: claude-code)'),
      model: z.string().optional().describe('Model name'),
    },
    async ({ description, provider, model }) => {
      try {
        const agentsDir = findAgentsDir();
        const llmProvider = provider || 'claude-code';
        const defaultModels: Record<string, string> = {
          claude-code: 'claude-sonnet-4-20250514',
          gemini-cli: 'gemini-2.5-pro',
          copilot-cli: 'gpt-4o',
          codex-cli: 'claude-sonnet-4-20250514',
          openclaw-cli: 'claude-sonnet-4-20250514',
          deepseek: 'deepseek-chat',
          claude: 'claude-sonnet-4-20250514',
          openai: 'gpt-4o',
          ollama: 'llama3',
        };
        const llmModel = model || defaultModels[llmProvider] || 'claude-sonnet-4-20250514';

        const result = await silentCall(() =>
          composeWorkflow({
            description,
            agentsDir,
            llmConfig: { provider: llmProvider, model: llmModel },
          }),
        );

        let text = `✅ 工作流已生成: ${result.relativePath}\n\n${result.yaml}`;
        if (result.warnings.length > 0) {
          text += `\n\n⚠️ 校验警告:\n${result.warnings.map(w => `  - ${w}`).join('\n')}`;
        }

        return { content: [{ type: 'text' as const, text }] };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `生成失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 6: list_roles ───
  server.tool(
    'list_roles',
    '列出 174 个 AI 角色（按分类：engineering/设计/marketing/产品/游戏/学术等），每个角色包含名称和完整描述。用于：查找特定角色、了解角色能力、选择合适的角色执行任务。',
    {
      agents_dir: z.string().optional().describe('Path to agents directory'),
    },
    async ({ agents_dir }) => {
      try {
        const agentsDir = findAgentsDir(agents_dir);

        // 直接读取所有角色文件，获取完整信息
        const categories = readdirSync(agentsDir).filter(name => {
          return statSync(resolve(agentsDir, name)).isDirectory();
        });

        const allRoles: Array<{ category: string; name: string; description: string }> = [];

        for (const cat of categories) {
          const catDir = resolve(agentsDir, cat);
          const files = readdirSync(catDir).filter(f => f.endsWith('.md'));

          for (const file of files) {
            try {
              const content = readFileSync(resolve(catDir, file), 'utf-8');
              // 解析 frontmatter
              const parts = content.split('---', 3);
              if (parts.length >= 3) {
                const fm = yaml.load(parts[1]) as Record<string, string>;
                if (fm?.name) {
                  allRoles.push({
                    category: cat,
                    name: fm.name,
                    description: fm.description || '',
                  });
                }
              }
            } catch {
              // 跳过解析失败的文件
            }
          }
        }

        // 按分类组织输出
        const byCategory: Record<string, typeof allRoles> = {};
        for (const role of allRoles) {
          if (!byCategory[role.category]) byCategory[role.category] = [];
          byCategory[role.category].push(role);
        }

        const lines: string[] = [];
        for (const [cat, roles] of Object.entries(byCategory)) {
          lines.push(`## ${cat} (${roles.length})`);
          for (const r of roles) {
            const desc = r.description ? ` — ${r.description.slice(0, 60)}${r.description.length > 60 ? '...' : ''}` : '';
            lines.push(`- ${r.name}${desc}`);
          }
          lines.push('');
        }

        return {
          content: [{ type: 'text' as const, text: `共 ${allRoles.length} 个角色:\n\n${lines.join('\n')}` }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `列出角色失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 7: list_skills ───
  server.tool(
    'list_skills',
    '列出 20 个开发技能（chinese-code-review/chinese-git-workflow/mcp-builder/test-driven-development 等），每个技能包含名称和完整描述。用于：应用技能到当前任务、查找特定技能、了解更多技能用法。',
    {
      skills_dir: z.string().optional().describe('Path to skills directory'),
    },
    async ({ skills_dir }) => {
      try {
        const skillsDir = findSuperpowersDir(skills_dir);
        const skillsPath = resolve(skillsDir, 'skills');

        if (!existsSync(skillsPath)) {
          return { content: [{ type: 'text' as const, text: '未找到 skills 目录' }], isError: true };
        }

        const skillDirs = readdirSync(skillsPath).filter(name => {
          return statSync(resolve(skillsPath, name)).isDirectory();
        });

        const skills: Array<{ name: string; description: string }> = [];

        for (const name of skillDirs) {
          try {
            const skillFile = resolve(skillsPath, name, 'SKILL.md');
            if (existsSync(skillFile)) {
              const content = readFileSync(skillFile, 'utf-8');
              const parts = content.split('---', 3);
              if (parts.length >= 3) {
                const fm = yaml.load(parts[1]) as Record<string, string>;
                skills.push({
                  name: fm.name || name,
                  description: fm.description || '',
                });
              }
            }
          } catch {
            skills.push({ name, description: '' });
          }
        }

        const lines = skills.map(s => {
          const desc = s.description ? ` — ${s.description.slice(0, 80)}${s.description.length > 80 ? '...' : ''}` : '';
          return `- ${s.name}${desc}`;
        });

        return {
          content: [{ type: 'text' as const, text: `共 ${skills.length} 个技能:\n\n${lines.join('\n')}` }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `列出技能失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 8: get_skill ───
  server.tool(
    'get_skill',
    '获取指定技能的完整内容（SKILL.md），包含技能说明、使用方法、模板等。用于：查看技能详情、学习技能用法。',
    {
      name: z.string().describe('技能名称，如 chinese-code-review'),
      skills_dir: z.string().optional().describe('Path to skills directory'),
    },
    async ({ name, skills_dir }) => {
      try {
        const skillsDir = findSuperpowersDir(skills_dir);
        const skillPath = resolve(skillsDir, 'skills', name, 'SKILL.md');

        if (!existsSync(skillPath)) {
          return { content: [{ type: 'text' as const, text: `技能不存在: ${name}` }], isError: true };
        }

        const content = readFileSync(skillPath, 'utf-8');
        return {
          content: [{ type: 'text' as const, text: `# ${name}\n\n${content}` }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `读取技能失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Tool 9: apply_skill ───
  server.tool(
    'apply_skill',
    '将技能应用到当前任务——读取技能内容并结合任务描述，返回如何在当前任务中使用该技能的指导。用于：当用户要求使用某个技能完成任务时。',
    {
      name: z.string().describe('技能名称'),
      task: z.string().describe('任务描述'),
      skills_dir: z.string().optional().describe('Path to skills directory'),
    },
    async ({ name, task, skills_dir }) => {
      try {
        const skillsDir = findSuperpowersDir(skills_dir);
        const skillPath = resolve(skillsDir, 'skills', name, 'SKILL.md');

        if (!existsSync(skillPath)) {
          return { content: [{ type: 'text' as const, text: `技能不存在: ${name}` }], isError: true };
        }

        const content = readFileSync(skillPath, 'utf-8');

        // 提取 YAML frontmatter
        const parts = content.split('---', 3);
        if (parts.length < 3) {
          return { content: [{ type: 'text' as const, text: '技能格式错误: 缺少 YAML frontmatter' }], isError: true };
        }

        let frontmatter: Record<string, string> = {};
        try {
          frontmatter = yaml.load(parts[1]) as Record<string, string>;
        } catch {
          return { content: [{ type: 'text' as const, text: '技能格式错误: YAML 解析失败' }], isError: true };
        }

        const description = frontmatter.description || '';
        const body = parts.slice(2).join('---').trim();

        return {
          content: [{
            type: 'text' as const,
            text: `# 技能: ${name}\n\n**描述**: ${description}\n\n**任务**: ${task}\n\n---\n\n## 技能内容\n\n${body.slice(0, 3000)}${body.length > 3000 ? '\n\n...(内容过长，已截断)' : ''}`,
          }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: `应用技能失败: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  );

  // ─── Start server ───
  if (verbose) {
    console.error('[ao-mcp] Starting MCP server...');
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);

  if (verbose) {
    console.error('[ao-mcp] Server connected via stdio');
  }
}
