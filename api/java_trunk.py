from tree_sitter import Language, Parser, Node
import tree_sitter_java as tsjava   # 导入 Java 语法
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class CodeChunk:
    file_path: str
    file_type: str
    chunk_type: str       # "class", "interface", "method", "constructor" 等
    name: str
    start_line: int       # 1-based
    end_line: int         # 1-based
    start_byte: int
    end_byte: int
    content: str

    def __str__(self):
        return f"{self.chunk_type.upper():<12} {self.name:<40} [{self.start_line:4}-{self.end_line:4}]  {self.file_path}"

def extract_java_chunks(file_path: str | Path) -> List[CodeChunk]:
    file_path = Path(file_path)
    # 跳过测试文件
    if not file_path.is_file() or not file_path.suffix == ".java" or "test" in str(file_path).lower():
        return []

    try:
        source_bytes = file_path.read_bytes()  # 保持 bytes，避免编码问题
    except Exception as e:
        print(f"读取失败 {file_path}: {e}")
        return []

    # 初始化 Parser 和 Java Language
    JAVA_LANGUAGE = Language(tsjava.language())
    parser = Parser()
    parser.language = JAVA_LANGUAGE

    try:
        tree = parser.parse(source_bytes)
    except Exception as e:
        print(f"解析失败 {file_path}: {e}")
        return []

    chunks: List[Document] = []
    source_text = source_bytes.decode("utf-8", errors="replace")   # 用于切片内容

    def traverse(node: Node):
        # 提取类 / 接口
        if node.type in ("class_declaration", "interface_declaration"):
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode("utf8") if name_node else "???"
            content = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            content = _preprocess_java(content)
            chunks.append(CodeChunk(
                file_path=str(file_path),
                file_type=file_path.suffix[1:],
                chunk_type="class" if node.type == "class_declaration" else "interface",
                name=name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                content=content
            ))

        # 提取方法 / 构造方法
        elif node.type in ("method_declaration", "constructor_declaration"):
            class_name = get_containing_class_name(node)
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode("utf8") if name_node else "???"
            name = f"{class_name}.{name}"
            # 可选：提取参数列表（更精确签名）
            params_node = node.child_by_field_name("parameters")
            params = ""
            if params_node:
                params_text = params_node.text.decode("utf8", errors="replace").strip()
                params = params_text.replace("\n", " ").replace("  ", " ")

            full_name = f"{name}{params}"
            chunks.append(CodeChunk(
                file_path=str(file_path),
                file_type=file_path.suffix[1:],
                chunk_type="constructor" if node.type == "constructor_declaration" else "method",
                name=full_name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                content=source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            ))

        # 递归遍历子节点
        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return chunks

def _preprocess_java(content: str) -> str:  
    """Java文件预处理：去掉import语句"""  
    lines = content.split('\n')  
    filtered_lines = []  
      
    for line in lines:  
        stripped = line.strip()  
        # 跳过import和package语句  
        if not (stripped.startswith('import ')):  
            filtered_lines.append(line)  
      
    return '\n'.join(filtered_lines)  
def get_containing_class_name(method_node: Node) -> str:
    """
    从 method_declaration 节点向上遍历，找到最近的 class_declaration / interface_declaration 等
    返回类名，如果找不到返回 "???" 或空字符串
    """
    current = method_node
    while current is not None:
        node_type = current.type
        
        # Java 中常见的类型声明节点
        if node_type in (
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
            # 可选：annotation_declaration, local_variable_declaration 中的匿名类等（较少见）
        ):
            name_node = current.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8", errors="replace")
            return "???"

        # 如果遇到 lambda / 匿名类 / 嵌套块，可以选择停止或继续向上
        # 这里简单继续向上，直到 compilation_unit（文件根）
        current = current.parent
    
    return ""  # 文件根也没找到类（理论上不应该发生，除非方法在顶层——Java 不允许）

def extract_from_directory(dir_path: str | Path):
    dir_path = Path(dir_path)
    all_chunks = []

    for java_file in dir_path.rglob("*.java"):
        chunks = extract_java_chunks(java_file)
        all_chunks.extend(chunks)

    return all_chunks

# ------------------ 使用示例 ------------------
if __name__ == "__main__":
    # 单文件测试
    # chunks = extract_java_chunks("src/main/java/com/example/UserService.java")

    # 整个目录
    project_dir = "/home/cheers/jagat/jagat/jagat-biz/avstream"
    chunks = extract_from_directory(project_dir)

    # 按类型 / 行号排序输出前 15 个
    chunks.sort(key=lambda c: (c.file_path, c.start_line))
    for chunk in chunks:
        print(chunk)
        print(chunk.content)  # 想看内容可打开
        print("-" * 80)