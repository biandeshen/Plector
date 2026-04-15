"""文档自动生成器

职责：根据代码结构和注释自动生成 API 文档
遵循规则：函数不超过 50 行
"""

import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class DocEntry:
    """文档条目"""
    name: str
    kind: str  # class, function, method, module
    signature: str = ""
    docstring: str = ""
    children: List["DocEntry"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedDoc:
    """生成的文档"""
    title: str
    content: str
    entries: List[DocEntry]
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocGenerator:
    """文档生成器"""
    
    def __init__(self):
        self._extractors = {
            "class": self._extract_class,
            "function": self._extract_function,
            "module": self._extract_module,
        }
    
    def generate_from_module(self, module: Any, title: str = "") -> GeneratedDoc:
        """从模块生成文档"""
        module_name = getattr(module, "__name__", "unknown")
        title = title or module_name
        
        entries = []
        for name in dir(module):
            if name.startswith("_"):
                continue
            
            obj = getattr(module, name)
            
            if inspect.isclass(obj):
                entry = self._extract_class(obj)
                entries.append(entry)
            elif inspect.isfunction(obj):
                entry = self._extract_function(obj)
                entries.append(entry)
        
        content = self._render_markdown(title, entries)
        
        return GeneratedDoc(
            title=title,
            content=content,
            entries=entries,
            metadata={"module": module_name},
        )
    
    def generate_from_class(self, cls: type, title: str = "") -> GeneratedDoc:
        """从类生成文档"""
        class_name = cls.__name__
        title = title or class_name
        
        entries = []
        
        # 类本身
        class_entry = self._extract_class(cls)
        entries.append(class_entry)
        
        # 方法
        for name in dir(cls):
            if name.startswith("_"):
                continue
            
            method = getattr(cls, name)
            if callable(method) and not isinstance(method, type):
                entry = self._extract_method(cls, name, method)
                class_entry.children.append(entry)
        
        content = self._render_markdown(title, entries)
        
        return GeneratedDoc(
            title=title,
            content=content,
            entries=entries,
            metadata={"class": class_name},
        )
    
    def generate_from_directory(self, directory: Path) -> List[GeneratedDoc]:
        """从目录批量生成文档"""
        import importlib.util
        from pathlib import Path as P
        
        docs = []
        
        for py_file in P(directory).glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    doc = self.generate_from_module(module, py_file.stem)
                    docs.append(doc)
            except Exception as e:
                print(f"[DocGenerator] Failed to process {py_file}: {e}")
        
        return docs
    
    # ========== 提取器 ==========
    
    def _extract_class(self, cls: type) -> DocEntry:
        """提取类信息"""
        return DocEntry(
            name=cls.__name__,
            kind="class",
            docstring=inspect.getdoc(cls) or "",
            metadata={
                "bases": [b.__name__ for b in cls.__bases__],
            },
        )
    
    def _extract_function(self, func: callable) -> DocEntry:
        """提取函数信息"""
        try:
            sig = inspect.signature(func)
            sig_str = self._format_signature(sig)
        except (ValueError, TypeError):
            sig_str = "()"
        
        return DocEntry(
            name=func.__name__,
            kind="function",
            signature=sig_str,
            docstring=inspect.getdoc(func) or "",
        )
    
    def _extract_method(self, cls: type, name: str, method: callable) -> DocEntry:
        """提取方法信息"""
        try:
            sig = inspect.signature(method)
            sig_str = self._format_signature(sig)
        except (ValueError, TypeError):
            sig_str = "()"
        
        return DocEntry(
            name=name,
            kind="method",
            signature=sig_str,
            docstring=inspect.getdoc(method) or "",
        )
    
    def _extract_module(self, module: Any) -> DocEntry:
        """提取模块信息"""
        return DocEntry(
            name=module.__name__,
            kind="module",
            docstring=inspect.getdoc(module) or "",
        )
    
    # ========== 渲染器 ==========
    
    def _render_markdown(self, title: str, entries: List[DocEntry]) -> str:
        """渲染为 Markdown"""
        lines = [
            f"# {title}",
            "",
        ]
        
        for entry in entries:
            lines.extend(self._render_entry(entry))
        
        return "\n".join(lines)
    
    def _render_entry(self, entry: DocEntry, level: int = 2) -> List[str]:
        """渲染单个条目"""
        lines = []
        heading = "#" * level
        
        if entry.kind == "class":
            lines.append(f"{heading} {entry.name}")
            if entry.metadata.get("bases"):
                lines.append(f"*继承自: {', '.join(entry.metadata['bases'])}*")
        elif entry.kind == "function":
            lines.append(f"{heading} `{entry.name}{entry.signature}`")
        elif entry.kind == "method":
            lines.append(f"{heading} `{entry.name}{entry.signature}`")
        else:
            lines.append(f"{heading} {entry.name}")
        
        if entry.docstring:
            lines.append("")
            lines.append(entry.docstring)
        
        # 子条目
        for child in entry.children:
            lines.extend(self._render_entry(child, level + 1))
        
        lines.append("")
        return lines
    
    # ========== 工具方法 ==========
    
    def _format_signature(self, sig: inspect.Signature) -> str:
        """格式化函数签名"""
        params = []
        
        for param_name, param in sig.parameters.items():
            if param.default != inspect.Parameter.empty:
                params.append(f"{param_name}={repr(param.default)}")
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                params.append(f"*{param_name}")
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                params.append(f"**{param_name}")
            else:
                params.append(param_name)
        
        return f"({', '.join(params)})"


# ========== 快捷函数 ==========

def generate_api_docs(module_path: str, output_path: str) -> None:
    """生成 API 文档快捷函数"""
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("temp_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {module_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    generator = DocGenerator()
    doc = generator.generate_from_module(module)
    
    Path(output_path).write_text(doc.content, encoding="utf-8")
