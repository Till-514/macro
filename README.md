# Import Excellent 工具说明

这个文件夹里是几个用于扫描日志、扫描 `.mac` / `.1.bl` 配对关系、并按 CSV 结果整理文件的 Python 脚本。

所有脚本只读取或复制文件，不会修改、移动、删除源文件。

## 环境要求

需要电脑可以运行 Python 3。

在 PowerShell 里进入脚本所在目录：

```powershell
cd C:\Users\GESIC\Desktop\xuhongtao\Import_excellent
```

## 1. 提取 ImportLog 里的 Excellent 行

脚本：

```text
extract_import_excellent.py
```

用途：

从 log 文件中读取包含 `[ImportLog]` 的行，只保留结果字段为 `Excellent` 的行，并按导入文件路径去重。输出内容保持原 log 行格式。

示例：

```powershell
python .\extract_import_excellent.py C:\your\log\import.log -o import_excellent.log
```

如果要扫描一个文件夹里的所有 `.log` 文件：

```powershell
python .\extract_import_excellent.py C:\your\log_folder -o import_excellent.log
```

## 2. 扫描 `.mac` 和 `.1.bl` 是否配对

脚本：

```text
scan_mac_bl_pairs.py
scan_mac_bl_pairs_V2.py
```

用途：

扫描指定目录或文件清单，判断是否存在这种配对：

```text
M41_PRT.mac
M41_PRT.1.bl
```

匹配规则是按文件名主干判断：

```text
xxx.mac <=> xxx.1.bl
```

示例：

```powershell
python .\scan_mac_bl_pairs.py C:\your\macro_folder -o C:\your\result
```

如果脚本就在要扫描的目录下：

```powershell
python .\scan_mac_bl_pairs.py . -o .
```

输出两个 CSV：

```text
matched_mac_bl.csv
unmatched_mac_bl.csv
```

`matched_mac_bl.csv` 记录 `.mac` 和 `.1.bl` 都存在的文件。

`unmatched_mac_bl.csv` 记录只有 `.mac` 没有 `.1.bl`，或者只有 `.1.bl` 没有 `.mac` 的文件。

## 3. 根据 matched 表整理文件

脚本：

```text
collect_matched_mac_files_V2.py
```

用途：

读取 `matched_mac_bl.csv`，根据表里的 `.mac` 文件信息整理文件。

输出目录里会生成两个文件夹：

```text
output_matched
├─ macro
└─ bl
```

`macro` 文件夹会复制：

```text
cns_PRT.mac
cns_PRT.1.bl
```

`bl` 文件夹会根据 `.mac` 名字去你提供的位置查找相关模型文件。

例如：

```text
breakCorner001_PRT.mac
```

会提取关键词：

```text
breakCorner001
```

然后在 `--bl-search-dir` 目录下递归查找文件名包含 `breakCorner001` 且后缀符合规则的文件，例如：

```text
breakCorner001.Z3PRT
breakCorner001.Z3PRT.z3bak
breakCorner001_bak.SLDPRT
```

运行示例：

```powershell
python .\collect_matched_mac_files_V2.py C:\your\result\matched_mac_bl.csv -o C:\your\output_matched --bl-search-dir C:\your\bl_source
```

如果路径里有空格，要加双引号：

```powershell
python .\collect_matched_mac_files_V2.py "C:\your result\matched_mac_bl.csv" -o "C:\your output\output_matched" --bl-search-dir "C:\your bl source"
```

## 4. 根据 unmatched 表整理文件

脚本：

```text
collect_unmatched_filesV2.py
```

用途：

读取 `unmatched_mac_bl.csv`，根据表里的 `file_path` 整理未匹配文件。

输出目录里也会生成两个文件夹：

```text
output_unmatched
├─ macro
└─ bl
```

`macro` 文件夹会复制表里的 `.mac` 或 `.1.bl`，并尝试根据名字补找对应文件：

```text
xxx.mac <=> xxx.1.bl
```

`bl` 文件夹会根据文件名关键词，在 `--bl-search-dir` 里查找相关 `.Z3PRT`、`.Z3PRT.z3bak`、`.SLDPRT` 文件。

运行示例：

```powershell
python .\collect_unmatched_filesV2.py C:\your\result\unmatched_mac_bl.csv -o C:\your\output_unmatched --bl-search-dir C:\your\bl_source
```

## 5. 保留目录结构

整理脚本会保留源文件目录结构。

如果想指定从哪一层目录开始保留，可以加：

```powershell
--macro-source-root C:\your\macro_root
--bl-source-root C:\your\bl_source
```

示例：

```powershell
python .\collect_matched_mac_files_V2.py matched_mac_bl.csv -o output_matched --bl-search-dir C:\your\bl_source --macro-source-root C:\your\macro_root --bl-source-root C:\your\bl_source
```

一般情况下可以不写 `--macro-source-root` 和 `--bl-source-root`。

## 6. 增加要复制的模型后缀

如果要让整理脚本额外识别 `.zpx`，打开这两个文件：

```text
collect_matched_mac_files_V2.py
collect_unmatched_filesV2.py
```

找到这一行：

```python
MODEL_SUFFIXES = (".z3prt", ".z3prt.z3bak", ".sldprt")
```

改成：

```python
MODEL_SUFFIXES = (".z3prt", ".z3prt.z3bak", ".sldprt", ".zpx")
```

这样像下面这种文件也会被复制到输出目录的 `bl` 文件夹：

```text
breakCorner001_PRT.zpx
```

## 7. 重新运行是否会重复拷贝

重新运行脚本不会生成第二份重复文件。

如果目标位置已经有同名文件，会覆盖原文件。

需要注意：如果上一次输出目录里有文件，但这一次 CSV 里已经没有对应记录，脚本不会自动删除这些旧文件。想得到完全干净的结果，可以先删除输出目录，再重新运行。

示例：

```powershell
Remove-Item .\output_matched -Recurse -Force
```

然后重新运行整理脚本。

## 常用完整流程

先扫描 `.mac` / `.1.bl` 配对：

```powershell
python .\scan_mac_bl_pairs.py C:\your\macro_folder -o C:\your\result
```

整理 matched 文件：

```powershell
python .\collect_matched_mac_files_V2.py C:\your\result\matched_mac_bl.csv -o C:\your\output_matched --bl-search-dir C:\your\bl_source
```

整理 unmatched 文件：

```powershell
python .\collect_unmatched_filesV2.py C:\your\result\unmatched_mac_bl.csv -o C:\your\output_unmatched --bl-search-dir C:\your\bl_source
```
