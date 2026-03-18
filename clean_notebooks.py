#!/usr/bin/env python3
"""
清理 Jupyter Notebook 输出
不需要安装 jupyter，只需要 Python 标准库
"""

import json
import sys
from pathlib import Path

def clean_notebook(notebook_path):
    """清理单个 notebook 的输出"""
    try:
        # 读取 notebook
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        # 统计清理前的信息
        total_cells = len(notebook.get('cells', []))
        cells_with_output = 0

        # 清理每个 cell 的输出
        for cell in notebook.get('cells', []):
            if cell.get('cell_type') == 'code':
                # 检查是否有输出
                if cell.get('outputs') or cell.get('execution_count'):
                    cells_with_output += 1

                # 清空输出
                cell['outputs'] = []
                cell['execution_count'] = None

        # 写回文件
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, ensure_ascii=False, indent=1)

        return True, total_cells, cells_with_output

    except Exception as e:
        return False, 0, 0, str(e)

def main():
    # 查找所有 notebook 文件
    notebooks = []
    base_dir = Path(__file__).parent

    # 在指定目录中查找
    for pattern in ['**/*.ipynb']:
        for nb in base_dir.glob(pattern):
            # 排除 checkpoint 文件
            if '.ipynb_checkpoints' not in str(nb):
                notebooks.append(nb)

    if not notebooks:
        print("❌ 没有找到 Jupyter Notebook 文件")
        return 1

    print(f"📓 找到 {len(notebooks)} 个 Notebook 文件")
    print("=" * 60)

    success_count = 0
    failed_count = 0

    for notebook in notebooks:
        rel_path = notebook.relative_to(base_dir)
        print(f"\n清理: {rel_path}")

        result = clean_notebook(notebook)

        if result[0]:  # 成功
            total_cells, cells_with_output = result[1], result[2]
            print(f"  ✅ 成功")
            print(f"     总 cells: {total_cells}")
            print(f"     清理了: {cells_with_output} 个有输出的 cells")
            success_count += 1
        else:  # 失败
            error = result[3] if len(result) > 3 else "未知错误"
            print(f"  ❌ 失败: {error}")
            failed_count += 1

    print("\n" + "=" * 60)
    print(f"✅ 成功: {success_count} 个")
    if failed_count > 0:
        print(f"❌ 失败: {failed_count} 个")
    print("=" * 60)

    return 0 if failed_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
