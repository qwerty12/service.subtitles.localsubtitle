# -*- coding: utf-8 -*-

# Adapted by ChatGPT from https://github.com/SubtitleEdit/subtitleedit
# Licensed under the GPL v3. Copyright 2001-2024, Nikse

def remove_ass_alignment_tags(s: str) -> str:
    return (s.replace("{\\an1}", "")  # ASS tags alone
              .replace("{\\an2}", "")
              .replace("{\\an3}", "")
              .replace("{\\an4}", "")
              .replace("{\\an5}", "")
              .replace("{\\an6}", "")
              .replace("{\\an7}", "")
              .replace("{\\an8}", "")
              .replace("{\\an9}", "")

              .replace("{an1\\", "{")  # ASS multi tags (start)
              .replace("{an2\\", "{")
              .replace("{an3\\", "{")
              .replace("{an4\\", "{")
              .replace("{an5\\", "{")
              .replace("{an6\\", "{")
              .replace("{an7\\", "{")
              .replace("{an8\\", "{")
              .replace("{an9\\", "{")

              .replace("\\an1\\", "\\")  # ASS multi tags (middle)
              .replace("\\an2\\", "\\")
              .replace("\\an3\\", "\\")
              .replace("\\an4\\", "\\")
              .replace("\\an5\\", "\\")
              .replace("\\an6\\", "\\")
              .replace("\\an7\\", "\\")
              .replace("\\an8\\", "\\")
              .replace("\\an9\\", "\\")

              .replace("\\an1}", "}")  # ASS multi tags (end)
              .replace("\\an2}", "}")
              .replace("\\an3}", "}")
              .replace("\\an4}", "}")
              .replace("\\an5}", "}")
              .replace("\\an6}", "}")
              .replace("\\an7}", "}")
              .replace("\\an8}", "}")
              .replace("\\an9}", "}")

              .replace("{\\a1}", "")  # SSA tags
              .replace("{\\a2}", "")
              .replace("{\\a3}", "")
              .replace("{\\a4}", "")
              .replace("{\\a5}", "")
              .replace("{\\a6}", "")
              .replace("{\\a7}", "")
              .replace("{\\a8}", "")
              .replace("{\\a9}", ""))

def strip_position_tags(subs):
    for line in subs:
        if '{' in line.text:
            line.text = remove_ass_alignment_tags(line.text)

