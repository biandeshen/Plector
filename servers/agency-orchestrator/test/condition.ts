/**
 * 条件表达式求值测试
 */
import { evaluateCondition } from '../src/core/condition.js';

let passed = 0;
let failed = 0;

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`  ✅ ${name}`);
    passed++;
  } catch (err) {
    console.log(`  ❌ ${name}: ${err instanceof Error ? err.message : err}`);
    failed++;
  }
}

function assert(condition: boolean, msg: string): void {
  if (!condition) throw new Error(msg);
}

console.log('\n=== Condition Evaluator ===');

// contains 运算符
test('contains: 匹配子串', () => {
  const ctx = new Map([['category', 'this is a bug_fix issue']]);
  assert(evaluateCondition('{{category}} contains bug', ctx) === true, '应匹配 bug');
});

test('contains: 大小写不敏感', () => {
  const ctx = new Map([['type', 'BUG_FIX']]);
  assert(evaluateCondition('{{type}} contains bug', ctx) === true, '应忽略大小写');
});

test('contains: 不匹配时返回 false', () => {
  const ctx = new Map([['category', 'new_feature']]);
  assert(evaluateCondition('{{category}} contains bug', ctx) === false, '不应匹配');
});

test('contains: 关键词有空格（引号包裹）', () => {
  const ctx = new Map([['msg', 'this is a bug fix']]);
  assert(evaluateCondition('{{msg}} contains "bug fix"', ctx) === true, '应匹配带空格的关键词');
});

// equals 运算符
test('equals: 精确匹配', () => {
  const ctx = new Map([['answer', 'yes']]);
  assert(evaluateCondition('{{answer}} equals yes', ctx) === true, '应精确匹配');
});

test('equals: 大小写不敏感', () => {
  const ctx = new Map([['answer', 'YES']]);
  assert(evaluateCondition('{{answer}} equals yes', ctx) === true, '应忽略大小写');
});

test('equals: trim 后匹配', () => {
  const ctx = new Map([['answer', '  yes  ']]);
  assert(evaluateCondition('{{answer}} equals yes', ctx) === true, '应 trim 后匹配');
});

test('equals: 不匹配时返回 false', () => {
  const ctx = new Map([['answer', 'maybe yes']]);
  assert(evaluateCondition('{{answer}} equals yes', ctx) === false, 'equals 不应做子串匹配');
});

// 边界情况
test('变量替换后再求值', () => {
  const ctx = new Map([['feedback', '文案质量不错，通过']]);
  assert(evaluateCondition('{{feedback}} contains 通过', ctx) === true, '应处理中文');
});

test('未知运算符抛错', () => {
  const ctx = new Map([['x', 'hello']]);
  try {
    evaluateCondition('{{x}} matches hello', ctx);
    throw new Error('应该抛错');
  } catch (err) {
    assert((err as Error).message.includes('不支持的条件运算符'), '应提示不支持');
  }
});

test('格式错误抛错', () => {
  const ctx = new Map([['x', 'hello']]);
  try {
    evaluateCondition('bad format', ctx);
    throw new Error('应该抛错');
  } catch (err) {
    assert((err as Error).message.includes('条件格式错误'), '应提示格式错误');
  }
});

// 结果
console.log('\n' + '='.repeat(50));
console.log(`  Condition 测试: ${passed} 通过, ${failed} 失败 (共 ${passed + failed} 项)`);
if (failed === 0) console.log('  全部通过!');
else process.exit(1);
console.log('='.repeat(50) + '\n');
