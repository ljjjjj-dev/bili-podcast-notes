"""把某一期的 OneNote 版放进 macOS 剪贴板（带格式），在 OneNote 里 Cmd+V 即可。

用法: python3 clip.py <剧集文件夹>
"""
import sys, os, subprocess

path = os.path.join(sys.argv[1], "OneNote版.html")
js = """
ObjC.import('AppKit');
function run(argv){
  const h=$.NSString.stringWithContentsOfFileEncodingError(argv[0],$.NSUTF8StringEncoding,null);
  const pb=$.NSPasteboard.generalPasteboard; pb.clearContents;
  pb.setStringForType(h,'public.html'); pb.setStringForType($('播客笔记（请在 OneNote 中粘贴）'),'public.utf8-plain-text');
  return '已放进剪贴板：' + h.length + ' 字符';
}
"""
r = subprocess.run(["osascript", "-l", "JavaScript", "-", path], input=js, capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
