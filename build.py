# build.py
# 使用 Nuitka 打包 DeskPet
# 运行: python build.py

import os
import sys
import subprocess

def build():
    # Nuitka 命令
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--windows-disable-console",
        "--enable-plugin=pyside6",
        "--windows-icon-from-ico=skins/default/icon.ico",
        "--include-data-dir=./skins=skins",
        "--include-data-dir=./prompts=prompts",
        "--include-data-dir=./templates=templates",
        "--include-data-dir=./hooks=hooks",
        "--include-data-dir=./systems=systems",
        "--output-filename=DeskPet.exe",
        "--output-dir=dist",
        "--company-name=MessayPet",
        "--product-name=DeskPet",
        "main.py"
    ]

    print("开始打包...")
    print(f"命令: {' '.join(cmd)}")

    result = subprocess.run(cmd)
    return result.returncode == 0

if __name__ == "__main__":
    success = build()
    if success:
        print("\n打包成功！输出目录: dist/")
    else:
        print("\n打包失败！")
        sys.exit(1)